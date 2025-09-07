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
    Document,
    MedicalCategory,
    MedicalSpecialty,
    DocumentType,
    Tag,
    DocumentTag,
    TagKind,
    LabIndicator,
    LabTestMeasurement,
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
            if resp and getattr(resp, "full_text_annotation", None) and resp.full_text_annotation.text:
                text = resp.full_text_annotation.text
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

def _parse_ref_range(s):
    if not s:
        return None, None
    txt = str(s)
    m = re.findall(r"[-+]?\d*[\.,]?\d+", txt)
    vals = []
    for t in m:
        try:
            vals.append(float(t.replace(",", ".")))
        except Exception:
            pass
    if len(vals) >= 2:
        return min(vals[0], vals[1]), max(vals[0], vals[1])
    if len(vals) == 1:
        return vals[0], None
    return None, None

def _iso_date(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(str(s), fmt).date()
        except Exception:
            continue
    try:
        return datetime.fromisoformat(str(s)).date()
    except Exception:
        return None

def _iso_dt(s):
    if not s:
        return None
    t = str(s).replace("Z", "").strip()
    fmts = ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M:%S", "%Y-%m-%d"]
    for f in fmts:
        try:
            dt = datetime.strptime(t, f)
            try:
                return make_aware(dt, get_current_timezone())
            except Exception:
                return dt
        except Exception:
            continue
    return None

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
            try:
                return Tag.objects.get(slug=slug)
            except Exception:
                return None

def _attach_doc_tag(doc, tag, permanent=True):
    if not tag:
        return
    try:
        DocumentTag.objects.get_or_create(document=doc, tag=tag, defaults={"is_inherited": False, "is_permanent": bool(permanent)})
    except Exception:
        pass

def _attach_event_tag(ev, tag):
    if not tag:
        return
    try:
        ev.tags.add(tag)
    except Exception:
        pass

def _ensure_indicator(name, unit, ref_range):
    if not name:
        return None
    nm = (name or "").strip()
    un = (unit or "").strip()
    low, high = _parse_ref_range(ref_range)
    slug = re.sub(r"[^a-z0-9\-]+", "-", nm.lower())
    try:
        ind = LabIndicator.objects.get(slug__iexact=slug)
        updates = []
        if un and getattr(ind, "unit", "") != un:
            ind.unit = un
            updates.append("unit")
        if low is not None and getattr(ind, "reference_low", None) != low:
            ind.reference_low = low
            updates.append("reference_low")
        if high is not None and getattr(ind, "reference_high", None) != high:
            ind.reference_high = high
            updates.append("reference_high")
        if updates:
            ind.save(update_fields=updates)
        return ind
    except LabIndicator.DoesNotExist:
        try:
            ind = LabIndicator.objects.create(unit=un, reference_low=low, reference_high=high, is_active=True)
            try:
                ind.set_current_language("bg")
                ind.name = nm
                ind.save()
            except Exception:
                pass
            return ind
        except Exception:
            return None

def _noon(dt_date):
    if not isinstance(dt_date, date):
        return now()
    dtt = datetime.combine(dt_date, time(12, 0, 0))
    try:
        return make_aware(dtt, get_current_timezone())
    except Exception:
        return dtt

def _norm_name(s):
    x = re.sub(r"\s+", " ", str(s or "")).strip()
    return x

def _slugify_name(s):
    return "doctor:" + re.sub(r"[^a-z0-9\-]+", "-", _norm_name(s).lower())

@transaction.atomic
def confirm_and_save(user, category, specialty, doc_type, existing_event, file, file_mime, file_kind, final_text, final_summary, analysis, doctor=None):
    patient, _ = PatientProfile.objects.get_or_create(user=user)
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
    size_val = getattr(file, "size", None)
    doc = Document.objects.create(
        owner=user,
        medical_event=ev,
        category=category if isinstance(category, MedicalCategory) else None,
        specialty=specialty if isinstance(specialty, MedicalSpecialty) else None,
        doc_type=doc_type if isinstance(doc_type, DocumentType) else None,
        file=file,
        file_mime=file_mime,
        file_size=size_val,
        doc_kind=(str(file_kind).lower() if file_kind else "other"),
        original_ocr_text=final_text or "",
        summary=final_summary or "",
    )
    data = analysis.get("data") if isinstance(analysis, dict) else {}
    dc = data.get("date_created") if isinstance(data, dict) else None
    dc_iso = None
    if dc:
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y"):
            try:
                dc_iso = datetime.strptime(str(dc), fmt).date()
                break
            except Exception:
                continue
        if not dc_iso:
            try:
                dc_iso = datetime.fromisoformat(str(dc)).date()
            except Exception:
                dc_iso = None
    if dc_iso:
        doc.date_created = dc_iso
        try:
            doc.save(update_fields=["date_created"])
        except Exception:
            pass
    perm = []
    if file_kind:
        perm.append(("permanent:document_kind:" + str(file_kind).lower(), str(file_kind)))
    if specialty:
        perm.append(("permanent:specialty:" + str(getattr(specialty, "id", "")), getattr(specialty, "safe_translation_getter", lambda *a, **k: None)("name", any_language=True) or getattr(specialty, "name", "") or "specialty"))
    if category:
        perm.append(("permanent:category:" + str(getattr(category, "id", "")), getattr(category, "safe_translation_getter", lambda *a, **k: None)("name", any_language=True) or getattr(category, "name", "") or "category"))
    if doc_type:
        perm.append(("permanent:doc_type:" + str(getattr(doc_type, "id", "")), getattr(doc_type, "safe_translation_getter", lambda *a, **k: None)("name", any_language=True) or getattr(doc_type, "name", "") or "doc_type"))
    dd_tag = None
    src_date = dc_iso or getattr(ev, "event_date", None) or now().date()
    try:
        dd = src_date.strftime("%d-%m-%Y")
        dd_tag = ("permanent:date:" + dd, "date:" + dd)
    except Exception:
        dd_tag = None
    for slug, label in perm:
        t = _ensure_tag(slug, label)
        _attach_doc_tag(doc, t, True)
        _attach_event_tag(ev, t)
    if dd_tag:
        t = _ensure_tag(dd_tag[0], dd_tag[1])
        _attach_doc_tag(doc, t, True)
        _attach_event_tag(ev, t)
    editable = []
    if isinstance(data, dict):
        for s in data.get("suggested_tags") or []:
            val = str(s).strip()
            if val:
                editable.append(val)
    for tag_name in editable:
        slug = "user:" + re.sub(r"[^a-z0-9\-]+", "-", tag_name.lower())
        t = _ensure_tag(slug, tag_name)
        _attach_doc_tag(doc, t, False)
        _attach_event_tag(ev, t)
    labs = []
    if isinstance(data, dict):
        labs = data.get("blood_test_results") or []
    if labs:
        for r in labs:
            name = (r.get("indicator_name") or "").strip()
            if not name:
                continue
            val = _parse_float(r.get("value"))
            unit = (r.get("unit") or "").strip()
            ref = r.get("reference_range") or ""
            when = None
            if r.get("measured_at"):
                t = str(r.get("measured_at")).replace("Z", "").strip()
                fmts = ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M:%S", "%Y-%m-%d"]
                for f in fmts:
                    try:
                        dt = datetime.strptime(t, f)
                        try:
                            when = make_aware(dt, get_current_timezone())
                        except Exception:
                            when = dt
                        break
                    except Exception:
                        continue
            if when is None:
                if getattr(ev, "event_date", None):
                    dtt = datetime.combine(ev.event_date, time(12, 0, 0))
                    try:
                        when = make_aware(dtt, get_current_timezone())
                    except Exception:
                        when = dtt
                else:
                    when = now()
            ind = _ensure_indicator(name, unit, ref)
            if ind is None or val is None:
                continue
            try:
                LabTestMeasurement.objects.create(
                    medical_event=ev,
                    indicator=ind,
                    value=val,
                    measured_at=when,
                )
            except Exception:
                pass
    doc_block = doctor or {}
    name_in = re.sub(r"\s+", " ", str(doc_block.get("full_name") or "")).strip()
    sel_specialty_id = doc_block.get("specialty_id")
    if name_in:
        slug = "doctor:" + re.sub(r"[^a-z0-9\-]+", "-", name_in.lower())
        tag = _ensure_tag(slug, name_in)
        _attach_doc_tag(doc, tag, False)
        _attach_event_tag(ev, tag)
    if sel_specialty_id:
        try:
            sp = MedicalSpecialty.objects.get(id=sel_specialty_id)
            sp_name = getattr(sp, "safe_translation_getter", lambda *a, **k: None)("name", any_language=True) or getattr(sp, "name", "") or ""
            tslug = "doctor_specialty:" + str(sel_specialty_id)
            t = _ensure_tag(tslug, sp_name or tslug)
            _attach_doc_tag(doc, t, False)
            _attach_event_tag(ev, t)
        except MedicalSpecialty.DoesNotExist:
            pass
    return {"event_id": ev.id, "document_id": doc.id}
