from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from records.models import (
    DocumentType,
    MedicalSpecialty,
    MedicalCategory,
    MedicalEvent,
    Document,
    PatientProfile,
    LabIndicator,
)

from decimal import Decimal
import math
import os, requests, json, re, time, hashlib, unicodedata
from datetime import datetime
from django.utils import timezone


def _parse_date(value):
    s = (value or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    try:
        return datetime.fromisoformat(s).date()
    except Exception:
        return None

def _safe_name(o):
    n = ""
    if hasattr(o, "safe_translation_getter"):
        try:
            n = o.safe_translation_getter("name", any_language=True) or ""
        except Exception:
            n = ""
    if not n:
        n = getattr(o, "name", "") or getattr(o, "title", "") or getattr(o, "slug", "") or str(o)
    return n

def _q_names(model):
    out = []
    for o in model.objects.order_by("id"):
        out.append({"id": o.id, "name": _safe_name(o)})
    return out

def _id_to_name(model, id_str):
    s = str(id_str or "").strip()
    if not s.isdigit():
        return ""
    obj = model.objects.filter(id=int(s)).first()
    return _safe_name(obj) if obj else ""

def _merge_lines(a, b):
    seen, out = set(), []
    for chunk in (a or "", b or ""):
        for line in chunk.replace("\r","").split("\n"):
            s = line.strip()
            if s and s not in seen:
                seen.add(s); out.append(s)
    return "\n".join(out).strip()



LAB_INDEX_CACHE = None


def _lab_index_map():
    global LAB_INDEX_CACHE
    if LAB_INDEX_CACHE:
        return LAB_INDEX_CACHE
    try:
        indicators = (
            LabIndicator.objects.filter(is_active=True)
            .prefetch_related("aliases")
            .order_by("id")
        )
    except Exception:
        LAB_INDEX_CACHE = ({}, {})
        return LAB_INDEX_CACHE

    canonical = {}
    meta = {}

    def _key(label):
        if not label:
            return ""
        s = unicodedata.normalize("NFKD", str(label))
        s = "".join(ch for ch in s if not unicodedata.combining(ch))
        s = re.sub(r"[^a-zA-Zа-яА-Я0-9%]+", " ", s)
        return re.sub(r"\s+", " ", s).strip().lower()

    def _store(label, target):
        k = _key(label)
        if k:
            canonical[k] = target

    for indicator in indicators:
        name = _safe_name(indicator).strip()
        if not name:
            continue
        meta[name] = {
            "unit": (indicator.unit or "").strip() or None,
            "ref_low": indicator.reference_low,
            "ref_high": indicator.reference_high,
        }
        _store(name, name)
        try:
            aliases = [a.alias() for a in indicator.aliases.all() if hasattr(a, "alias")]
        except Exception:
            aliases = []
        for alias in aliases:
            alias_name = (alias or "").strip()
            if alias_name:
                _store(alias_name, name)

    LAB_INDEX_CACHE = (canonical, meta)
    return LAB_INDEX_CACHE


def _normalize_indicator_name(name):
    label = (name or "").strip()
    if not label:
        return "", {}
    canonical, meta = _lab_index_map()
    s = unicodedata.normalize("NFKD", label)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"\s*-\s*(%|бр\.?)\s*$", r" \1", s, flags=re.IGNORECASE)
    key = re.sub(r"[^a-zA-Zа-яА-Я0-9%]+", " ", s).strip().lower()
    target = canonical.get(key, label.strip())
    meta_entry = meta.get(target, {})
    return target, meta_entry


def _normalize_ocr_text(text):
    s = (text or "").replace("\r\n", "\n")
    s = re.sub(r"[‐‒–—−]", "-", s)
    s = re.sub(r"-\s*96(?=\s*\d)", " %", s)
    s = re.sub(r"([\wа-яА-Я])\s*-\s*96\b", r"\1 %", s)
    s = re.sub(r"-\s*%(?=\s*\d)", " %", s)
    s = s.replace("|", " ")
    return s


