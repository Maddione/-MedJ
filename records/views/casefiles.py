from datetime import datetime
from types import SimpleNamespace
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, F, DateTimeField
from django.db.models.functions import Coalesce, Cast
from django.shortcuts import render, get_object_or_404
from records.models import (
    Document,
    MedicalEvent,
    MedicalCategory,
    MedicalSpecialty,
    DocumentType,
    Tag,
)

def _sel_list(qd, key):
    vals = qd.getlist(key)
    out = []
    for v in vals:
        s = str(v).strip()
        if s:
            out.append(s)
    return out

def _t(obj, field):
    try:
        return obj.safe_translation_getter(field) or ""
    except Exception:
        try:
            return getattr(obj, field, "") or ""
        except Exception:
            return ""

@login_required
def casefiles(request):
    patient = getattr(getattr(request.user, "patient_profile", None), "id", None)
    if not patient:
        ctx = {
            "categories": [],
            "specialties": [],
            "tags_all": [],
            "selected": {
                "category": [],
                "specialty": [],
                "tags": [],
                "q": "",
                "date_from": "",
                "date_to": "",
                "sort": "date_desc",
            },
            "grouped": [],
            "hot_categories": [],
            "hot_specialties": [],
        }
        return render(request, "main/casefiles.html", ctx)

    sel_categories = _sel_list(request.GET, "category")
    sel_specialties = _sel_list(request.GET, "specialty")
    sel_tags = _sel_list(request.GET, "tags")
    q = (request.GET.get("q") or "").strip()
    date_from = (request.GET.get("date_from") or "").strip()
    date_to = (request.GET.get("date_to") or "").strip()
    sort = (request.GET.get("sort") or "date_desc").strip()

    qs = (
        Document.objects.select_related(
            "doc_type",
            "medical_event",
            "medical_event__specialty",
            "medical_event__category",
        )
        .filter(medical_event__patient_id=patient, owner=request.user)
    )

    if date_from:
        qs = qs.filter(medical_event__event_date__gte=date_from)
    if date_to:
        qs = qs.filter(medical_event__event_date__lte=date_to)

    if sel_tags:
        ids = [int(t) for t in sel_tags if str(t).isdigit()]
        names = [t for t in sel_tags if not str(t).isdigit()]
        tag_q = Q()
        if ids:
            tag_q |= Q(tags__id__in=ids)
        if names:
            tag_q |= Q(tags__translations__name__in=names)
        qs = qs.filter(tag_q).distinct()

    if q:
        qs = qs.filter(
            Q(summary__icontains=q)
            | Q(tags__translations__name__icontains=q)
            | Q(medical_event__summary__icontains=q)
            | Q(doc_type__translations__name__icontains=q)
        ).distinct()

    if sel_specialties:
        qs = qs.filter(
            medical_event__specialty_id__in=[
                int(x) for x in sel_specialties if str(x).isdigit()
            ]
        )
    if sel_categories:
        qs = qs.filter(
            medical_event__category_id__in=[
                int(x) for x in sel_categories if str(x).isdigit()
            ]
        )

    qs = qs.annotate(
        sort_date=Coalesce(
            Cast(F("medical_event__event_date"), DateTimeField()),
            F("uploaded_at"),
            output_field=DateTimeField(),
        )
    )
    sort_map = {
        "date_asc": ("sort_date", "id"),
        "date_desc": ("-sort_date", "-id"),
        "type_asc": ("doc_type__translations__name", "id"),
        "type_desc": ("-doc_type__translations__name", "-id"),
        "name_asc": ("summary", "id"),
        "name_desc": ("-summary", "-id"),
        "spec_asc": ("medical_event__specialty__translations__name", "id"),
        "spec_desc": ("-medical_event__specialty__translations__name", "-id"),
    }
    qs = qs.order_by(*sort_map.get(sort, ("-sort_date", "-id")))
    docs = list(qs)

    items = []
    for d in docs:
        ev = d.medical_event
        dt = getattr(ev, "event_date", None) or getattr(d, "uploaded_at", None)
        doc_type_name = _t(d.doc_type, "name") if getattr(d, "doc_type", None) else ""
        spec_name = _t(ev.specialty, "name") if getattr(ev, "specialty", None) else ""
        try:
            tag_names = [(_t(t, "name") or "") for t in d.tags.all()]
        except Exception:
            tag_names = []
        items.append(
            {
                "id": d.id,
                "event_id": getattr(ev, "id", None),
                "date": dt,
                "title": d.summary or doc_type_name or "Document",
                "type_name": doc_type_name,
                "specialist": spec_name,
                "tags": [x for x in tag_names if x],
            }
        )

    groups = {}
    months_bg = [
        "Януари",
        "Февруари",
        "Март",
        "Април",
        "Май",
        "Юни",
        "Юли",
        "Август",
        "Септември",
        "Октомври",
        "Ноември",
        "Декември",
    ]
    for it in items:
        dt = it["date"]
        if not dt:
            key = "nodate"
            label = "Без дата"
        else:
            key = f"{dt.year:04d}-{dt.month:02d}"
            label = f"{months_bg[dt.month-1]},{dt.year}"
        if key not in groups:
            groups[key] = {"label": label, "items": []}
        groups[key]["items"].append(it)

    ordered = sorted(
        groups.items(), key=lambda kv: (kv[0] == "nodate", kv[0]), reverse=True
    )
    grouped = [
        {"label": v["label"], "items": v["items"], "count": len(v["items"])}
        for _, v in ordered
    ]

    base_for_counts = (
        Document.objects.select_related(
            "medical_event",
            "medical_event__specialty",
            "medical_event__category",
        )
        .filter(medical_event__patient_id=patient, owner=request.user)
    )
    if date_from:
        base_for_counts = base_for_counts.filter(
            medical_event__event_date__gte=date_from
        )
    if date_to:
        base_for_counts = base_for_counts.filter(
            medical_event__event_date__lte=date_to
        )
    if sel_specialties:
        base_for_counts = base_for_counts.filter(
            medical_event__specialty_id__in=[
                int(x) for x in sel_specialties if str(x).isdigit()
            ]
        )
    if sel_categories:
        base_for_counts = base_for_counts.filter(
            medical_event__category_id__in=[
                int(x) for x in sel_categories if str(x).isdigit()
            ]
        )

    cat_counts = (
        base_for_counts.exclude(medical_event__category__isnull=True)
        .values("medical_event__category_id")
        .annotate(c=Count("id"))
    )
    cat_count_map = {r["medical_event__category_id"]: r["c"] for r in cat_counts}
    categories = [
        {"id": c.id, "name": _t(c, "name"), "count": int(cat_count_map.get(c.id, 0))}
        for c in MedicalCategory.objects.filter(is_active=True).order_by(
            "translations__name"
        )
    ]

    spec_counts = (
        base_for_counts.exclude(medical_event__specialty__isnull=True)
        .values("medical_event__specialty_id")
        .annotate(c=Count("id"))
    )
    spec_count_map = {r["medical_event__specialty_id"]: r["c"] for r in spec_counts}
    specialties = [
        {"id": s.id, "name": _t(s, "name"), "count": int(spec_count_map.get(s.id, 0))}
        for s in MedicalSpecialty.objects.filter(is_active=True).order_by(
            "translations__name"
        )
    ]

    tags_qs = (
        Tag.objects.filter(
            documents__medical_event__patient_id=patient, documents__owner=request.user
        )
        .distinct()
        .order_by("translations__name")
    )
    tags_all = [{"id": t.id, "name": _t(t, "name")} for t in tags_qs]

    ctx = {
        "categories": categories,
        "specialties": specialties,
        "tags_all": tags_all,
        "grouped": grouped,
        "selected": {
            "category": sel_categories,
            "specialty": sel_specialties,
            "tags": sel_tags,
            "q": q,
            "date_from": date_from,
            "date_to": date_to,
            "sort": sort,
        },
        "hot_categories": [],
        "hot_specialties": [],
    }
    return render(request, "main/casefiles.html", ctx)

@login_required
def event_detail(request, pk):
    ev = get_object_or_404(
        MedicalEvent.objects.select_related(
            "specialty", "category", "doc_type", "patient"
        ),
        pk=pk,
        owner=request.user,
    )
    docs = ev.documents.select_related("doc_type").order_by("-uploaded_at", "-id")
    proxy = SimpleNamespace(
        event_date=ev.event_date,
        get_event_type_title_display=_t(ev.doc_type, "name"),
        display_categories=_t(ev.category, "name") if ev.category_id else "",
        specialty=SimpleNamespace(name=_t(ev.specialty, "name")),
        summary=ev.summary or "",
    )
    ctx = {"medical_event": proxy, "documents": docs}
    return render(request, "subpages/eventsubpages/event_detail.html", ctx)
