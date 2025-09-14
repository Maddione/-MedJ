import os
import csv
import re
from pathlib import Path
from rapidfuzz import process, fuzz

UNIT_ALIASES = {
    "g/dl": "g/dL",
    "mg/dl": "mg/dL",
    "μg/dl": "µg/dL",
    "ug/dl": "µg/dL",
    "µg/dl": "µg/dL",
    "ng/ml": "ng/mL",
    "pg/ml": "pg/mL",
    "ng/dl": "ng/dL",
    "iu/l": "IU/L",
    "miu/l": "mIU/L",
    "miv/l": "mIU/L",
    "m1u/l": "mIU/L",
    "mlu/l": "mIU/L",
    "u/l": "U/L",
    "ku/l": "kU/L",
    "mmol/l": "mmol/L",
    "mol/l": "mol/L",
    "meq/l": "mEq/L",
    "µmol/l": "µmol/L",
    "μmol/l": "µmol/L",
    "umol/l": "µmol/L",
    "nmol/l": "nmol/L",
    "pmol/l": "pmol/L",
    "fl": "fL",
    "µl": "µL",
    "μl": "µL",
    "ul": "µL",
    "pg": "pg",
    "%": "%",
    "‰": "‰",
    "x10^3/μl": "×10^3/µL",
    "x10^3/ul": "×10^3/µL",
    "x10e3/μl": "×10^3/µL",
    "x10.e3/μl": "×10^3/µL",
    "x10^6/μl": "×10^6/µL",
    "x10^6/ul": "×10^6/µL",
    "10^3/µl": "×10^3/µL",
    "10^6/µl": "×10^6/µL",
}

EXP_RE = [
    (re.compile(r"(?i)\b(?:x|×)?\s*10[\.e\^ ]*3\s*/\s*(?:µ|μ|u)?l\b"), "×10^3/µL"),
    (re.compile(r"(?i)\b(?:x|×)?\s*10[\.e\^ ]*6\s*/\s*(?:µ|μ|u)?l\b"), "×10^6/µL"),
]

_UNIT_TOKEN_RE = re.compile(
    r"(?:[A-Za-zµμu%‰\^0-9\.\-]+/[A-Za-zµμuL]+|×10\^3/µL|×10\^6/µL|fL|pg|%|‰)"
)

def _canon_unit(token: str) -> str:
    t0 = token.strip().replace("μ", "µ")
    t = t0.lower()
    if t in UNIT_ALIASES:
        return UNIT_ALIASES[t]
    for rgx, rep in EXP_RE:
        if rgx.fullmatch(t0):
            return rep
    return t0

def _sanitize_units_inline(text: str) -> str:
    t = text
    for rgx, rep in EXP_RE:
        t = rgx.sub(rep, t)
    t = re.sub(r"(?i)\bg/?d[lL]\b", "g/dL", t)
    t = re.sub(r"(?i)\bmg/?d[lL]\b", "mg/dL", t)
    t = re.sub(r"(?i)\b(?:µ|μ|u)g/?d[lL]\b", "µg/dL", t)
    t = re.sub(r"(?i)\bng/?m[lL]\b", "ng/mL", t)
    t = re.sub(r"(?i)\bpg/?m[lL]\b", "pg/mL", t)
    t = re.sub(r"(?i)\b[mM][iI1l][uU]/[lL]\b", "mIU/L", t)
    t = re.sub(r"(?i)\b[iI][uU]/[lL]\b", "IU/L", t)
    t = t.replace(" o/oo ", " ‰ ")
    return t

def _open_csv_reader(csv_path: str):
    encodings = ["utf-8-sig", "utf-8", "cp1251", "windows-1252", "latin1", "iso-8859-1"]
    p = Path(csv_path)
    if not p.exists():
        return None, None
    for enc in encodings:
        try:
            f = p.open("r", encoding=enc, newline="")
            r = csv.DictReader(f)
            # force header read to validate encoding
            _ = r.fieldnames
            return f, r
        except UnicodeDecodeError:
            continue
        except Exception:
            if 'f' in locals():
                f.close()
            break
    f = p.open("r", encoding="utf-8", errors="ignore", newline="")
    r = csv.DictReader(f)
    return f, r

def load_lab_db(csv_path: str):
    names = []
    units = {}
    if not csv_path:
        return names, units
    f, r = _open_csv_reader(csv_path)
    if not r:
        return names, units
    with f:
        fieldnames = r.fieldnames or []
        cols = {c.lower(): c for c in fieldnames}
        k_name = (
            cols.get("indicator_name")
            or cols.get("indicator")
            or cols.get("analyte")
            or cols.get("test")
            or cols.get("name")
            or cols.get("display_name")
        )
        k_unit = cols.get("unit") or cols.get("units") or cols.get("unit_name")
        for row in r:
            get = row.get
            n = (get(k_name) or "").strip() if k_name else ""
            if not n:
                continue
            n = re.sub(r"\s{2,}", " ", n)
            names.append(n)
            if k_unit:
                u = (get(k_unit) or "").strip()
                if u:
                    units[n] = _canon_unit(u)
    names = sorted(set(names))
    return names, units

def normalize_indicator(token: str, names: list[str]) -> str:
    if not token or not names:
        return token
    hit = process.extractOne(token, names, scorer=fuzz.WRatio)
    if not hit or hit[1] < 86:
        return token
    return hit[0]

def normalize_units_in_line(line: str) -> str:
    line2 = _sanitize_units_inline(line)
    for raw in set(_UNIT_TOKEN_RE.findall(line2)):
        line2 = line2.replace(raw, _canon_unit(raw))
    return line2

def normalize_ocr_text(text: str, csv_path: str) -> str:
    names, unit_map = load_lab_db(csv_path)
    out = []
    for raw in (text or "").splitlines():
        line = normalize_units_in_line(raw)
        parts = re.split(r"\s{2,}|\t", line.strip())
        if parts:
            head = parts[0]
            head_clean = re.sub(r"[^A-Za-zА-Яа-я0-9\-\+\%/µ\.]", " ", head).strip()
            head_norm = normalize_indicator(head_clean, names)
            if head_norm and head_norm != head:
                line = line.replace(head, head_norm, 1)
            if head_norm in unit_map and re.search(r"[A-Za-zµ/%‰]", line):
                target = re.escape(unit_map[head_norm])
                line = re.sub(
                    r"(g/dL|mg/dL|µg/dL|ng/mL|pg/mL|IU/L|mIU/L|U/L|kU/L|mmol/L|mol/L|mEq/L|µmol/L|nmol/L|pmol/L|×10\^3/µL|×10\^6/µL|fL|pg|%|‰)",
                    unit_map[head_norm],
                    line,
                    count=1,
                )
        out.append(line)
    return "\n".join(out).strip()
