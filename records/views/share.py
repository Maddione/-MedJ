from __future__ import annotations

import json
import time
from io import BytesIO
from urllib.parse import urlencode

import qrcode
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.db.models import Q
from django.http import HttpRequest, JsonResponse, HttpResponseBadRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from records.models import (
    Document,
    LabIndicator,
    LabTestMeasurement,
    MedicalCategory,
    MedicalEvent,
    MedicalSpecialty,
    Tag,
    TagKind,
)
from .utils import require_patient_profile, parse_date, safe_translated

_SIGNER_SALT = "medj.share"


def _make_token(payload: dict) -> str:
    s = signing.Signer(salt=_SIGNER_SALT)
    data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    return s.sign(data)


def share_document_page(request: HttpRequest) -> HttpResponse:
    patient = require_patient_profile(request.user)

    def _sorted(items):
        return sorted(
            items,
            key=lambda item: (item.get("name") or item.get("label") or "").lower(),
        )

    specialties_qs = (
        MedicalSpecialty.objects.filter(
            Q(events__patient=patient) | Q(documents__owner=request.user)
        )
        .distinct()
    )
    specialty_options = _sorted(
        [
            {
                "id": spec.id,
                "name": safe_translated(spec) or getattr(spec, "slug", str(spec.id)),
            }
            for spec in specialties_qs
        ]
    )

    categories_qs = (
        MedicalCategory.objects.filter(
            Q(events__patient=patient) | Q(documents__owner=request.user)
        )
        .distinct()
    )
    category_options = _sorted(
        [
            {
                "id": cat.id,
                "name": safe_translated(cat) or getattr(cat, "slug", str(cat.id)),
            }
            for cat in categories_qs
        ]
    )

    events_qs = (
        MedicalEvent.objects.filter(patient=patient)
        .select_related("specialty", "category")
        .order_by("-event_date", "-id")
    )
    event_options = [
        {
            "id": ev.id,
            "label": " — ".join(
                part
                for part in [
                    ev.event_date.strftime("%d.%m.%Y") if ev.event_date else "",
                    ev.summary
                    or safe_translated(ev.specialty)
                    or safe_translated(ev.category)
                    or _("Събитие #{id}").format(id=ev.id),
                ]
                if part
            ),
        }
        for ev in events_qs[:50]
    ]

    indicator_labels = {}
    indicator_tag_qs = (
        Tag.objects.filter(kind=TagKind.INDICATOR, documents__owner=request.user)
        .distinct()
    )
    for tag in indicator_tag_qs:
        indicator_labels[tag.slug] = safe_translated(tag) or tag.slug

    indicator_qs = (
        LabIndicator.objects.filter(measurements__medical_event__patient=patient)
        .distinct()
    )
    for indicator in indicator_qs:
        indicator_labels.setdefault(
            indicator.slug,
            safe_translated(indicator) or indicator.slug,
        )

    indicator_options = _sorted(
        [
            {
                "slug": slug,
                "name": label,
            }
            for slug, label in indicator_labels.items()
        ]
    )

    context = {
        "specialty_options": specialty_options,
        "category_options": category_options,
        "event_options": event_options,
        "indicator_options": indicator_options,
    }
    return render(request, "main/share.html", context)


def share_view(request: HttpRequest, token: str) -> HttpResponse:
    return render(request, "subpages/share_view.html", {"token": token})


def share_revoke(request: HttpRequest, token: str) -> JsonResponse:
    return JsonResponse({"ok": True, "token": str(token)})


def healthcheck(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})


