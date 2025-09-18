from __future__ import annotations
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpRequest, HttpResponse, JsonResponse
from django import forms
from django.template.loader import render_to_string
from django.utils.html import escape

from ..models import Document, MedicalEvent
from ..forms import DocumentEditForm, DocumentTagForm
from .utils import require_patient_profile

class MoveDocumentForm(forms.Form):
    target_event = forms.IntegerField()

@login_required
def documents(request: HttpRequest) -> HttpResponse:
    patient = require_patient_profile(request.user)
    qs = (
        Document.objects.filter(medical_event__patient=patient)
        .select_related("medical_event", "doc_type")
        .order_by("-document_date", "-id")
    )
    return render(request, "subpages/documents.html", {"documents": qs})

@login_required
def document_detail(request: HttpRequest, pk: int) -> HttpResponse:
    document_qs = (
        Document.objects.select_related("doc_type", "medical_event", "owner")
        .prefetch_related("tags")
        .filter(owner=request.user)
    )
    doc = get_object_or_404(document_qs, pk=pk)
    return render(
        request,
        "subpages/documentsubpages/document_detail.html",
        {"document": doc, "event": doc.medical_event},
    )

@login_required
def document_edit(request: HttpRequest, pk: int) -> HttpResponse:
    require_patient_profile(request.user)
    doc = get_object_or_404(Document.objects.filter(owner=request.user), pk=pk)
    if request.method == "POST":
        form = DocumentEditForm(request.POST, instance=doc)
        if form.is_valid():
            form.save()
            messages.success(request, "Документът е обновен.")
            return redirect("medj:document_detail", pk=doc.pk)
    else:
        form = DocumentEditForm(instance=doc)
    return render(request, "subpages/documentsubpages/document_edit.html", {"document": doc, "form": form})

@login_required
def document_edit_tags(request: HttpRequest, pk: int) -> HttpResponse:
    patient = require_patient_profile(request.user)
    doc = get_object_or_404(Document, pk=pk, medical_event__patient=patient)
    if request.method == "POST":
        form = DocumentTagForm(request.POST, instance=doc)
        if form.is_valid():
            form.save()
            messages.success(request, "Таговете са обновени.")
            return redirect("medj:document_detail", pk=doc.pk)
    else:
        form = DocumentTagForm(instance=doc)
    return render(request, "subpages/documentsubpages/document_edit_tags.html", {"form": form, "document": doc})


@login_required
def document_export_pdf(request: HttpRequest, pk: int) -> HttpResponse:
    doc = get_object_or_404(
        Document.objects.select_related("doc_type", "category", "medical_event"),
        pk=pk,
        owner=request.user,
    )
    body = doc.analysis_html or f"<pre>{escape((doc.analysis_text or doc.ocr_text or '').strip())}</pre>"
    html = render_to_string("subpages/documentsubpages/document_pdf.html", {"document": doc, "html": body})
    try:
        from weasyprint import HTML

        pdf = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="document_{doc.pk}.pdf"'
        return response
    except Exception:
        return HttpResponse(html, content_type="text/html")

@login_required
def document_move(request: HttpRequest, pk: int) -> HttpResponse:
    patient = require_patient_profile(request.user)
    doc = get_object_or_404(Document, pk=pk, medical_event__patient=patient)
    if request.method == "POST":
        form = MoveDocumentForm(request.POST)
        if form.is_valid():
            target_id = form.cleaned_data["target_event"]
            target_event = get_object_or_404(MedicalEvent, pk=target_id, patient=patient)
            doc.medical_event = target_event
            doc.save(update_fields=["medical_event"])
            messages.success(request, "Документът беше преместен.")
            return redirect("medj:document_detail", pk=doc.pk)
    else:
        events = MedicalEvent.objects.filter(patient=patient).order_by("-event_date", "-id")
        form = MoveDocumentForm()
        return render(request, "subpages/documentsubpages/document_move.html", {"form": form, "events": events, "document": doc})
    return redirect("medj:document_detail", pk=doc.pk)

@login_required
def delete_document(request: HttpRequest, document_id: int | str) -> JsonResponse:
    patient = require_patient_profile(request.user)
    doc = get_object_or_404(Document, pk=document_id, medical_event__patient=patient)
    doc.delete()
    return JsonResponse({"ok": True, "deleted": document_id})
