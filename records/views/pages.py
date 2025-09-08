from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from ..models import Document

@login_required
def history_view(request):
    documents = (
        Document.objects.filter(owner=request.user)
        .select_related("medical_event")
        .order_by("-uploaded_at")
    )
    return render(request, "main/history.html", {"documents": documents})
