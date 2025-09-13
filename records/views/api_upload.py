from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse

from records.models import MedicalEvent

from .upload import upload_ocr, upload_analyze, upload_confirm


@login_required
@require_http_methods(["GET"])
def events_suggest(request):

    qs = MedicalEvent.objects.filter(owner=request.user)
    cat_id = request.GET.get("category_id")
    spec_id = request.GET.get("specialty_id")
    doc_type_id = request.GET.get("doc_type_id")
    if cat_id:
        qs = qs.filter(category_id=cat_id)
    if spec_id:
        qs = qs.filter(specialty_id=spec_id)
    if doc_type_id:
        qs = qs.filter(doc_type_id=doc_type_id)
    events = [{"id": ev.id} for ev in qs.order_by("-event_date")[:20]]
    return JsonResponse({"events": events})