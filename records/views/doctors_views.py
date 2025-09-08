from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET
from django.db.models import Q, Case, When, IntegerField
from records.models import Practitioner

@login_required
def doctors_list(request):
    qs = (
        Practitioner.objects.filter(owner=request.user, is_active=True)
        .select_related("specialty")
        .order_by("full_name")
    )
    return render(request, "subpages/doctors.html", {"doctors": qs})

@login_required
@require_GET
def doctors_suggest(request):
    q = (request.GET.get("q") or "").strip()
    specialty_id = request.GET.get("specialty_id")
    qs = Practitioner.objects.filter(owner=request.user, is_active=True)
    if q:
        qs = qs.filter(full_name__icontains=q)
    if specialty_id:
        qs = qs.annotate(
            prio=Case(
                When(specialty_id=specialty_id, then=0),
                default=1,
                output_field=IntegerField(),
            )
        ).order_by("prio", "full_name")
    else:
        qs = qs.order_by("full_name")
    items = [
        {"id": p.id, "full_name": p.full_name, "specialty_id": p.specialty_id} for p in qs[:10]
    ]
    return JsonResponse({"results": items})
