from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from records.models import (
    DocumentType,
    MedicalSpecialty,
    MedicalCategory,
    MedicalEvent,
    Document,
    PatientProfile,
)
import os, requests, json, re, time, hashlib
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
    meta_list = []
    for f in files:
        txt, meta = _ocr_pipeline(f, ctx)
        merged = _merge_lines(merged, txt)
        if meta:
            meta_list.append(meta)

    resp = {"ocr_text": merged}
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
            summary = (data.get("summary") or "").strip()
            elapsed = int(max((time.monotonic() - started) * 1000, 0))
            meta = {
                "engine": f"OpenAI {model}",
                "provider": "openai",
                "duration_ms": elapsed,
            }
            return JsonResponse({"summary": summary, "data": data, "meta": meta})
        except Exception:
            pass
    data = _fallback_extract(clean, specialty_name)
    summary = data.get("summary","")
    elapsed = int(max((time.monotonic() - started) * 1000, 0))
    meta = {
        "engine": "Правила (fallback)",
        "provider": "fallback",
        "duration_ms": elapsed,
    }
    return JsonResponse({"summary": summary, "data": data, "meta": meta})

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
        }
    )

@login_required
@require_http_methods(["GET"])
def upload_preview(request):
    ctx = {
        "categories": MedicalCategory.objects.order_by("id"),
        "specialties": MedicalSpecialty.objects.order_by("id"),
        "doc_types": DocumentType.objects.order_by("id"),
    }
    return render(request, "main/upload.html", ctx)

@login_required
@require_http_methods(["GET"])
def upload_history(request):
    documents = (
        Document.objects.filter(owner=request.user)
        .select_related("medical_event", "doc_type")
        .order_by("-uploaded_at")
    )
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