def _parse_float(value):
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if math.isfinite(value):
            return float(value)
        return None
    s = re.sub(r"[^0-9,.-]", "", str(value))
    if not s:
        return None
    s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        try:
            return float(Decimal(s))
        except Exception:
            return None


def _format_number(value):
    if value is None:
        return ""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if float(value).is_integer():
            return str(int(value))
        return f"{float(value):.2f}".rstrip("0").rstrip(".")
    return str(value)


def _split_range(text):
    if not text:
        return None, None, None
    m = re.search(
        r"(?P<low>[-+]?\d+(?:[.,]\d+)?)(?:\s*%?)\s*[-–]\s*(?P<high>[-+]?\d+(?:[.,]\d+)?)(?:\s*%?)",
        str(text),
    )
    if not m:
        return None, None, None
    return _parse_float(m.group("low")), _parse_float(m.group("high")), m


def _normalize_unit(raw):
    if not raw:
        return None
    unit = re.sub(r"[;:,]+$", "", str(raw).strip())
    tokens = [tok for tok in re.split(r"\s+", unit) if tok]
    cleaned = [tok for tok in tokens if tok.lower() not in {"m", "k", "ж", "мъже", "жени"}]
    unit = " ".join(cleaned) if cleaned else unit
    return unit or None


def _collect_lab_rows(text):
    norm = _normalize_ocr_text(text)
    lines = [ln.strip() for ln in norm.split("\n") if ln.strip()]
    rows = []
    seen = set()
    for line in lines:
        if len(line) < 6:
            continue
        if re.match(r"^(?:резултат|units|референтни|таблица|panel)", line, flags=re.IGNORECASE):
            continue
        value_match = re.search(r"[-+]?\d+(?:[.,]\d+)?", line)
        if not value_match:
            continue
        name_part = line[: value_match.start()].strip(" :").strip()
        rest = line[value_match.start():].strip()
        if not name_part:
            continue
        value_text = value_match.group(0)
        after_value = rest[len(value_text) :].strip()
        unit = None
        ref_low = None
        ref_high = None
        unit_part = ""
        if after_value:
            ref_low, ref_high, match = _split_range(after_value)
            if match:
                unit_part = after_value[: match.start()].strip()
            else:
                unit_part = after_value
            unit = _normalize_unit(unit_part)
        else:
            ref_low = ref_high = None
        if (ref_low is None and ref_high is None) and unit_part:
            ref_low, ref_high, match_alt = _split_range(unit_part)
            if match_alt:
                unit = _normalize_unit(unit_part[: match_alt.start()].strip()) or unit
        value_num = _parse_float(value_text)
        name_clean = re.sub(r"\s{2,}", " ", name_part)
        canonical_name, meta = _normalize_indicator_name(name_clean)
        if canonical_name in seen:
            continue
        seen.add(canonical_name)
        ref_low_val = ref_low if ref_low is not None else meta.get("ref_low")
        ref_high_val = ref_high if ref_high is not None else meta.get("ref_high")
        row = {
            "indicator_name": canonical_name,
            "value": value_num if value_num is not None else value_text,
            "unit": unit or meta.get("unit"),
            "ref_low": ref_low_val,
            "ref_high": ref_high_val,
        }
        if ref_low_val is not None or ref_high_val is not None:
            low_txt = _format_number(ref_low_val) or "—"
            high_txt = _format_number(ref_high_val) or "—"
            row["reference_range"] = f"{low_txt}-{high_txt}"
        rows.append(row)
    return rows


def _lab_status(row):
    try:
        value = _parse_float(row.get("value"))
        low = _parse_float(row.get("ref_low"))
        high = _parse_float(row.get("ref_high"))
    except Exception:
        value = low = high = None
    if value is None:
        return "unknown"
    if low is not None and value < low:
        return "low"
    if high is not None and value > high:
        return "high"
    return "normal"


