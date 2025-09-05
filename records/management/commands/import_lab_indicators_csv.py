import csv
import io
from pathlib import Path
from typing import Iterable

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify
from parler.utils.context import switch_language

from records.models import LabIndicator, LabIndicatorAlias, get_indicator_canonical_tag


SEPS = [",", ";", "|", "/"]


def _split_aliases(val: str) -> list[str]:
    if not val:
        return []
    s = val
    for sep in SEPS[1:]:
        s = s.replace(sep, SEPS[0])
    parts = [p.strip() for p in s.split(SEPS[0])]
    return [p for p in parts if p]


def _detect_encoding(path: Path) -> str:
    encs = ["utf-8-sig", "utf-8", "cp1251", "cp1250", "windows-1252", "iso-8859-1"]
    raw = path.read_bytes()
    for enc in encs:
        try:
            raw.decode(enc)
            return enc
        except Exception:
            continue
    return "iso-8859-1"


def _float_or_none(x):
    if x in (None, ""):
        return None
    try:
        return float(str(x).replace(",", "."))
    except Exception:
        return None


def _unique_slug_for_indicator(base_text: str | None) -> str:

    from uuid import uuid4

    base = (base_text or "").strip()
    s = slugify(base)[:255] if base else ""
    if not s:

        s = f"indicator-{uuid4().hex[:12]}"

    candidate = s
    idx = 1
    while LabIndicator.objects.filter(slug=candidate).exists():

        suffix = f"-{idx}"
        candidate = f"{s[: max(0, 255 - len(suffix))]}{suffix}"
        idx += 1
        if idx > 9999:

            candidate = f"{s[:242]}-{uuid4().hex[:12]}"
            break
    return candidate


