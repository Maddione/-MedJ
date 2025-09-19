from __future__ import annotations

import csv
from io import StringIO
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse

from ..forms import LabTestMeasurementForm
from ..models import LabIndicator, LabTestMeasurement, MedicalEvent
from .utils import parse_date, require_patient_profile


def _indicator_label(indicator: LabIndicator) -> str:
    getter = getattr(indicator, "safe_translation_getter", None)
    if callable(getter):
        try:
            label = getter("name", any_language=True)
            if label:
                return str(label)
        except Exception:
            pass
    return (getattr(indicator, "name", None) or indicator.slug or "").strip()


def _indicator_queryset(patient, event=None):
    qs = LabIndicator.objects.filter(measurements__medical_event__patient=patient)
    if event is not None:
        qs = qs.filter(measurements__medical_event=event)
    qs = qs.prefetch_related("translations").distinct()
    return qs.order_by("translations__name", "slug")


def _parse_filter_params(request: HttpRequest):
    selected = [slug for slug in request.GET.getlist("indicator") if str(slug).strip()]
    start_raw = (request.GET.get("start_date") or "").strip()
    end_raw = (request.GET.get("end_date") or "").strip()
    start_dt = parse_date(start_raw) if start_raw else None
    end_dt = parse_date(end_raw) if end_raw else None
    return selected, start_raw, end_raw, start_dt, end_dt


def _coerce_bool(value, default=False):
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _build_measurement_rows(qs):
    rows = []
    for measurement in qs:
        indicator = measurement.indicator
        event = measurement.medical_event
        rows.append(
            {
                "object": measurement,
                "indicator_name": _indicator_label(indicator),
                "indicator_slug": indicator.slug,
                "value": measurement.value,
                "unit": indicator.unit or "",
                "measured_at": measurement.measured_at,
                "event": event,
                "event_summary": getattr(event, "summary", ""),
                "event_date": getattr(event, "event_date", None),
                "abnormal_flag": measurement.abnormal_flag,
                "reference_low": indicator.reference_low,
                "reference_high": indicator.reference_high,
            }
        )
    return rows


def _labtests_context(request: HttpRequest, patient, base_qs, event=None):
    selected, start_raw, end_raw, start_dt, end_dt = _parse_filter_params(request)
    qs = base_qs
    if selected:
        qs = qs.filter(indicator__slug__in=selected)
    if start_dt:
        qs = qs.filter(measured_at__date__gte=start_dt)
    if end_dt:
        qs = qs.filter(measured_at__date__lte=end_dt)
    qs = qs.select_related("indicator", "medical_event").order_by("-measured_at", "-id")
    measurements = list(qs)
    indicator_qs = _indicator_queryset(patient, event)
    indicator_options = [
        {
            "slug": ind.slug,
            "label": _indicator_label(ind),
            "checked": ind.slug in selected,
        }
        for ind in indicator_qs
    ]
    indicator_options.sort(key=lambda x: x["label"].lower())

    csv_params = []
    for slug in selected:
        csv_params.append(("indicator", slug))
    if start_raw:
        csv_params.append(("start_date", start_raw))
    if end_raw:
        csv_params.append(("end_date", end_raw))
    if event:
        csv_params.append(("event", str(event.id)))
    csv_params.append(("download", "1"))
    csv_url = reverse("medj:export_lab_csv")
    csv_download_url = f"{csv_url}?{urlencode(csv_params, doseq=True)}"

    return {
        "medical_event": event,
        "measurements": _build_measurement_rows(measurements),
        "indicators": indicator_options,
        "selected_indicators": set(selected),
        "start_date": start_raw,
        "end_date": end_raw,
        "csv_download_url": csv_download_url,
        "has_filters": bool(selected or start_raw or end_raw),
        "total_measurements": len(measurements),
    }


@login_required
def labtests(request: HttpRequest) -> HttpResponse:
    patient = require_patient_profile(request.user)
    base_qs = LabTestMeasurement.objects.filter(medical_event__patient=patient)
    context = _labtests_context(request, patient, base_qs, event=None)
    return render(request, "subpages/labtestssubpages/labtests.html", context)