def _build_lab_summary(rows):
    if not rows:
        return {
            "abnormal": [],
            "text": "Не са разпознати лабораторни показатели в документа.",
        }
    abnormal = []
    for row in rows:
        status = _lab_status(row)
        if status in {"low", "high"}:
            abnormal.append({"row": row, "status": status})
    summary_bits = [f"Идентифицирани са {len(rows)} лабораторни показателя."]
    if abnormal:
        details = []
        for item in abnormal[:5]:
            r = item["row"]
            status = "под нормата" if item["status"] == "low" else "над нормата"
            ref_text = ""
            low = _format_number(r.get("ref_low"))
            high = _format_number(r.get("ref_high"))
            if low or high:
                ref_text = f" (реф. диапазон {low or '—'} - {high or '—'})"
            details.append(
                f"{r['indicator_name']} – {status}{ref_text} със стойност { _format_number(r.get('value')) } {r.get('unit') or ''}"
            )
        summary_bits.append("Установени отклонения: " + "; ".join(details) + ".")
        summary_bits.append("Препоръка: обсъдете резултатите със специалист и проследете динамиката на показателите.")
    else:
        summary_bits.append("Всички налични показатели са в посочените референтни граници.")
    return {"abnormal": abnormal, "text": " ".join(summary_bits)}


def _suggest_tags(rows, specialty_name, doc_type_name):
    tags = []
    if doc_type_name:
        tags.append(doc_type_name)
    if specialty_name:
        tags.append(specialty_name)
    if rows:
        tags.extend(["лаборатория", "кръвни изследвания"])
    abnormal = [item["row"]["indicator_name"] for item in _build_lab_summary(rows)["abnormal"]]
    tags.extend(abnormal)
    seen = []
    for tag in tags:
        label = (tag or "").strip()
        if label and label not in seen:
            seen.append(label)
    return seen


