from __future__ import annotations

import csv
from io import StringIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect

from ..forms import LabTestMeasurementForm
from ..models import LabIndicator, LabTestMeasurement, MedicalEvent
from .utils import parse_date, require_patient_profile


@login_required
def labtests(request: HttpRequest) -> HttpResponse:
    require_patient_profile(request.user)
    indicators = (
        LabIndicator.objects.filter(is_active=True)
        .prefetch_related("translations")
        .order_by("translations__name", "id")
    )
    return render(
        request,
        "subpages/labtestssubpages/labtests.html",
        {"indicators": indicators, "medical_event": None},
    )


@login_required
def labtests_view(request: HttpRequest, event_id: int | str) -> HttpResponse:
    patient = require_patient_profile(request.user)
    event = get_object_or_404(MedicalEvent, pk=event_id, patient=patient)

    indicators = (
        LabIndicator.objects.filter(is_active=True)
        .prefetch_related("translations")
        .order_by("translations__name", "id")
    )
    series: dict[str, list[dict]] = {}

    qs = (
        LabTestMeasurement.objects.filter(medical_event=event)
        .select_related("indicator")
        .order_by("indicator__name", "measured_at")
    )
    for m in qs:
        name = m.indicator.safe_translation_getter("name", any_language=True) or m.indicator.slug
        key = name
        series.setdefault(key, []).append(
            {
                "date": m.measured_at.isoformat() if m.measured_at else "",
                "value": float(m.value),
                "unit": m.indicator.unit or "",
                "abn": m.is_abnormal,
            }
        )

    return render(
        request,
        "subpages/labtestssubpages/labtests.html",
        {"medical_event": event, "series": series, "indicators": indicators},
    )


@login_required
def labtest_edit(request: HttpRequest, event_id: int | str) -> HttpResponse:
    patient = require_patient_profile(request.user)
    event = get_object_or_404(MedicalEvent, pk=event_id, patient=patient)

    if request.method == "POST":
        form = LabTestMeasurementForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.medical_event = event
            obj.save()
            messages.success(request, "Записано.")
            return redirect("medj:labtests_view", event_id=event.id)
    else:
        form = LabTestMeasurementForm(initial={"medical_event": event.id})

    return render(request, "subpages/labtest_edit.html", {"event": event, "form": form})


@login_required
def export_lab_csv(request: HttpRequest) -> HttpResponse:
    patient = require_patient_profile(request.user)
    event_id = request.GET.get("event")
    codes_raw = (request.GET.get("codes") or "").strip()
    from_raw = (request.GET.get("from") or "").strip()
    to_raw = (request.GET.get("to") or "").strip()

    indicator_slugs = [slug.strip() for slug in codes_raw.split(",") if slug.strip()]
    date_from = parse_date(from_raw) if from_raw else None
    date_to = parse_date(to_raw) if to_raw else None

    measurements = LabTestMeasurement.objects.filter(medical_event__patient=patient).select_related("indicator", "medical_event")
    if event_id and str(event_id).isdigit():
        measurements = measurements.filter(medical_event_id=int(event_id))
    if indicator_slugs:
        measurements = measurements.filter(indicator__slug__in=indicator_slugs)
    if date_from:
        measurements = measurements.filter(measured_at__date__gte=date_from)
    if date_to:
        measurements = measurements.filter(measured_at__date__lte=date_to)

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["event_id", "event_date", "indicator", "value", "unit", "measured_at"])
    for item in measurements.order_by("measured_at", "id"):
        indicator_name = item.indicator.safe_translation_getter("name", any_language=True) or item.indicator.slug
        measured_at = item.measured_at.isoformat() if item.measured_at else ""
        event_date = item.medical_event.event_date.isoformat() if item.medical_event and item.medical_event.event_date else ""
        writer.writerow([
            item.medical_event_id,
            event_date,
            indicator_name,
            item.value,
            item.indicator.unit or "",
            measured_at,
        ])

    resp = HttpResponse(buffer.getvalue(), content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="lab-results.csv"'
    return resp
