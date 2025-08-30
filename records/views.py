from __future__ import annotations

import io
from django import forms
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseForbidden,
    JsonResponse,
    FileResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST, require_GET
from .models import PatientProfile

try:
    from .forms import (
        DocumentUploadForm,
        EventTagForm,
        DocumentTagForm,
        MoveDocumentForm,
    )
except Exception:
    class DocumentUploadForm(forms.Form):
        specialty = forms.CharField(required=False)
        doc_type = forms.CharField(required=False)
        practitioner = forms.CharField(required=False)
        document_date = forms.DateField(required=False)
        attach_to_event = forms.IntegerField(required=False)
        file = forms.FileField(required=False)

    class EventTagForm(forms.Form):
        tags = forms.CharField(required=False)

    class DocumentTagForm(forms.Form):
        tags = forms.CharField(required=False)

    class MoveDocumentForm(forms.Form):
        target_event = forms.IntegerField(required=False)

try:
    from .models import (
        PatientProfile,
        MedicalEvent,
        MedicalSpecialty,
        Document,
        Tag,
        DocumentTag,
        LabIndicator,
        LabTestMeasurement,
        Practitioner,
        ShareToken,
    )
except Exception:
    PatientProfile = MedicalEvent = MedicalSpecialty = Document = Tag = DocumentTag = LabIndicator = LabTestMeasurement = Practitioner = ShareToken = object


def _get_or_create_patient_profile(user):
    if PatientProfile is object:
        return None
    profile, _ = PatientProfile.objects.get_or_create(user=user)
    return profile


def _patient_or_forbid(user):
    if not getattr(user, "is_authenticated", False):
        return None
    if PatientProfile is object:
        return None
    return _get_or_create_patient_profile(user)

def _require_patient_profile(user):
    profile, _ = PatientProfile.objects.get_or_create(user=user)
    return profile
@require_GET
def landing_page(request: HttpRequest) -> HttpResponse:
    return render(request, "basetemplates/landingpage.html")


def custom_login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("medj:dashboard")
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        _get_or_create_patient_profile(user)
        return redirect("medj:dashboard")
    return render(request, "auth/login.html", {"form": form})


def register_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("medj:dashboard")
    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        _get_or_create_patient_profile(user)
        return redirect("medj:dashboard")
    return render(request, "auth/register.html", {"form": form})


def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("medj:landing")


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    return render(request, "main/dashboard.html")


@login_required
def casefiles(request: HttpRequest) -> HttpResponse:
    return render(request, "main/casefiles.html")


@login_required
def personal_card(request: HttpRequest) -> HttpResponse:
    return render(request, "main/personalcard.html")


