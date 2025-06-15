# MedJ/views.py
import os
import json
import hashlib
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.files.storage import default_storage
from django.utils.translation import gettext
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db import transaction
from django.core.files.base import ContentFile
# import fitz # Размаркирай, ако използваш PyMuPDF

from .forms import CustomUserCreationForm
from .models import (
    PatientProfile, Document, MedicalCategory, MedicalSpecialty,
    MedicalEvent, DocumentTag, BloodTestResult, Practitioner, NarrativeSectionResult
)

# --- Симулация на AI Анализатор (без промяна) ---
def call_gpt_for_document(file_content, user_context):
    # ... (кодът на симулацията остава същият) ...
    return {
        "summary": "Пациентът е лекуван за пневмония от д-р Стефанова...",
        "event_date": "2025-06-10",
        "suggested_tags": ["Пневмония", "Болнично лечение", "Антибиотик", "Левкоцити"],
        "structured_data": [
            {"type": "narrative_section", "title": "Заключение и препоръки", "content": "Пациентът се изписва..."},
            {"type": "detected_practitioner", "name": "Мария Стефанова", "title": "Д-р", "inferred_specialty": "Пулмология"},
            {"type": "blood_test_panel", "panel_name": "ПКК", "results": [{"indicator_name": "Левкоцити (WBC)", "value": "12.5", "unit": "x10^9/L", "reference_range": "4.0 - 10.0"}]}
        ]
    }

# --- ОСНОВНИ ИЗГЛЕДИ ---
# КОРИГИРАНИ ПЪТИЩА СПОРЕД СТРУКТУРАТА ТИ
def landing_page(request): return render(request, 'basetemplates/landingpage.html')
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid(): login(request, form.get_user()); return redirect('medj:dashboard')
    else: form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST);
        if form.is_valid(): form.save(); return redirect('medj:login')
    else: form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})
def logout_view(request): logout(request); return redirect('medj:landingpage')


# --- ИЗГЛЕДИ ЗА ЛОГНАТИ ПОТРЕБИТЕЛИ ---
# КОРИГИРАНИ ПЪТИЩА И ЛОГИКА
@login_required
def dashboard(request): return render(request, 'main/dashboard.html')

@login_required
def upload_page(request):
    context = {
        'categories': MedicalCategory.objects.all(),
        # Вече не е нужно да подаваме ВСИЧКИ специалности, но не пречи
        'specialties': MedicalSpecialty.objects.all(),
        'event_types': MedicalEvent.EventType.choices
    }
    return render(request, 'main/upload.html', context)

@login_required
@require_POST
def perform_ocr(request):
    # ... (логиката остава същата) ...
    full_ocr_text = "Симулиран анонимизиран текст от документа."
    file_hash = hashlib.sha256(request.FILES.get('document').read()).hexdigest()
    request.session['ocr_text'] = full_ocr_text
    request.session['file_hash'] = file_hash
    return JsonResponse({'status': 'success', 'ocr_text_for_display': full_ocr_text})

@login_required
@require_POST
def analyze_document(request):
    # ... (логиката остава същата) ...
    data = json.loads(request.body)
    user_context = {'category_id': data.get('category_id'),'event_type': data.get('event_type_title'),}
    edited_text = data.get('edited_text')
    gpt_result = call_gpt_for_document(edited_text, user_context)
    with transaction.atomic():
        patient_profile = PatientProfile.objects.get(user=request.user)
        source_document = Document.objects.create(patient=patient_profile)
        category = MedicalCategory.objects.get(pk=user_context['category_id'])
        event_date_str = gpt_result.get("event_date")
        event_date = timezone.datetime.strptime(event_date_str, "%Y-%m-%d").date() if event_date_str else timezone.now().date()
        medical_event = MedicalEvent.objects.create(patient=patient_profile,source_document=source_document,event_type_title=user_context['event_type'],category=category,event_date=event_date,summary=gpt_result.get("summary", ""))
        if 'structured_data' in gpt_result:
            for item in gpt_result['structured_data']:
                item_type = item.get('type')
                if item_type == 'blood_test_panel':
                    for result_data in item.get('results', []): BloodTestResult.objects.create(medical_event=medical_event, indicator_name=result_data.get("indicator_name"), value=result_data.get("value"), unit=result_data.get("unit", ""), reference_range=result_data.get("reference_range", ""))
                elif item_type == 'narrative_section': NarrativeSectionResult.objects.create(medical_event=medical_event, title=item.get('title', 'N/A'), content=item.get('content', ''))
                elif item_type == 'detected_practitioner':
                    practitioner_name = item.get('name')
                    if practitioner_name:
                        practitioner, _ = Practitioner.objects.get_or_create(name=practitioner_name, defaults={'title': item.get('title', 'Д-р')})
                        medical_event.practitioners.add(practitioner)
        if gpt_result.get("suggested_tags"):
            for tag_name in gpt_result["suggested_tags"]:
                tag, _ = DocumentTag.objects.get_or_create(name=tag_name.strip())
                medical_event.tags.add(tag)
    return JsonResponse({'status': 'success', 'message': 'Документът е успешно анализиран и записан!', 'event_id': medical_event.id})

# --- ПРАЗНИ ИЗГЛЕДИ С КОРЕКТНИ ПЪТИЩА ---
@login_required
def upload_history(request): return render(request, 'main/history.html')

@login_required
def document_detail_view(request, event_id): return render(request, 'subpages/document_detail.html', {'event_id': event_id})

@login_required
def casefiles(request): return render(request, 'main/casefiles.html')

@login_required
def personalcard(request): return render(request, 'main/personalcard.html')

@login_required
def profile(request): return render(request, 'subpages/profile.html')

@login_required
def doctors(request): return render(request, 'subpages/doctors.html')

# --- НОВ ИЗГЛЕД ЗА AJAX ---
@login_required
def get_specialties_for_category(request):
    """
    Връща списък със специалности (в JSON формат)
    въз основа на ID на избрана категория.
    Използва се от AJAX заявка в upload.html.
    """
    category_id = request.GET.get('category_id')
    specialties = MedicalSpecialty.objects.filter(category_id=category_id).order_by('name')
    # Преобразуваме данните в списък от речници, които JavaScript разбира
    specialties_list = list(specialties.values('id', 'name'))
    return JsonResponse({'specialties': specialties_list})