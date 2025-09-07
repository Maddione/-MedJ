import base64
import json
import os
import time
import requests
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils.dateparse import parse_date
from django.utils.timezone import now
from django.db import transaction
from django.shortcuts import get_object_or_404
from ..models import OcrLog, MedicalEvent, MedicalCategory, MedicalSpecialty, DocumentType, Document

try:
    from google.cloud import vision as gvision
except Exception:
    gvision = None

try:
    from records.management.services import upload_flow as svc
except Exception:
    svc = None

def _env(name, default=None):
    return os.environ.get(name, default)

def _ddmmyyyy(d):
    if not d:
        return ""
    if isinstance(d, str):
        p = parse_date(d)
        d = p or d
    try:
        return d.strftime("%d-%m-%Y")
    except Exception:
        return ""

def _ocr_with_vision(fileobj):
    if gvision is None:
        return None
    try:
        client = gvision.ImageAnnotatorClient()
    except Exception:
        return None
    data = fileobj.read()
    fileobj.seek(0)
    image = gvision.Image(content=data)
    try:
        resp = client.document_text_detection(image=image)
        return getattr(resp.full_text_annotation, "text", "") or None
    except Exception:
        return None

def _ocr_with_flask(fileobj, filename):
    url = _env("OCR_SERVICE_URL") or _env("OCR_API_URL")
    if not url:
        return ""
    try:
        fileobj.seek(0)
        files = {"file": (filename, fileobj.read())}
        r = requests.post(url.rstrip("/") + "/ocr", files=files, timeout=60)
        j = r.json() if r.ok else {}
        return j.get("ocr_text") or j.get("text") or ""
    except Exception:
        return ""

@csrf_exempt
@require_POST
@login_required
def upload_ocr(request):
    f = request.FILES.get("file")
    if not f:
        return HttpResponseBadRequest("missing file")
    started = time.time()
    text = ""
    source = "vision"
    if svc and hasattr(svc, "vision_ocr_first_fallback_flask"):
        try:
            text, source = svc.vision_ocr_first_fallback_flask(f)
        except Exception:
            text, source = "", "flask"
    if not text:
        t = _ocr_with_vision(f)
        if t:
            text, source = t, "vision"
        else:
            text, source = _ocr_with_flask(f, getattr(f, "name", "upload.bin")), "flask"
    dur = int((time.time() - started) * 1000)
    try:
        OcrLog.objects.create(user=request.user, source=source, duration_ms=dur)
    except Exception:
        pass
    return JsonResponse({"ocr_text": text or "", "source": source})