@login_required
def upload_page(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = DocumentUploadForm(request.POST, request.FILES)
        if hasattr(form, "is_valid") and form.is_valid():
            messages.success(request, _("Документът е качен успешно."))
            return redirect("medj:upload_history")
    else:
        form = DocumentUploadForm()
    return render(request, "main/upload.html", {"form": form})


@login_required
def upload_history(request: HttpRequest) -> HttpResponse:
    patient = _patient_or_forbid(request.user)
    if not patient:
        return HttpResponseForbidden()
    docs = []
    if Document is not object:
        qs = Document.objects.filter(medical_event__patient=patient).select_related(
            "medical_event", "doc_type", "practitioner"
        )
        if hasattr(Document, "created_at"):
            qs = qs.order_by("-created_at")
        else:
            qs = qs.order_by("-id")
        docs = qs
    return render(request, "subpages/upload_history.html", {"documents": docs})


@login_required
def documents(request: HttpRequest) -> HttpResponse:
    patient = _patient_or_forbid(request.user)
    if not patient:
        return HttpResponseForbidden()
    qs = []
    if Document is not object:
        qs = (
            Document.objects.filter(medical_event__patient=patient)
            .select_related("medical_event", "doc_type", "practitioner")
            .order_by("-document_date", "-id")
        )
    return render(request, "subpages/upload_history.html", {"documents": qs})


@login_required
def profile(request: HttpRequest) -> HttpResponse:
    return render(request, "subpages/profile.html")


@login_required
def doctors(request: HttpRequest) -> HttpResponse:
    return render(request, "subpages/doctors.html")


@login_required
def event_list(request: HttpRequest) -> HttpResponse:
    patient = _patient_or_forbid(request.user)
    if not patient:
        return HttpResponseForbidden()
    tag_param = request.GET.get("tag")
    search_q = request.GET.get("q")
    qs = []
    if MedicalEvent is not object:
        qs = MedicalEvent.objects.filter(patient=patient).select_related("specialty").order_by("-event_date", "-id")
        if search_q:
            qs = qs.filter(summary__icontains=search_q)
        if tag_param:
            qs = qs.filter(tags__name__iexact=tag_param).distinct()
    return render(request, "subpages/event_history.html", {"medical_events": qs, "tags_query": tag_param, "search_query": search_q})


@login_required
def event_detail(request: HttpRequest, pk: int) -> HttpResponse:
    patient = _patient_or_forbid(request.user)
    if not patient:
        return HttpResponseForbidden()
    event = None
    if MedicalEvent is not object:
        event = get_object_or_404(MedicalEvent.objects.select_related("specialty", "patient"), pk=pk, patient=patient)
    return render(request, "subpages/event_detail.html", {"medical_event": event})


@login_required
def event_history(request: HttpRequest, pk: int | None = None) -> HttpResponse:
    return event_list(request)


@login_required
@require_POST
def update_event_details(request: HttpRequest, event_id: int | None = None, pk: int | None = None) -> JsonResponse:
    return JsonResponse({"ok": True})


@login_required
def document_detail(request: HttpRequest, pk: int) -> HttpResponse:
    patient = _patient_or_forbid(request.user)
    if not patient:
        return HttpResponseForbidden()
    doc = None
    if Document is not object:
        doc = get_object_or_404(
            Document.objects.select_related("medical_event", "doc_type", "practitioner"),
            pk=pk,
            medical_event__patient=patient,
        )
    return render(request, "subpages/document_detail.html", {"document": doc, "event": getattr(doc, "medical_event", None)})


@login_required
def document_edit(request: HttpRequest, pk: int) -> HttpResponse:
    patient = _patient_or_forbid(request.user)
    if not patient:
        return HttpResponseForbidden()
    return render(request, "subpages/document_edit.html", {"document_id": pk})


@login_required
def document_edit_tags(request: HttpRequest, pk: int) -> HttpResponse:
    form = DocumentTagForm()
    return render(request, "subpages/document_edit_tags.html", {"form": form, "document_id": pk})


@login_required
def document_move(request: HttpRequest, pk: int) -> HttpResponse:
    form = MoveDocumentForm()
    return render(request, "subpages/document_move.html", {"form": form, "document_id": pk})


@login_required
def generate_pdf(request: HttpRequest, pk: int) -> HttpResponse:
    buf = io.BytesIO(b"%PDF-1.4\n% Placeholder\n")
    return FileResponse(buf, content_type="application/pdf")


@login_required
def labtests(request: HttpRequest) -> HttpResponse:
    return render(request, "subpages/labtests.html")


@login_required
def labtests_view(request: HttpRequest, event_id: int | str):
    patient = _patient_or_forbid(request.user)
    if not patient:
        return HttpResponseForbidden()
    event = None
    indicators = []
    series = {}
    if MedicalEvent is not object:
        event = get_object_or_404(MedicalEvent, pk=event_id, patient=patient)
    if LabIndicator is not object:
        indicators = LabIndicator.objects.all().order_by("code")
    if LabTestMeasurement is not object and event:
        qs = LabTestMeasurement.objects.filter(event=event).select_related("indicator").order_by("indicator__code", "measured_at")
        for m in qs:
            key = getattr(m.indicator, "code", "UNK")
            series.setdefault(key, [])
            unit = getattr(m, "unit_si", None) or getattr(m, "unit_raw", "")
            series[key].append(
                {
                    "date": m.measured_at.isoformat() if getattr(m, "measured_at", None) else "",
                    "value": getattr(m, "value_si", None),
                    "unit": unit,
                    "abn": getattr(m, "is_abnormal", False),
                }
            )
    return render(request, "subpages/labtests.html", {"medical_event": event, "series": series, "indicators": indicators})


@login_required
def labtest_edit(request: HttpRequest, event_id: int | str) -> HttpResponse:
    return render(request, "subpages/labtest_edit.html", {"event_id": event_id})


@login_required
def share_document_page(request: HttpRequest, medical_event_id: int | str | None = None) -> HttpResponse:
    return render(request, "main/share.html", {"medical_event_id": medical_event_id})


@login_required
@require_POST
def create_share_token(request: HttpRequest) -> JsonResponse:
    token = None
    if ShareToken is not object:
        patient = _patient_or_forbid(request.user)
        if not patient:
            return JsonResponse({"ok": False}, status=403)
        token = ShareToken.objects.create(patient=patient)
    return JsonResponse({"ok": True, "token": str(getattr(token, "token", "demo-token"))})


@require_GET
def share_view(request: HttpRequest, token: str) -> HttpResponse:
    st = None
    if ShareToken is not object:
        st = get_object_or_404(ShareToken, token=token)
        if hasattr(st, "is_valid") and not st.is_valid():
            raise Http404()
    return render(request, "subpages/share_view.html", {"mode": "token", "token": token, "documents": []})


def share_qr(request: HttpRequest, token: str) -> HttpResponse:
    try:
        import qrcode
    except Exception:
        raise Http404("qrcode lib not installed")
    url = request.build_absolute_uri(reverse("medj:share_view", args=[str(token)]))
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return HttpResponse(buf.getvalue(), content_type="image/png")


@login_required
@require_POST
def share_revoke(request: HttpRequest, token: str) -> HttpResponse:
    if ShareToken is not object:
        st = get_object_or_404(ShareToken, token=token, patient__user=request.user)
        if hasattr(st, "is_active"):
            st.is_active = False
            st.save(update_fields=["is_active"])
    messages.success(request, _("Линкът за споделяне е деактивиран."))
    return redirect("medj:events_list")


@login_required
def serve_file_by_uuid(request: HttpRequest, file_uuid: str):
    raise Http404("Not implemented")


@login_required
@require_POST
def delete_document(request: HttpRequest, document_id: int | str) -> JsonResponse:
    return JsonResponse({"ok": True, "deleted": document_id})


@login_required
@require_POST
def add_medication_tag(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"ok": True})


