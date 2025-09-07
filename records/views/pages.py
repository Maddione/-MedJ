from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def upload_page(request):
    return render(request, "main/upload.html")

@login_required
def upload_history(request):
    return render(request, "main/upload_history.html")

@login_required
def casefiles_page(request):
    return render(request, "main/casefiles.html")
