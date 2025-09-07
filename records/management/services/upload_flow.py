import os
import io
import json
from datetime import datetime, date, time as dtime
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils.timezone import now, make_aware, get_current_timezone
from django.utils.dateparse import parse_datetime, parse_date

from django.contrib.auth import get_user_model

from records.models import (
    MedicalEvent,
    MedicalCategory,
    MedicalSpecialty,
    DocumentType,
    Document,
)

try:
    from records.models import Tag
except Exception:
    Tag = None

try:
    from records.models import LabIndicator, LabTestMeasurement
except Exception:
    LabIndicator = None
    LabTestMeasurement = None

try:
    from records.models import Doctor
except Exception:
    Doctor = None

try:
    from google.cloud import vision as gvision
except Exception:
    gvision = None

import requests

try:
    from records.services.llm import anonymizer as anonymizer_mod
except Exception:
    anonymizer_mod = None

try:
    from records.services.llm import gpt_client as gpt_client_mod
except Exception:
    gpt_client_mod = None


def _env(name, default=None):
    return os.environ.get(name, default)


def _to_iso_date(val):
    if not val:
        return None
    if isinstance(val, (datetime, date)):
        if isinstance(val, datetime):
            return val.date()
        return val
    d = parse_date(str(val))
    return d


def _to_aware_dt(val, fallback_day=None):
    tz = get_current_timezone()
    if isinstance(val, datetime):
        return val if val.tzinfo else make_aware(val, timezone=tz)
    if isinstance(val, date):
        dt = datetime.combine(val, dtime(12, 0, 0))
        return make_aware(dt, timezone=tz)
    if isinstance(val, str):
        dt = parse_datetime(val)
        if dt:
            return dt if dt.tzinfo else make_aware(dt, timezone=tz)
        d = parse_date(val)
        if d:
            dt = datetime.combine(d, dtime(12, 0, 0))
            return make_aware(dt, timezone=tz)
    if fallback_day:
        dt = datetime.combine(fallback_day, dtime(12, 0, 0))
        return make_aware(dt, timezone=tz)
    return make_aware(datetime.utcnow(), timezone=tz)


def _to_float(val):
    try:
        return float(Decimal(str(val)))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _parse_ref_range(s):
    if not s:
        return None, None
    s = str(s)
    for sep in ["-", "–", "—", " to ", ":", "/"]:
        if sep in s:
            parts = [p.strip() for p in s.split(sep)]
            if len(parts) >= 2:
                return _to_float(parts[0]), _to_float(parts[1])
    return None, None


def _ddmmyyyy(d):
    if not d:
        return ""
    if isinstance(d, str):
        d = _to_iso_date(d)
    try:
        return d.strftime("%d-%m-%Y")
    except Exception:
        return ""


def vision_ocr_first_fallback_flask(file_obj):
    text = ""
    source = "flask"
    if gvision is not None:
        try:
            client = gvision.ImageAnnotatorClient()
            data = file_obj.read()
            file_obj.seek(0)
            image = gvision.Image(content=data)
            resp = client.document_text_detection(image=image)
            txt = getattr(resp.full_text_annotation, "text", "") or ""
            if txt:
                return txt, "vision"
        except Exception:
            pass
    url = _env("OCR_SERVICE_URL") or _env("OCR_API_URL")
    if url:
        try:
            file_obj.seek(0)
            files = {"file": (getattr(file_obj, "name", "upload.bin"), file_obj.read())}
            r = requests.post(url.rstrip("/") + "/ocr", files=files, timeout=60)
            j = r.json() if r.ok else {}
            text = j.get("ocr_text") or ""
            source = j.get("source") or "flask"
        except Exception:
            text, source = "", "flask"
    return text, source


def events_suggest(user, category_id, specialty_id, doc_type_id):
    if not (category_id and specialty_id and doc_type_id):
        return []
    qs = (
        MedicalEvent.objects.filter(
            owner=user,
            category_id=category_id,
            specialty_id=specialty_id,
            doc_type_id=doc_type_id,
        )
        .order_by("-event_date")[:20]
        .only("id", "event_date", "summary")
    )
    return [{"id": e.id, "event_date": _ddmmyyyy(e.event_date), "summary": e.summary or ""} for e in qs]


def anonymize_and_analyze(text, specialty_id=None, user=None):
    src = text or ""
    anon = src
    if anonymizer_mod and hasattr(anonymizer_mod, "anonymize"):
        try:
            anon = anonymizer_mod.anonymize(src) or src
        except Exception:
            anon = src
    out = None
    if gpt_client_mod and hasattr(gpt_client_mod, "analyze"):
        try:
            out = gpt_client_mod.analyze(anon, specialty_id=specialty_id, user=user)
        except Exception:
            out = None
    if isinstance(out, dict) and "summary" in out and "data" in out:
        return out
    s = " ".join(src.strip().splitlines())[:400]
    data = {
        "summary": s,
        "event_date": now().date().strftime("%Y-%m-%d"),
        "detected_specialty": "",
        "suggested_tags": [],
        "blood_test_results": [],
        "diagnosis": "",
        "treatment_plan": "",
        "doctors": [],
        "date_created": None,
    }
    return {"summary": s, "data": data}


