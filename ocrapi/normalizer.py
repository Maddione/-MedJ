import os
import csv
import re
from rapidfuzz import process, fuzz

UNIT_ALIASES = {
    "g/dl":"g/dL",
    "mg/dl":"mg/dL",
    "μg/dl":"µg/dL",
    "ug/dl":"µg/dL",
    "µg/dl":"µg/dL",
    "ng/ml":"ng/mL",
    "pg/ml":"pg/mL",
    "ng/dl":"ng/dL",
    "iu/l":"IU/L",
    "miu/l":"mIU/L",
    "miv/l":"mIU/L",
    "m1u/l":"mIU/L",
    "mlu/l":"mIU/L",
    "u/l":"U/L",
    "ku/l":"kU/L",
    "mmol/l":"mmol/L",
    "mol/l":"mol/L",
    "meq/l":"mEq/L",
    "µmol/l":"µmol/L",
    "μmol/l":"µmol/L",
    "umol/l":"µmol/L",
    "nmol/l":"nmol/L",
    "pmol/l":"pmol/L",
    "fl":"fL",
    "µl":"µL",
    "μl":"µL",
    "ul":"µL",
    "pg":"pg",
    "%":"%",
    "‰":"‰",
    "x10^3/μl":"×10^3/µL",
    "x10^3/ul":"×10^3/µL",
    "x10e3/μl":"×10^3/µL",
    "x10.e3/μl":"×10^3/µL",
    "x10^6/μl":"×10^6/µL",
    "x10^6/ul":"×10^6/µL",
    "10^3/µl":"×10^3/µL",
    "10^6/µl":"×10^6/µL"
}

EXP_RE = [
    (re.compile(r"(?i)x?\s*10[\.e\^ ]*3\s*/\s*(?:µ|μ|u)?l"), "×10^3/µL"),
    (re.compile(r"(?i)x?\s*10[\.e\^ ]*6\s*/\s*(?:µ|μ|u)?l"), "×10^6/µL")
]

def _canon_unit(token):
    t0 = token.strip().replace("μ","µ")
    t = t0.lower()
    if t in UNIT_ALIASES:
        return UNIT_ALIASES[t]
    for rgx, rep in EXP_RE:
        if rgx.fullmatch(t0):
            return rep
    return t0

def _sanitize_units_inline(text):
    t = text
    for rgx, rep in EXP_RE:
        t = re.sub(rgx, rep, t)
    t = re.sub(r"(?i)µ?g/?d[lL]", "g/dL", t)
    t = re.sub(r"(?i)mg/?d[lL]", "mg/dL", t)
    t = re.sub(r"(?i)(?:µ|μ|u)g/?d[lL]", "µg/dL", t)
    t = re.sub(r"(?i)ng/?m[lL]", "ng/mL", t)
    t = re.sub(r"(?i)pg/?m[lL]", "pg/mL", t)
    t = re.sub(r"(?i)[mM][iI1l][uU]/[lL]", "mIU/L", t)
    t = re.sub(r"(?i)[iI][uU]/[lL]", "IU/L", t)
    t = t.replace(" o/oo ", " ‰ ")
    return t

def load_lab_db(csv_path):
    names = []
    units = {}
    if not csv_path or not os.path.exists(csv_path):
        return names, units
    with open(csv_path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        cols = {c.lower(): c for c in r.fieldnames}
        k_name = cols.get("indicator_name") or cols.get("test") or cols.get("name") or list(cols.values())[0]
        k_unit = cols.get("unit") or cols.get("units")
        for row in r:
            n = (row.get(k_name) or "").strip()
            if not n:
                continue
            names.append(n)
            if k_unit:
                u = (row.get(k_unit) or "").strip()
                if u:
                    units[n] = _canon_unit(u)
    return names, units

def normalize_indicator(token, names):
    if not token or not names:
        return token
    hit = process.extractOne(token, names, scorer=fuzz.WRatio)
    if not hit or hit[1] < 86:
        return token
    return hit[0]

def normalize_units_in_line(line):
    line2 = _sanitize_units_inline(line)
    matches = re.findall(r"([A-Za-zµμu/%\^0-9\.\-]+/[A-Za-zµμuL]+|×10\^3/µL|×10\^6/µL|fL|pg|%)", line2)
    for raw in set(matches):
        line2 = line2.replace(raw, _canon_unit(raw))
    return line2

def normalize_ocr_text(text, csv_path):
    names, unit_map = load_lab_db(csv_path)
    out = []
    for raw in text.splitlines():
        line = normalize_units_in_line(raw)
        parts = re.split(r"\s{2,}|\t", line.strip())
        if parts:
            head = parts[0]
            head_clean = re.sub(r"[^A-Za-zА-Яа-я0-9\-\+\%/µ\.]", " ", head).strip()
            head_norm = normalize_indicator(head_clean, names)
            if head_norm and head_norm != head:
                line = line.replace(head, head_norm, 1)
            if head_norm in unit_map and re.search(r"[A-Za-zµ/%]", line) and unit_map[head_norm] not in line:
                line = re.sub(r"(g/dL|mg/dL|µg/dL|ng/mL|pg/mL|IU/L|mIU/L|U/L|kU/L|mmol/L|mol/L|mEq/L|µmol/L|nmol/L|pmol/L|×10\^3/µL|×10\^6/µL|fL|pg|%|‰)",
                              unit_map[head_norm], line)
        out.append(line)
    return "\n".join(out).strip()
