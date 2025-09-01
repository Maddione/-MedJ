from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def casefiles(request):
    patient = cf_get_patient(request.user)
    if not patient:
        return render(request, "main/casefiles.html", {
            "categories": [], "specialties": [], "tags_all": [],
            "selected": {"category": [], "specialty": [], "tags": [], "q": "", "date_from": "", "date_to": "", "sort": "date_desc"},
            "grouped": [], "hot_categories": [], "hot_specialties": [],
        })

    has_category = True
    try:
        MedicalEvent._meta.get_field("category")
    except Exception:
        has_category = False

    base_qs = (
        Document.objects
        .select_related("doc_type", "medical_event", "medical_event__specialty")
        .filter(medical_event__patient=patient)
    )

    sel_categories = cf_parse_multi(request.GET, "category")   # ако has_category=True → category ids, иначе → doc_type ids
    sel_specialties = cf_parse_multi(request.GET, "specialty")
    sel_tags = cf_parse_multi(request.GET, "tags")
    q = (request.GET.get("q") or "").strip()
    date_from = (request.GET.get("date_from") or "").strip()
    date_to = (request.GET.get("date_to") or "").strip()
    sort = (request.GET.get("sort") or "date_desc").strip()

    qs = base_qs

    if date_from:
        qs = qs.filter(medical_event__event_date__gte=date_from)
    if date_to:
        qs = qs.filter(medical_event__event_date__lte=date_to)

    if sel_tags:
        ids = [int(t) for t in sel_tags if str(t).isdigit()]
        names = [t for t in sel_tags if not str(t).isdigit()]
        tag_filter = Q()
        if ids:
            tag_filter |= Q(tags__id__in=ids)
        if names:
            tag_filter |= Q(tags__name__in=names)
        qs = qs.filter(tag_filter).distinct()

    if q:
        qs = qs.filter(
            Q(title__icontains=q)
            | Q(tags__name__icontains=q)
            | Q(medical_event__summary__icontains=q)
            | Q(doc_type__translations__name__icontains=q)
        ).distinct()

    main_qs = qs
    if sel_specialties:
        main_qs = main_qs.filter(medical_event__specialty_id__in=[int(x) for x in sel_specialties if str(x).isdigit()])
    if sel_categories:
        if has_category:
            main_qs = main_qs.filter(medical_event__category_id__in=[int(x) for x in sel_categories if str(x).isdigit()])
        else:
            main_qs = main_qs.filter(doc_type_id__in=[int(x) for x in sel_categories if str(x).isdigit()])

    main_qs = main_qs.annotate(
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
        "name_asc": ("title", "id"),
        "name_desc": ("-title", "-id"),
        "spec_asc": ("medical_event__specialty__translations__name", "id"),
        "spec_desc": ("-medical_event__specialty__translations__name", "-id"),
    }
    main_qs = main_qs.order_by(*sort_map.get(sort, ("-sort_date", "-id")))

    docs = list(main_qs)

    items = []
    for d in docs:
        ev = d.medical_event
        dt = getattr(ev, "event_date", None) or getattr(d, "uploaded_at", None)
        doc_type_name = cf_t(d.doc_type, "name") if getattr(d, "doc_type", None) else ""
        spec_name = cf_t(ev.specialty, "name") if getattr(ev, "specialty", None) else ""
        try:
            tag_names = list(d.tags.values_list("name", flat=True))
        except Exception:
            tag_names = []
        items.append({
            "id": d.id,
            "event_id": getattr(ev, "id", None),
            "date": dt,
            "title": d.title or doc_type_name or "Document",
            "type_name": doc_type_name,
            "specialist": spec_name,
            "tags": tag_names,
        })

    groups = {}
    for it in items:
        dt = it["date"]
        if not dt:
            key = "Без дата"; label = "Без дата"
        else:
            months_bg = ["Януари","Февруари","Март","Април","Май","Юни","Юли","Август","Септември","Октомври","Ноември","Декември"]
            key = f"{dt.year:04d}-{dt.month:02d}"
            label = f"{months_bg[dt.month-1]},{dt.year}"
        groups.setdefault(key, {"label": label, "items": []})
        groups[key]["items"].append(it)

    ordered = sorted(groups.items(), key=lambda kv: (kv[0] == "Без дата", kv[0]), reverse=True)
    grouped = [{"label": v["label"], "items": v["items"], "count": len(v["items"])} for _, v in ordered]


    if has_category:
        try:
            categories = [
                {"id": c.id, "name": cf_t(c, "name"), "count": int(cat_count_map.get(c.id, 0))}
                for c in (  # редът е по име
                    getattr(type("X", (), {"objects": DocumentType.objects}), "objects").filter(
                        is_active=True).order_by("translations__name")
                )
            ]
        except Exception:
            categories = []
    else:
        try:
            categories = [
                {"id": dt.id, "name": cf_t(dt, "name"), "count": int(cat_count_map.get(dt.id, 0))}
                for dt in DocumentType.objects.filter(is_active=True).order_by("translations__name")
            ]
        except Exception:
            categories = []

    try:
        specialties = [
            {"id": s.id, "name": cf_t(s, "name"), "count": int(spec_count_map.get(s.id, 0))}
            for s in MedicalSpecialty.objects.filter(is_active=True).order_by("translations__name")
        ]
    except Exception:
        specialties = []
    try:
        tags_all = list(
            Tag.objects.filter(document__medical_event__patient=patient)
            .annotate(c=Count("id"))
            .order_by("name")
            .values("id", "name")
        )
    except Exception:
        tags_all = []

    cat_qs = qs
    if sel_specialties:
        cat_qs = cat_qs.filter(medical_event__specialty_id__in=[int(x) for x in sel_specialties if str(x).isdigit()])

    if has_category:
        cat_counts_qs = (
            cat_qs.exclude(medical_event__category__isnull=True)
            .values("medical_event__category_id", "medical_event__category__translations__name")
            .annotate(c=Count("id"))
            .order_by("-c")
        )
        hot_categories = [
                             {"id": r["medical_event__category_id"],
                              "name": r["medical_event__category__translations__name"] or "", "count": r["c"]}
                             for r in cat_counts_qs if r["c"] > 0
                         ][:6]
        cat_count_map = {r["medical_event__category_id"]: r["c"] for r in cat_counts_qs}
    else:
        cat_counts_qs = (
            cat_qs.exclude(doc_type__isnull=True)
            .values("doc_type_id", "doc_type__translations__name")
            .annotate(c=Count("id"))
            .order_by("-c")
        )
        hot_categories = [
                             {"id": r["doc_type_id"], "name": r["doc_type__translations__name"] or "", "count": r["c"]}
                             for r in cat_counts_qs if r["c"] > 0
                         ][:6]
        cat_count_map = {r["doc_type_id"]: r["c"] for r in cat_counts_qs}

    spec_qs = qs
    if sel_categories:
        if has_category:
            spec_qs = spec_qs.filter(
                medical_event__category_id__in=[int(x) for x in sel_categories if str(x).isdigit()])
        else:
            spec_qs = spec_qs.filter(doc_type_id__in=[int(x) for x in sel_categories if str(x).isdigit()])

    spec_counts_qs = (
        spec_qs.exclude(medical_event__specialty__isnull=True)
        .values("medical_event__specialty_id", "medical_event__specialty__translations__name")
        .annotate(c=Count("id"))
        .order_by("-c")
    )
    hot_specialties = [
                          {"id": r["medical_event__specialty_id"],
                           "name": r["medical_event__specialty__translations__name"] or "", "count": r["c"]}
                          for r in spec_counts_qs if r["c"] > 0
                      ][:6]
    spec_count_map = {r["medical_event__specialty_id"]: r["c"] for r in spec_counts_qs}

    context = {
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
        "hot_categories": hot_categories,
        "hot_specialties": hot_specialties,
    }
    return render(request, "main/casefiles.html", context)
