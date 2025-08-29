import csv
import io
import qrcode
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _l
from django.views.decorators.http import require_POST
from weasyprint import HTML
from .forms import (
    RegisterForm,
    DocumentUploadForm,
    EventTagForm,
    DocumentTagForm,
    MoveDocumentForm,
    DocumentEditForm,
)
from .models import (
    MedicalEvent,
    MedicalSpecialty,
    Document,
    Tag,
    DocumentTag,
    LabIndicator,
    LabTestMeasurement,
    PractitionerProfile,
    ShareToken,
)

def _require_patient_profile(user):
    if not hasattr(user, "patient_profile"):
        return None
    return user.patient_profile

def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, _l("Регистрацията е успешна."))
            return redirect("medj:landing")
        else:
            messages.error(request, _l("Моля, коригирайте грешките във формата."))
    else:
        form = RegisterForm()
    return render(request, "auth/register.html", {"form": form})

def custom_login_view(request):
    if request.user.is_authenticated:
        return redirect("medj:dashboard")
    from django.contrib.auth.views import LoginView
    return LoginView.as_view(template_name="auth/login.html")(request)

def custom_logout_view(request):
    logout(request)
    return redirect("medj:landing")

@login_required
def dashboard(request):
    """
    Минимална динамика за началното табло:
    - брой събития
    - брой документи
    - последни 5 събития/документа
    """
    patient = _require_patient_profile(request.user)
    if not patient:
        return HttpResponseForbidden()

    events_qs = MedicalEvent.objects.filter(patient=patient).order_by("-event_date", "-id")
    docs_qs = Document.objects.filter(medical_event__patient=patient).order_by("-uploaded_at", "-id")

    ctx = {
        "events_count": events_qs.count(),
        "documents_count": docs_qs.count(),
        "recent_events": events_qs.select_related("specialty")[:5],
        "recent_documents": docs_qs.select_related("doc_type", "medical_event")[:5],
    }
    return render(request, "main/dashboard.html", ctx)

@login_required
def upload_document(request):
    patient = _require_patient_profile(request.user)
    if not patient:
        return HttpResponseForbidden()
    if request.method == "POST":
        form = DocumentUploadForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            specialty = form.cleaned_data["specialty"]
            doc_type = form.cleaned_data["doc_type"]
            practitioner = form.cleaned_data.get("practitioner")
            document_date = form.cleaned_data["document_date"]
            attach_to_event = form.cleaned_data.get("attach_to_event")
            file = form.cleaned_data["file"]
            with transaction.atomic():
                if attach_to_event:
                    event = attach_to_event
                else:
                    event = MedicalEvent.objects.create(
                        patient=patient,
                        specialty=specialty,
                        event_date=document_date,
                    )
                doc = Document.objects.create(
                    medical_event=event,
                    doc_type=doc_type,
                    practitioner=practitioner,
                    document_date=document_date,
                    file=file,
                    doc_kind=("pdf" if str(file.name).lower().endswith(".pdf") else "image"),
                )
            messages.success(request, _l("Документът е качен успешно."))
            return redirect("medj:medical_event_detail", pk=event.pk)
    else:
        form = DocumentUploadForm(user=request.user)
    return render(request, "main/upload.html", {"form": form})

@login_required
def events_by_specialty(request):
    patient = _require_patient_profile(request.user)
    if not patient:
        return JsonResponse({"results": []})
    try:
        spec_id = int(request.GET.get("specialty"))
    except (TypeError, ValueError):
        return JsonResponse({"results": []})
    qs = MedicalEvent.objects.filter(patient=patient, specialty_id=spec_id).order_by("-event_date")
    results = [{"id": e.id, "date": e.event_date.strftime("%Y-%m-%d"), "summary": e.summary or ""} for e in qs]
    return JsonResponse({"results": results})

@login_required
def event_list(request):
    patient = _require_patient_profile(request.user)
    if not patient:
        return HttpResponseForbidden()
    qs = MedicalEvent.objects.filter(patient=patient).select_related("specialty", "patient__user").prefetch_related("tags", "documents")
    tag_param = request.GET.get("tags", "").strip()
    search_q = request.GET.get("q", "").strip()
    if tag_param:
        names = [t.strip() for t in tag_param.split(",") if t.strip()]
        if names:
            qs = qs.filter(tags__name__in=names).distinct()
    if search_q:
        qs = qs.filter(
            Q(summary__icontains=search_q) |
            Q(tags__name__icontains=search_q) |
            Q(specialty__translations__name__icontains=search_q)  # i18n
        ).distinct()
    qs = qs.order_by("-event_date", "-id")
    return render(request, "subpages/event_history.html", {"medical_events": qs, "tags_query": tag_param, "search_query": search_q})

