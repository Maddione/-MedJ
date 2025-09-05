from __future__ import annotations
import os, json, uuid
from io import BytesIO
from decimal import Decimal
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render

from ..models import (
    Document, MedicalEvent, MedicalSpecialty,
    LabIndicator, LabTestMeasurement, DocumentTag,
)
from ..forms import DocumentUploadForm
from .utils import (
    require_patient_profile, save_temp_upload, load_temp_file_bytes,
    ocr_from_storage, anonymize, gpt_analyze, get_or_create_tags,
)

ALLOWED_EXTS = {".pdf", ".jpg", ".jpeg", ".png"}


def _ext(name: str) -> str:
    n = (name or "").lower()
    i = n.rfind(".")
    return n[i:] if i >= 0 else ""


def _images_to_pdf_bytes(files) -> bytes:

    try:
        from PIL import Image
    except Exception:
        return b""

    images = []
    sorted_files = sorted(files, key=lambda f: (getattr(f, "name", "") or "").lower())
    for f in sorted_files:
        try:
            im = Image.open(f)
            if im.mode != "RGB":
                im = im.convert("RGB")
            images.append(im)
        except Exception:
            continue

    if not images:
        return b""
    buf = BytesIO()
    if len(images) == 1:
        images[0].save(buf, format="PDF")
    else:
        images[0].save(buf, format="PDF", save_all=True, append_images=images[1:])
    return buf.getvalue()


@login_required
def upload_page(request: HttpRequest) -> HttpResponse:
    form = DocumentUploadForm(user=request.user)
    return render(request, "main/upload.html", {"form": form, "step": "form"})


@login_required
def upload_preview(request: HttpRequest) -> HttpResponse:

    if request.method != "POST":
        return render(request, "main/upload.html", {"form": DocumentUploadForm(user=request.user), "step": "form"})

    form = DocumentUploadForm(request.POST, request.FILES, user=request.user)
    if not form.is_valid():
        return render(request, "main/upload.html", {"form": form, "step": "form"})

    files = list(request.FILES.getlist("files") or [])
    if not files:
        single = request.FILES.get("file") or request.FILES.get("document_file")
        if single:
            files = [single]

    if not files:
        form.add_error(None, "Моля, прикачете файл(ове).")
        return render(request, "main/upload.html", {"form": form, "step": "form"})

    pdfs, images, bad = 0, 0, 0
    for f in files:
        e = _ext(getattr(f, "name", ""))
        if e not in ALLOWED_EXTS:
            bad += 1
        elif e == ".pdf":
            pdfs += 1
        else:
            images += 1

    if bad > 0:
        form.add_error(None, "Има файлове с неподдържан формат. Позволени: PDF, JPG, JPEG, PNG.")
        return render(request, "main/upload.html", {"form": form, "step": "form"})
    if pdfs > 1:
        form.add_error(None, "Позволен е само един PDF.")
        return render(request, "main/upload.html", {"form": form, "step": "form"})
    if pdfs == 1 and images > 0:
        form.add_error(None, "Не смесвайте PDF и изображения в едно качване.")
        return render(request, "main/upload.html", {"form": form, "step": "form"})

    if pdfs == 1 and len(files) == 1:
        uploaded_file = files[0]
        tmp_rel_path = save_temp_upload(uploaded_file)
        file_type = "pdf"
        final_filename = uploaded_file.name
    else:

        pdf_bytes = _images_to_pdf_bytes(files)
        if not pdf_bytes:

            return JsonResponse(
                {"ok": False, "error": "Липсва зависимост за обединение на изображения (Pillow). Добави 'Pillow>=10' в requirements и rebuild."},
                status=400,
            )
        tmp_dir = getattr(settings, "TEMP_UPLOADS_DIR", "temp_uploads")
        fname = f"merged-{uuid.uuid4().hex}.pdf"
        tmp_rel_path = default_storage.save(os.path.join(tmp_dir, fname), ContentFile(pdf_bytes))
        file_type = "pdf"
        final_filename = fname

    ocr_text = (ocr_from_storage(tmp_rel_path) or "").strip()
    anonymized = anonymize(ocr_text)

    specialty = form.cleaned_data["specialty"]
    doc_type = form.cleaned_data["doc_type"]

    gpt_result = gpt_analyze(
        anonymized,
        doc_kind=getattr(doc_type, "slug", None) or getattr(doc_type, "pk", ""),
        file_type=file_type,
        specialty_name=(
            specialty.safe_translation_getter("name", any_language=True)
            if hasattr(specialty, "safe_translation_getter") else str(specialty)
        ),
    ) or {}

    html_fragment = gpt_result.get("html_fragment") or gpt_result.get("html") or ""
    explanation = gpt_result.get("explanation") or ""

    payload = {
        "tmp_rel_path": tmp_rel_path,
        "doc_type_id": getattr(doc_type, "id", doc_type),
        "specialty_id": getattr(specialty, "id", specialty),
        "target_event": form.cleaned_data.get("target_event").id if form.cleaned_data.get("target_event") else None,
        "new_event_date": (
            form.cleaned_data.get("new_event_date").strftime("%Y-%m-%d")
            if form.cleaned_data.get("new_event_date") else None
        ),
        "user_tags": form.get_normalized_tags() if hasattr(form, "get_normalized_tags") else [],
        "gpt": gpt_result,
        "ocr_text": ocr_text,
        "filename": final_filename,
    }

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "ok": True,
            "extracted_text": ocr_text,
            "html_fragment": html_fragment,
            "explanation": explanation,
            "payload": payload,
        })

    return render(
        request,
        "subpages/upload_preview.html",
        {
            "extracted_text": ocr_text,
            "html_fragment": html_fragment,
            "explanation": explanation,
            "payload": json.dumps(payload),
        },
    )


