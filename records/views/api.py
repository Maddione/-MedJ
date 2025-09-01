from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest

from records.models import MedicalEvent
from .helpers import get_patient


@login_required
def events_by_specialty(request):
    if request.headers.get("x-requested-with") != "XMLHttpRequest":
        return HttpResponseBadRequest("Expected AJAX")
    patient = get_patient(request.user)
    if not patient:
        return JsonResponse({"results": []})
    spec_id = request.GET.get("specialty")
    cat_id  = request.GET.get("category")
    qs = MedicalEvent.objects.filter(patient=patient).order_by("-event_date", "-id")
    if spec_id and spec_id.isdigit(): qs = qs.filter(specialty_id=int(spec_id))
    if cat_id  and cat_id.isdigit():  qs = qs.filter(category_id=int(cat_id))
    data = [{"id": ev.id, "date": ev.event_date.isoformat() if ev.event_date else "",
             "summary": (ev.summary or "")[:120]} for ev in qs[:100]]
    return JsonResponse({"results": data})
