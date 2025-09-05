from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.translation import gettext as _
from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class AccountForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["email", "username"]

class SettingsView(LoginRequiredMixin, View):
    template_name = "main/profile_settings.html"

    def get(self, request):
        ctx = {"account_form": AccountForm(instance=request.user)}
        return render(request, self.template_name, ctx)

    def post(self, request):
        form = AccountForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, _("Настройките са запазени."))
            return redirect("medj:profile")
        return render(request, self.template_name, {"account_form": form})
