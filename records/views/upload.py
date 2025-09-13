from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from records.models import (
    DocumentType,
    MedicalSpecialty,
    MedicalCategory,
    MedicalEvent,
)
import os, requests, json, re
from datetime import datetime

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

def _call_flask_ocr(dj_file, ctx):
    url = os.getenv("OCR_API_URL") or os.getenv("OCR_SERVICE_URL") or "http://ocr:5000/ocr"
    timeout = float(os.getenv("OCR_HTTP_TIMEOUT", "90"))
    dj_file.seek(0)
    files = {"file": (dj_file.name, dj_file.read(), dj_file.content_type or "application/octet-stream")}
    data = {
        "event_type": ctx.get("event_type",""),
        "category_name": ctx.get("category_name",""),
        "specialty_name": ctx.get("specialty_name","")
    }
    try:
        r = requests.post(url, files=files, data=data, timeout=timeout)
        if r.status_code != 200:
            return ""
        if "application/json" in r.headers.get("content-type",""):
            p = r.json()
            if isinstance(p, dict):
                return (p.get("ocr_text") or p.get("text") or p.get("full_text") or p.get("data",{}).get("raw_text","") or "").strip()
        return (r.text or "").strip()
    except Exception:
        return ""

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
        return ""
    try:
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=blob)
        resp = client.document_text_detection(image=image)
        if getattr(resp, "full_text_annotation", None) and getattr(resp.full_text_annotation, "text", ""):
            return resp.full_text_annotation.text.strip()
        arr = getattr(resp, "text_annotations", None)
        if arr and len(arr) > 0 and getattr(arr[0], "description", ""):
            return arr[0].description.strip()
        return ""
    except Exception:
        return ""

def _ocr_pipeline(dj_file, ctx):
    dj_file.seek(0)
    vb = dj_file.read()
    vision_txt = ""
    if _vision_available():
        vision_txt = _call_vision_ocr_bytes(vb)
    if vision_txt:
        return vision_txt
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
    d = {"summary":"", "event_date":"", "detected_specialty": specialty_hint or "", "suggested_tags":[], "blood_test_results":[], "diagnosis":"", "treatment_plan":"", "doctors":[]}
    t = (text or "").strip()
    lines = [x.strip() for x in t.replace("\r","").split("\n") if x.strip()]
    d["summary"] = " ".join(lines[:6])[:800]
    m = re.search(r"\b(20\d{2}|19\d{2})[-./](0?[1-9]|1[0-2])[-./](0?[1-9]|[12]\d|3[01])\b", t)
    if m:
        try:
            dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()
            d["event_date"] = dt.isoformat()
        except Exception:
            d["event_date"] = ""
    return d

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
    for f in files:
        txt = _ocr_pipeline(f, ctx)
        merged = _merge_lines(merged, txt)
    return JsonResponse({"ocr_text": merged})

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
    clean = _anonymize(txt)
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
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
            summary = (data.get("summary") or "").strip()
            return JsonResponse({"summary": summary, "data": data})
        except Exception:
            pass
    data = _fallback_extract(clean, specialty_name)
    summary = data.get("summary","")
    return JsonResponse({"summary": summary, "data": data})

@login_required
@require_http_methods(["POST"])
def upload_confirm(request):
    return JsonResponse({"ok": True})

@login_required
@require_http_methods(["GET"])
def upload_preview(request):
    return render(request, "main/upload.html", {})

@login_required
@require_http_methods(["GET"])
def upload_history(request):
    return render(request, "main/upload_history.html")

@login_required
@require_http_methods(["GET"])
def events_suggest(request):
    qs = MedicalEvent.objects.filter(owner=request.user)
    cat_id = request.GET.get("category_id") or request.GET.get("category")
    spec_id = request.GET.get("specialty_id") or request.GET.get("specialty")
    doc_id = request.GET.get("doc_type_id") or request.GET.get("doc_type")
    if cat_id and cat_id.isdigit():
        qs = qs.filter(category_id=int(cat_id))
    if spec_id and spec_id.isdigit():
        qs = qs.filter(specialty_id=int(spec_id))
    if doc_id and doc_id.isdigit():
        qs = qs.filter(doc_type_id=int(doc_id))
    qs = qs.order_by("-event_date", "-id")[:10]
    items = []
    for ev in qs:
        d = ev.event_date.isoformat() if getattr(ev, "event_date", None) else ""
        items.append({"id": ev.id, "event_date": d})
    return JsonResponse({"events": items})
