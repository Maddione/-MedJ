from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.translation import gettext as _
from django import forms
from django.contrib.auth import get_user_model
from ..models import PatientProfile
from ..forms import PatientProfileForm

User = get_user_model()

class AccountForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["email", "username"]

class ProfileView(LoginRequiredMixin, View):
    template_name = "main/profile.html"

    def get(self, request):
        profile, _ = PatientProfile.objects.get_or_create(user=request.user)
        ctx = {
            "account_form": AccountForm(instance=request.user),
            "profile_form": PatientProfileForm(instance=profile),
        }
        return render(request, self.template_name, ctx)

    def post(self, request):
        profile, _ = PatientProfile.objects.get_or_create(user=request.user)
        aform = AccountForm(request.POST, instance=request.user)
        pform = PatientProfileForm(request.POST, instance=profile)
        if aform.is_valid() and pform.is_valid():
            aform.save()
            pform.save()
            messages.success(request, _("Профилът е обновен."))
            return redirect("medj:profile")
        return render(request, self.template_name, {"account_form": aform, "profile_form": pform})
