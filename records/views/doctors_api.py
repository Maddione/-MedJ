from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from ..models import Tag, DocumentTag, Document

@require_GET
@login_required
def doctors_suggest(request):
    q = (request.GET.get("q") or "").strip().lower()
    specialty_id = request.GET.get("specialty_id")
    qs = Tag.objects.filter(
        documenttag__document__owner=request.user,
        slug__startswith="doctor:"
    ).distinct()
    if q:
        qs = qs.filter(
            Q(translations__name__icontains=q) | Q(slug__icontains=q)
        )
    qs = qs.annotate(usage_count=Count("documenttag__id")).order_by("-usage_count", "translations__name")[:20]
    data = []
    for t in qs:
        name = getattr(t, "safe_translation_getter", lambda *a, **k: None)("name", any_language=True) or t.slug.replace("doctor:", "").replace("-", " ").title()
        data.append({"id": t.id, "full_name": name})
    return JsonResponse({"results": data})
