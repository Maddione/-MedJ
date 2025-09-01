from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse

@login_required
def personal_card(request: HttpRequest) -> HttpResponse:
    return render(request, "main/personalcard.html")

@login_required
def profile(request: HttpRequest) -> HttpResponse:
    return render(request, "subpages/profile.html")

@login_required
def doctors(request: HttpRequest) -> HttpResponse:
    return render(request, "subpages/doctors.html")