@login_required
def event_detail(request, pk):
    patient = _require_patient_profile(request.user)
    if not patient:
        return HttpResponseForbidden()
    event = get_object_or_404(MedicalEvent, pk=pk, patient=patient)
    docs = event.documents.select_related("doc_type", "practitioner").all().order_by("-document_date", "-uploaded_at")
    diagnoses = event.diagnoses.all()
    treatment_plans = event.treatment_plans.all()
    narrative_sections = event.narrative_sections.all()
    tags_for_event = event.tags.all()
    blood_test_results = LabTestMeasurement.objects.filter(event=event).select_related("indicator").order_by("-measured_at")
    source_document = docs.first()
    ctx = {
        "medical_event": event,
        "blood_test_results": blood_test_results,
        "narrative_sections": narrative_sections,
        "diagnoses": diagnoses,
        "treatment_plans": treatment_plans,
        "tags_for_event": tags_for_event,
        "source_document": source_document,
    }
    return render(request, "subpages/event_detail.html", ctx)

@login_required
def medical_event_delete(request, pk):
    patient = _require_patient_profile(request.user)
    if not patient:
        return HttpResponseForbidden()
    event = get_object_or_404(MedicalEvent, pk=pk, patient=patient)
    if request.method == "POST":
        event.delete()
        messages.success(request, _l("Събитието е изтрито."))
        return redirect("medj:medical_event_list")
    return render(request, "subpages/medical_event_confirm_delete.html", {"medical_event": event})

@login_required
def event_edit_tags(request, pk):
    patient = _require_patient_profile(request.user)
    if not patient:
        return HttpResponseForbidden()
    event = get_object_or_404(MedicalEvent, pk=pk, patient=patient)
    if request.method == "POST":
        form = EventTagForm(request.POST)
        if form.is_valid():
            new_tags = set(form.cleaned_data["tags"].values_list("id", flat=True))
            current = set(event.tags.values_list("id", flat=True))
            to_add = new_tags - current
            to_remove = current - new_tags
            if to_add:
                event.tags.add(*list(to_add))
            if to_remove:
                event.tags.remove(*list(to_remove))
            messages.success(request, _l("Таговете на събитието са обновени."))
            return redirect("medj:medical_event_detail", pk=event.pk)
    else:
        form = EventTagForm(initial={"tags": event.tags.all()})
    return render(request, "subpages/event_edit_tags.html", {"form": form, "medical_event": event})

@login_required
def document_detail(request, pk):
    patient = _require_patient_profile(request.user)
    if not patient:
        return HttpResponseForbidden()
    doc = get_object_or_404(Document.objects.select_related("medical_event", "doc_type", "practitioner"), pk=pk, medical_event__patient=patient)
    event = doc.medical_event
    return render(request, "subpages/document_detail.html", {"document": doc, "event": event})

@login_required
def document_edit(request, pk):
    patient = _require_patient_profile(request.user)
    if not patient:
        return HttpResponseForbidden()
    doc = get_object_or_404(
        Document.objects.select_related("medical_event"),
        pk=pk,
        medical_event__patient=patient,
    )
    if request.method == "POST":
        form = DocumentEditForm(request.POST, instance=doc)
        if form.is_valid():
            form.save()
            messages.success(request, _l("Документът е обновен."))
            return redirect("medj:document_detail", pk=doc.pk)
    else:
        form = DocumentEditForm(instance=doc)
    return render(request, "subpages/document_edit.html", {"form": form, "document": doc})

@login_required
def document_edit_tags(request, pk):
    patient = _require_patient_profile(request.user)
    if not patient:
        return HttpResponseForbidden()
    doc = get_object_or_404(Document.objects.select_related("medical_event"), pk=pk, medical_event__patient=patient)
    if request.method == "POST":
        form = DocumentTagForm(request.POST)
        if form.is_valid():
            new_tags = set(form.cleaned_data["tags"].values_list("id", flat=True))
            current = set(doc.tags.values_list("id", flat=True))
            inherited_ids = set(DocumentTag.objects.filter(document=doc, is_inherited=True).values_list("tag_id", flat=True))
            # Премахваме само "не-наследени" когато трябва
            to_add = new_tags - current
            to_remove = (current - new_tags) - inherited_ids
            if to_add:
                doc.tags.add(*list(to_add))
            if to_remove:
                doc.tags.remove(*list(to_remove))
            messages.success(request, _l("Таговете на документа са обновени."))
            return redirect("medj:document_detail", pk=doc.pk)
    else:
        form = DocumentTagForm(initial={"tags": doc.tags.exclude(documenttag__is_inherited=True)})
    return render(request, "subpages/document_edit_tags.html", {"form": form, "document": doc})

@login_required
def document_move(request, pk):
    patient = _require_patient_profile(request.user)
    if not patient:
        return HttpResponseForbidden()
    doc = get_object_or_404(Document.objects.select_related("medical_event"), pk=pk, medical_event__patient=patient)
    initial_specialty = doc.medical_event.specialty
    if request.method == "POST":
        form = MoveDocumentForm(request.POST, user=request.user, specialty=initial_specialty)
        if form.is_valid():
            target = form.cleaned_data["target_event"]
            new_date = form.cleaned_data["new_event_date"]
            specialty = form.cleaned_data["specialty"]
            if target:
                doc.medical_event = target
                doc.save(update_fields=["medical_event"])
            else:
                new_event = MedicalEvent.objects.create(
                    patient=patient,
                    specialty=specialty,
                    event_date=new_date,
                )
                doc.medical_event = new_event
                doc.save(update_fields=["medical_event"])
            messages.success(request, _l("Документът е преместен."))
            return redirect("medj:document_detail", pk=doc.pk)
    else:
        form = MoveDocumentForm(user=request.user, specialty=initial_specialty)
    return render(request, "subpages/document_move.html", {"form": form, "document": doc})

