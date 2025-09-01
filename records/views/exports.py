from __future__ import annotations
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404

from ..models import Document, MedicalEvent
from records.services.print_utils import render_template_to_pdf, pdf_response

@login_required
def document_export_pdf(request: HttpRequest, pk: int) -> HttpResponse:
    doc = get_object_or_404(Document, pk=pk, owner=request.user)
    context = {"document": doc, "user": request.user}
    pdf_bytes = render_template_to_pdf(request, "subpages/document_export_pdf.html", context)
    return pdf_response(f"document_{pk}.pdf", pdf_bytes, inline=True)

@login_required
def event_export_lab_period(request: HttpRequest, pk: int) -> HttpResponse:
    event = get_object_or_404(MedicalEvent, pk=pk, patient__user=request.user)
    from .utils import parse_date
    dfrom = parse_date(request.GET.get("from"))
    dto = parse_date(request.GET.get("to"))

    from ..models import LabTestMeasurement
    qs = (LabTestMeasurement.objects
          .filter(medical_event=event)
          .select_related("indicator")
          .order_by("indicator__name", "measured_at"))
    if dfrom:
        qs = qs.filter(measured_at__gte=dfrom)
    if dto:
        qs = qs.filter(measured_at__lte=dto)

    # build_lab_matrix приемам, че е твой helper. Ако е другаде – импортирай оттам.
    from records.services.lab_utils import build_lab_matrix
    matrix = build_lab_matrix(qs)

    context = {
        "event": event,
        "period_from": dfrom,
        "period_to": dto,
        "lab_headers": matrix["headers"],
        "lab_rows": matrix["rows"],
    }
    pdf_bytes = render_template_to_pdf(request, "print/lab_period_v1.html", context)
    return pdf_response(f"event_{pk}_labs.pdf", pdf_bytes, inline=True)

@login_required
def event_export_pdf(request: HttpRequest, pk: int) -> HttpResponse:
    event = get_object_or_404(
        MedicalEvent.objects.select_related("patient__user", "specialty").prefetch_related(
            "diagnoses", "medications", "lab_measurements__indicator", "documents", "tags"
        ),
        pk=pk, patient__user=request.user
    )

    patient_name = event.patient.user.get_full_name() or event.patient.user.username
    specialty_name = event.specialty.safe_translation_getter("name", any_language=True) if event.specialty else ""

    diagnoses_rows = [
        {"Код": d.code or "", "Описание": d.text or "", "Дата": d.diagnosed_at or ""}
        for d in event.diagnoses.all()
    ]
    medications_rows = [
        {"Име": m.name or "", "Дозировка": m.dosage or "", "Начало": m.start_date or "", "Край": m.end_date or ""}
        for m in event.medications.all()
    ]
    labs_rows = [
        {"Показател": m.indicator.name, "Стойност": m.value, "Единица": m.indicator.unit or "", "Дата": m.measured_at or event.event_date}
        for m in event.lab_measurements.select_related("indicator").all()
    ]
    docs_rows = [
        {"Тип": d.doc_type.safe_translation_getter("name", any_language=True), "Дата": d.document_date, "Бележки": d.notes or ""}
        for d in event.documents.all()
    ]

    context = {
        "patient_name": patient_name,
        "event_date": event.event_date,
        "specialty_name": specialty_name,
        "event_summary": event.summary or "",
        "event_tags": [t.name for t in event.tags.all()],
        "diagnoses_headers": ["Код", "Описание", "Дата"],
        "diagnoses_rows": diagnoses_rows,
        "medications_headers": ["Име", "Дозировка", "Начало", "Край"],
        "medications_rows": medications_rows,
        "labs_headers": ["Показател", "Стойност", "Единица", "Дата"],
        "labs_rows": labs_rows,
        "docs_headers": ["Тип", "Дата", "Бележки"],
        "docs_rows": docs_rows,
    }

    pdf_bytes = render_template_to_pdf(request, "print/event_v1.html", context)
    return pdf_response(f"event_{pk}.pdf", pdf_bytes, inline=True)

from django.shortcuts import render

def print_csv(request):

    context = {
        "filters": request.GET,
        "columns": ["Дата", "Показател", "Стойност", "Единица", "Реф. интервал", "Отклонение"],
        "rows": [],
    }
    return render(request, "subpages/csv_print.html", context)

def print_pdf(request):

    context = {"filters": request.GET}
    return render(request, "subpages/document_export_pdf.html", context)

