from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from records.models import DocumentType, MedicalSpecialty, MedicalCategory

def _opt(obj):
    return {"id": obj.id, "name": getattr(obj, "name", getattr(obj, "title", str(obj)))}

@login_required
def document_types(request):
    data = [_opt(dt) for dt in DocumentType.objects.order_by("id")]
    return JsonResponse({"results": data})

@login_required
def specialties(request):
    data = [_opt(s) for s in MedicalSpecialty.objects.order_by("id")]
    return JsonResponse({"results": data})

@login_required
def categories(request):
    data = [_opt(c) for c in MedicalCategory.objects.order_by("id")]
    return JsonResponse({"results": data})