def _ensure_permanent_tags(document, creation_date=None):
    if not Tag:
        return
    perm = []
    try:
        if document.doc_kind:
            t, _ = Tag.objects.get_or_create(slug=f"document_kind:{document.doc_kind}")
            perm.append(t)
        if document.specialty_id:
            t, _ = Tag.objects.get_or_create(slug=f"specialty:{document.specialty_id}")
            perm.append(t)
        if document.category_id:
            t, _ = Tag.objects.get_or_create(slug=f"category:{document.category_id}")
            perm.append(t)
        if document.doc_type_id:
            t, _ = Tag.objects.get_or_create(slug=f"doc_type:{document.doc_type_id}")
            perm.append(t)
        if creation_date:
            t, _ = Tag.objects.get_or_create(slug=f"date:{_ddmmyyyy(creation_date)}")
            perm.append(t)
        if perm:
            document.tags.add(*perm)
    except Exception:
        pass


def _upsert_doctor(doctor_block):
    if not Doctor or not doctor_block:
        return None
    full = (doctor_block.get("full_name") or "").strip()
    if not full:
        return None
    spec = (doctor_block.get("specialty") or "").strip()
    try:
        obj, _ = Doctor.objects.get_or_create(full_name=full, defaults={"specialty_text": spec})
        if spec and not obj.specialty_text:
            obj.specialty_text = spec
            obj.save(update_fields=["specialty_text"])
        return obj
    except Exception:
        return None


def _lab_indicator_by_name(name, unit=None, ref_range=None):
    if not LabIndicator or not name:
        return None
    try:
        obj, _ = LabIndicator.objects.get_or_create(name=name.strip())
        if unit and not getattr(obj, "unit", None):
            obj.unit = unit
        if ref_range:
            lo, hi = _parse_ref_range(ref_range)
            if lo is not None:
                obj.reference_low = lo
            if hi is not None:
                obj.reference_high = hi
        obj.save()
        return obj
    except Exception:
        return None


def _create_lab_measurement(event, ind, value, measured_at):
    if not LabTestMeasurement or not event or not ind:
        return
    v = _to_float(value)
    ts = _to_aware_dt(measured_at, fallback_day=event.event_date or now().date())
    try:
        LabTestMeasurement.objects.create(medical_event=event, indicator=ind, value=v, measured_at=ts)
    except Exception:
        pass


@transaction.atomic
def confirm_and_save(
    user,
    category,
    specialty,
    doc_type,
    existing_event=None,
    file=None,
    file_mime="",
    file_kind="",
    final_text="",
    final_summary="",
    analysis=None,
    doctor=None,
):
    ev = existing_event
    if not ev:
        try:
            patient = getattr(user, "patient_profile", None)
        except Exception:
            patient = None
        ev = MedicalEvent.objects.create(
            patient=patient,
            owner=user,
            category=category,
            specialty=specialty,
            doc_type=doc_type,
            event_date=now().date(),
            summary=(final_summary or "")[:255],
        )
    doc = Document(
        owner=user,
        medical_event=ev,
        category=category,
        specialty=specialty,
        doc_type=doc_type,
        original_ocr_text=final_text or "",
        summary=(final_summary or "")[:255],
        file_mime=file_mime or "",
        doc_kind=(file_kind or "other"),
    )
    if file:
        doc.file = file
        try:
            doc.file_size = getattr(file, "size", 0)
        except Exception:
            pass
    doc.save()

    creation_date = None
    if isinstance(analysis, dict):
        data = analysis.get("data") if isinstance(analysis.get("data"), dict) else analysis
        if data:
            cd = data.get("date_created")
            creation_date = _to_iso_date(cd) or None
    _ensure_permanent_tags(doc, creation_date=creation_date)

    editable_tags = []
    try:
        if isinstance(analysis, dict):
            data = analysis.get("data") if isinstance(analysis.get("data"), dict) else analysis
            for t in (data.get("suggested_tags") or []):
                if Tag and isinstance(t, str) and t.strip():
                    tag, _ = Tag.objects.get_or_create(slug=t.strip())
                    editable_tags.append(tag)
        if editable_tags:
            doc.tags.add(*editable_tags)
    except Exception:
        pass

    if doctor:
        d = _upsert_doctor(doctor)
        if d and hasattr(doc, "doctors"):
            try:
                doc.doctors.add(d)
            except Exception:
                pass

    if isinstance(analysis, dict):
        data = analysis.get("data") if isinstance(analysis.get("data"), dict) else analysis
        labs = data.get("blood_test_results") or []
        if isinstance(labs, list):
            for r in labs:
                try:
                    name = (r.get("indicator_name") or "").strip()
                    value = r.get("value")
                    unit = r.get("unit")
                    ref = r.get("reference_range")
                    ts = r.get("measured_at") or ev.event_date
                    ind = _lab_indicator_by_name(name, unit=unit, ref_range=ref)
                    if ind:
                        _create_lab_measurement(ev, ind, value, ts)
                except Exception:
                    continue

    return {"ok": True, "event_id": ev.id, "document_id": doc.id}
