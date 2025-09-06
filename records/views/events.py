from __future__ import annotations
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.http import HttpRequest, HttpResponse, JsonResponse

from ..models import MedicalEvent, LabTestMeasurement, LabIndicator
from .utils import require_patient_profile

@login_required
def event_list(request: HttpRequest) -> HttpResponse:
    patient = require_patient_profile(request.user)
    tag_param = request.GET.get("tag")
    search_q = request.GET.get("q")
    qs = MedicalEvent.objects.filter(patient=patient).select_related("specialty").order_by("-event_date", "-id")
    if search_q:
        qs = qs.filter(summary__icontains=search_q)
    if tag_param:
        qs = qs.filter(tags__name__iexact=tag_param).distinct()
    return render(request, "subpages/event_list.html", {"medical_events": qs, "tags_query": tag_param, "search_query": search_q})

@login_required
def event_detail(request: HttpRequest, pk: int) -> HttpResponse:
    patient = require_patient_profile(request.user)
    event = get_object_or_404(
        MedicalEvent.objects.select_related("specialty", "patient").prefetch_related(
            "documents", "diagnoses", "treatment_plans", "narrative_sections", "medications", "tags"
        ),
        pk=pk, patient=patient,
    )
    measurements = (
        LabTestMeasurement.objects.filter(medical_event=event)
        .select_related("indicator")
        .order_by("indicator__name", "measured_at")
    )
    return render(request, "subpages/eventsubpages/event_detail.html", {"medical_event": event, "measurements": measurements, "documents": event.documents.all()})

@login_required
def event_history(request: HttpRequest, pk: int | None = None) -> HttpResponse:
    return event_list(request)

@login_required
def update_event_details(request: HttpRequest, event_id: int | None = None, pk: int | None = None) -> JsonResponse:

    return JsonResponse({"ok": True})

@login_required
def events_by_specialty(request: HttpRequest) -> JsonResponse:
    patient = require_patient_profile(request.user)
    spec_val = request.GET.get("specialty_id") or request.GET.get("specialty")
    try:
        spec_id = int(spec_val)
    except (TypeError, ValueError):
        return JsonResponse({"results": []})
    qs = MedicalEvent.objects.filter(patient=patient, specialty_id=spec_id).order_by("-event_date", "-id")
    results = [
        {"id": e.id, "date": e.event_date.strftime("%Y-%m-%d") if e.event_date else "", "summary": e.summary or ""}
        for e in qs
    ]
    return JsonResponse({"results": results})

@login_required
def tags_autocomplete(request: HttpRequest) -> JsonResponse:
    from ..models import Tag
    q = request.GET.get("q") or ""
    if not q:
        return JsonResponse({"results": []})
    data = [{"id": t.id, "name": t.name} for t in Tag.objects.filter(name__icontains=q).order_by("name")[:20]]
    return JsonResponse({"results": data})