@csrf_exempt
@require_POST
@login_required
def events_suggest(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        payload = request.POST
    category_id = payload.get("category_id")
    specialty_id = payload.get("specialty_id")
    doc_type_id = payload.get("doc_type_id")
    if not (category_id and specialty_id and doc_type_id):
        return JsonResponse({"events": []})
    qs = MedicalEvent.objects.filter(
        owner=request.user,
        category_id=category_id,
        specialty_id=specialty_id,
        doc_type_id=doc_type_id,
    ).order_by("-event_date")[:20]
    data = [{"id": e.id, "event_date": _ddmmyyyy(e.event_date), "summary": e.summary or ""} for e in qs]
    return JsonResponse({"events": data})

@csrf_exempt
@require_POST
@login_required
def upload_analyze(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("invalid json")
    text = payload.get("text") or ""
    specialty_id = payload.get("specialty") or payload.get("specialty_id")
    specialty_name = ""
    if specialty_id:
        sp = MedicalSpecialty.objects.filter(id=specialty_id).first()
        if sp:
            try:
                specialty_name = sp.safe_translation_getter("name", any_language=True) or ""
            except Exception:
                specialty_name = ""
    result = None
    try:
        from records.services.llm import anonymizer as anonymizer_mod
    except Exception:
        anonymizer_mod = None
    try:
        from records.services.llm import gpt_client as gpt_client_mod
    except Exception:
        gpt_client_mod = None
    anon = text
    if anonymizer_mod and hasattr(anonymizer_mod, "anonymize"):
        try:
            anon = anonymizer_mod.anonymize(text) or text
        except Exception:
            anon = text
    if gpt_client_mod:
        fn = None
        if hasattr(gpt_client_mod, "analyze_text"):
            fn = gpt_client_mod.analyze_text
        elif hasattr(gpt_client_mod, "analyze"):
            fn = gpt_client_mod.analyze
        if fn:
            try:
                result = fn(anon, specialty_name=specialty_name) if "specialty_name" in fn.__code__.co_varnames else fn(anon, specialty_id=specialty_id)
            except Exception:
                result = None
    if isinstance(result, dict) and "summary" in result and "data" in result:
        return JsonResponse(result)
    summary = (text or "").strip().splitlines()
    summary = " ".join(summary)[:400]
    data = {
        "summary": summary,
        "event_date": now().date().strftime("%Y-%m-%d"),
        "detected_specialty": specialty_name,
        "suggested_tags": [],
        "blood_test_results": [],
        "diagnosis": "",
        "treatment_plan": "",
        "doctors": [],
        "date_created": None,
    }
    return JsonResponse({"summary": summary, "data": data})

@csrf_exempt
@require_POST
@login_required
@transaction.atomic
def upload_confirm(request):
    content_type = request.META.get("CONTENT_TYPE", "")
    meta = {}
    analysis = {}
    final_text = ""
    final_summary = ""
    file_obj = None
    file_mime = ""
    file_kind = ""
    doctor_block = {}

    if "multipart/form-data" in content_type:
        meta_raw = request.POST.get("meta")
        analysis_raw = request.POST.get("analysis")
        final_text = request.POST.get("final_text") or ""
        final_summary = request.POST.get("final_summary") or ""
        try:
            meta = json.loads(meta_raw) if meta_raw else {}
            analysis = json.loads(analysis_raw) if analysis_raw else {}
        except Exception:
            return HttpResponseBadRequest("invalid meta/analysis")
        file_obj = request.FILES.get("file")
        file_mime = getattr(file_obj, "content_type", "") if file_obj else ""
        file_kind = meta.get("doc_kind") or ""
        doctor_block = meta.get("doctor") or {}
    else:
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except Exception:
            return HttpResponseBadRequest("invalid json")
        meta = payload.get("meta") or {}
        analysis = payload.get("analysis") or {}
        final_text = payload.get("final_text") or ""
        final_summary = payload.get("final_summary") or ""
        file_mime = payload.get("file_mime") or ""
        file_kind = payload.get("file_kind") or ""
        doctor_block = payload.get("doctor") or {}
        file_b64 = payload.get("file_b64") or ""
        file_name = payload.get("file_name") or "document.bin"
        if file_b64:
            from django.core.files.base import ContentFile
            try:
                data = base64.b64decode(file_b64.split(",")[-1].encode("utf-8"))
                file_obj = ContentFile(data, name=file_name)
            except Exception:
                file_obj = None

    category_id = meta.get("category_id")
    specialty_id = meta.get("specialty_id")
    doc_type_id = meta.get("doc_type_id")
    if not (category_id and specialty_id and doc_type_id):
        return HttpResponseBadRequest("missing taxonomy")

    event_id = meta.get("event_id")
    existing_event = MedicalEvent.objects.filter(pk=event_id, owner=request.user).first() if event_id else None
    category = get_object_or_404(MedicalCategory, pk=category_id)
    specialty = get_object_or_404(MedicalSpecialty, pk=specialty_id)
    doc_type = get_object_or_404(DocumentType, pk=doc_type_id)

    if svc and hasattr(svc, "confirm_and_save"):
        try:
            result = svc.confirm_and_save(
                user=request.user,
                category=category,
                specialty=specialty,
                doc_type=doc_type,
                existing_event=existing_event,
                file=file_obj,
                file_mime=file_mime,
                file_kind=file_kind,
                final_text=final_text,
                final_summary=final_summary,
                analysis=analysis,
                doctor=doctor_block or None,
            )
            if isinstance(result, dict):
                return JsonResponse({"ok": True, **result})
        except Exception:
            return HttpResponseBadRequest("confirm_error")

    if not existing_event:
        existing_event = MedicalEvent.objects.create(
            patient=request.user.patient_profile,
            owner=request.user,
            category=category,
            specialty=specialty,
            doc_type=doc_type,
            event_date=now().date(),
            summary=final_summary[:255] if final_summary else "",
        )
    doc = Document.objects.create(
        owner=request.user,
        medical_event=existing_event,
        category=category,
        specialty=specialty,
        doc_type=doc_type,
        file=file_obj,
        file_mime=file_mime,
        file_size=getattr(file_obj, "size", 0) if file_obj else 0,
        doc_kind=(str(file_kind).lower() if file_kind else "other"),
        original_ocr_text=final_text or "",
        summary=final_summary[:255] if final_summary else "",
    )
    return JsonResponse({"event_id": existing_event.id, "document_id": doc.id, "ok": True})
