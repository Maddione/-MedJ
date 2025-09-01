import re
import unicodedata

CANONICAL_INDICATORS = {
    "hemoglobin":   [r"\b(hb|hgb|hemoglobin|haemoglobin|хемоглобин)\b"],
    "hematocrit":   [r"\b(hct|ht|hematocrit|haematocrit|хематокрит)\b"],
    "rbc":          [r"\b(rbc|erythrocytes?|еритроцит[аи])\b"],
    "wbc":          [r"\b(wbc|leukocytes?|leucocytes?|левкоцит[аи])\b"],
    "platelets":    [r"\b(plt|platelets?|thrombocytes?|тромбоцит[аи])\b"],
    "mcv":          [r"\b(mcv)\b"],
    "mch":          [r"\b(mch)\b"],
    "mchc":         [r"\b(mchc)\b"],
    "rdw":          [r"\b(rdw)\b"],
    "mpv":          [r"\b(mpv)\b"],
    "pct":          [r"\b(pct)\b"],
    "pdw":          [r"\b(pdw)\b"],
    "neutrophils":  [r"\b(neu|neutrophils?|неутрофил[аи])\b"],
    "lymphocytes":  [r"\b(lym|lymphocytes?|лимфоцит[аи])\b"],
    "monocytes":    [r"\b(mon|monocytes?|моноцит[аи])\b"],
    "eosinophils":  [r"\b(eos|eosinophils?|еозинофил[аи])\b"],
    "basophils":    [r"\b(bas|basophils?|базофил[аи])\b"],

    "glucose":      [r"\b(glucose|глюкоза)\b"],
    "chol_total":   [r"\b(total\s*chol(esterol)?|общ(.*)холестерол)\b"],
    "ldl":          [r"\b(ldl)\b"],
    "hdl":          [r"\b(hdl)\b"],
    "triglycerides":[r"\b(triglycerides?|триглицерид[аи])\b"],

    "tsh":          [r"\b(tsh)\b"],
    "ft4":          [r"\b(ft-?4|free\s*t4)\b"],
    "ft3":          [r"\b(ft-?3|free\s*t3)\b"],

    "hba1c":        [r"\b(hb\s*a1c|hba1c|гликиран(.*)хемоглобин)\b"],

    "crp":          [r"\b(crp|c-?reactive\s*protein|с-?реактивен(.*)протеин)\b"],
    "esr":          [r"\b(esr|erythrocyte\s*sedimentation\s*rate|суе|скорост.*утаяване)\b"],

    "creatinine":   [r"\b(creatinine|креатинин)\b"],
    "urea":         [r"\b(urea|карбамид|урея)\b"],
    "uric_acid":    [r"\b(uric\s*acid|пикочна\s*киселина)\b"],

    "alt":          [r"\b(alt|sgpt|аланин(.*)трансаминаза)\b"],
    "ast":          [r"\b(ast|sgot|аспартат(.*)трансаминаза)\b"],
    "ggt":          [r"\b(ggt|гама-?глутамил(.*)трансфераза)\b"],
    "alp":          [r"\b(alp|alkaline\s*phosphatase|алкална(.*)фосфатаза)\b"],
    "bilirubin_total":[r"\b(total\s*bilirubin|общ(.*)билирубин)\b"],

    "ferritin":     [r"\b(ferritin|феритин)\b"],
    "iron":         [r"\b(iron|serum\s*iron|желязо)\b"],
    "transferrin":  [r"\b(transferrin|трансферин)\b"],
    "tibc":         [r"\b(tibc|total\s*iron\s*binding\s*capacity|общ(.*)желязо.*свързващ)\b"],

    "vitamin_d":    [r"\b(25\(oh\)d|vit(amin)?\s*d|витамин\s*d)\b"],

    "inr":          [r"\b(inr)\b"],
    "pt":           [r"\b(pt|prothrombin\s*time)\b"],
    "aptt":         [r"\b(aptt|activated\s*partial\s*thromboplastin\s*time)\b"],

    "albumin":      [r"\b(albumin|албумин)\b"],
    "total_protein":[r"\b(total\s*protein|общ(.*)протеин)\b"],

    "na":           [r"\b(na|sodium|натрий)\b"],
    "k":            [r"\b(k|potassium|калий)\b"],
    "cl":           [r"\b(cl|chloride|хлориди?)\b"],
    "ca":           [r"\b(ca|calcium|калций)\b"],
    "mg":           [r"\b(mg|magnesium|магнезий)\b"],

    "ddimer":       [r"\b(d-?dimer|д-?димер)\b"],
}

DEFAULT_UNITS = {
    "hemoglobin": "g/L", "hematocrit": "%", "rbc": "T/L", "wbc": "G/L", "platelets": "G/L",
    "mcv": "fL", "mch": "pg", "mchc": "g/L", "rdw": "%", "mpv": "fL",
    "glucose": "mmol/L", "chol_total": "mmol/L", "ldl": "mmol/L", "hdl": "mmol/L", "triglycerides": "mmol/L",
    "tsh": "mIU/L", "ft4": "pmol/L", "ft3": "pmol/L",
    "hba1c": "%", "crp": "mg/L", "esr": "mm/h",
    "creatinine": "µmol/L", "urea": "mmol/L", "uric_acid": "µmol/L",
    "alt": "U/L", "ast": "U/L", "ggt": "U/L", "alp": "U/L", "bilirubin_total": "µmol/L",
    "ferritin": "µg/L", "iron": "µmol/L", "transferrin": "g/L", "tibc": "µmol/L",
    "vitamin_d": "ng/mL",
    "inr": "", "pt": "s", "aptt": "s",
    "albumin": "g/L", "total_protein": "g/L",
    "na": "mmol/L", "k": "mmol/L", "cl": "mmol/L", "ca": "mmol/L", "mg": "mmol/L",
    "ddimer": "µg/mL FEU",
}

def _norm_text(s: str) -> str:
    s = s or ""
    s = s.lower().strip()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s)

def normalize_indicator(name: str) -> tuple[str, str]:

    n = _norm_text(name)
    for canon, patterns in CANONICAL_INDICATORS.items():
        for pat in patterns:
            if re.search(pat, n, flags=re.IGNORECASE):
                return canon, canon
    return "", name or ""
