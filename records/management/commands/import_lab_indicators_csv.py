import csv
import io
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from parler.utils.context import switch_language
from records.models import LabIndicator, LabIndicatorAlias, get_indicator_canonical_tag

SEPS = [",", ";", "|", "/"]

def split_aliases(val: str):
    if not val:
        return []
    s = val
    for sep in SEPS[1:]:
        s = s.replace(sep, SEPS[0])
    parts = [p.strip() for p in s.split(SEPS[0])]
    return [p for p in parts if p]

def detect_encoding(path: Path) -> str:
    tried = []
    encs = ["utf-8-sig", "utf-8", "cp1251", "cp1250", "windows-1252", "iso-8859-1"]
    raw = path.read_bytes()
    for enc in encs:
        try:
            raw.decode(enc)
            return enc
        except Exception:
            tried.append(enc)
            continue
    return "iso-8859-1"

class Command(BaseCommand):
    help = "Import or update LabIndicator rows and aliases from CSV (auto-detect encoding and delimiter)."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str)
        parser.add_argument("--update", action="store_true", default=False)

    @transaction.atomic
    def handle(self, *args, **opts):
        p = Path(opts["csv_path"])
        if not p.exists():
            raise CommandError(f"CSV not found: {p}")

        enc = detect_encoding(p)
        raw = p.read_bytes()
        text = raw.decode(enc, errors="replace")

        sample = text[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";,|\t,")
        except Exception:
            dialect = csv.excel
            dialect.delimiter = ";"

        f = io.StringIO(text)
        reader = csv.DictReader(f, dialect=dialect)
        headers = {h.strip().lower(): h for h in (reader.fieldnames or [])}

        def col(*names):
            for n in names:
                if n in headers:
                    return headers[n]
            return None

        col_bg = col("name_bg", "bg", "namebg", "name")
        col_en = col("name_en", "en", "nameen")
        col_unit = col("unit", "units")
        col_low = col("reference_low", "ref_low", "low")
        col_high = col("reference_high", "ref_high", "high")
        col_alias = col("aliases", "alias", "aka")

        if not col_bg and not col_en:
            raise CommandError("CSV must contain column name_bg or name_en")

        updated = 0
        created = 0
        alias_new = 0

        for row in reader:
            name_bg = (row.get(col_bg) or "").strip() if col_bg else ""
            name_en = (row.get(col_en) or "").strip() if col_en else ""
            unit = (row.get(col_unit) or "").strip() if col_unit else ""
            low = row.get(col_low) if col_low else None
            high = row.get(col_high) if col_high else None
            aliases = split_aliases(row.get(col_alias) or "") if col_alias else []

            q = LabIndicator.objects.all()
            found = None
            if name_bg:
                found = q.filter(translations__name__iexact=name_bg).first()
            if not found and name_en:
                found = q.filter(translations__name__iexact=name_en).first()

            ind = found
            if ind and opts["update"]:
                if unit:
                    ind.unit = unit
                if low not in (None, ""):
                    try:
                        ind.reference_low = float(str(low).replace(",", "."))
                    except Exception:
                        pass
                if high not in (None, ""):
                    try:
                        ind.reference_high = float(str(high).replace(",", "."))
                    except Exception:
                        pass
                ind.save()
                if name_bg:
                    with switch_language(ind, "bg"):
                        ind.name = name_bg
                        ind.save()
                if name_en:
                    with switch_language(ind, "en-us"):
                        ind.name = name_en
                        ind.save()
                updated += 1

            if not ind:
                ind = LabIndicator.objects.create(unit=unit or "")
                if low not in (None, ""):
                    try:
                        ind.reference_low = float(str(low).replace(",", "."))
                    except Exception:
                        pass
                if high not in (None, ""):
                    try:
                        ind.reference_high = float(str(high).replace(",", "."))
                    except Exception:
                        pass
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

            for a in aliases:
                key = a.strip()
                if not key:
                    continue
                obj, made = LabIndicatorAlias.objects.get_or_create(indicator=ind, alias=key.lower())
                if made:
                    alias_new += 1

            get_indicator_canonical_tag(ind)

        self.stdout.write(self.style.SUCCESS(
            f"Detected encoding={enc}; Indicators created={created} updated={updated} aliases={alias_new}"
        ))
