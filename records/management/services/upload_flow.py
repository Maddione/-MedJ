import os
import io
import re
from datetime import datetime, date, time
from decimal import Decimal

from django.db import transaction
from django.utils.timezone import now, make_aware, get_current_timezone

try:
    import requests
except Exception:
    requests = None

try:
    from google.cloud import vision
except Exception:
    vision = None

from records.models import (
    PatientProfile,
    MedicalEvent,
    MedicalCategory,
    MedicalSpecialty,
    DocumentType,
    Document,
    Tag,
    EventTag,
    DocumentTag,
    TagKind,
    LabIndicator,
    LabTestMeasurement,
    Practitioner, DocumentPractitioner,
)


def vision_ocr_first_fallback_flask(file_obj):
    content = file_obj.read() if hasattr(file_obj, "read") else bytes(file_obj or b"")
    source = "vision"
    text = ""
    if vision is not None:
        try:
            client = vision.ImageAnnotatorClient()
            image = vision.Image(content=content)
            resp = client.document_text_detection(image=image)
            if getattr(resp, "full_text_annotation", None):
                text = resp.full_text_annotation.text or ""
        except Exception:
            text = ""
    if not text:
        source = "flask"
        url = os.getenv("OCR_SERVICE_URL", "").strip() or os.getenv("OCR_API_URL", "").strip()
        if url and requests is not None:
            try:
                u = url.rstrip("/") + "/ocr" if not url.rstrip("/").endswith("/ocr") else url
                files = {"file": ("upload.bin", io.BytesIO(content), "application/octet-stream")}
                r = requests.post(u, files=files, timeout=30)
                if r.ok:
                    try:
                        j = r.json()
                        text = j.get("ocr_text") or j.get("text") or ""
                    except Exception:
                        text = r.text or ""
            except Exception:
                text = ""
    return text or "", source


def _parse_float(x):
    if x is None:
        return None
    s = str(x).strip().replace(",", ".")
    try:
        return float(s)
    except Exception:
        try:
            return float(Decimal(re.sub(r"[^\d\.\-]", "", s)))
        except Exception:
            return None


def _dt_from_date(dt_date: date):
    if not dt_date:
        return now()
    dtt = datetime.combine(dt_date, time(12, 0, 0))
    try:
        return make_aware(dtt, get_current_timezone())
    except Exception:
        return dtt


