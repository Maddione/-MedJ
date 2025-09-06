from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.translation import gettext as translate
from django.views import View
from django.urls import reverse
from django.http import HttpResponse, Http404, JsonResponse
from django.views.decorators.http import require_POST
from io import BytesIO
import qrcode
from records.forms import PatientProfileForm
from records.models import PatientProfile
from django.contrib import messages as dj_messages


class PersonalCardView(LoginRequiredMixin, View):
    template_name = "main/personalcard.html"

    def get(self, request):
        profile, _ = PatientProfile.objects.get_or_create(user=request.user)
        form = PatientProfileForm(instance=profile)
        share_url = (
            request.build_absolute_uri(
                reverse("medj:personalcard_public", args=[profile.share_token])
            )
            if profile.share_token
            else ""
        )
        return render(
            request,
            self.template_name,
            {
                "profile_form": form,
                "share_token": profile.share_token,
                "share_enabled": profile.share_enabled,
                "share_url": share_url,
            },
        )

    def post(self, request):
        profile, _ = PatientProfile.objects.get_or_create(user=request.user)
        form = PatientProfileForm(request.POST, request.FILES, instance=profile)
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
        if form.is_valid():
            form.save()
            if is_ajax:
                return JsonResponse({"ok": True})
            dj_messages.success(request, translate("Личният картон е запазен."))
            return redirect("medj:personalcard")
        if is_ajax:
            return JsonResponse({"ok": False, "errors": form.errors}, status=400)
        share_url = (
            request.build_absolute_uri(
                reverse("medj:personalcard_public", args=[profile.share_token])
            )
            if profile.share_token
            else ""
        )
        dj_messages.error(request, translate("Моля, поправете грешките по-долу."))
        return render(
            request,
            self.template_name,
            {
                "profile_form": form,
                "share_token": profile.share_token,
                "share_enabled": profile.share_enabled,
                "share_url": share_url,
            },
        )


@login_required
def enable_share(request):
    if not request.user.is_authenticated:
        raise Http404
    profile, _ = PatientProfile.objects.get_or_create(user=request.user)
    profile.ensure_share_token()
    profile.share_enabled = True
    profile.save()
    dj_messages.success(request, translate("Споделянето е включено."))
    return redirect("medj:personalcard")


@login_required
@require_POST
def personalcard_share_enable_api(request):
    profile, _ = PatientProfile.objects.get_or_create(user=request.user)
    if not profile.share_token:
        profile.ensure_share_token()
    profile.share_enabled = True
    profile.save()
    qr_path = reverse("medj:personalcard_qr", kwargs={"token": profile.share_token})
    qr_url = request.build_absolute_uri(qr_path)
    return JsonResponse({"ok": True, "token": profile.share_token, "qr_url": qr_url})


def personalcard_qr(request, token):
    try:
        PatientProfile.objects.get(share_token=token, share_enabled=True)
    except PatientProfile.DoesNotExist:
        raise Http404
    url = request.build_absolute_uri(reverse("medj:personalcard_public", args=[token]))
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return HttpResponse(buf.getvalue(), content_type="image/png")


def public_personalcard(request, token):
    profile = get_object_or_404(PatientProfile, share_token=token, share_enabled=True)
    return render(request, "public/personalcard_public.html", {"p": profile})
