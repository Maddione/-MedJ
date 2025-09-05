from __future__ import annotations
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render

from records.services.csv_to_pdf import csv_to_pdf_with_template

PDF_DIR = Path(settings.BASE_DIR) / "records" / "pdf_templates"
PDF_BG = PDF_DIR / "pdf-template-bg.pdf"


@login_required
def csv_print_page(request):
    return render(request, "subpages/csv_print.html")


@login_required
def csv_print_to_pdf(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST expected")
    if not PDF_BG.exists():
        return HttpResponseBadRequest("Missing pdf-template-bg.pdf")

    kind = (request.POST.get("kind") or "events").strip()
    f = request.FILES.get("csv")
    if not f:
        return HttpResponseBadRequest("No CSV file uploaded")

    pdf_bytes = csv_to_pdf_with_template(f, kind, str(PDF_BG))
    resp = HttpResponse(pdf_bytes, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="MedJ-{kind}.pdf"'
    return resp
