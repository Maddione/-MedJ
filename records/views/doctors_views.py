from django.db import models
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from records.models import Practitioner

@login_required
@require_GET
def doctors_suggest(request):
    q = (request.GET.get("q") or "").strip()
    spec_id = request.GET.get("specialty_id") or ""
    qs = Practitioner.objects.filter(owner=request.user, is_active=True)
    if q:
        qs = qs.filter(full_name__icontains=q)
    if spec_id:
        try:
            sid = int(spec_id)
            qs = qs.order_by(
                models.Case(
                    models.When(specialty_id=sid, then=models.Value(0)),
                    default=models.Value(1),
                    output_field=models.IntegerField(),
                ),
                "full_name",
            )
        except Exception:
            qs = qs.order_by("full_name")
    else:
        qs = qs.order_by("full_name")
    qs = qs.select_related("specialty")[:10]
    results = [{"id": p.id, "full_name": p.full_name, "specialty_id": p.specialty_id or None} for p in qs]
    return JsonResponse({"results": results})
