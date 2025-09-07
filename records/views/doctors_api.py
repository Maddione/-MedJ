from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.db.models import Case, When, Value, IntegerField
from ..models import Practitioner


@require_GET
@login_required
def doctors_suggest(request):
    query = (request.GET.get("q") or "").strip()
    specialty_id = request.GET.get("specialty_id")

    qs = Practitioner.objects.filter(
        owner=request.user,
        is_active=True
    )

    if query:
        qs = qs.filter(full_name__icontains=query)

    if specialty_id and specialty_id.isdigit():
        specialty_id_int = int(specialty_id)
        qs = qs.annotate(
            is_match=Case(
                When(specialty_id=specialty_id_int, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        ).order_by("-is_match", "full_name")
    else:
        qs = qs.order_by("full_name")

    results = qs[:20]

    data = []
    for p in results:
        name = p.full_name
        if p.specialty:

            specialty_name = getattr(p.specialty, "name", "")
            name = f"{p.full_name} ({specialty_name})"

        data.append({
            "id": p.id,
            "full_name": p.full_name,
            "display_name": name,
        })

    return JsonResponse({"results": data})