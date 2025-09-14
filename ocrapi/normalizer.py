import os
import csv
import re
from pathlib import Path
from rapidfuzz import process, fuzz

UNIT_ALIASES = {
    "g/dl": "g/dL","mg/dl": "mg/dL","μg/dl": "µg/dL","ug/dl": "µg/dL","µg/dl": "µg/dL",
    "ng/ml": "ng/mL","pg/ml": "pg/mL","ng/dl": "ng/dL","iu/l": "IU/L","miu/l": "mIU/L",
    "miv/l": "mIU/L","m1u/l": "mIU/L","mlu/l": "mIU/L","u/l": "U/L","ku/l": "kU/L",
    "mmol/l": "mmol/L","mol/l": "mol/L","meq/l": "mEq/L","µmol/l": "µmol/L","μmol/l": "µmol/L",
    "umol/l": "µmol/L","nmol/l": "nmol/L","pmol/l": "pmol/L","fl": "fL","µl": "µL","μl": "µL",
    "ul": "µL","pg": "pg","%": "%","‰": "‰","x10^3/μl": "×10^3/µL","x10^3/ul": "×10^3/µL",
    "x10e3/μl": "×10^3/µL","x10.e3/μl": "×10^3/µL","x10^6/μl": "×10^6/µL","x10^6/ul": "×10^6/µL",
    "10^3/µl": "×10^3/µL","10^6/µl": "×10^6/µL"
}

EXP_RE = [
    (re.compile(r"(?i)\b(?:x|×)?\s*10[\.e\^ ]*3\s*/\s*(?:µ|μ|u)?l\b"), "×10^3/µL"),
    (re.compile(r"(?i)\b(?:x|×)?\s*10[\.e\^ ]*6\s*/\s*(?:µ|μ|u)?l\b"), "×10^6/µL"),
]

_UNIT_TOKEN_RE = re.compile(r"(?:[A-Za-zµμu%‰\^0-9\.\-]+/[A-Za-zµμuL]+|×10\^3/µL|×10\^6/µL|fL|pg|%|‰)")

_ALIAS_MAP = {}

def _canon_unit(token: str) -> str:
    t0 = token.strip().replace("μ","µ")
    t = t0.lower()
    if t in UNIT_ALIASES: return UNIT_ALIASES[t]
    for rgx, rep in EXP_RE:
        if rgx.fullmatch(t0): return rep
    return t0

def _sanitize_units_inline(text: str) -> str:
    t = text
    for rgx, rep in EXP_RE: t = rgx.sub(rep, t)
    t = re.sub(r"(?i)\bg/?d[lL]\b","g/dL",t)
    t = re.sub(r"(?i)\bmg/?d[lL]\b","mg/dL",t)
    t = re.sub(r"(?i)\b(?:µ|μ|u)g/?d[lL]\b","µg/dL",t)
    t = re.sub(r"(?i)\bng/?m[lL]\b","ng/mL",t)
    t = re.sub(r"(?i)\bpg/?m[lL]\b","pg/mL",t)
    t = re.sub(r"(?i)\b[mM][iI1l][uU]/[lL]\b","mIU/L",t)
    t = re.sub(r"(?i)\b[iI][uU]/[lL]\b","IU/L",t)
    t = t.replace(" o/oo "," ‰ ")
    return t

def _open_csv_reader(csv_path: str):
    p = Path(csv_path)
    if not p.exists(): return None, None, None
    encodings = ["utf-8-sig","utf-8","cp1251","windows-1252","latin1","iso-8859-1"]
    for enc in encodings:
        try:
            f = p.open("r", encoding=enc, newline="")
            r = csv.DictReader(f)
            _ = r.fieldnames
            return f, r, enc
        except UnicodeDecodeError:
            continue
    f = p.open("r", encoding="utf-8", errors="ignore", newline="")
    r = csv.DictReader(f)
    return f, r, "utf-8/ignore"

def _num(x: str):
    x = (x or "").strip()
    if not x: return None
    x = x.replace(",", ".")
    try: return float(x)
    except Exception: return None

