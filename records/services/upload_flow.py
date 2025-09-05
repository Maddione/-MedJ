import json
import os
import requests
import uuid
from pathlib import Path

from django.conf import settings
from django.db import transaction

from records.constants import doc_behavior_for
from records.models import (
    Document, MedicalEvent,
    LabIndicator, LabTestMeasurement
)
from records.utils.labs import normalize_indicator, DEFAULT_UNITS
from records.views.helpers import media_tmp_dir, to_django_file, safe_name, add_tag


def call_ocr_api(file_path: str, doc_type_name="", specialty_name="") -> dict:
    url = os.environ.get("OCR_API_URL", getattr(settings, "OCR_API_URL", "http://ocrapi:5000/ocr"))
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f)}
        data = {}
        if doc_type_name: data["doc_type"] = doc_type_name
        if specialty_name: data["specialty"] = specialty_name
        r = requests.post(url, files=files, data=data, timeout=90)
    r.raise_for_status()
    return r.json()

def persist_upload(*, patient, tmp_abs: Path, doc_type, specialty, category,
                   target_event_id=None, new_event_date=None,
                   approved_text: str = "", analysis: dict | None = None) -> tuple[MedicalEvent, Document]:
    analysis = analysis or {}
    with transaction.atomic():
        # Event
        if target_event_id:
            event = (MedicalEvent.objects
                     .select_for_update()
                     .filter(id=target_event_id, patient=patient)
                     .first())
            if event is None:
                raise ValueError("Selected event not found or not accessible.")
            if event.specialty_id != specialty.id:
                event.specialty = specialty
            if getattr(event, "category_id", None) != (category.id if category else None):
                event.category = category
            event.save(update_fields=["specialty", "category"])
        else:
            event = MedicalEvent.objects.create(
                patient=patient,
                specialty=specialty,
                category=category,
                event_date=new_event_date,
                summary="",
            )

        # Document
        doc = Document.objects.create(
            medical_event=event,
            doc_type=doc_type,
            title=safe_name(doc_type) or "Document",
            file=to_django_file(tmp_abs),
        )

        # Summary / date
        if analysis.get("event_date") and not event.event_date:
            event.event_date = analysis["event_date"]
        if analysis.get("summary") and not event.summary:
            event.summary = (analysis["summary"] or "")[:500]
        if not event.summary and approved_text:
            event.summary = approved_text.splitlines()[0][:500]
        event.save()

        # Full JSON → doc.meta (ако го имаш)
        if hasattr(doc, "meta"):
            doc.meta = analysis or {}
            doc.save(update_fields=["meta"])

        # Tags: detected_specialty, specialty, doc_type, category, date
        det_spec = (analysis.get("detected_specialty") or "").strip()
        if det_spec:
            add_tag(det_spec, event, doc)
        add_tag(safe_name(specialty), event, doc)
        add_tag(safe_name(doc_type), event, doc)
        if category:
            add_tag(safe_name(category), event, doc)
        if event.event_date:
            add_tag(event.event_date.isoformat(), event, doc)
        try:
            event.tags.add(*doc.tags.all())
        except Exception:
            pass

        # Labs (ако има)
        for row in (analysis.get("blood_test_results") or []):
            raw = (row.get("indicator") or "").strip()
            if not raw:
                continue
            canon, display = normalize_indicator(raw)
            unit = (row.get("unit") or "").strip() or (DEFAULT_UNITS.get(canon) if canon else None)
            indicator, _ = LabIndicator.objects.get_or_create(
                name=display,
                defaults={"unit": unit, "reference_low": row.get("ref_low"), "reference_high": row.get("ref_high")}
            )
            LabTestMeasurement.objects.create(
                medical_event=event,
                indicator=indicator,
                value=row.get("value"),
                measured_at=row.get("measured_at") or analysis.get("event_date") or event.event_date,
            )

        # Diagnosis / Plan по вид документ
        beh = doc_behavior_for(doc_type)
        if beh.get("has_diag"):
            diag = (analysis.get("diagnosis") or "").strip()
            if diag and hasattr(event, "diagnosis") and not event.diagnosis:
                event.diagnosis = diag[:1000]
                event.save(update_fields=["diagnosis"])
        if beh.get("has_rx"):
            plan = (analysis.get("treatment_plan") or "").strip()
            if plan and hasattr(event, "treatment_plan") and not event.treatment_plan:
                event.treatment_plan = plan[:2000]
                event.save(update_fields=["treatment_plan"])

    return event, doc

def store_temp_analysis(analysis: dict) -> str:
    name = f"{uuid.uuid4().hex}.json"
    path = media_tmp_dir() / name
    path.write_text(json.dumps(analysis, ensure_ascii=False), encoding="utf-8")
    return name

def load_temp_analysis(name: str) -> dict:
    path = media_tmp_dir() / name
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    finally:
        try: path.unlink()
        except Exception: pass
