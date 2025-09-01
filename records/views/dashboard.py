from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def dashboard(request):
    patient = _require_patient_profile(request.user)
    today = now().date()

    top_indicators = list(
        LabTestMeasurement.objects
        .filter(medical_event__patient=patient)
        .values('indicator__name', 'indicator__unit')
        .annotate(c=Count('id'))
        .order_by('-c')[:4]
    )

    charts_data = []
    for item in top_indicators:
        name = item['indicator__name']
        unit = item.get('indicator__unit') or ''
        qs = (
            LabTestMeasurement.objects
            .filter(medical_event__patient=patient, indicator__name=name)
            .order_by('measured_at', 'id')
            .values('measured_at', 'value')
        )
        series = []
        for r in qs:
            d = r['measured_at']
            v = r['value']
            if d is None or v is None:
                continue
            try:
                fv = float(v)
            except Exception:
                continue
            series.append({'x': d.isoformat(), 'y': fv})
        if series:
            charts_data.append({'name': name, 'unit': unit, 'series': series})

    upcoming_events_qs = (
        MedicalEvent.objects
        .filter(patient=patient, event_date__gte=today)
        .select_related('specialty')
        .order_by('event_date')[:10]
    )
    upcoming_events = []
    for ev in upcoming_events_qs:
        spec = ev.specialty.safe_translation_getter("name", any_language=True) if ev.specialty else ""
        title = spec or (ev.summary[:60] + "…") if ev.summary else "Преглед"
        upcoming_events.append({"event_date": ev.event_date, "title": title})

    pres_qs = Document.objects.filter(medical_event__patient=patient)
    try:
        pres_qs = pres_qs.filter(doc_type__translations__name='Рецепта')
    except Exception:
        try:
            pres_qs = pres_qs.filter(doc_type__slug='recepta')
        except Exception:
            pass
    pres_qs = pres_qs.select_related('doc_type').order_by('-uploaded_at')[:10]
    prescriptions = [{
        "id": d.id,
        "created_at": d.uploaded_at,
        "title": d.doc_type.safe_translation_getter("name", any_language=True) or "Рецепта",
    } for d in pres_qs]

    return render(
        request,
        'main/dashboard.html',
        {
            'charts_data': charts_data,
            'upcoming_events': upcoming_events,
            'prescriptions': prescriptions,
        },
    )