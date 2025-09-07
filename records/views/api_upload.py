import io
import os
import json
import time
from datetime import date
from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils.timezone import now
from django.utils.dateparse import parse_date
from django.utils.translation import gettext as _
from ..models import MedicalEvent, MedicalCategory, MedicalSpecialty, DocumentType, Document, OcrLog
import requests

try:
    from google.cloud import vision as gvision
except Exception:
    gvision = None


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


def _ocr_with_vision(fileobj, filename):
    if gvision is None:
        return None
    client = gvision.ImageAnnotatorClient()
    data = fileobj.read()
    fileobj.seek(0)
    image = gvision.Image(content=data)
    if filename.lower().endswith(".pdf"):
        try:
            from google.cloud.vision_v1 import types
        except Exception:
            return None
        try:
            req = gvision.AnnotateFileRequest(
                requests=[gvision.AnnotateImageRequest(image=image, features=[gvision.Feature(type_=gvision.Feature.Type.DOCUMENT_TEXT_DETECTION)])]
            )
            resp = client.batch_annotate_files(requests=[req])
            pages = []
            for r in resp.responses:
                for p in getattr(r.responses[0], "full_text_annotation", None).pages or []:
                    pages.append(p)
            text = getattr(resp.responses[0].responses[0].full_text_annotation, "text", "") if resp.responses else ""
            return text or None
        except Exception:
            return None
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
        return j.get("ocr_text") or ""
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
    source = "vision"
    text = _ocr_with_vision(f, f.name)
    if not text:
        source = "flask"
        text = _ocr_with_flask(f, f.name)
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
    specialty_id = payload.get("specialty")
    summary = (text or "").strip().splitlines()
    summary = " ".join(summary)[:400]
    data = {
        "summary": summary,
        "event_date": now().date().strftime("%Y-%m-%d"),
        "detected_specialty": "",
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
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("invalid json")
    meta = payload.get("meta") or {}
    analysis = payload.get("analysis") or {}
    final_text = payload.get("final_text") or ""
    event_id = meta.get("event_id")
    category_id = meta.get("category_id")
    specialty_id = meta.get("specialty_id")
    doc_type_id = meta.get("doc_type_id")
    if not (category_id and specialty_id and doc_type_id):
        return HttpResponseBadRequest("missing taxonomy")
    if event_id:
        try:
            ev = MedicalEvent.objects.get(pk=event_id, owner=request.user)
        except MedicalEvent.DoesNotExist:
            ev = None
    else:
        ev = None
    if not ev:
        try:
            cat = MedicalCategory.objects.get(pk=category_id)
            spe = MedicalSpecialty.objects.get(pk=specialty_id)
            dt = DocumentType.objects.get(pk=doc_type_id)
        except Exception:
            return HttpResponseBadRequest("invalid taxonomy")
        ev = MedicalEvent.objects.create(
            patient=request.user.patient_profile,
            owner=request.user,
            specialty=spe,
            category=cat,
            doc_type=dt,
            event_date=now().date(),
            summary=analysis.get("summary") or "",
        )
    doc = Document.objects.create(
        owner=request.user,
        medical_event=ev,
        specialty=ev.specialty,
        category=ev.category,
        doc_type=ev.doc_type,
        original_ocr_text=final_text or "",
        summary=(analysis.get("summary") or "")[:255],
        file_size=0,
        file_mime="",
        doc_kind="other",
    )
    return JsonResponse({"ok": True, "event_id": ev.id, "document_id": doc.id})