@login_required
@transaction.atomic
def upload_confirm(request: HttpRequest) -> HttpResponse:
    try:
        payload_raw = request.POST.get("payload") or request.body.decode("utf-8")
        payload = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
    except Exception:
        return JsonResponse({"ok": False, "error": "invalid payload"}, status=400)

    tmp_rel_path = payload.get("tmp_rel_path")
    if not tmp_rel_path or not default_storage.exists(tmp_rel_path):
        return JsonResponse({"ok": False, "error": "missing temp file"}, status=400)

    patient = require_patient_profile(request.user)
    spec_id = payload.get("specialty_id")
    doc_type_id = payload.get("doc_type_id")

    specialty = get_object_or_404(MedicalSpecialty, pk=spec_id) if spec_id else None
    doc_type_model = Document._meta.get_field("doc_type").remote_field.model
    doc_type = get_object_or_404(doc_type_model, pk=doc_type_id) if doc_type_id else None

    target_event_id = payload.get("target_event")
    new_event_date_str = payload.get("new_event_date")
    ocr_text = payload.get("ocr_text") or ""
    user_tags = payload.get("user_tags") or []
    gpt = payload.get("gpt") or {}

    if target_event_id:
        event = get_object_or_404(MedicalEvent, pk=target_event_id, patient=patient)
    else:
        if not new_event_date_str:
            return JsonResponse({"ok": False, "error": "event date required"}, status=400)
        try:
            event_date = datetime.strptime(new_event_date_str, "%Y-%m-%d").date()
        except Exception:
            return JsonResponse({"ok": False, "error": "bad event date"}, status=400)
        event = MedicalEvent.objects.create(
            patient=patient, specialty=specialty, event_date=event_date,
            summary=gpt.get("summary") or ""
        )

    file_bytes = load_temp_file_bytes(tmp_rel_path)
    final_name = os.path.basename(tmp_rel_path.split("/", 1)[-1])
    content = ContentFile(file_bytes)

    document = Document(
        owner=request.user,
        medical_event=event,
        doc_type=doc_type,
        document_date=event.event_date,
        original_ocr_text=ocr_text,
    )
    document.file.save(final_name, content, save=True)

    all_tag_names = set(user_tags)
    for t in gpt.get("suggested_tags", []) or []:
        if isinstance(t, str):
            all_tag_names.add(t.strip())
        elif isinstance(t, dict):
            name = t.get("name") or t.get("text")
            if name:
                all_tag_names.add(name.strip())

    tag_objs = get_or_create_tags(
        sorted({x for x in all_tag_names if x}),
        doc_type=doc_type, specialty=specialty, default="test_type"
    )
    if tag_objs:
        event.tags.add(*tag_objs)
        for tag in tag_objs:
            DocumentTag.objects.get_or_create(
                document=document, tag=tag, defaults={"is_inherited": False}
            )
    for item in gpt.get("blood_test_results", []) or []:
        ind_name = (item.get("indicator_name") or item.get("indicator") or "").strip()
        if not ind_name:
            continue
        unit = (item.get("unit") or "").strip() or None
        ref = item.get("reference_range") or ""
        ref_low = ref_high = None
        if isinstance(ref, str) and "-" in ref:
            parts = [p.strip() for p in ref.split("-", 1)]
            try:
                ref_low = Decimal(parts[0].replace(",", "."))
                ref_high = Decimal(parts[1].replace(",", "."))
            except Exception:
                ref_low = ref_high = None

        indicator, _ = LabIndicator.objects.get_or_create(name=ind_name, defaults={"unit": unit})
        if unit and not indicator.unit:
            indicator.unit = unit
            indicator.save(update_fields=["unit"])
        if ref_low is not None or ref_high is not None:
            indicator.reference_low = ref_low
            indicator.reference_high = ref_high
            indicator.save(update_fields=["reference_low", "reference_high"])

        value = item.get("value")
        try:
            value_dec = Decimal(str(value).replace(",", ".")) if value is not None else None
        except Exception:
            value_dec = None

        LabTestMeasurement.objects.create(
            medical_event=event,
            indicator=indicator,
            value=value_dec if value_dec is not None else Decimal("0"),
            measured_at=event.event_date,
        )
    from ..models import Diagnosis, TreatmentPlan, NarrativeSectionResult, Medication
    for d in gpt.get("diagnosis", []) or []:
        if isinstance(d, dict):
            Diagnosis.objects.create(
                medical_event=event, code=d.get("code") or None,
                text=d.get("text") or "", diagnosed_at=event.event_date
            )
        elif isinstance(d, str):
            Diagnosis.objects.create(medical_event=event, text=d, diagnosed_at=event.event_date)

    for p in gpt.get("treatment_plan", []) or []:
        txt = p.get("text") if isinstance(p, dict) else str(p)
        if txt:
            TreatmentPlan.objects.create(
                medical_event=event, plan_text=txt, start_date=event.event_date
            )

    for n in gpt.get("narratives", []) or []:
        if isinstance(n, dict):
            title = n.get("title") or "Наратив"
            NarrativeSectionResult.objects.create(
                medical_event=event, title=title, content=n.get("content") or ""
            )
        elif isinstance(n, str):
            NarrativeSectionResult.objects.create(
                medical_event=event, title="Наратив", content=n
            )

    for m in gpt.get("medications", []) or []:
        if isinstance(m, dict):
            name = (m.get("name") or "").strip()
            if name:
                Medication.objects.create(
                    medical_event=event, name=name,
                    dosage=m.get("dosage") or None, start_date=event.event_date
                )
    try:
        default_storage.delete(tmp_rel_path)
    except Exception:
        pass

    messages.success(request, "Документът и събитието са записани успешно.")
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "saved_event_id": event.id, "document_id": document.id})
    return render(request, "subpages/upload_confirm.html", {"saved_event_id": event.id})


@login_required
def upload_history(request: HttpRequest) -> HttpResponse:
    patient = require_patient_profile(request.user)
    docs = (
        Document.objects
        .select_related("doc_type", "medical_event", "medical_event__specialty")
        .filter(medical_event__patient=patient)
        .order_by("-uploaded_at", "-id")
    )
    return render(request, "main/upload_history.html", {"docs": docs})