def _extract_event_date(text):
    if not text:
        return ""
    patterns = [
        r"(20\d{2}|19\d{2})[-./](0?[1-9]|1[0-2])[-./](0?[1-9]|[12]\d|3[01])",
        r"(0?[1-9]|[12]\d|3[01])[-./](0?[1-9]|1[0-2])[-./](20\d{2}|19\d{2})",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if not m:
            continue
        chunks = [c for c in m.groups() if c is not None]
        if len(chunks) != 3:
            continue
        try:
            if pat.startswith("(20"):
                y, mth, d = chunks
            else:
                d, mth, y = chunks
            dt = datetime(int(y), int(mth), int(d)).date()
            return dt.isoformat()
        except Exception:
            continue
    return ""


def _enrich_analysis(raw_data, text, specialty_name, doc_type_name):
    data = raw_data if isinstance(raw_data, dict) else {}
    rows = list(data.get("blood_test_results") or [])
    parsed_rows = _collect_lab_rows(text)
    indicator_map = {}
    for row in rows:
        name = row.get("indicator_name") or row.get("name")
        if not name:
            continue
        indicator_map[name] = {
            "indicator_name": name,
            "value": row.get("value"),
            "unit": row.get("unit"),
            "ref_low": row.get("ref_low") if row.get("ref_low") is not None else row.get("reference_low"),
            "ref_high": row.get("ref_high") if row.get("ref_high") is not None else row.get("reference_high"),
        }
    for row in parsed_rows:
        name = row["indicator_name"]
        if name in indicator_map:
            existing = indicator_map[name]
            for key in ["value", "unit", "ref_low", "ref_high"]:
                if existing.get(key) in (None, "") and row.get(key) not in (None, ""):
                    existing[key] = row.get(key)
        else:
            indicator_map[name] = row
    combined_rows_raw = list(indicator_map.values())
    combined_rows = []
    for row in combined_rows_raw:
        name_source = row.get("indicator_name") or row.get("name")
        canonical_name, meta = _normalize_indicator_name(name_source)
        if not canonical_name:
            continue
        value_raw = row.get("value")
        value_num = _parse_float(value_raw)
        value_final = value_num if value_num is not None else (
            str(value_raw).strip() if value_raw not in (None, "") else ""
        )
        ref_low_val = row.get("ref_low") if row.get("ref_low") not in ("", None) else None
        ref_high_val = row.get("ref_high") if row.get("ref_high") not in ("", None) else None
        ref_low_val = _parse_float(ref_low_val)
        ref_high_val = _parse_float(ref_high_val)
        if ref_low_val is None and meta.get("ref_low") is not None:
            ref_low_val = _parse_float(meta.get("ref_low"))
        if ref_high_val is None and meta.get("ref_high") is not None:
            ref_high_val = _parse_float(meta.get("ref_high"))
        unit_val = row.get("unit") or meta.get("unit")
        unit_val = _normalize_unit(unit_val) if unit_val else None
        normalized = {
            "indicator_name": canonical_name,
            "value": value_final,
            "unit": unit_val or None,
            "ref_low": ref_low_val,
            "ref_high": ref_high_val,
        }
        if ref_low_val is not None or ref_high_val is not None:
            low_txt = _format_number(ref_low_val) or "—"
            high_txt = _format_number(ref_high_val) or "—"
            normalized["reference_range"] = f"{low_txt}-{high_txt}"
        combined_rows.append(normalized)

    lab_summary = _build_lab_summary(combined_rows)
    summary_text = (data.get("summary") or "").strip()
    if not summary_text:
        base_summary = text.strip().split("\n")[:4]
        summary_text = " ".join(base_summary).strip()[:800]
    summary_text = summary_text or "Няма генерирано резюме."
    if lab_summary["text"] and lab_summary["text"] not in summary_text:
        summary_text = (summary_text + " " + lab_summary["text"]).strip()
    combined_tags = data.get("suggested_tags") or []
    suggested = _suggest_tags(combined_rows, specialty_name, doc_type_name)
    for tag in suggested:
        if tag not in combined_tags:
            combined_tags.append(tag)
    detected_specialty = data.get("detected_specialty") or specialty_name or ""
    event_date = data.get("event_date") or _extract_event_date(text)
    analysis_data = {
        **data,
        "summary": summary_text,
        "event_date": event_date,
        "detected_specialty": detected_specialty,
        "suggested_tags": combined_tags,
        "blood_test_results": combined_rows,
        "abnormal_findings": [
            {
                "indicator_name": item["row"]["indicator_name"],
                "status": item["status"],
                "value": item["row"].get("value"),
                "unit": item["row"].get("unit"),
                "ref_low": item["row"].get("ref_low"),
                "ref_high": item["row"].get("ref_high"),
            }
            for item in lab_summary["abnormal"]
        ],
        "tables": [
            {
                "title": "Лабораторни показатели",
                "columns": ["Показател", "Стойност", "Единици", "Реф. мин", "Реф. макс"],
                "rows": [
                    [
                        row["indicator_name"],
                        _format_number(row.get("value")),
                        row.get("unit") or "",
                        _format_number(row.get("ref_low")),
                        _format_number(row.get("ref_high")),
                    ]
                    for row in combined_rows
                ],
            }
        ] if combined_rows else [],
        "lab_overview": lab_summary["text"],
        "normalized_text": _normalize_ocr_text(text),
    }
    analysis_data.setdefault("diagnosis", "")
    analysis_data.setdefault("treatment_plan", "")
    analysis_data.setdefault("doctors", [])
    return summary_text, analysis_data

def _lab_index_payload():
    try:
        indicators = (
            LabIndicator.objects.filter(is_active=True)
            .prefetch_related("aliases")
            .order_by("id")
        )
    except Exception:
        return []

    rows = []
    seen = set()
    for indicator in indicators:
        name = _safe_name(indicator).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        entry = {
            "name": name,
            "unit": (indicator.unit or "").strip(),
            "ref_low": float(indicator.reference_low) if indicator.reference_low is not None else None,
            "ref_high": float(indicator.reference_high) if indicator.reference_high is not None else None,
            "aliases": [],
        }
        try:
            aliases = [a.alias() for a in indicator.aliases.all() if hasattr(a, "alias")]
            entry["aliases"] = [alias for alias in aliases if alias]
        except Exception:
            entry["aliases"] = []
        rows.append(entry)
    return rows

def _call_flask_ocr(dj_file, ctx):
    url = os.getenv("OCR_API_URL") or os.getenv("OCR_SERVICE_URL") or "http://ocr:5000/ocr"
    timeout = float(os.getenv("OCR_HTTP_TIMEOUT", "90"))
    dj_file.seek(0)
    files = {"file": (dj_file.name, dj_file.read(), dj_file.content_type or "application/octet-stream")}
    data = {
        "event_type": ctx.get("event_type", ""),
        "category_name": ctx.get("category_name", ""),
        "specialty_name": ctx.get("specialty_name", ""),
    }
    started = time.monotonic()
    base_meta = {"engine": "OCR Service"}
    try:
        r = requests.post(url, files=files, data=data, timeout=timeout)
        elapsed = int(max((time.monotonic() - started) * 1000, 0))
        meta = {**base_meta, "duration_ms": elapsed}
        if r.status_code != 200:
            meta["status_code"] = r.status_code
            return "", meta
        if "application/json" in r.headers.get("content-type", ""):
            p = r.json()
            if isinstance(p, dict):
                text = (
                    p.get("ocr_text")
                    or p.get("text")
                    or p.get("full_text")
                    or p.get("data", {}).get("raw_text", "")
                    or ""
                ).strip()
                resp_meta = p.get("meta") if isinstance(p.get("meta"), dict) else {}
                if resp_meta:
                    for k, v in resp_meta.items():
                        if v is None:
                            continue
                        meta.setdefault(k, v)
                if not meta.get("engine"):
                    meta["engine"] = (
                        resp_meta.get("engine")
                        if isinstance(resp_meta, dict)
                        else None
                    ) or p.get("engine") or p.get("provider") or base_meta["engine"]
                return text, meta
        text = (r.text or "").strip()
        return text, meta
    except Exception:
        base_meta["error"] = "request_failed"
        return "", base_meta

def _vision_available():
    try:
        from google.cloud import vision
        client = vision.ImageAnnotatorClient()
        _ = client
        return True
    except Exception:
        return False

def _call_vision_ocr_bytes(blob):
    try:
        from google.cloud import vision
    except Exception:
        return "", {"engine": "Google Cloud Vision", "error": "unavailable"}
    try:
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=blob)
        started = time.monotonic()
        resp = client.document_text_detection(image=image)
        elapsed = int(max((time.monotonic() - started) * 1000, 0))
        meta = {"engine": "Google Cloud Vision", "duration_ms": elapsed}
        if getattr(resp, "full_text_annotation", None) and getattr(resp.full_text_annotation, "text", ""):
            return resp.full_text_annotation.text.strip(), meta
        arr = getattr(resp, "text_annotations", None)
        if arr and len(arr) > 0 and getattr(arr[0], "description", ""):
            return arr[0].description.strip(), meta
        return "", meta
    except Exception:
        return "", {"engine": "Google Cloud Vision", "error": "failed"}

