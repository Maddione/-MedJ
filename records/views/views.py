from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from django.contrib.auth import get_user_model
from records.forms import AccountForm, PatientProfileForm
from records.models import PatientProfile

User = get_user_model()

@login_required
@transaction.atomic
def profile_view(request):
    profile, _ = PatientProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        account_form = AccountForm(request.POST, instance=request.user)
        profile_form = PatientProfileForm(request.POST, instance=profile)
        if account_form.is_valid() and profile_form.is_valid():
            account_form.save()
            profile_form.save()
            messages.success(request, "Профилът е обновен.")
            return redirect("medj:profile")
        else:
            return render(request, "main/profile.html", {"account_form": account_form, "profile_form": profile_form})
    account_form = AccountForm(instance=request.user)
    profile_form = PatientProfileForm(instance=profile)
    return render(request, "main/profile.html", {"account_form": account_form, "profile_form": profile_form})
