import csv
import io
import qrcode
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
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
    LoginForm,
    DocumentUploadForm,
    EventTagForm,
    DocumentTagForm,
    MoveDocumentForm,
    DocumentEditForm,
)
from .models import (
    MedicalEvent,
    Document,
    Tag,
    DocumentTag,
    LabIndicator,
    LabTestMeasurement,
    PractitionerProfile,
    ShareToken,
    PatientProfile,
)

def _require_patient_profile(user):
    try:
        patient_profile = user.patient_profile
    except PatientProfile.DoesNotExist:
        patient_profile = PatientProfile.objects.create(user=user)
    return patient_profile

def landing_view(request):
    if request.user.is_authenticated:
        return redirect("medj:dashboard")
    return render(request, "basetemplates/landingpage.html")

class CustomLoginView(LoginView):
    form_class = LoginForm
    template_name = 'auth/login.html'
    redirect_authenticated_user = True
login_view = CustomLoginView.as_view()

def logout_view(request):
    logout(request)
    return redirect("medj:landing")

@login_required
def history_view(request):
    return render(request, 'main/history.html')

@login_required
def share_page_view(request):
    return render(request, 'main/share.html')

@login_required
def casefiles_view(request):
    return render(request, 'main/casefiles.html')

@login_required
def profile_view(request):
    return render(request, 'subpages/profile.html')

@login_required
def labtests_overview(request):
    return render(request, 'subpages/labtests.html')

@login_required
def event_new(request):
    return render(request, 'subpages/medical_event_form.html')

def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, _l("Регистрацията е успешна."))
            return redirect("medj:dashboard")
        else:
            messages.error(request, _l("Моля, коригирайте грешките във формата."))
    else:
        form = RegisterForm()
    return render(request, "auth/register.html", {"form": form})

@login_required
def upload_document(request):
    patient = _require_patient_profile(request.user)
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
            Q(specialty__name__icontains=search_q)
        ).distinct()
    qs = qs.order_by("-event_date", "-id")
    return render(request, "subpages/event_history.html", {"medical_events": qs, "tags_query": tag_param, "search_query": search_q})

@login_required
def event_detail(request, pk):
    patient = _require_patient_profile(request.user)
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
    event = get_object_or_404(MedicalEvent, pk=pk, patient=patient)
    if request.method == "POST":
        event.delete()
        messages.success(request, _l("Събитието е изтрито."))
        return redirect("medj:medical_event_list")
    return render(request, "subpages/medical_event_confirm_delete.html", {"medical_event": event})

@login_required
def event_edit_tags(request, pk):
    patient = _require_patient_profile(request.user)
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
def document_edit_tags(request, pk):
    patient = _require_patient_profile(request.user)
    doc = get_object_or_404(Document.objects.select_related("medical_event"), pk=pk, medical_event__patient=patient)
    if request.method == "POST":
        form = DocumentTagForm(request.POST)
        if form.is_valid():
            new_tags = set(form.cleaned_data["tags"].values_list("id", flat=True))
            current = set(doc.tags.values_list("id", flat=True))
            inherited_ids = set(DocumentTag.objects.filter(document=doc, is_inherited=True).values_list("tag_id", flat=True))
            keep_inherited = current & inherited_ids
            target = new_tags | keep_inherited
            to_add = target - current
            to_remove = current - target
            if to_add:
                DocumentTag.objects.bulk_create([DocumentTag(document=doc, tag_id=t, is_inherited=False) for t in to_add if t not in inherited_ids])
            if to_remove:
                DocumentTag.objects.filter(document=doc, tag_id__in=list(to_remove), is_inherited=False).delete()
            messages.success(request, _l("Таговете на документа са обновени."))
            return redirect("medj:medical_event_detail", pk=doc.medical_event_id)
    else:
        form = DocumentTagForm(initial={"tags": doc.tags.all()})
    return render(request, "subpages/document_edit_tags.html", {"form": form, "document": doc})

@login_required
def document_move(request, pk):
    patient = _require_patient_profile(request.user)
    doc = get_object_or_404(Document.objects.select_related("medical_event"), pk=pk, medical_event__patient=patient)
    initial_specialty = doc.medical_event.specialty
    if request.method == "POST":
        form = MoveDocumentForm(request.POST, user=request.user, specialty=initial_specialty)
        if form.is_valid():
            target_event = form.cleaned_data.get("target_event")
            new_event_date = form.cleaned_data.get("new_event_date")
            specialty = form.cleaned_data["specialty"]
            with transaction.atomic():
                if target_event:
                    doc.medical_event = target_event
                    doc.save(update_fields=["medical_event"])
                else:
                    new_event = MedicalEvent.objects.create(patient=patient, specialty=specialty, event_date=new_event_date)
                    doc.medical_event = new_event
                    doc.document_date = new_event_date
                    doc.save(update_fields=["medical_event", "document_date"])
            messages.success(request, _l("Документът е преместен успешно."))
            return redirect("medj:medical_event_detail", pk=doc.medical_event_id)
    else:
        form = MoveDocumentForm(user=request.user, specialty=initial_specialty)
    return render(request, "subpages/document_move.html", {"form": form, "document": doc})