def _ocr_pipeline(dj_file, ctx):
    dj_file.seek(0)
    vb = dj_file.read()
    vision_txt, vision_meta = "", {}
    if _vision_available():
        vision_txt, vision_meta = _call_vision_ocr_bytes(vb)
    if vision_txt:
        return vision_txt, vision_meta
    dj_file.seek(0)
    return _call_flask_ocr(dj_file, ctx)

def _anonymize(t):
    t = re.sub(r"\b\d{10}\b", "<ID>", t or "")
    t = re.sub(r"\b(?:\+?\d{3}[-.\s]?)?\d{3}[-.\s]?\d{3}[-.\s]?\d{3,4}\b", "<PHONE>", t)
    t = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "<EMAIL>", t)
    t = re.sub(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b", "<DATE>", t)
    t = re.sub(r"\b[А-ЯA-Z][а-яa-z]+ [А-ЯA-Z][а-яa-z]+(?: [А-ЯA-Z][а-яa-z]+)?\b", "<NAME>", t)
    return t

def _build_system_prompt():
    return (
        "Върни САМО JSON в UTF-8 без обяснения и без markdown. "
        "{"
        '"summary":"",'
        '"event_date":"",'
        '"detected_specialty":"",'
        '"suggested_tags":[],'
        '"blood_test_results":[{"indicator_name":"","value":"","unit":"","reference_range":""}],'
        '"diagnosis":"",'
        '"treatment_plan":"",'
        '"doctors":[]'
        "}"
        " Ако липсва информация за поле, остави празно или празен списък."
    )

def _fallback_extract(text, specialty_hint):
    summary, data = _enrich_analysis({}, text, specialty_hint, "")
    data.setdefault("diagnosis", "")
    data.setdefault("treatment_plan", "")
    data.setdefault("doctors", [])
    return data

@login_required
@require_http_methods(["POST"])
def upload_ocr(request):
    files = request.FILES.getlist("files")
    if not files and request.FILES.get("file"):
        files = [request.FILES["file"]]
    if not files:
        return HttpResponseBadRequest("No files")
    doc_name = _id_to_name(DocumentType, request.POST.get("doc_type_id") or request.POST.get("doc_type", ""))
    spec_name = _id_to_name(MedicalSpecialty, request.POST.get("specialty_id") or request.POST.get("specialty", ""))
    cat_id = (
        request.POST.get("category_id")
        or request.POST.get("med_category", "")
        or request.POST.get("category", "")
    )
    cat_name = _id_to_name(MedicalCategory, cat_id)
    ctx = {"event_type": doc_name, "specialty_name": spec_name, "category_name": cat_name}
    merged = ""
    meta_list = []
    for f in files:
        txt, meta = _ocr_pipeline(f, ctx)
        merged = _merge_lines(merged, txt)
        if meta:
            meta_list.append(meta)
    resp = {"ocr_text": merged, "normalized_text": _normalize_ocr_text(merged)}

    if meta_list:
        if len(meta_list) == 1:
            resp["meta"] = meta_list[0]
        else:
            engines = []
            total = 0
            for m in meta_list:
                eng = m.get("engine") if isinstance(m, dict) else ""
                if eng and eng not in engines:
                    engines.append(eng)
                dur = m.get("duration_ms") if isinstance(m, dict) else None
                if isinstance(dur, (int, float)):
                    total += int(dur)
            meta_combined = {}
            if engines:
                meta_combined["engine"] = ", ".join(engines)
            if total:
                meta_combined["duration_ms"] = total
            if meta_combined:
                resp["meta"] = meta_combined
                
    meta = resp.get("meta") or {}
    if not meta.get("engine"):
        meta["engine"] = "OCR Service"
        resp["meta"] = meta
    resp["source"] = meta.get("engine") or "ocr"

    return JsonResponse(resp)

@login_required
@require_http_methods(["POST"])
def upload_analyze(request):
    try:
        if request.content_type and "application/json" in request.content_type:
            payload = json.loads(request.body or "{}")
            txt = (payload.get("text") or "").strip()
            specialty_id = payload.get("specialty_id") or payload.get("specialty")
        else:
            txt = (request.POST.get("text") or "").strip()
            specialty_id = request.POST.get("specialty_id") or request.POST.get("specialty")
    except Exception:
        txt, specialty_id = "", None
    if not txt:
        return HttpResponseBadRequest("No text")
    specialty_name = _id_to_name(MedicalSpecialty, specialty_id)
    doc_type_id = None
    if "payload" in locals():
        doc_type_id = payload.get("doc_type_id") or payload.get("doc_type")
    if doc_type_id in (None, ""):
        doc_type_id = request.POST.get("doc_type_id") or request.POST.get("doc_type")
    doc_type_name = _id_to_name(DocumentType, doc_type_id)
    clean = _anonymize(txt)
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    started = time.monotonic()
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            sys = _build_system_prompt()
            resp = client.chat.completions.create(
                model=model,
                response_format={"type": "json_object"},
                max_tokens=1200,
                messages=[{"role": "system", "content": sys}, {"role": "user", "content": clean}]
            )
            content = resp.choices[0].message.content or "{}"
            data = json.loads(content)
            summary, enriched = _enrich_analysis(data, txt, specialty_name, doc_type_name)
            summary = (data.get("summary") or "").strip()

            elapsed = int(max((time.monotonic() - started) * 1000, 0))
            meta = {
                "engine": f"OpenAI {model}",
                "provider": "openai",
                "duration_ms": elapsed,
            }

            return JsonResponse({"summary": summary, "data": enriched, "meta": meta})
        except Exception:
            pass
        data = _fallback_extract(txt, specialty_name)
        summary, enriched = _enrich_analysis(data, txt, specialty_name, doc_type_name)
        elapsed = int(max((time.monotonic() - started) * 1000, 0))
        meta = {
            "engine": "MedJ Analyzer",
            "provider": "internal",
            "duration_ms": elapsed,
        }
        return JsonResponse({"summary": summary, "data": enriched, "meta": meta})

    @login_required
    @require_http_methods(["POST"])
    def upload_confirm(request):
        upload_file = request.FILES.get("file")
        if not upload_file:
            return HttpResponseBadRequest("Missing file")

        def _obj_or_400(model, key):
            value = request.POST.get(key) or request.POST.get(key.replace("_id", ""), "")
            if not value or not str(value).isdigit():
                return None
            return model.objects.filter(id=int(value)).first()

        category = _obj_or_400(MedicalCategory, "category_id")
        specialty = _obj_or_400(MedicalSpecialty, "specialty_id")
        doc_type = _obj_or_400(DocumentType, "doc_type_id")
        if not (category and specialty and doc_type):
            return HttpResponseBadRequest("Missing classification")

        file_kind = (request.POST.get("file_kind") or "").strip().lower()
        valid_kinds = {"image", "pdf", "other"}

        def _guess_file_kind(f):
            name = (getattr(f, "name", "") or "").lower()
        if name.endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp")):
            return "image"
        if name.endswith(".pdf"):
            return "pdf"
        mime = (getattr(f, "content_type", "") or "").lower()
        if mime.startswith("image/"):
            return "image"
        if mime == "application/pdf":
            return "pdf"
        return "other"

    if file_kind not in valid_kinds:
        file_kind = _guess_file_kind(upload_file)

    event = None
    event_id = request.POST.get("event_id") or ""
    if event_id and str(event_id).isdigit():
        event = MedicalEvent.objects.filter(id=int(event_id), owner=request.user).first()

    ocr_text = request.POST.get("ocr_text") or ""
    ocr_meta_raw = request.POST.get("ocr_meta") or ""
    analysis_raw = request.POST.get("analysis") or ""
    analysis_meta_raw = request.POST.get("analysis_meta") or ""
    summary = (request.POST.get("summary") or "").strip()
    document_date = _parse_date(request.POST.get("document_date"))

    def _json_load(raw):
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except Exception:
            return {}

    ocr_meta = _json_load(ocr_meta_raw)
    if not isinstance(ocr_meta, dict):
        ocr_meta = {}
    analysis_payload = _json_load(analysis_raw)
    if not isinstance(analysis_payload, dict):
        analysis_payload = {}
    analysis_meta = _json_load(analysis_meta_raw)
    if not isinstance(analysis_meta, dict):
        analysis_meta = {}
    if analysis_meta:
        analysis_payload.setdefault("meta", analysis_meta)

    event_date = (
        _parse_date(request.POST.get("event_date"))
        or _parse_date(analysis_payload.get("event_date"))
        or _parse_date((analysis_payload.get("data") or {}).get("event_date"))
        or timezone.now().date()
    )

    if not document_date and event_date:
        document_date = event_date

    patient, _ = PatientProfile.objects.get_or_create(user=request.user)

    if not event:
        event_summary = summary[:255] if summary else (_safe_name(doc_type) or "Документ")
        event = MedicalEvent.objects.create(
            patient=patient,
            owner=request.user,
            specialty=specialty,
            category=category,
            doc_type=doc_type,
            event_date=event_date,
            summary=event_summary,
        )

    hasher = hashlib.sha256()
    try:
        for chunk in upload_file.chunks():
            hasher.update(chunk)
    except Exception:
        data = upload_file.read()
        hasher.update(data)
    digest = hasher.hexdigest()
    try:
        upload_file.seek(0)
    except Exception:
        pass

    doc = Document(
        owner=request.user,
        medical_event=event,
        specialty=specialty,
        category=category,
        doc_type=doc_type,
        document_date=document_date,
        date_created=timezone.now().date(),
        doc_kind=file_kind or _guess_file_kind(upload_file),
        file_size=getattr(upload_file, "size", None) or None,
        file_mime=getattr(upload_file, "content_type", None) or None,
        original_ocr_text=ocr_text,
        summary=summary or str(analysis_payload.get("summary") or ""),
        notes=json.dumps(
            {
                "analysis": analysis_payload,
                "ocr_meta": ocr_meta,
            },
            ensure_ascii=False,
        ),
        sha256=digest,
    )
    doc.file.save(upload_file.name, upload_file, save=False)
    doc.save()

    detail_bits = [f"Документ №{doc.id}"]
    if event:
        detail_bits.append(f"Събитие №{event.id}")

    meta = {
        "engine": "MedJ Upload",
        "detail": " • ".join(detail_bits),
        "document_id": doc.id,
    }
    if event:
        meta["event_id"] = event.id

    return JsonResponse(
        {
            "ok": True,
            "document_id": doc.id,
            "event_id": event.id if event else None,
            "meta": meta,
            "file_url": doc.file.url if doc.file else "",

            "redirect_url": reverse("medj:documents"),
        }
    )

@login_required
@require_http_methods(["GET"])
def upload_preview(request):
    ctx = {
        "categories": MedicalCategory.objects.order_by("id"),
        "specialties": MedicalSpecialty.objects.order_by("id"),
        "doc_types": DocumentType.objects.order_by("id"),
        "lab_index": _lab_index_payload(),
        "upload_config": {"documents_url": reverse("medj:documents")},

    }
    return render(request, "main/upload.html", ctx)

@login_required
@require_http_methods(["GET"])
def upload_history(request):
    return redirect("medj:documents")
    documents = (
        Document.objects.filter(owner=request.user)
        .select_related("medical_event", "doc_type")
        .order_by("-uploaded_at"))
    return render(request, "main/history.html", {"documents": documents})


@login_required
@require_http_methods(["GET"])
def events_suggest(request):
    qs = MedicalEvent.objects.filter(owner=request.user)
    cat_id = request.GET.get("category_id") or request.GET.get("category")
    spec_id = request.GET.get("specialty_id") or request.GET.get("specialty")
    doc_id = request.GET.get("doc_type_id") or request.GET.get("doc_type")
    file_kind = (request.GET.get("file_kind") or "").strip()
    if cat_id and str(cat_id).isdigit():
        qs = qs.filter(category_id=int(cat_id))
    if spec_id and str(spec_id).isdigit():
        qs = qs.filter(specialty_id=int(spec_id))
    if doc_id and str(doc_id).isdigit():
        qs = qs.filter(doc_type_id=int(doc_id))
    if file_kind:
        qs = qs.filter(documents__doc_kind=file_kind).distinct()
    qs = qs.order_by("-event_date", "-id")[:20]
    items = []
    for ev in qs:
        d = ev.event_date.isoformat() if getattr(ev, "event_date", None) else ""
        title = " • ".join([x for x in [d, _safe_name(ev.specialty), _safe_name(ev.doc_type)] if x])
        items.append({"id": ev.id, "event_date": d, "title": title})
    return JsonResponse({"events": items})