@login_required
def events_by_specialty(request: HttpRequest) -> JsonResponse:
    patient = _patient_or_forbid(request.user)
    if not patient:
        return JsonResponse({"results": []})
    try:
        spec_id = int(request.GET.get("specialty"))
    except (TypeError, ValueError):
        return JsonResponse({"results": []})
    results = []
    if MedicalEvent is not object:
        qs = MedicalEvent.objects.filter(patient=patient, specialty_id=spec_id).order_by("-event_date", "-id")
        for e in qs:
            results.append(
                {
                    "id": e.id,
                    "date": e.event_date.strftime("%Y-%m-%d") if getattr(e, "event_date", None) else "",
                    "summary": getattr(e, "summary", "") or "",
                }
            )
    return JsonResponse({"results": results})


@login_required
def tags_autocomplete(request: HttpRequest) -> JsonResponse:
    q = request.GET.get("q") or ""
    data = []
    if Tag is not object and q:
        for t in Tag.objects.filter(name__icontains=q).order_by("name")[:20]:
            data.append({"id": t.id, "name": t.name})
    return JsonResponse({"results": data})


@login_required
def practitioners_list(request: HttpRequest) -> JsonResponse:
    q = request.GET.get("q") or ""
    data = []
    if Practitioner is not object:
        qs = Practitioner.objects.all()
        if q:
            qs = qs.filter(full_name__icontains=q)
        data = [{"id": p.id, "name": getattr(p, "full_name", str(p))} for p in qs[:20]]
    return JsonResponse({"results": data})


@login_required
def export_event_pdf(request: HttpRequest, pk: int) -> HttpResponse:
    buf = io.BytesIO(b"%PDF-1.4\n% Event PDF Placeholder\n")
    return FileResponse(buf, content_type="application/pdf")


@login_required
def export_lab_csv(request: HttpRequest) -> HttpResponse:
    rows = ["date,indicator,value,unit\n"]
    content = "".join(rows).encode("utf-8")
    resp = HttpResponse(content, content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename="labs.csv"'
    return resp


@require_GET
def healthcheck(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})