def _norm_name(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def _ensure_tag(slug, name):
    try:
        tag = Tag.objects.get(slug=slug)
        return tag
    except Tag.DoesNotExist:
        try:
            tag = Tag.objects.create(slug=slug, kind=TagKind.SYSTEM, is_active=True)
            try:
                tag.set_current_language("bg")
                if not getattr(tag, "name", None):
                    tag.name = name or slug
                tag.save()
            except Exception:
                pass
            return tag
        except Exception:
            return None


def _attach_doc_tag(doc, tag, permanent=False):
    if not tag:
        return
    try:
        DocumentTag.objects.get_or_create(
            document=doc,
            tag=tag,
            defaults={"is_inherited": False, "is_permanent": bool(permanent)},
        )
    except Exception:
        pass


def _attach_event_tag(ev, tag):
    if not tag:
        return
    try:
        EventTag.objects.get_or_create(event=ev, tag=tag)
    except Exception:
        pass


@transaction.atomic
def confirm_and_save(
    user,
    category,
    specialty,
    doc_type,
    existing_event,
    file,
    file_mime,
    file_kind,
    final_text,
    final_summary,
    analysis,
    doctor=None,
):
    patient = getattr(user, "patient_profile", None)
    ev = existing_event
    if ev is None:
        ev = MedicalEvent.objects.create(
            patient=patient,
            owner=user,
            category=category if isinstance(category, MedicalCategory) else None,
            specialty=specialty if isinstance(specialty, MedicalSpecialty) else None,
            doc_type=doc_type if isinstance(doc_type, DocumentType) else None,
            event_date=now().date(),
            summary=None,
        )
    doc = Document.objects.create(
        owner=user,
        medical_event=ev,
        specialty=specialty if isinstance(specialty, MedicalSpecialty) else None,
        category=category if isinstance(category, MedicalCategory) else None,
        doc_type=doc_type if isinstance(doc_type, DocumentType) else None,
        file=file,
        file_mime=file_mime or "",
        file_size=getattr(file, "size", None) if file is not None else None,
        doc_kind=(str(file_kind).lower() if file_kind else "other"),
        original_ocr_text=final_text or "",
        summary=final_summary or "",
    )
    data = analysis.get("data") if isinstance(analysis, dict) else {}
    dc = data.get("date_created") if isinstance(data, dict) else None
    if dc:
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y"):
            try:
                doc.date_created = datetime.strptime(str(dc), fmt).date()
                break
            except Exception:
                continue
        if not doc.date_created:
            try:
                doc.date_created = datetime.fromisoformat(str(dc)).date()
            except Exception:
                pass
        if doc.date_created:
            try:
                doc.save(update_fields=["date_created"])
            except Exception:
                pass
    permanent = []
    if category:
        permanent.append((f"category:{category.slug}", "category"))
    if specialty:
        permanent.append((f"specialty:{specialty.slug}", "specialty"))
    if doc_type:
        permanent.append((f"doc_type:{doc_type.slug}", "doc_type"))
    if doc.doc_kind:
        permanent.append((f"doc_kind:{doc.doc_kind}", "doc_kind"))
    if doc.date_created:
        permanent.append((f"date:{doc.date_created.strftime('%d-%m-%Y')}", doc.date_created.strftime("%d-%m-%Y")))
    for slug, label in permanent:
        t = _ensure_tag(slug, label)
        _attach_doc_tag(doc, t, True)
        _attach_event_tag(ev, t)
    editable_names = []
    if isinstance(data, dict):
        for s in data.get("suggested_tags") or []:
            val = str(s).strip()
            if val:
                editable_names.append(val)
    for tag_name in editable_names:
        slug = "user:" + re.sub(r"[^a-z0-9\-]+", "-", tag_name.lower())
        t = _ensure_tag(slug, tag_name)
        _attach_doc_tag(doc, t, False)
        _attach_event_tag(ev, t)
    labs = (data.get("blood_test_results") or []) if isinstance(data, dict) else []
    for r in labs:
        try:
            name = (r.get("indicator_name") or "").strip()
            if not name:
                continue
            val = _parse_float(r.get("value"))
            if val is None:
                continue
            unit = (r.get("unit") or "").strip()
            ref = r.get("reference_range") or ""
            when = r.get("measured_at") or data.get("event_date")
            if when:
                try:
                    dt = datetime.fromisoformat(str(when))
                    try:
                        when_dt = make_aware(dt, get_current_timezone())
                    except Exception:
                        when_dt = dt
                except Exception:
                    when_dt = _dt_from_date(ev.event_date)
            else:
                when_dt = _dt_from_date(ev.event_date)
            slug = re.sub(r"[^a-z0-9\-]+", "-", name.lower())
            ind, _ = LabIndicator.objects.get_or_create(slug=slug, defaults={"unit": unit or None})
            if ref and (ind.reference_low is None or ind.reference_high is None):
                try:
                    parts = str(ref).replace(",", ".").split("-")
                    lo = float(parts[0].strip()) if len(parts) == 2 else None
                    hi = float(parts[1].strip()) if len(parts) == 2 else None
                except Exception:
                    lo, hi = None, None
                changed = False
                if lo is not None and ind.reference_low is None:
                    ind.reference_low = lo; changed = True
                if hi is not None and ind.reference_high is None:
                    ind.reference_high = hi; changed = True
                if changed:
                    ind.save(update_fields=["reference_low", "reference_high"])
            LabTestMeasurement.objects.create(
                medical_event=ev,
                indicator=ind,
                value=val,
                measured_at=when_dt,
            )
        except Exception:
            continue
    doc_block = doctor or {}
    pid = doc_block.get("practitioner_id")
    name_in = _norm_name(doc_block.get("full_name") or "")
    sel_specialty_id = doc_block.get("specialty_id")
    role_in = (doc_block.get("role") or "author").strip().lower()
    is_primary_in = bool(doc_block.get("is_primary", True))
    practitioner = None
    if pid:
        practitioner = Practitioner.objects.filter(id=pid, owner=user).first()
        if practitioner and not name_in:
            name_in = practitioner.full_name
        if practitioner and not sel_specialty_id:
            sel_specialty_id = practitioner.specialty_id
    elif name_in:
        try:
            qs = Practitioner.objects.filter(owner=user, full_name__iexact=name_in)
            if sel_specialty_id:
                qs = qs.filter(specialty_id=sel_specialty_id)
            practitioner = qs.first()
            if practitioner is None:
                practitioner = Practitioner.objects.create(
                    owner=user, full_name=name_in, specialty_id=sel_specialty_id or None, is_active=True
                )
        except Exception:
            practitioner = None
    if practitioner:
        try:
            DocumentPractitioner.objects.get_or_create(
                document=doc, practitioner=practitioner, role=role_in, defaults={"is_primary": is_primary_in}
            )
        except Exception:
            pass
        t = _ensure_tag("doctor:" + re.sub(r"[^a-z0-9\-]+", "-", (practitioner.full_name or name_in).lower()), practitioner.full_name or name_in)
        _attach_doc_tag(doc, t, False)
        _attach_event_tag(ev, t)
        spec_for_tag = sel_specialty_id or practitioner.specialty_id
        if spec_for_tag:
            try:
                sp = MedicalSpecialty.objects.get(id=spec_for_tag)
                sp_name = getattr(sp, "safe_translation_getter", lambda *a, **k: None)("name", any_language=True) or getattr(sp, "name", "") or ""
                t2 = _ensure_tag(f"doctor_specialty:{spec_for_tag}", sp_name or f"doctor_specialty:{spec_for_tag}")
                _attach_doc_tag(doc, t2, False)
                _attach_event_tag(ev, t2)
            except MedicalSpecialty.DoesNotExist:
                pass
    return {"event_id": ev.id, "document_id": doc.id}