@login_required
def labtest_edit(request, pk):
    patient = _require_patient_profile(request.user)
    event = get_object_or_404(MedicalEvent, pk=pk, patient=patient)
    indicators = LabIndicator.objects.all().order_by("code")
    dates = list(
        LabTestMeasurement.objects.filter(event=event)
        .values_list("measured_at", flat=True)
        .distinct()
        .order_by("measured_at")
    )
    measurements = LabTestMeasurement.objects.filter(event=event).select_related("indicator").order_by("indicator__code", "measured_at")
    matrix = {}
    for m in measurements:
        key = m.indicator.code
        matrix.setdefault(key, {})
        matrix[key][m.measured_at] = m
    if request.method == "POST":
        for key, value in request.POST.items():
            if not key.startswith("cell__"):
                continue
            _, code, dt_str = key.split("__", 2)
            val = value.strip()
            if not val:
                continue
            indicator = LabIndicator.objects.filter(code=code).first()
            if not indicator:
                continue
            dt = timezone.datetime.strptime(dt_str, "%Y-%m-%d").date()
            existing = LabTestMeasurement.objects.filter(event=event, indicator=indicator, measured_at=dt).first()
            if existing:
                existing.value_raw = val
                existing.save(update_fields=["value_raw"])
            else:
                LabTestMeasurement.objects.create(
                    event=event,
                    document=event.documents.first(),
                    indicator=indicator,
                    measured_at=dt,
                    value_raw=val,
                )
        messages.success(request, _l("Промените са записани."))
        return redirect("medj:labtest_edit", pk=event.pk)
    ctx = { "medical_event": event, "indicators": indicators, "dates": dates, "matrix": matrix }
    return render(request, "subpages/labtest_edit.html", ctx)


@login_required
def practitioners_list(request):
    doctors = PractitionerProfile.objects.select_related("specialty").all().order_by("full_name")
    return render(request, "subpages/doctors.html", {"doctors": doctors})

@login_required
@require_POST
def create_share_token(request):
    patient = _require_patient_profile(request.user)
    scope = request.POST.get("scope")
    duration = request.POST.get("duration")
    allow_download = request.POST.get("allow_download") == "1"
    if scope not in {"document", "event"}:
        raise PermissionDenied()
    if duration not in {"1h", "6h", "12h", "24h", "72h", "7d"}:
        duration = "6h"
    if scope == "document":
        pk = request.POST.get("document_id")
        doc = get_object_or_404(Document, pk=pk, medical_event__patient=patient)
        obj_event = None
        obj_doc = doc
    else:
        pk = request.POST.get("event_id")
        ev = get_object_or_404(MedicalEvent, pk=pk, patient=patient)
        obj_event = ev
        obj_doc = None
    now = timezone.now()
    delta_map = {"1h": 1, "6h": 6, "12h": 12, "24h": 24, "72h": 72, "7d": 168}
    expires_at = now + timezone.timedelta(hours=delta_map[duration])
    st = ShareToken.objects.create(
        scope=scope,
        document=obj_doc,
        event=obj_event,
        patient=patient,
        allow_download=allow_download,
        expires_at=expires_at,
        is_active=True,
    )
    messages.success(request, _l("Създаден е линк за споделяне."))
    return redirect("medj:share_view", token=st.token)

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

@login_required
def document_detail(request, pk):
    patient = _require_patient_profile(request.user)
    doc = get_object_or_404(Document.objects.select_related("medical_event", "doc_type", "practitioner"), pk=pk, medical_event__patient=patient)
    event = doc.medical_event
    return render(request, "subpages/document_detail.html", {"document": doc, "event": event})