class Command(BaseCommand):
    help = (
        "Import or update LabIndicator rows and aliases from CSV. "
        "Auto-detects encoding/delimiter. Accepts multiple header aliases, incl.:\n"
        "- name_en/name_bg OR 'Standard Name - Full'/'Standard Name - Abbrev'\n"
        "- any number of 'Abbrev' columns (treated as aliases)\n"
        "- any number of 'UNITS' columns (first non-empty used)\n"
        "- REF LOW/HIGH (generic) or REF LOW/HIGH MALE/FEMALE (gendered)"
    )

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Path to CSV file")
        parser.add_argument("--update", action="store_true", default=False, help="Update existing indicators if found")

    @transaction.atomic
    def handle(self, *args, **opts):
        p = Path(opts["csv_path"])
        if not p.exists():
            raise CommandError(f"CSV not found: {p}")

        enc = _detect_encoding(p)
        raw = p.read_bytes()
        text = raw.decode(enc, errors="replace")

        sample = text[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";,|\t,")
        except Exception:
            dialect = csv.excel
            dialect.delimiter = ","

        f = io.StringIO(text)
        reader = csv.DictReader(f, dialect=dialect)
        if not reader.fieldnames:
            raise CommandError("CSV has no header.")

        headers_lower = [h.strip().lower() for h in reader.fieldnames]
        header_map = {h.strip().lower(): h for h in reader.fieldnames}

        def col_first(names: Iterable[str]) -> str | None:
            for n in names:
                key = n.strip().lower()
                if key in header_map:
                    return header_map[key]
            return None

        def cols_all(contains: Iterable[str]) -> list[str]:
            tokens = [t.lower() for t in contains]
            out: list[str] = []
            for i, low in enumerate(headers_lower):
                if all(t in low for t in tokens):
                    out.append(reader.fieldnames[i])
            return out

        name_bg_col = col_first(["name_bg", "bg", "namebg"])
        name_en_col = col_first(["name_en", "en", "nameen"])
        std_name_full = col_first(["standard name - full"])
        std_name_abbrev = col_first(["standard name - abbrev"])

        abbrev_cols = cols_all(["abbrev"])

        unit_cols = [c for c in reader.fieldnames if "units" in c.strip().lower()]

        category_col = col_first(["category"])

        ref_low_generic = col_first(["reference_low", "ref_low", "low"])
        ref_high_generic = col_first(["reference_high", "ref_high", "high"])
        ref_low_male = col_first(["ref low male"])
        ref_high_male = col_first(["ref high male"])
        ref_low_female = col_first(["ref low female"])
        ref_high_female = col_first(["ref high female"])

        if not (name_bg_col or name_en_col or std_name_full or std_name_abbrev):
            raise CommandError(
                "CSV must contain at least one of: name_bg, name_en, 'Standard Name - Full', 'Standard Name - Abbrev'."
            )

        created = 0
        updated = 0
        alias_new = 0
        alias_conflict = 0

        for row in reader:

            name_bg = (row.get(name_bg_col) or "").strip() if name_bg_col else ""
            name_en = (row.get(name_en_col) or "").strip() if name_en_col else ""

            if not name_en and std_name_full:
                name_en = (row.get(std_name_full) or "").strip()
            if not name_en and std_name_abbrev:
                name_en = (row.get(std_name_abbrev) or "").strip()

            if not (name_bg or name_en):
                continue

            alias_values: list[str] = []
            for c in abbrev_cols:
                v = (row.get(c) or "").strip()
                if v:
                    alias_values.append(v)

            aliases_col = col_first(["aliases", "alias", "aka"])
            if aliases_col:
                alias_values += _split_aliases(row.get(aliases_col) or "")

            unit = ""
            for c in unit_cols:
                v = (row.get(c) or "").strip()
                if v:
                    unit = v
                    break

            _category = (row.get(category_col) or "").strip() if category_col else ""

            low = (row.get(ref_low_generic) or "").strip() if ref_low_generic else ""
            high = (row.get(ref_high_generic) or "").strip() if ref_high_generic else ""
            if not low:
                low = (row.get(ref_low_male) or "").strip() if ref_low_male else ""
            if not low:
                low = (row.get(ref_low_female) or "").strip() if ref_low_female else ""
            if not high:
                high = (row.get(ref_high_male) or "").strip() if ref_high_male else ""
            if not high:
                high = (row.get(ref_high_female) or "").strip() if ref_high_female else ""

            low_f = _float_or_none(low)
            high_f = _float_or_none(high)

            q = LabIndicator.objects.all()
            ind = None
            if name_bg:
                ind = q.filter(translations__name__iexact=name_bg).first()
            if not ind and name_en:
                ind = q.filter(translations__name__iexact=name_en).first()

            if not ind:
                base_for_slug = name_en or name_bg
                slug_val = _unique_slug_for_indicator(base_for_slug)

                ind = LabIndicator.objects.create(unit=unit or "", slug=slug_val)
                if low_f is not None:
                    ind.reference_low = low_f
                if high_f is not None:
                    ind.reference_high = high_f
                ind.save()

                if name_bg:
                    with switch_language(ind, "bg"):
                        ind.name = name_bg
                        ind.save()
                if name_en:
                    with switch_language(ind, "en-us"):
                        ind.name = name_en
                        ind.save()

                created += 1
            else:
                if opts["update"]:
                    changed = False
                    if unit and ind.unit != unit:
                        ind.unit = unit
                        changed = True
                    if low_f is not None and ind.reference_low != low_f:
                        ind.reference_low = low_f
                        changed = True
                    if high_f is not None and ind.reference_high != high_f:
                        ind.reference_high = high_f
                        changed = True
                    if changed:
                        ind.save()

                    if name_bg:
                        with switch_language(ind, "bg"):
                            if ind.name != name_bg:
                                ind.name = name_bg
                                ind.save()
                    if name_en:
                        with switch_language(ind, "en-us"):
                            if ind.name != name_en:
                                ind.name = name_en
                                ind.save()
                    updated += 1

            for a in alias_values:
                key = (a or "").strip()
                if not key:
                    continue
                norm = slugify(key)[:255]

                existing = LabIndicatorAlias.objects.filter(alias_norm=norm).first()
                if existing:
                    if existing.indicator_id != ind.id:
                        alias_conflict += 1

                    continue

                LabIndicatorAlias.objects.create(indicator=ind, alias_raw=key)
                alias_new += 1

            get_indicator_canonical_tag(ind)

        self.stdout.write(
            self.style.SUCCESS(
                f"Detected encoding={enc}; Indicators created={created} updated={updated} "
                f"aliases_added={alias_new} alias_conflicts_skipped={alias_conflict}"
            )
        )
