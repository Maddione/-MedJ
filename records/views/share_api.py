import io
import json
import secrets
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password, check_password
from django.core.cache import cache
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest, Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.conf import settings
from django.urls import reverse
import logging
from records.models import Document, MedicalEvent, ShareLink

try:
    import qrcode
except Exception:
    qrcode = None

log = logging.getLogger("records.share")


def _abs_url(request, path):
    base = request.build_absolute_uri("/")
    if not base.endswith("/"):
        base += "/"
    return base + path.lstrip("/")


def _rate_limit_key(user_id):
    return f"share_create_rl_{user_id}"


def _rate_limited(user_id, max_per_window=10, window_seconds=300):
    k = _rate_limit_key(user_id)
    v = cache.get(k)
    if not v:
        cache.set(k, 1, timeout=window_seconds)
        return False
    if v >= max_per_window:
        return True
    cache.incr(k, 1)
    return False


@login_required
@csrf_exempt
@require_POST
def share_create(request):
    if _rate_limited(request.user.id):
        return HttpResponseBadRequest("rate_limited")
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("invalid_json")
    object_type = (data.get("object_type") or "").strip()
    object_id = data.get("object_id")
    scope = (data.get("scope") or "full").strip().lower()
    fmt = (data.get("format") or "html").strip().lower()
    expire_days = int(data.get("expire_days") or 30)
    if expire_days < 1:
        expire_days = 1
    if expire_days > 365:
        expire_days = 365
    password = data.get("password") or ""
    if object_type not in ("event", "document"):
        return HttpResponseBadRequest("bad_object_type")
    if not object_id:
        return HttpResponseBadRequest("missing_object_id")
    if scope not in ("full", "summary", "labs"):
        scope = "full"
    if object_type == "event":
        obj = get_object_or_404(MedicalEvent, id=object_id, owner=request.user)
    else:
        obj = get_object_or_404(Document, id=object_id, owner=request.user)
    token = secrets.token_urlsafe(16)
    expires_at = now() + timedelta(days=expire_days)
    pwd_hash = make_password(password) if password else ""
    sl = ShareLink.objects.create(
        token=token,
        owner=request.user,
        object_type=object_type,
        object_id=obj.id,
        scope=scope,
        format=fmt,
        expires_at=expires_at,
        password_hash=pwd_hash,
        status="active",
    )
    url_path = f"s/{token}/"
    qr_path = f"api/share/qr/{token}.png"
    log.info("share_create user=%s type=%s id=%s token=%s", request.user.id, object_type, object_id, token)
    return JsonResponse({
        "ok": True,
        "token": token,
        "url": _abs_url(request, url_path),
        "qr": _abs_url(request, qr_path),
        "expires_at": expires_at.strftime("%d-%m-%Y"),
        "status": sl.status,
        "scope": sl.scope,
        "format": sl.format,
    })


def _session_pw_flag(token):
    return f"share_pw_ok_{token}"


def _check_expired(sl):
    return bool(sl.expires_at and sl.expires_at < now())


def _get_scope(sl):
    v = (sl.scope or "full").lower()
    return v if v in ("full", "summary", "labs") else "full"


def _get_objects(sl):
    if sl.object_type == "event":
        event = get_object_or_404(MedicalEvent, id=sl.object_id)
        document = None
    else:
        document = get_object_or_404(Document, id=sl.object_id)
        event = getattr(document, "medical_event", None)
    return event, document


def _need_password(sl, request):
    if not sl.password_hash:
        return False
    flag = request.session.get(_session_pw_flag(sl.token), False)
    return not bool(flag)


def _set_password_ok(sl, request):
    request.session[_session_pw_flag(sl.token)] = True
    request.session.modified = True


def _labs_for_event(ev):
    try:
        qs = getattr(ev, "lab_measurements", None)
        if qs is None:
            qs = getattr(ev, "labtests", None)
        if qs is None:
            return []
        return list(qs.select_related("indicator").order_by("measured_at", "id"))
    except Exception:
        return []


def _render_public(request, sl, need_password=False, wrong_password=False):
    scope = _get_scope(sl)
    event, document = _get_objects(sl)
    ctx = {"share": sl, "event": event, "document": document, "need_password": need_password, "wrong_password": wrong_password, "scope": scope, "labs": _labs_for_event(event) if event else []}
    return render(request, "subpages/share_public.html", ctx)


def share_public(request, token):
    sl = get_object_or_404(ShareLink, token=token, status="active")
    if _check_expired(sl):
        raise Http404()
    if request.method == "POST":
        pw = request.POST.get("password") or ""
        if not sl.password_hash:
            return redirect(reverse("medj:share_public", kwargs={"token": token}))
        if check_password(pw, sl.password_hash):
            _set_password_ok(sl, request)
            log.info("share_access user=anon token=%s ok=1", token)
            return redirect(reverse("medj:share_public", kwargs={"token": token}))
        else:
            log.info("share_access user=anon token=%s ok=0", token)
            return _render_public(request, sl, need_password=True, wrong_password=True)
    if _need_password(sl, request):
        return _render_public(request, sl, need_password=True, wrong_password=False)
    log.info("share_access user=anon token=%s ok=1", token)
    return _render_public(request, sl, need_password=False, wrong_password=False)


@login_required
@require_GET
def share_history(request):
    qs = ShareLink.objects.filter(owner=request.user).order_by("-created_at")
    items = []
    for s in qs:
        items.append({
            "token": s.token,
            "object_type": s.object_type,
            "object_id": s.object_id,
            "scope": _get_scope(s),
            "format": s.format,
            "status": s.status,
            "expires_at": s.expires_at.strftime("%d-%m-%Y") if s.expires_at else "",
            "url": _abs_url(request, f"s/{s.token}/"),
        })
    return JsonResponse({"results": items})


@login_required
@csrf_exempt
@require_POST
def share_revoke(request, token):
    sl = get_object_or_404(ShareLink, token=token, owner=request.user)
    sl.status = "revoked"
    sl.save(update_fields=["status"])
    log.info("share_revoke user=%s token=%s", request.user.id, token)
    return JsonResponse({"ok": True})


@require_GET
def share_qr_png(request, token):
    if qrcode is None:
        raise Http404()
    get_object_or_404(ShareLink, token=token)
    url = _abs_url(request, f"s/{token}/")
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return HttpResponse(buf.getvalue(), content_type="image/png")


@login_required
def share_history_page(request):
    return render(request, "subpages/share_history.html", {})