def load_lab_db(csv_path: str):
    global _ALIAS_MAP
    names, units = [], {}
    _ALIAS_MAP = {}
    if not csv_path: return names, units
    f, r, _ = _open_csv_reader(csv_path)
    if not r: return names, units
    with f:
        fields = r.fieldnames or []
        cols = {c.lower(): c for c in fields}
        k_full = (cols.get("standard name - full") or cols.get("name") or cols.get("indicator_name")
                  or cols.get("indicator") or cols.get("analyte") or cols.get("test") or cols.get("display_name"))
        abbr_keys = [c for c in fields if c.lower() in {"standard name - abbrev","abbrev"} or c.lower().startswith("abbrev")]
        unit_keys = [c for c in fields if c.lower() in {"unit","units","unit_name"} or c.lower().startswith("units")]
        for row in r:
            full = (row.get(k_full) or "").strip() if k_full else ""
            tokens = set()
            if full:
                full = re.sub(r"\s{2,}"," ",full)
                tokens.add(full)
            for k in abbr_keys:
                v = (row.get(k) or "").strip()
                if v: tokens.add(re.sub(r"\s{2,}"," ",v))
            unit_val = ""
            for uk in unit_keys:
                u = (row.get(uk) or "").strip()
                if u: unit_val = u; break
            if not tokens: continue
            for t in tokens:
                names.append(t)
                _ALIAS_MAP[t] = full or t
                if unit_val: units[t] = _canon_unit(unit_val)
    names = sorted(set(names))
    return names, units

def load_lab_refs(csv_path: str):
    refs = {}
    f, r, _ = _open_csv_reader(csv_path)
    if not r: return refs
    fields = r.fieldnames or []
    cols = {c.lower(): c for c in fields}
    k_full = (cols.get("standard name - full") or cols.get("name") or cols.get("indicator_name")
              or cols.get("indicator") or cols.get("analyte") or cols.get("test") or cols.get("display_name"))
    male_low = (cols.get("ref low male") or cols.get("male low") or cols.get("ref_low_male") or cols.get("low male"))
    male_high = (cols.get("ref high male") or cols.get("male high") or cols.get("ref_high_male") or cols.get("high male"))
    female_low = (cols.get("ref low female") or cols.get("female low") or cols.get("ref_low_female") or cols.get("low female"))
    female_high = (cols.get("ref high female") or cols.get("female high") or cols.get("ref_high_female") or cols.get("high female"))
    unit_key = (cols.get("units") or cols.get("unit") or cols.get("unit_name"))
    with f:
        for row in r:
            name = (row.get(k_full) or "").strip() if k_full else ""
            if not name: continue
            name = re.sub(r"\s{2,}"," ",name)
            unit = _canon_unit((row.get(unit_key) or "").strip()) if unit_key else ""
            mlo = _num(row.get(male_low) or "") if male_low else None
            mhi = _num(row.get(male_high) or "") if male_high else None
            flo = _num(row.get(female_low) or "") if female_low else None
            fhi = _num(row.get(female_high) or "") if female_high else None
            refs[name] = {"unit": unit or None, "male": (mlo, mhi), "female": (flo, fhi)}
    return refs

def normalize_indicator(token: str, names: list[str]) -> str:
    if not token or not names: return token
    hit = process.extractOne(token, names, scorer=fuzz.WRatio)
    if not hit or hit[1] < 86: return token
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
            match_token = normalize_indicator(head_clean, names)
            canon = _ALIAS_MAP.get(match_token, match_token)
            if canon and canon != head:
                line = line.replace(head, canon, 1)
            target_unit = unit_map.get(canon) or unit_map.get(match_token)
            if target_unit and re.search(r"[A-Za-zµ/%‰]", line) and target_unit not in line:
                line = re.sub(
                    r"(g/dL|mg/dL|µg/dL|ng/mL|pg/Ml|pg/mL|IU/L|mIU/L|U/L|kU/L|mmol/L|mol/L|mEq/L|µmol/L|nmol/L|pmol/L|×10\^3/µL|×10\^6/µL|fL|pg|%|‰)",
                    target_unit,
                    line,
                    count=1,
                )
        out.append(line)
    return "\n".join(out).strip()