@login_required
def labtests_view(request: HttpRequest, event_id: int | str) -> HttpResponse:
    patient = require_patient_profile(request.user)
    event = get_object_or_404(MedicalEvent, pk=event_id, patient=patient)
    base_qs = LabTestMeasurement.objects.filter(medical_event=event)
    context = _labtests_context(request, patient, base_qs, event=event)
    return render(request, "subpages/labtestssubpages/labtests.html", context)


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
    download = _coerce_bool(request.GET.get("download"), default=False)
    selected, start_raw, end_raw, start_dt, end_dt = _parse_filter_params(request)
    event_raw = request.GET.get("event")
    base_qs = LabTestMeasurement.objects.filter(medical_event__patient=patient)
    event_obj = None
    if event_raw and str(event_raw).isdigit():
        event_id = int(event_raw)
        base_qs = base_qs.filter(medical_event_id=event_id)
        event_obj = MedicalEvent.objects.filter(pk=event_id, patient=patient).first()

    qs = base_qs
    if selected:
        qs = qs.filter(indicator__slug__in=selected)
    if start_dt:
        qs = qs.filter(measured_at__date__gte=start_dt)
    if end_dt:
        qs = qs.filter(measured_at__date__lte=end_dt)
    qs = qs.select_related("indicator", "medical_event").order_by("measured_at", "id")
    measurements = list(qs)

    only_abnormal = _coerce_bool(request.GET.get("only_abnormal"), default=False)
    if only_abnormal:
        measurements = [m for m in measurements if m.abnormal_flag]

    separator_choice = (request.GET.get("separator") or "comma").lower()
    if separator_choice in {";", "semicolon"}:
        delimiter = ";"
        separator_choice = "semicolon"
    elif separator_choice in {"\\t", "tab"}:
        delimiter = "\t"
        separator_choice = "tab"
    else:
        delimiter = ","
        separator_choice = "comma"

    decimal_choice_raw = (request.GET.get("decimal") or ".").strip()
    if decimal_choice_raw in {",", "comma"}:
        decimal_char = ","
        decimal_choice = ","
    else:
        decimal_char = "."
        decimal_choice = "."

    include_header = _coerce_bool(request.GET.get("header"), default=True)

    def format_decimal(value):
        if value in (None, ""):
            return ""
        if isinstance(value, (int, float)):
            text = f"{value:.6f}".rstrip("0").rstrip(".")
        else:
            text = str(value)
        if decimal_char != ".":
            text = text.replace(".", decimal_char)
        return text

    if download:
        buffer = StringIO()
        writer = csv.writer(buffer, delimiter=delimiter)
        if include_header:
            writer.writerow([
                "event_id",
                "event_date",
                "indicator_slug",
                "indicator_name",
                "value",
                "unit",
                "reference_low",
                "reference_high",
                "measured_at",
                "abnormal_flag",
            ])
        for item in measurements:
            indicator = item.indicator
            event = item.medical_event
            indicator_name = _indicator_label(indicator)
            measured_at = item.measured_at.isoformat() if item.measured_at else ""
            event_date = event.event_date.isoformat() if event and event.event_date else ""
            writer.writerow([
                item.medical_event_id,
                event_date,
                indicator.slug,
                indicator_name,
                format_decimal(item.value),
                indicator.unit or "",
                format_decimal(indicator.reference_low),
                format_decimal(indicator.reference_high),
                measured_at,
                item.abnormal_flag,
            ])
        resp = HttpResponse(buffer.getvalue(), content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="lab-results.csv"'
        return resp

    indicator_options = [
        {
            "slug": ind.slug,
            "label": _indicator_label(ind),
            "checked": ind.slug in selected,
        }
        for ind in _indicator_queryset(patient, event_obj)
    ]
    indicator_options.sort(key=lambda x: x["label"].lower())

    context = {
        "indicators": indicator_options,
        "selected_indicators": set(selected),
        "start_date": start_raw,
        "end_date": end_raw,
        "include_header": include_header,
        "only_abnormal": only_abnormal,
        "separator": separator_choice,
        "decimal": decimal_choice,
        "result_count": len(measurements),
    }
    return render(request, "subpages/labtestssubpages/labtests_export_csv.html", context)
