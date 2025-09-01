from django.shortcuts import render
from django.views.decorators.http import require_GET
from django.http import HttpRequest, HttpResponse

@require_GET
def landing_page(request: HttpRequest) -> HttpResponse:
    return render(request, "basetemplates/landingpage.html")