@login_required
def export_event_pdf(request, pk):
    patient = _require_patient_profile(request.user)
    if not patient:
        return HttpResponseForbidden()
    event = get_object_or_404(MedicalEvent, pk=pk, patient=patient)
    docs = event.documents.select_related("doc_type").all().order_by("document_date")
    ctx = {"medical_event": event, "documents": docs}
    html = render_to_string("subpages/event_export_pdf.html", ctx, request=request)
    pdf = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()
    filename = f"Event-{event.event_date.strftime('%Y-%m-%d')}.pdf"
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp

@login_required
def export_lab_csv(request, pk):
    patient = _require_patient_profile(request.user)
    if not patient:
        return HttpResponseForbidden()
    event = get_object_or_404(MedicalEvent, pk=pk, patient=patient)
    measurements = LabTestMeasurement.objects.filter(event=event).select_related("indicator").order_by("measured_at", "indicator__code")

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["measured_at", "code", "value_si", "unit_si", "ref_low_si", "ref_high_si", "is_abnormal"])
    for m in measurements:
        writer.writerow([
            m.measured_at.isoformat(),
            m.indicator.code if m.indicator else "",
            m.value_si if m.value_si is not None else "",
            m.unit_si or "",
            m.ref_low_si if m.ref_low_si is not None else "",
            m.ref_high_si if m.ref_high_si is not None else "",
            "" if m.is_abnormal is None else ("1" if m.is_abnormal else "0"),
        ])
    resp = HttpResponse(buf.getvalue(), content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="lab_results_{event.pk}.csv"'
    return resp

@login_required
def tags_autocomplete(request):
    patient = _require_patient_profile(request.user)
    if not patient:
        return HttpResponseForbidden()
    q = request.GET.get("q", "").strip()
    qs = Tag.objects.all()
    if q:
        qs = qs.filter(name__icontains=q)
    data = [{"id": t.id, "name": t.name} for t in qs.order_by("name")[:20]]
    return JsonResponse(data, safe=False)

@login_required
def upload_history(request):
    patient = _require_patient_profile(request.user)
    if not patient:
        return HttpResponseForbidden()
    docs = Document.objects.filter(medical_event__patient=patient).select_related("doc_type", "medical_event__specialty", "practitioner").prefetch_related("tags")
    tag_param = request.GET.get("tags", "").strip()
    search_q = request.GET.get("q", "").strip()
    if tag_param:
        names = [t.strip() for t in tag_param.split(",") if t.strip()]
        if names:
            docs = docs.filter(tags__name__in=names).distinct()
    if search_q:
        docs = docs.filter(
            Q(file__icontains=search_q) |
            Q(doc_type__translations__name__icontains=search_q) |
            Q(medical_event__specialty__translations__name__icontains=search_q) |
            Q(tags__name__icontains=search_q)
        ).distinct()
    docs = docs.order_by("-uploaded_at", "-id")
    return render(request, "subpages/upload_history.html", {"documents": docs, "tags_query": tag_param, "search_query": search_q})

def share_view(request, token):
    st = get_object_or_404(ShareToken, token=token)
    if not st.is_valid():
        raise Http404()
    st.times_used = st.times_used + 1
    st.save(update_fields=["times_used"])
    common = {
        "allow_download": st.allow_download,
        "token": st.token,
        "expires_at": st.expires_at,
        "owner_patient_id": st.patient_id,
    }
    if st.scope == "document" and st.document:
        obj = st.document
        ctx = {
            "mode": "document",
            "file_url": obj.file.url,
            "file_name": obj.file.name,
            "doc_type": obj.doc_type,
            "event": obj.medical_event,
            **common,
        }
    elif st.scope == "event" and st.event:
        obj = st.event
        docs = obj.documents.all().order_by("document_date")
        ctx = {
            "mode": "event",
            "event": obj,
            "documents": docs,
            **common,
        }
    else:
        raise Http404()
    resp = render(request, "subpages/share_view.html", ctx)
    resp["X-Frame-Options"] = "SAMEORIGIN"
    resp["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return resp

def share_qr(request, token):
    st = get_object_or_404(ShareToken, token=token)
    if not st.is_valid():
        raise Http404()
    url = request.build_absolute_uri(reverse("medj:share_view", args=[str(st.token)]))
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return HttpResponse(buf.getvalue(), content_type="image/png")

@login_required
@require_POST
def share_revoke(request, token):
    st = get_object_or_404(ShareToken, token=token, patient__user=request.user)
    st.is_active = False
    st.save(update_fields=["is_active"])
    messages.success(request, _l("Линкът за споделяне е деактивиран."))
    return redirect("medj:medical_event_list")
