from __future__ import annotations
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpRequest, HttpResponse

from ..models import MedicalEvent, LabIndicator, LabTestMeasurement
from ..forms import LabTestMeasurementForm
from .utils import require_patient_profile, parse_date

@login_required
def labtests(request: HttpRequest) -> HttpResponse:
    return render(request, "subpages/labtests.html")

@login_required
def labtests_view(request: HttpRequest, event_id: int | str) -> HttpResponse:
    patient = require_patient_profile(request.user)
    event = get_object_or_404(MedicalEvent, pk=event_id, patient=patient)
    indicators = LabIndicator.objects.all().order_by("name")
    series: dict[str, list[dict]] = {}
    qs = (
        LabTestMeasurement.objects.filter(medical_event=event)
        .select_related("indicator")
        .order_by("indicator__name", "measured_at")
    )
    for m in qs:
        key = m.indicator.name
        series.setdefault(key, []).append({
            "date": m.measured_at.isoformat() if m.measured_at else "",
            "value": float(m.value),
            "unit": m.indicator.unit or "",
            "abn": m.is_abnormal,
        })
    return render(request, "subpages/labtests.html", {"medical_event": event, "series": series, "indicators": indicators})

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
    rows = ["date,indicator,value,unit\n"]
    content = "".join(rows).encode("utf-8")
    from django.http import HttpResponse
    resp = HttpResponse(content, content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename="labs.csv"'
    return resp
