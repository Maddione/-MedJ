import csv
import io
import json
import os
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone
from records.models import MedicalEvent, Document, Tag, DocumentTag, Practitioner, DocumentPractitioner, LabIndicator, LabTestMeasurement, ShareLink, EventTag

def _fmt_ddmmyyyy(d):
    return d.strftime("%d-%m-%Y")

def _parse_ddmmyyyy(s):
    return datetime.strptime(s, "%d-%m-%Y").date()

def _get_user(request):
    return request.user

@csrf_exempt
@require_POST
@login_required
def api_upload_ocr(request):
    text = ""
    source = "vision"
    file = request.FILES.get("file")
    if file:
        text = ""
        source = "vision"
    return JsonResponse({"ocr_text": text, "source": source})

@csrf_exempt
@require_POST
@login_required
def api_upload_analyze(request):
    body = json.loads(request.body.decode("utf-8"))
    ocr_text = body.get("ocr_text") or ""
    specialty_id = body.get("specialty_id")
    summary = ocr_text[:500]
    data = {
        "summary": summary,
        "event_date": timezone.now().date().isoformat(),
        "detected_specialty": str(specialty_id) if specialty_id else "",
        "suggested_tags": [],
        "blood_test_results": [],
        "diagnosis": "",
        "treatment_plan": "",
        "doctors": [],
        "date_created": timezone.now().date().isoformat(),
    }
    return JsonResponse({"summary": summary, "data": data})

@csrf_exempt
@require_POST
@login_required
@transaction.atomic
def api_upload_confirm(request):
    user = _get_user(request)
    body = json.loads(request.body.decode("utf-8"))
    ocr_text = body.get("ocr_text") or ""
    summary_text = body.get("summary") or ""
    event_id = body.get("event_id")
    date_created = body.get("date_created")
    category = body.get("category")
    specialty = body.get("specialty")
    doc_type = body.get("doc_type")
    doc_kind = body.get("doc_kind")
    if event_id:
        event = get_object_or_404(MedicalEvent, id=event_id, owner=user)
    else:
        event = MedicalEvent.objects.create(owner=user, patient=user.patient_profile, specialty_id=specialty, category_id=category, doc_type_id=doc_type, event_date=timezone.now().date())
    document = Document.objects.create(
        owner=user,
        medical_event=event,
        original_ocr_text=ocr_text,
        summary=summary_text,
        doc_kind=doc_kind,
        specialty_id=specialty,
        category_id=category,
        doc_type_id=doc_type
    )
    perms = []
    if date_created:
        try:
            dc = _parse_ddmmyyyy(date_created)
        except ValueError:
            dc = None
        if dc:
            document.date_created = dc
            document.save(update_fields=["date_created"])
            perms.append(("date", _fmt_ddmmyyyy(dc)))
    for cat, name in perms:
        tag, _ = Tag.objects.get_or_create(slug=name, kind=cat, defaults={"is_active": True})
        DocumentTag.objects.get_or_create(document=document, tag=tag, defaults={"is_permanent": True})
        EventTag.objects.get_or_create(event=event, tag=tag)
    labs = body.get("blood_test_results") or []
    for item in labs:
        indicator_name = item.get("indicator_name") or ""
        val = item.get("value")
        unit = item.get("unit") or ""
        try:
            value = float(val)
        except Exception:
            continue
        ind, _ = LabIndicator.objects.get_or_create(slug=indicator_name.lower().strip().replace(" ", "_"), defaults={"unit": unit})
        LabTestMeasurement.objects.create(medical_event=event, indicator=ind, value=value, measured_at=timezone.now())
    return JsonResponse({"ok": True, "event_id": event.id, "document_id": document.id})

@require_GET
@login_required
def api_events_suggest(request):
    user = _get_user(request)
    category = request.GET.get("category_id")
    specialty = request.GET.get("specialty_id")
    doc_type = request.GET.get("doc_type_id")
    qs = MedicalEvent.objects.filter(owner=user).order_by("-event_date")
    results = []
    for e in qs[:50]:
        results.append({"id": e.id, "event_date": _fmt_ddmmyyyy(e.event_date), "title": str(e)})
    return JsonResponse({"results": results})

@require_GET
@login_required
def api_doctors_suggest(request):
    user = _get_user(request)
    q = request.GET.get("q", "").strip()
    specialty_id = request.GET.get("specialty_id")
    qs = Practitioner.objects.filter(owner=user, is_active=True)
    if q:
        qs = qs.filter(full_name__icontains=q)
    if specialty_id:
        try:
            s = int(specialty_id)
            qs = qs.filter(specialty_id=s)
        except Exception:
            pass
    data = [{"id": p.id, "name": p.full_name} for p in qs.order_by("full_name")[:20]]
    return JsonResponse({"results": data})

@csrf_exempt
@require_POST
@login_required
def api_share_create(request):
    user = _get_user(request)
    body = json.loads(request.body.decode("utf-8"))
    object_type = body.get("object_type")
    object_id = int(body.get("object_id"))
    fmt = body.get("format") or "html"
    sl = ShareLink.objects.create(owner=user, object_type=object_type, object_id=object_id, format=fmt)
    url = f"/s/{sl.token}/"
    return JsonResponse({"url": url, "token": sl.token})

@require_GET
def public_share_view(request, token):
    sl = get_object_or_404(ShareLink, token=token, status="active")
    if sl.expires_at and sl.expires_at < timezone.now():
        raise Http404
    if sl.object_type == "event":
        obj = get_object_or_404(MedicalEvent, id=sl.object_id)
        return render(request, "main/share_event.html", {"event": obj, "share": sl})
    obj = get_object_or_404(Document, id=sl.object_id)
    return render(request, "main/share_document.html", {"document": obj, "share": sl})

@require_GET
@login_required
def api_export_csv(request):
    user = _get_user(request)
    event_id = request.GET.get("event_id")
    if not event_id:
        return JsonResponse({"error": "event_id required"}, status=400)
    event = get_object_or_404(MedicalEvent, id=event_id, owner=user)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["event_id", "event_date", "indicator_name", "value", "unit", "reference_low", "reference_high", "measured_at", "tags"])
    tags = [f"{t.kind}:{t.slug}" for t in event.tags.all()]
    for m in event.labtests.select_related("indicator"):
        writer.writerow([event.id, _fmt_ddmmyyyy(event.event_date), m.indicator.slug, m.value, m.indicator.unit or "", m.indicator.reference_low or "", m.indicator.reference_high or "", _fmt_ddmmyyyy(m.measured_at.date()), ";".join(tags)])
    resp = HttpResponse(output.getvalue(), content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="event_{event.id}.csv"'
    return resp