@login_required
@require_POST
def create_download_links(request: HttpRequest) -> JsonResponse:
    try:
        data = json.loads(request.body or "{}")
    except Exception:
        return HttpResponseBadRequest("bad json")

    def as_bool(value, default=True):
        if value in (None, "", []):
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    generate_events = as_bool(data.get("generate_events"), True)
    generate_labs = as_bool(data.get("generate_labs"), True)
    generate_csv = as_bool(data.get("generate_csv"), True)

    def clamp_hours(value, default):
        try:
            val = int(value)
        except Exception:
            val = default
        if val < 1:
            val = 1
        if val > 8760:
            val = 8760
        return val

    hours_events = clamp_hours(data.get("hours_events", 24), 24)
    hours_labs = clamp_hours(data.get("hours_labs", 24), 24)
    hours_csv = clamp_hours(data.get("hours_csv", 24), 24)

    filters = data.get("filters") or {}
    start_raw = (data.get("start_date") or "").strip()
    end_raw = (data.get("end_date") or "").strip()
    start_dt = parse_date(start_raw) if start_raw else None
    end_dt = parse_date(end_raw) if end_raw else None

    patient = require_patient_profile(request.user)

    def as_int_list(value):
        if isinstance(value, (list, tuple)):
            items = value
        elif value in (None, ""):
            items = []
        else:
            items = [value]
        out = []
        for item in items:
            try:
                out.append(int(item))
            except (TypeError, ValueError):
                continue
        return out

    category_ids = as_int_list(filters.get("category"))
    specialty_ids = as_int_list(filters.get("specialty"))
    event_ids = as_int_list(filters.get("event"))
    indicator_raw = filters.get("indicator")
    if isinstance(indicator_raw, (list, tuple)):
        indicator_slugs = [str(v).strip() for v in indicator_raw if str(v).strip()]
    elif indicator_raw:
        indicator_slugs = [str(indicator_raw).strip()]
    else:
        indicator_slugs = []

    indicator_event_ids = []
    if indicator_slugs:
        indicator_event_ids = list(
            LabTestMeasurement.objects.filter(
                medical_event__patient=patient,
                indicator__slug__in=indicator_slugs,
            )
            .values_list("medical_event_id", flat=True)
            .distinct()
        )

    docs_qs = (
        Document.objects.filter(owner=request.user)
        .select_related("doc_type")
        .prefetch_related("tags")
        .order_by("-uploaded_at")
    )
    if category_ids:
        docs_qs = docs_qs.filter(category_id__in=category_ids)
    if specialty_ids:
        docs_qs = docs_qs.filter(specialty_id__in=specialty_ids)
    if event_ids:
        docs_qs = docs_qs.filter(medical_event_id__in=event_ids)
    if indicator_slugs:
        indicator_filter = Q(tags__slug__in=indicator_slugs) | Q(
            medical_event__labtests__indicator__slug__in=indicator_slugs
        )
        if indicator_event_ids:
            indicator_filter = indicator_filter | Q(medical_event_id__in=indicator_event_ids)
        docs_qs = docs_qs.filter(indicator_filter)
    if start_dt:
        docs_qs = docs_qs.filter(
            Q(uploaded_at__date__gte=start_dt)
            | Q(document_date__gte=start_dt)
            | Q(medical_event__event_date__gte=start_dt)
        )
    if end_dt:
        docs_qs = docs_qs.filter(
            Q(uploaded_at__date__lte=end_dt)
            | Q(document_date__lte=end_dt)
            | Q(medical_event__event_date__lte=end_dt)
        )
    docs_qs = docs_qs.distinct()

    docs_total = docs_qs.count()
    doc_items = []
    for doc in docs_qs[:25]:
        detail_url = request.build_absolute_uri(
            reverse("medj:document_detail", args=[doc.id])
        )
        export_pdf_url = request.build_absolute_uri(
            reverse("medj:document_export_pdf", args=[doc.id])
        )
        doc_items.append(
            {
                "id": doc.id,
                "title": doc.display_title,
                "uploaded_at": timezone.localtime(doc.uploaded_at).strftime("%d.%m.%Y %H:%M") if doc.uploaded_at else "",
                "document_date": doc.document_date.isoformat() if doc.document_date else "",
                "detail_url": detail_url,
                "export_pdf_url": export_pdf_url,
                "tags": [
                    t.safe_translation_getter("name", any_language=True) or getattr(t, "name", "")
                    for t in doc.tags.all()
                ],
            }
        )

    lab_qs = LabTestMeasurement.objects.filter(medical_event__patient=patient)
    if category_ids:
        lab_qs = lab_qs.filter(medical_event__category_id__in=category_ids)
    if specialty_ids:
        lab_qs = lab_qs.filter(medical_event__specialty_id__in=specialty_ids)
    if event_ids:
        lab_qs = lab_qs.filter(medical_event_id__in=event_ids)
    if indicator_slugs:
        lab_qs = lab_qs.filter(indicator__slug__in=indicator_slugs)
    if start_dt:
        lab_qs = lab_qs.filter(measured_at__date__gte=start_dt)
    if end_dt:
        lab_qs = lab_qs.filter(measured_at__date__lte=end_dt)
    labs_total = lab_qs.count()

    events_qs = MedicalEvent.objects.filter(patient=patient)
    if category_ids:
        events_qs = events_qs.filter(category_id__in=category_ids)
    if specialty_ids:
        events_qs = events_qs.filter(specialty_id__in=specialty_ids)
    if event_ids:
        events_qs = events_qs.filter(id__in=event_ids)
    if indicator_event_ids:
        events_qs = events_qs.filter(id__in=indicator_event_ids)
    if start_dt:
        events_qs = events_qs.filter(event_date__gte=start_dt)
    if end_dt:
        events_qs = events_qs.filter(event_date__lte=end_dt)
    events_total = events_qs.distinct().count()

    base_params = {}
    if start_dt:
        base_params["start_date"] = start_dt.isoformat()
    if end_dt:
        base_params["end_date"] = end_dt.isoformat()
    if specialty_ids:
        base_params["specialty"] = [str(s) for s in specialty_ids]
    if category_ids:
        base_params["category"] = [str(c) for c in category_ids]
    if event_ids:
        base_params["event"] = [str(e) for e in event_ids]
    if indicator_slugs:
        base_params["indicator"] = indicator_slugs

    now = int(time.time())
    urls = {"pdf_events_url": "", "pdf_labs_url": "", "csv_url": ""}
    if generate_events:
        pdf_events_path = reverse("medj:print_pdf")
        payload_events = {"k": "print_pdf", "exp": now + hours_events * 3600, "labs": 0}
        token_events = _make_token(payload_events)
        qs_events = dict(base_params)
        qs_events["t"] = token_events
        events_url = request.build_absolute_uri(pdf_events_path) + "?" + urlencode(qs_events, doseq=True)
        urls["pdf_events_url"] = events_url
    if generate_labs:
        pdf_labs_path = reverse("medj:print_pdf")
        payload_labs = {"k": "print_pdf", "exp": now + hours_labs * 3600, "labs": 1}
        token_labs = _make_token(payload_labs)
        qs_labs = dict(base_params)
        qs_labs["labs"] = 1
        qs_labs["t"] = token_labs
        labs_url = request.build_absolute_uri(pdf_labs_path) + "?" + urlencode(qs_labs, doseq=True)
        urls["pdf_labs_url"] = labs_url
    if generate_csv:
        csv_path = reverse("medj:print_csv")
        payload_csv = {"k": "print_csv", "exp": now + hours_csv * 3600}
        token_csv = _make_token(payload_csv)
        qs_csv = dict(base_params)
        qs_csv["t"] = token_csv
        csv_url = request.build_absolute_uri(csv_path) + "?" + urlencode(qs_csv, doseq=True)
        urls["csv_url"] = csv_url

    pieces = []
    if docs_total:
        pieces.append(f"{docs_total} документа")
    if events_total:
        pieces.append(f"{events_total} събития")
    if labs_total:
        pieces.append(f"{labs_total} лабораторни показателя")
    if pieces:
        notice = "Намерени: " + ", ".join(pieces) + "."
    else:
        notice = "Няма резултати за избраните филтри."

    payload = {
        **urls,
        "counts": {
            "documents": docs_total,
            "events": events_total,
            "labs": labs_total,
        },
        "documents": doc_items,
        "notice": notice,
    }

    return JsonResponse(payload)


@login_required
@require_POST
def create_share_token(request: HttpRequest) -> JsonResponse:
    return create_download_links(request)


def share_qr(request: HttpRequest, token=None) -> HttpResponse:
    if request.method == "POST":
        try:
            payload = json.loads(request.body or "{}")
        except Exception:
            payload = {}
        url = (payload.get("url") or "").strip()
    else:
        url = (request.GET.get("url") or "").strip()
    if not url:
        return HttpResponseBadRequest("missing url")
    img = qrcode.make(url)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return HttpResponse(buf.read(), content_type="image/png")


def qr_for_url(request: HttpRequest) -> HttpResponse:
    return share_qr(request)
