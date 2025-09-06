from __future__ import annotations
import json, time
from io import BytesIO
from urllib.parse import urlencode

import qrcode
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, JsonResponse, HttpResponseBadRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.core import signing
from django.views.decorators.http import require_POST

_SIGNER_SALT = "medj.share"


def _make_token(payload: dict) -> str:
    s = signing.Signer(salt=_SIGNER_SALT)
    data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    return s.sign(data)


def share_document_page(request: HttpRequest) -> HttpResponse:
    return render(request, "main/share.html")


def share_view(request: HttpRequest, token: str) -> HttpResponse:
    return render(request, "subpages/share_view.html", {"token": token})


def share_revoke(request: HttpRequest, token: str) -> JsonResponse:
    return JsonResponse({"ok": True, "token": str(token)})


def healthcheck(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})


@login_required
@require_POST
def create_download_links(request: HttpRequest) -> JsonResponse:
    try:
        data = json.loads(request.body or "{}")
    except Exception:
        return HttpResponseBadRequest("bad json")

    start_date = (data.get("start_date") or "").strip()
    end_date = (data.get("end_date") or "").strip()
    filters = data.get("filters") or {}

    def norm_hours(x, default):
        try:
            v = int(x)
        except Exception:
            v = default
        if v < 1:
            v = 1
        if v > 8760:
            v = 8760
        return v

    hours_events = norm_hours(data.get("hours_events", 24), 24)
    hours_labs = norm_hours(data.get("hours_labs", 24), 24)
    hours_csv = norm_hours(data.get("hours_csv", 24), 24)

    base_params = {}
    if start_date:
        base_params["start_date"] = start_date
    if end_date:
        base_params["end_date"] = end_date
    for key in ("specialty", "category", "event", "indicator"):
        val = filters.get(key)
        if not val:
            continue
        base_params[key] = list(val) if isinstance(val, (list, tuple)) else [val]

    now = int(time.time())

    pdf_events_path = reverse("medj:print_pdf")
    pdf_labs_path = reverse("medj:print_pdf")
    csv_path = reverse("medj:print_csv")

    payload_events = {"k": "print_pdf", "exp": now + hours_events * 3600, "labs": 0}
    payload_labs = {"k": "print_pdf", "exp": now + hours_labs * 3600, "labs": 1}
    payload_csv = {"k": "print_csv", "exp": now + hours_csv * 3600}

    token_events = _make_token(payload_events)
    token_labs = _make_token(payload_labs)
    token_csv = _make_token(payload_csv)

    qs_events = dict(base_params)
    qs_events["t"] = token_events
    events_url = request.build_absolute_uri(pdf_events_path) + "?" + urlencode(qs_events, doseq=True)

    qs_labs = dict(base_params)
    qs_labs["labs"] = 1
    qs_labs["t"] = token_labs
    labs_url = request.build_absolute_uri(pdf_labs_path) + "?" + urlencode(qs_labs, doseq=True)

    qs_csv = dict(base_params)
    qs_csv["t"] = token_csv
    csv_url = request.build_absolute_uri(csv_path) + "?" + urlencode(qs_csv, doseq=True)

    return JsonResponse({"pdf_events_url": events_url, "pdf_labs_url": labs_url, "csv_url": csv_url})


@login_required
@require_POST
def create_share_token(request: HttpRequest) -> JsonResponse:
    return create_download_links(request)


def share_qr(request: HttpRequest, token=None) -> HttpResponse:
    url = request.GET.get("url")
    if not url:
        return HttpResponseBadRequest("missing url")
    img = qrcode.make(url)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return HttpResponse(buf.read(), content_type="image/png")


def qr_for_url(request: HttpRequest) -> HttpResponse:
    return share_qr(request)
