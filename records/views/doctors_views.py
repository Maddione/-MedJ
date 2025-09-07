from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from records.models import Document, DocumentTag, Tag, MedicalSpecialty

@login_required
@require_GET
def doctors_suggest(request):
    q = (request.GET.get("q") or "").strip().lower()
    spec_id = request.GET.get("specialty_id")
    rels = DocumentTag.objects.select_related("tag", "document__specialty").filter(
        document__owner=request.user,
        tag__slug__startswith="doctor:"
    ).order_by("-id")[:500]
    acc = {}
    for r in rels:
        tag = r.tag
        name = getattr(tag, "safe_translation_getter", lambda *a, **k: None)("name", any_language=True) or getattr(tag, "name", "") or ""
        if not name:
            continue
        if q and q not in name.lower():
            continue
        sp = getattr(r.document, "specialty", None)
        sp_id = getattr(sp, "id", None)
        sp_name = ""
        if sp:
            sp_name = getattr(sp, "safe_translation_getter", lambda *a, **k: None)("name", any_language=True) or getattr(sp, "name", "") or ""
        bucket = acc.get(name)
        if not bucket:
            acc[name] = {"name": name, "specialty_id": sp_id, "specialty_name": sp_name, "count": 1}
        else:
            bucket["count"] += 1
            if spec_id and sp_id and str(sp_id) == str(spec_id):
                bucket["specialty_id"] = sp_id
                bucket["specialty_name"] = sp_name
    items = list(acc.values())
    items.sort(key=lambda x: (-x["count"], x["name"].lower()))
    if spec_id:
        items.sort(key=lambda x: (0 if str(x.get("specialty_id") or "") == str(spec_id) else 1, -x["count"], x["name"].lower()))
    return JsonResponse({"results": items[:10]})
