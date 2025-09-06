from __future__ import annotations
import io, os, csv, json, time
from pathlib import Path
from datetime import datetime
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.utils.translation import get_language
from django.core import signing
from ..models import Document, MedicalEvent
from records.services.print_utils import render_template_to_pdf, pdf_response
from records.services.csv_to_pdf import events_csv_to_pdf, labs_csv_to_pdf

_SIGNER_SALT = "medj.share"

def _templates_dir() -> Path:
    return Path(settings.BASE_DIR) / "records" / "pdf_templates"

def _template_pdf_path(request: HttpRequest) -> str:
    lang = (getattr(request, "LANGUAGE_CODE", None) or get_language() or "bg").lower().split("-")[0]
    suffix = "eng" if lang == "en" else "bg"
    two = _templates_dir() / f"pdf-template-twopage-{suffix}.pdf"
    one = _templates_dir() / f"pdf-template-{suffix}.pdf"
    if two.exists():
        return str(two)
    return str(one)

def _overlay_bytes_with_template(pdf_bytes: bytes, template_path: str) -> bytes:
    try:
        from PyPDF2 import PdfReader, PdfWriter
    except Exception:
        return pdf_bytes
    if not os.path.exists(template_path):
        return pdf_bytes
    try:
        tmpl_reader = PdfReader(template_path)
        gen_reader = PdfReader(io.BytesIO(pdf_bytes))
    except Exception:
        return pdf_bytes
    if not tmpl_reader.pages:
        return pdf_bytes
    first_tpl_page = tmpl_reader.pages[0]
    second_tpl_page = tmpl_reader.pages[1] if len(tmpl_reader.pages) >= 2 else None
    writer = PdfWriter()
    for i, gen_page in enumerate(gen_reader.pages):
        base_tpl = first_tpl_page if i == 0 else (second_tpl_page or first_tpl_page)
        try:
            page = base_tpl.clone()
        except Exception:
            import copy as _copy
            page = _copy.deepcopy(base_tpl)
        writer.add_page(page)
        writer.pages[-1].merge_page(gen_page)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()

def _token_ok(request: HttpRequest, kind: str) -> bool:
    t = request.GET.get("t")
    if not t:
        return False
    try:
        s = signing.Signer(salt=_SIGNER_SALT)
        raw = s.unsign(t)
        payload = json.loads(raw)
    except Exception:
        return False
    if payload.get("k") != kind:
        return False
    try:
        exp = int(payload.get("exp", 0))
    except Exception:
        return False
    if exp < int(time.time()):
        return False
    if kind == "print_pdf":
        labs_flag = 1 if request.GET.get("labs") else 0
        if int(payload.get("labs", 0)) != labs_flag:
            return False
    return True

def _ddmmyyyy(d):
    if not d:
        return ""
    if isinstance(d, str):
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y"):
            try:
                return datetime.strptime(d, fmt).strftime("%d-%m-%Y")
            except Exception:
                continue
        try:
            return datetime.fromisoformat(d).strftime("%d-%m-%Y")
        except Exception:
            return d
    try:
        return d.strftime("%d-%m-%Y")
    except Exception:
        return ""

def _event_tags_text(ev):
    names = []
    if hasattr(ev, "tags"):
        for t in ev.tags.all().order_by("id"):
            nm = getattr(t, "safe_translation_getter", lambda *a, **k: None)("name", any_language=True) or getattr(t, "name", "") or ""
            if nm:
                names.append(nm)
    return ", ".join(names)

@login_required
def document_export_pdf(request: HttpRequest, pk: int) -> HttpResponse:
    doc = get_object_or_404(Document, pk=pk, owner=request.user)
    context = {"document": doc, "user": request.user}
    pdf_bytes = render_template_to_pdf(request, "subpages/document_export_pdf.html", context)
    pdf_bytes = _overlay_bytes_with_template(pdf_bytes, _template_pdf_path(request))
    return pdf_response(f"document_{pk}.pdf", pdf_bytes, inline=True)

