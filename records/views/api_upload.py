import base64
import io
import json
import logging
import time
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from records.models import MedicalCategory, MedicalSpecialty, DocumentType, MedicalEvent
from records.services.upload_flow import vision_ocr_first_fallback_flask, confirm_and_save
from records.services.llm.anonymizer import anonymize_text
from records.services.llm.gpt_client import analyze_text

log = logging.getLogger("records.upload")

def _ip(request):
    x = request.META.get("HTTP_X_FORWARDED_FOR")
    if x:
        return x.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or "0.0.0.0"

def _rl_key(user_id, name, ip):
    return f"rl_{name}_{user_id or 0}_{ip}"

def _rate_limited(request, name, max_per_window=20, window_seconds=120):
    user_id = request.user.id if request.user.is_authenticated else 0
    key = _rl_key(user_id, name, _ip(request))
    v = cache.get(key)
    if not v:
        cache.set(key, 1, timeout=window_seconds)
        return False
    if v >= max_per_window:
        return True
    cache.incr(key, 1)
    return False

@login_required
@csrf_exempt
@require_POST
def upload_ocr(request):
    if _rate_limited(request, "ocr", 15, 120):
        return HttpResponseBadRequest("rate_limited")
    t0 = time.time()
    f = request.FILES.get("file")
    file_kind = request.POST.get("file_kind") or "other"
    category_id = request.POST.get("category_id")
    specialty_id = request.POST.get("specialty_id")
    doc_type_id = request.POST.get("doc_type_id")
    if not f or not category_id or not specialty_id or not doc_type_id:
        return HttpResponseBadRequest("missing_params")
    text, source = vision_ocr_first_fallback_flask(f)
    dt = int((time.time() - t0) * 1000)
    log.info("ocr user=%s kind=%s src=%s ms=%s size=%s", request.user.id, file_kind, source, dt, getattr(f, "size", None))
    return JsonResponse({"ocr_text": text or "", "source": source or ""})

@login_required
@csrf_exempt
@require_POST
def upload_analyze(request):
    if _rate_limited(request, "analyze", 30, 120):
        return HttpResponseBadRequest("rate_limited")
    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("invalid_json")
    text = body.get("text") or ""
    specialty_id = body.get("specialty_id")
    if not text or not specialty_id:
        return HttpResponseBadRequest("missing_params")
    specialty = get_object_or_404(MedicalSpecialty, id=specialty_id)
    t0 = time.time()
    anon = anonymize_text(text)
    res = analyze_text(anon, specialty_id=specialty.id)
    dt = int((time.time() - t0) * 1000)
    log.info("analyze user=%s specialty=%s ms=%s", request.user.id, specialty.id, dt)
    return JsonResponse(res or {"summary": "", "data": {"summary": "", "suggested_tags": []}})

@login_required
@csrf_exempt
@require_POST
def upload_confirm(request):
    if _rate_limited(request, "confirm", 20, 120):
        return HttpResponseBadRequest("rate_limited")
    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("invalid_json")
    category = get_object_or_404(MedicalCategory, id=body.get("category_id"))
    specialty = get_object_or_404(MedicalSpecialty, id=body.get("specialty_id"))
    doc_type = get_object_or_404(DocumentType, id=body.get("doc_type_id"))
    ev = None
    if body.get("event_id"):
        ev = get_object_or_404(MedicalEvent, id=body["event_id"], owner=request.user)
    final_text = body.get("final_text") or ""
    final_summary = body.get("final_summary") or ""
    analysis = body.get("analysis") or {}
    file_b64 = body.get("file_b64") or ""
    file_name = body.get("file_name") or "document.bin"
    file_mime = body.get("file_mime") or "application/octet-stream"
    file_kind = body.get("file_kind") or "other"
    try:
        raw = base64.b64decode(file_b64.encode("utf-8"))
    except Exception:
        raw = b""
    file_obj = ContentFile(raw, name=file_name)
    t0 = time.time()
    ids = confirm_and_save(
        user=request.user,
        category=category,
        specialty=specialty,
        doc_type=doc_type,
        existing_event=ev,
        file=file_obj,
        file_mime=file_mime,
        file_kind=file_kind,
        final_text=final_text,
        final_summary=final_summary,
        analysis=analysis,
    )
    dt = int((time.time() - t0) * 1000)
    log.info("confirm user=%s event=%s document=%s ms=%s", request.user.id, ids.get("event_id"), ids.get("document_id"), dt)
    return JsonResponse({"ok": True, **ids})

@login_required
@require_GET
def events_suggest(request):
    category_id = request.GET.get("category_id")
    specialty_id = request.GET.get("specialty_id")
    doc_type_id = request.GET.get("doc_type_id")
    if not category_id or not specialty_id or not doc_type_id:
        return JsonResponse({"events": []})
    qs = MedicalEvent.objects.filter(
        owner=request.user,
        category_id=category_id,
        specialty_id=specialty_id,
        doc_type_id=doc_type_id,
    ).order_by("-event_date", "-id")[:20]
    items = []
    for e in qs:
        items.append({"id": e.id, "event_date": e.event_date.strftime("%d-%m-%Y") if e.event_date else ""})
    return JsonResponse({"events": items})
