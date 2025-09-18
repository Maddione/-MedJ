from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from ..models import Document


def _user_documents(user):
    return (
        Document.objects.filter(owner=user)
        .select_related("medical_event", "doc_type")
        .order_by("-uploaded_at")
    )


@login_required
def documents_view(request):
    documents = _user_documents(request.user)
    return render(request, "main/documents.html", {"documents": documents})