@login_required
def document_edit(request, pk):
    patient = _require_patient_profile(request.user)
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
def export_event_pdf(request, pk):
    patient = _require_patient_profile(request.user)
    event = get_object_or_404(
        MedicalEvent.objects.select_related("specialty", "patient__user"),
        pk=pk,
        patient=patient,
    )
    documents = event.documents.select_related("doc_type", "practitioner").all().order_by("document_date", "uploaded_at")
    diagnoses = event.diagnoses.all().order_by("diagnosed_at")
    treatment_plans = event.treatment_plans.all().order_by("start_date")
    narrative_sections = event.narrative_sections.all().order_by("order", "id") if hasattr(event, "narrative_sections") else []
    labs = LabTestMeasurement.objects.filter(event=event).select_related("indicator").order_by("measured_at", "indicator__code")
    ctx = {
        "event": event,
        "documents": documents,
        "diagnoses": diagnoses,
        "treatment_plans": treatment_plans,
        "narrative_sections": narrative_sections,
        "labs": labs,
    }
    html = render_to_string("subpages/event_export_pdf.html", ctx, request=request)
    pdf = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()
    filename = f"Event-{event.event_date.strftime('%Y-%m-%d')}-{slugify(event.specialty.name if event.specialty else 'event')}.pdf"
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp

@login_required
def export_lab_csv(request):
    patient = _require_patient_profile(request.user)
    qs = LabTestMeasurement.objects.filter(event__patient=patient).select_related("event", "indicator", "document", "event__specialty", "document__practitioner").order_by("measured_at", "indicator__code")
    event_id = request.GET.get("event")
    if event_id:
        qs = qs.filter(event_id=event_id)
    date_from = request.GET.get("from")
    date_to = request.GET.get("to")
    if date_from:
        qs = qs.filter(measured_at__gte=date_from)
    if date_to:
        qs = qs.filter(measured_at__lte=date_to)
    codes = request.GET.get("codes")
    if codes:
        code_list = [c.strip() for c in codes.split(",") if c.strip()]
        if code_list:
            qs = qs.filter(indicator__code__in=code_list)
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="lab_measurements.csv"'
    w = csv.writer(resp)
    w.writerow(["patient", "event_date", "measured_at", "specialty", "indicator_code", "indicator_name", "value_si", "unit_si", "ref_low_si", "ref_high_si", "is_abnormal", "document_date", "doc_type", "practitioner"])
    for m in qs:
        w.writerow([
            patient.user.username if patient and patient.user else "",
            m.event.event_date.strftime("%Y-%m-%d") if m.event and m.event.event_date else "",
            m.measured_at.strftime("%Y-%m-%d") if m.measured_at else "",
            m.event.specialty.name if m.event and m.event.specialty else "",
            m.indicator.code if m.indicator else "",
            getattr(m.indicator, "name", "") if m.indicator else "",
            m.value_si if m.value_si is not None else m.value_raw,
            m.unit_si or m.unit_raw or "",
            m.ref_low_si or "",
            m.ref_high_si or "",
            "1" if m.is_abnormal else "0" if m.is_abnormal is not None else "",
            m.document.document_date.strftime("%Y-%m-%d") if m.document and m.document.document_date else "",
            m.document.doc_type.name if m.document and m.document.doc_type else "",
            m.document.practitioner.full_name if m.document and m.document.practitioner else "",
        ])
    return resp

@login_required
def generate_pdf(request, pk):
    patient = _require_patient_profile(request.user)
    doc = get_object_or_404(
        Document.objects.select_related("medical_event", "doc_type", "practitioner", "medical_event__specialty", "medical_event__patient__user"),
        pk=pk,
        medical_event__patient=patient,
    )
    ctx = {"document": doc, "event": doc.medical_event}
    html = render_to_string("subpages/document_export_pdf.html", ctx, request=request)
    pdf = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()
    filename = f"Document-{doc.document_date.strftime('%Y-%m-%d') if doc.document_date else 'undated'}-{slugify(doc.doc_type.name if doc.doc_type else 'document')}.pdf"
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp

@login_required
def tags_autocomplete(request):
    patient = _require_patient_profile(request.user)
    q = request.GET.get("q", "").strip()
    qs = Tag.objects.all()
    if q:
        qs = qs.filter(name__icontains=q)
    data = [{"id": t.id, "name": t.name} for t in qs.order_by("name")[:20]]
    return JsonResponse(data, safe=False)

@login_required
def upload_history(request):
    patient = _require_patient_profile(request.user)
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
            Q(doc_type__name__icontains=search_q) |
            Q(medical_event__specialty__name__icontains=search_q) |
            Q(tags__name__icontains=search_q)
        ).distinct()
    docs = docs.order_by("-uploaded_at", "-id")
    return render(request, "subpages/upload_history.html", {"documents": docs, "tags_query": tag_param, "search_query": search_q})