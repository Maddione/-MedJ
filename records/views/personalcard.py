from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.translation import gettext as translate
from django.views import View
from django.urls import reverse
from django.http import HttpResponse, Http404
from io import BytesIO
import qrcode
from records.forms import PatientProfileForm
from records.models import PatientProfile
from django.contrib import messages as dj_messages


class PersonalCardView(LoginRequiredMixin, View):
    template_name = "main/personalcard.html"

    def get(self, request):
        profile, created = PatientProfile.objects.get_or_create(user=request.user)
        form = PatientProfileForm(instance=profile)
        share_url = (
            request.build_absolute_uri(
                reverse("medj:personalcard_public", args=[profile.share_token])
            )
            if profile.share_token
            else ""
        )
        return render(request, self.template_name, {
            "profile_form": form,
            "share_token": profile.share_token,
            "share_enabled": profile.share_enabled,
            "share_url": share_url,
        })

    def post(self, request):
        profile, created = PatientProfile.objects.get_or_create(user=request.user)
        form = PatientProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            dj_messages.success(request, translate("Личният картон е запазен."))
            return redirect("medj:personalcard")
        share_url = (
            request.build_absolute_uri(
                reverse("medj:personalcard_public", args=[profile.share_token])
            )
            if profile.share_token
            else ""
        )
        dj_messages.error(request, translate("Моля, поправете грешките по-долу."))
        return render(request, self.template_name, {
            "profile_form": form,
            "share_token": profile.share_token,
            "share_enabled": profile.share_enabled,
            "share_url": share_url,
        })


def enable_share(request):
    if not request.user.is_authenticated:
        raise Http404
    profile, created = PatientProfile.objects.get_or_create(user=request.user)
    profile.ensure_share_token()
    profile.share_enabled = True
    profile.save()
    dj_messages.success(request, translate("Споделянето е включено."))
    return redirect("medj:personalcard")


def personalcard_qr(request, token):
    try:
        PatientProfile.objects.get(share_token=token, share_enabled=True)
    except PatientProfile.DoesNotExist:
        raise Http404
    url = request.build_absolute_uri(reverse("medj:personalcard_public", args=[token]))
    img = qrcode.make(url)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return HttpResponse(buf.getvalue(), content_type="image/png")


def public_personalcard(request, token):
    profile = get_object_or_404(PatientProfile, share_token=token, share_enabled=True)
    return render(request, "public/personalcard_public.html", {"p": profile})
