from __future__ import annotations

import io
import json
import uuid
from datetime import timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, Http404, HttpResponseBadRequest
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST

from ..forms import ShareCreateForm
from ..models import Document, DocumentShare

@login_required
@require_POST
def create_download_links(request):
    try:
        data = json.loads(request.body or "{}")
    except Exception:
        data = {}
    start_date = data.get("start_date") or ""
    end_date = data.get("end_date") or ""
    filters = data.get("filters") or {}
    qs = {}
    if start_date:
        qs["start_date"] = start_date
    if end_date:
        qs["end_date"] = end_date
    for key in ("specialty", "category", "event", "indicator"):
        val = filters.get(key)
        if not val:
            continue
        if isinstance(val, (list, tuple)):
            qs[key] = list(val)
        else:
            qs[key] = [val]
    query = urlencode(qs, doseq=True)
    pdf_events_url = reverse("medj:print_pdf") + (f"?{query}" if query else "")
    pdf_labs_url = reverse("medj:print_pdf") + (f"?labs=1&{query}" if query else "?labs=1")
    csv_url = reverse("medj:print_csv") + (f"?{query}" if query else "")
    return JsonResponse({
        "pdf_events_url": pdf_events_url,
        "pdf_labs_url": pdf_labs_url,
        "csv_url": csv_url,
        "pdf_url": pdf_events_url
    })

@login_required
def share_document_page(request: HttpRequest, medical_event_id: int | str | None = None) -> HttpResponse:
    form = ShareCreateForm(initial={"duration_hours": 24})
    return render(request, "main/share.html", {"medical_event_id": medical_event_id, "form": form})

@login_required
@require_POST
def create_share_token(request: HttpRequest) -> JsonResponse:
    try:
        data = request.POST or json.loads(request.body.decode("utf-8"))
    except Exception:
        data = request.POST
    document_id = data.get("document_id")
    duration_hours = int(data.get("duration_hours", 24))
    if not document_id:
        return JsonResponse({"ok": False, "error": "document_id required"}, status=400)
    doc = get_object_or_404(Document, pk=document_id, owner=request.user)
    expires_at = timezone.now() + timedelta(hours=duration_hours)
    share = DocumentShare.objects.create(document=doc, expires_at=expires_at, is_active=True)
    return JsonResponse({"ok": True, "token": str(share.token), "expires_at": expires_at.isoformat()})

@require_GET
def share_view(request: HttpRequest, token: uuid.UUID) -> HttpResponse:
    st = get_object_or_404(DocumentShare, token=token)
    if not st.is_active or st.is_expired():
        raise Http404()
    doc = st.document
    return render(request, "subpages/share_view.html", {"mode": "document", "token": str(token), "documents": [doc], "expires_at": st.expires_at, "owner_patient_id": getattr(doc.owner, "patient_profile_id", None), "allow_download": True, "file_url": getattr(doc.file, "url", ""), "file_name": getattr(doc.file, "name", "")})

def share_qr(request: HttpRequest, token: uuid.UUID) -> HttpResponse:
    try:
        import qrcode
    except Exception:
        raise Http404("qrcode library not installed")
    url = request.build_absolute_uri(reverse("medj:share_view", args=[str(token)]))
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return HttpResponse(buf.getvalue(), content_type="image/png")

@login_required
@require_POST
def share_revoke(request: HttpRequest, token: uuid.UUID) -> HttpResponse:
    st = get_object_or_404(DocumentShare, token=token, document__owner=request.user)
    st.is_active = False
    st.save(update_fields=["is_active"])
    messages.success(request, "Линкът за споделяне е деактивиран.")
    return redirect("medj:dashboard")

@require_GET
def qr_for_url(request: HttpRequest) -> HttpResponse:
    url = (request.GET.get("url") or "").strip()
    if not url:
        return HttpResponseBadRequest("url required")
    try:
        import qrcode
    except Exception:
        raise Http404("qrcode library not installed")
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return HttpResponse(buf.getvalue(), content_type="image/png")

@require_GET
def healthcheck(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})
