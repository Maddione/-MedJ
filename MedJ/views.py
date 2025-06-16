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
import fitz
from ocrapi.anonymizer import anonymize_text
from ocrapi.gpt_client import call_gpt_for_document
from ocrapi.vision_handler import extract_text_from_image

from .forms import CustomUserCreationForm
from .models import (
    PatientProfile, Document, MedicalCategory, MedicalSpecialty,
    MedicalEvent, DocumentTag, BloodTestResult, Practitioner, NarrativeSectionResult
)

# --- ОСНОВНИ ИЗГЛЕДИ ---
def landing_page(request): return render(request, 'basetemplates/landingpage.html')

def login_view(request):
    _ = gettext
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('medj:dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})

def register(request):
    _ = gettext
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('medj:login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

def logout_view(request): logout(request); return redirect('medj:landingpage')


# --- ИЗГЛЕДИ ЗА ЛОГНАТИ ПОТРЕБИТЕЛИ ---
@login_required
def dashboard(request): return render(request, 'main/dashboard.html')

@login_required
def upload_page(request):
    _ = gettext
    if request.method == 'POST':
        uploaded_file = request.FILES.get('document')
        event_type_title = request.POST.get('event_type')
        category_id = request.POST.get('category_id')
        specialty_id = request.POST.get('specialty_id')
        file_type = request.POST.get('file_type')

        # Валидация на входните данни
        if not all([uploaded_file, event_type_title, category_id, specialty_id, file_type]):
            context = {
                'categories': MedicalCategory.objects.all().order_by('name'),
                'specialties': MedicalSpecialty.objects.all().order_by('name'),
                'event_types': MedicalEvent.EventType.choices,
                'error_message': _('Моля, попълнете всички задължителни полета и изберете файл.')
            }
            return render(request, 'main/upload.html', context)

        full_ocr_text = ""
        file_hash = None
        processed_files_for_cleanup = []
        temp_file_path = None
        temp_file_url = None

        try:
            # 1. Запазване на файла и генериране на хеш
            temp_dir = os.path.join(default_storage.location, 'temp_processing')
            os.makedirs(temp_dir, exist_ok=True)

            temp_filename = default_storage.save(f"temp_processing/{uploaded_file.name}", uploaded_file)
            temp_file_path = default_storage.path(temp_filename)
            temp_file_url = default_storage.url(temp_filename)
            processed_files_for_cleanup.append(temp_file_path)

            uploaded_file.seek(0)
            file_content_bytes = uploaded_file.read()
            file_hash = hashlib.sha256(file_content_bytes).hexdigest()

            # Проверка за дубликат
            patient_profile, _ = PatientProfile.objects.get_or_create(user=request.user)
            if Document.objects.filter(file_hash=file_hash, patient=patient_profile).exists():
                context = {
                    'categories': MedicalCategory.objects.all().order_by('name'),
                    'specialties': MedicalSpecialty.objects.all().order_by('name'),
                    'event_types': MedicalEvent.EventType.choices,
                    'error_message': _('Този документ вече е качен от Вас.')
                }
                return render(request, 'main/upload.html', context)

            # 2. OCR обработка
            if file_type == 'pdf':
                pdf_document = fitz.open(temp_file_path)
                for page_num in range(len(pdf_document)):
                    page = pdf_document.load_page(page_num)
                    pix = page.get_pixmap(matrix=fitz.Matrix(300 / 72, 300 / 72))
                    image_filename = f"temp_processing/{os.path.splitext(uploaded_file.name)[0]}_page_{page_num}.png"
                    page_image_path = default_storage.path(image_filename)
                    pix.save(page_image_path)
                    processed_files_for_cleanup.append(page_image_path)
                    full_ocr_text += extract_text_from_image(page_image_path) + "\n\n"
                pdf_document.close()
            elif file_type == 'image':
                full_ocr_text = extract_text_from_image(temp_file_path)
            else:
                context = {
                    'categories': MedicalCategory.objects.all().order_by('name'),
                    'specialties': MedicalSpecialty.objects.all().order_by('name'),
                    'event_types': MedicalEvent.EventType.choices,
                    'error_message': _('Неподдържан файлов формат.')
                }
                return render(request, 'main/upload.html', context)

            if not full_ocr_text.strip():
                context = {
                    'categories': MedicalCategory.objects.all().order_by('name'),
                    'specialties': MedicalSpecialty.objects.all().order_by('name'),
                    'event_types': MedicalEvent.EventType.choices,
                    'error_message': _('Не беше разчетен текст от документа.')
                }
                return render(request, 'main/upload.html', context)

            # 3. Съхраняване на данни в сесията за следващата стъпка
            request.session['temp_ocr_text'] = full_ocr_text
            request.session['temp_file_hash'] = file_hash
            request.session['temp_file_path'] = temp_file_path
            request.session['temp_file_url'] = temp_file_url
            request.session['selected_event_type'] = event_type_title
            request.session['selected_category_id'] = category_id
            request.session['selected_specialty_id'] = specialty_id

            # Пренасочване към страницата за преглед и одобрение
            return redirect('medj:upload_review_page')

        except Exception as e:
            print(f"Error during upload_page POST: {e}")
            context = {
                'categories': MedicalCategory.objects.all().order_by('name'),
                'specialties': MedicalSpecialty.objects.all().order_by('name'),
                'event_types': MedicalEvent.EventType.choices,
                'error_message': _(f'Възникна грешка при обработката на документа: {e}')
            }
            return render(request, 'main/upload.html', context)
        finally:
            for path_to_clean in processed_files_for_cleanup:
                if path_to_clean != temp_file_path:
                    if default_storage.exists(path_to_clean):
                        default_storage.delete(path_to_clean)


    # --- ЛОГИКА ЗА GET ЗАЯВКА (Първоначално зареждане на страницата) ---
    context = {
        'categories': MedicalCategory.objects.all().order_by('name'),
        'specialties': MedicalSpecialty.objects.all().order_by('name'),
        'event_types': MedicalEvent.EventType.choices
    }
    return render(request, 'main/upload.html', context)


@login_required
def upload_review_page(request):
    _ = gettext
    temp_ocr_text = request.session.get('temp_ocr_text')
    temp_file_hash = request.session.get('temp_file_hash')
    temp_file_path = request.session.get('temp_file_path')
    temp_file_url = request.session.get('temp_file_url')
    selected_event_type_val = request.session.get('selected_event_type')
    selected_category_id = request.session.get('selected_category_id')
    selected_specialty_id = request.session.get('selected_specialty_id')

    # Вземане на имената за показване
    selected_event_type_display = dict(MedicalEvent.EventType.choices).get(selected_event_type_val, selected_event_type_val)
    selected_category = MedicalCategory.objects.filter(pk=selected_category_id).first()
    selected_specialty = MedicalSpecialty.objects.filter(pk=selected_specialty_id).first()

    # Определяне на типа на файла за визуализация
    file_type = None
    if temp_file_url:
        ext = os.path.splitext(temp_file_url)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
            file_type = 'image'
        elif ext == '.pdf':
            file_type = 'pdf'

    if not all([temp_ocr_text, temp_file_hash, temp_file_path, temp_file_url]):
        request.session.flush()
        return redirect('medj:upload_page')

    context = {
        'ocr_text': temp_ocr_text,
        'file_hash': temp_file_hash,
        'temp_file_url': temp_file_url,
        'file_type': file_type, # Използваме вече дефинирания file_type
        'selected_event_type': selected_event_type_display,
        'selected_category': selected_category.name if selected_category else 'N/A',
        'selected_specialty': selected_specialty.name if selected_specialty else 'N/A',
    }

    if request.method == 'POST':
        edited_text = request.POST.get('edited_ocr_text')

        if not edited_text:
            context['error_message'] = _('Моля, редактирайте или одобрете текста.')
            return render(request, 'subpages/upload_review.html', context)

        try:
            ocr_text_for_ai = edited_text # Ако анонимизацията е в GPT клиента или не е нужна преди GPT

            user_context = {
                'category': selected_category.name if selected_category else 'N/A',
                'event_type': selected_event_type_display,
                'specialty': selected_specialty.name if selected_specialty else 'N/A',
            }
            gpt_result = call_gpt_for_document(ocr_text_for_ai, user_context['category'], {})

            with transaction.atomic():
                patient_profile = PatientProfile.objects.get(user=request.user)

                source_document = Document(
                    patient=patient_profile,
                    file_hash=temp_file_hash,
                )
                with open(temp_file_path, 'rb') as f:
                    source_document.file.save(os.path.basename(temp_file_path), ContentFile(f.read()), save=True)

                category_obj = MedicalCategory.objects.filter(pk=selected_category_id).first()
                specialty_obj = MedicalSpecialty.objects.filter(pk=selected_specialty_id).first()

                event_date_str = gpt_result.get("event_date")
                event_date = timezone.datetime.strptime(event_date_str, "%Y-%m-%d").date() if event_date_str else timezone.now().date()

                medical_event = MedicalEvent.objects.create(
                    patient=patient_profile,
                    source_document=source_document,
                    event_type_title=selected_event_type_val,
                    category=category_obj,
                    specialty=specialty_obj,
                    event_date=event_date,
                    summary=gpt_result.get("summary", "")
                )

                if 'structured_data' in gpt_result:
                    for item in gpt_result['structured_data']:
                        item_type = item.get('type')
                        if item_type == 'blood_test_panel':
                            for result_data in item.get('results', []):
                                BloodTestResult.objects.create(
                                    medical_event=medical_event,
                                    indicator_name=result_data.get("indicator_name"),
                                    value=result_data.get("value"),
                                    unit=result_data.get("unit", ""),
                                    reference_range=result_data.get("reference_range", "")
                                )
                        elif item_type == 'narrative_section':
                            NarrativeSectionResult.objects.create(
                                medical_event=medical_event,
                                title=item.get('title', 'N/A'),
                                content=item.get('content', '')
                            )
                        elif item_type == 'detected_practitioner':
                            practitioner_name = item.get('name')
                            if practitioner_name:
                                practitioner, created = Practitioner.objects.get_or_create(
                                    name=practitioner_name,
                                    defaults={'title': item.get('title', 'Д-р')}
                                )
                                medical_event.practitioners.add(practitioner)

                if gpt_result.get("suggested_tags"):
                    for tag_name in gpt_result["suggested_tags"]:
                        tag, _ = DocumentTag.objects.get_or_create(name=tag_name.strip())
                        medical_event.tags.add(tag)

            request.session.flush()
            if temp_file_path and default_storage.exists(temp_file_path):
                 default_storage.delete(temp_file_path)

            return redirect('medj:document_detail', event_id=medical_event.id)

        except Exception as e:
            print(f"CRITICAL ERROR in upload_review_page POST: {e}")
            context['error_message'] = _(f'Възникна грешка при анализа и запазването: {e}')
            return render(request, 'subpages/upload_review.html', context)


    return render(request, 'subpages/upload_review.html', context)


# --- ПРАЗНИ ИЗГЛЕДИ С КОРЕКТНИ ПЪТИЩА ---
@login_required
def upload_history(request):
    patient_profile, _ = PatientProfile.objects.get_or_create(user=request.user)
    user_documents = Document.objects.filter(patient=patient_profile).order_by('-uploaded_at')
    context = {'documents': user_documents}
    return render(request, 'main/history.html', context)

@login_required
def document_detail_view(request, event_id):
    try:
        event = MedicalEvent.objects.get(id=event_id, patient__user=request.user)
        context = {
            'event': event,
            'blood_test_results': event.blood_test_results.all(),
            'source_document': event.source_document,
            'narrative_sections': event.narrative_section_results.all(),
            'practitioners': event.practitioners.all()
        }
        return render(request, 'subpages/document_detail.html', context)
    except MedicalEvent.DoesNotExist:
        return redirect('medj:history')

@login_required
def casefiles(request): return render(request, 'main/casefiles.html')

@login_required
def personalcard(request): return render(request, 'main/personalcard.html')

@login_required
def profile(request): return render(request, 'subpages/profile.html')

@login_required
def doctors(request): return render(request, 'subpages/doctors.html')