@login_required
def event_export_pdf(request: HttpRequest, pk: int) -> HttpResponse:
    event = get_object_or_404(
        MedicalEvent.objects.select_related("patient__user", "specialty").prefetch_related("documents", "tags"),
        pk=pk, patient__user=request.user
    )
    diagnoses = getattr(event, "diagnoses", None)
    treatment_plans = getattr(event, "treatment_plans", None)
    narrative_sections = getattr(event, "narrative_sections", None)
    labs_qs = getattr(event, "lab_measurements", None)
    context = {
        "event": event,
        "diagnoses": list(diagnoses.all()) if hasattr(diagnoses, "all") else [],
        "treatment_plans": list(treatment_plans.all()) if hasattr(treatment_plans, "all") else [],
        "narrative_sections": list(narrative_sections.all()) if hasattr(narrative_sections, "all") else [],
        "documents": list(event.documents.all()) if hasattr(event, "documents") else [],
        "labs": list(labs_qs.select_related("indicator").all()) if hasattr(labs_qs, "all") else [],
    }
    pdf_bytes = render_template_to_pdf(request, "subpages/event_export_pdf.html", context)
    pdf_bytes = _overlay_bytes_with_template(pdf_bytes, _template_pdf_path(request))
    return pdf_response(f"event_{pk}.pdf", pdf_bytes, inline=True)

@login_required
def export_csv(request: HttpRequest) -> HttpResponse:
    event_id = request.GET.get("event_id")
    if not event_id:
        return HttpResponseBadRequest("missing_event_id")
    ev = get_object_or_404(MedicalEvent, pk=event_id, patient__user=request.user)
    labs_qs = getattr(ev, "lab_measurements", None)
    rows = []
    if hasattr(labs_qs, "select_related"):
        for m in labs_qs.select_related("indicator").order_by("measured_at", "id"):
            ind = m.indicator
            name = getattr(ind, "safe_translation_getter", lambda *a, **k: None)("name", any_language=True) or getattr(ind, "name", "")
            rows.append([
                ev.id,
                _ddmmyyyy(ev.event_date),
                name,
                getattr(m, "value", ""),
                getattr(ind, "unit", ""),
                getattr(ind, "reference_low", ""),
                getattr(ind, "reference_high", ""),
                _ddmmyyyy(getattr(m, "measured_at", None)),
                _event_tags_text(ev),
            ])
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["event_id","event_date","indicator_name","value","unit","reference_low","reference_high","measured_at","tags"])
    for r in rows:
        w.writerow(r)
    resp = HttpResponse(out.getvalue(), content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="event_{ev.id}_labs.csv"'
    return resp

def print_csv(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated and not _token_ok(request, "print_csv"):
        return HttpResponseForbidden()
    labs = request.GET.get("labs")
    out = io.StringIO()
    w = csv.writer(out)
    if labs:
        w.writerow(["date", "indicator", "value", "unit", "reference_low", "reference_high", "abn"])
    else:
        w.writerow(["date", "category", "specialty", "summary"])
    resp = HttpResponse(out.getvalue(), content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="export.csv"'
    return resp

def print_pdf(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated and not _token_ok(request, "print_pdf"):
        return HttpResponseForbidden()
    labs = request.GET.get("labs")
    if labs:
        buf = io.StringIO()
        csv.writer(buf).writerow(["indicator", "value", "unit", "reference_low", "reference_high", "abn"])
        generated = labs_csv_to_pdf(io.BytesIO(buf.getvalue().encode("utf-8")))
        pdf_bytes = _overlay_bytes_with_template(generated, _template_pdf_path(request))
        return pdf_response("labs.pdf", pdf_bytes, inline=True)
    else:
        buf = io.StringIO()
        csv.writer(buf).writerow(["date", "category", "specialty", "summary"])
        generated = events_csv_to_pdf(io.BytesIO(buf.getvalue().encode("utf-8")))
        pdf_bytes = _overlay_bytes_with_template(generated, _template_pdf_path(request))
        return pdf_response("events.pdf", pdf_bytes, inline=True)
