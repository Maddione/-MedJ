import hashlib
import json
import os
import re
from datetime import date, datetime

from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.files.base import ContentFile
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError
from django.urls import reverse

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side

from ocrapi import anonymizer
from ocrapi.gpt_client import summarize_document, extract_entities, analyze_lab_results, get_summary_and_html_table, call_gpt_for_document
from ocrapi.vision_handler import perform_ocr_space

from .forms import CustomUserCreationForm
from .models import MedicalCategory, MedicalSpecialty, Document, MedicalEvent, Practitioner, BloodTestResult, \
    NarrativeSectionResult, PatientProfile, DocumentTag

# Allowed file extensions
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.tiff', '.bmp', '.webp']
ALLOWED_PDF_EXTENSIONS = ['.pdf']



# --- Public-facing pages ---
def landing_page(request):
    return render(request, 'basetemplates/landingpage.html')


def register_page(request):
    from .forms import CustomUserCreationForm
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            PatientProfile.objects.create(user=user)
            print(
                f"DEBUG: User '{user.username}' registered successfully with email '{user.email}'. PatientProfile created.")
            return redirect('medj:login')
        else:
            print(f"DEBUG: Registration form errors: {form.errors.as_json()}")
    else:
        form = CustomUserCreationForm()

    return render(request, 'registration/register.html', {'form': form})


# --- Authenticated pages ---
@login_required
def upload_page(request):
    categories = MedicalCategory.objects.all()
    specialties = MedicalSpecialty.objects.all()
    event_types = MedicalEvent.EventType.choices
    doctors = Practitioner.objects.all()

    messages_dict = {
        'unsupported_file_format': str(_('Неподдържан файлов формат.')),
        'no_file_chosen': str(_('Все още не е избран файл')),
        'choose_category_specialist_file': str(_('Моля, изберете категория, специалист и прикачете файл.')),
        'processing': str(_('Обработва се...')), 'ocr_error': str(_('Грешка при OCR:')),
        'unknown_server_error': str(_('Неизвестна сървърна грешка.')),
        'network_server_error': str(_('Мрежова или сървърна грешка.')),
        'critical_ocr_error': str(_('Критична грешка при OCR:')),
        'upload_button': str(_('Стартирай OCR')), 'analysis_ai': str(_('Анализира се с AI...')),
        'no_text_found': str(_('Не е намерен текст в документа.')), 'analysis_error': str(_('Грешка при анализ:')),
        'critical_analysis_error': str(_('Критична грешка при анализ:')),
        'approve_analyze_ai': str(_('Одобри и анализирай с AI')),
        'choose_category_first': str(_('Първо изберете тип събитие')),
        'choose_specialty_first': str(_('Първо изберете категория')),
        'choose_specialty_prompt': str(_('Изберете специалност...')),
        'error_fetching_specialties': str(_('Грешка при зареждане на специалностите.')),
        'analysis_ai_loading_message': str(_('Извършва се AI анализ, моля изчакайте...')),
        'save_success': str(_('Промените бяха запазени успешно!')),
        'save_error': str(_('Грешка при запазване на промените:')),
        'confirm_delete_event': str(_('Сигурни ли сте, че искате да изтриете това медицинско събитие и свързания с него документ?')),
        'deleting_event_text': str(_('Изтрива се...')),
        'event_deleted_success': str(_('Събитието и документът бяха успешно изтрити!')),
        'delete_error': str(_('Грешка при изтриване:')),
        'critical_delete_error': str(_('Критична грешка при изтриване:')),
        'save_details_button_text': str(_('Запази промените')),
        'delete_button_text': str(_('Изтрий документ')),
        'reanalyzing_text': str(_('Анализира се повторно...')),
        'document_reanalyzed_success': str(_('Документът е анализиран повторно и запазен!')),
    }

    if request.method == 'POST':
        try:
            pass
        except Exception as e:
            print(f"Error during upload_page POST (Non-AJAX form submit if any): {e}")
            return render(request, 'main/upload.html', {
                'categories': categories, 'specialties': specialties,
                'event_types': event_types, 'doctors': doctors,
                'error_message': _('Възникна грешка при обработката на формата: ') + str(e),
                'MESSAGES': json.dumps(messages_dict)
            })

    return render(request, 'main/upload.html', {
        'categories': categories,
        'specialties': specialties,
        'event_types': event_types,
        'doctors': doctors,
        'MESSAGES': json.dumps(messages_dict)
    })


@login_required
def dashboard_page(request):
    patient_profile, created = PatientProfile.objects.get_or_create(user=request.user)
    if created:
        print(f"DEBUG: Created PatientProfile for user: {request.user.username}")

    unique_indicators = BloodTestResult.objects.filter(
        medical_event__patient=patient_profile
    ).values_list('indicator_name', flat=True).distinct().order_by('indicator_name')

    all_blood_results = BloodTestResult.objects.filter(
        medical_event__patient=patient_profile
    ).order_by('medical_event__event_date', 'indicator_name')

    chart_data = {}
    for result in all_blood_results:
        indicator = result.indicator_name
        event_date = result.medical_event.event_date.strftime("%Y-%m-%d") if result.medical_event.event_date else "N/A"

        try:
            value = float(str(result.value).replace(',', '.'))
        except ValueError:
            value = None

        if indicator not in chart_data:
            chart_data[indicator] = []

        chart_data[indicator].append({
            'date': event_date,
            'value': value,
            'unit': result.unit,
            'reference_range': result.reference_range
        })

    context = {
        'unique_indicators_json': json.dumps(list(unique_indicators)),
        'all_blood_results_json': json.dumps(chart_data),
        'MESSAGES': json.dumps({
            'select_indicator': str(_('Изберете показател(и)')),
            'no_data_for_indicator': str(_('Няма данни за избрания показател.')),
            'no_blood_data': str(_('Все още няма качени данни за кръвни изследвания.')),
            'no_blood_data_upload_link': str(_('Качете първия си документ от тук.')),
        })
    }
    return render(request, 'main/dashboard.html', context)


@login_required
def casefiles_page(request):
    return render(request, 'main/casefiles.html')


@login_required
def personalcard_page(request):
    return render(request, 'main/personalcard.html')


@login_required
def history_page(request):
    user_events = MedicalEvent.objects.filter(patient=request.user.patientprofile).order_by('-created_at')
    context = {
        'medical_events': user_events
    }
    return render(request, 'main/history.html', context)


@login_required
def doctors_page(request):
    doctors_list = Practitioner.objects.all().order_by('name')
    context = {'doctors': doctors_list}
    return render(request, 'subpages/doctors.html', context)


@login_required
def profile_page(request):
    return render(request, 'subpages/profile.html')


@login_required
def event_detail_page(request, event_id):
    medical_event = get_object_or_404(MedicalEvent, id=event_id, patient__user=request.user)
    document = medical_event.source_document
    editable_summary_text = medical_event.summary

    blood_results = medical_event.blood_test_results.all().order_by('indicator_name')
    narrative_sections = medical_event.narrative_section_results.all().order_by('title')
    practitioners_for_event = medical_event.practitioners.all().order_by('name')
    tags_for_event = medical_event.tags.all().order_by('name')

    messages_dict = {
        'save_success': str(_('Промените бяха запазени успешно!')),
        'save_error': str(_('Грешка при запазване на промените:')),
        'confirm_delete_event': str(_('Сигурни ли сте, че искате да изтриете това медицинско събитие и свързания с него документ?')),
        'deleting_event_text': str(_('Изтрива се...')),
        'event_deleted_success': str(_('Събитието и документът бяха успешно изтрити!')),
        'delete_error': str(_('Грешка при изтриване:')),
        'critical_delete_error': str(_('Критична грешка при изтриване:')),
        'unknown_server_error': str(_('Неизвестна сървърна грешка.')),
        'network_server_error': str(_('Мрежова или сървърна грешка.')),
    }

    context = {
        'medical_event': medical_event,
        'document': document,
        'editable_summary_text': editable_summary_text,
        'blood_results': blood_results,
        'narrative_sections': narrative_sections,
        'practitioners_for_event': practitioners_for_event,
        'tags_for_event': tags_for_event,
        'MESSAGES': json.dumps(messages_dict),
    }
    return render(request, 'subpages/event_detail.html', context)


@login_required
def upload_history_page(request):
    documents = Document.objects.filter(patient__user=request.user).order_by('-uploaded_at')
    context = {
        'documents': documents
    }
    return render(request, 'subpages/upload_history.html', context)


@csrf_exempt
@login_required
def update_event_details(request, event_id):
    if request.method == 'POST':
        try:
            medical_event = get_object_or_404(MedicalEvent, id=event_id, patient__user=request.user)
            data = json.loads(request.body)

            new_summary = data.get('summary')
            if new_summary is not None:
                medical_event.summary = new_summary

            new_event_date_str = data.get('event_date')
            if new_event_date_str:
                try:
                    medical_event.event_date = datetime.strptime(new_event_date_str, '%Y-%m-%d').date()
                except ValueError:
                    print(f"Warning: Could not parse new_event_date: {new_event_date_str}")

            new_tags = data.get('tags')
            if new_tags is not None:
                medical_event.tags.clear()
                for tag_name in new_tags:
                    tag, created = DocumentTag.objects.get_or_create(name=tag_name)
                    medical_event.tags.add(tag)

            medical_event.updated_at = timezone.now()
            medical_event.save()

            print(f"DEBUG: MedicalEvent ID {event_id} details updated successfully.")
            return JsonResponse({'status': 'success', 'message': _('Промените бяха запазени успешно!')})

        except MedicalEvent.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': _('Медицинско събитие не е намерено.')}, status=404)
        except Exception as e:
            print(f"ERROR: Failed to update MedicalEvent ID {event_id} details: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': _('Невалидна заявка.')}, status=400)


@csrf_exempt
@login_required
def delete_document(request, document_id):
    if request.method == 'POST':
        try:
            document = get_object_or_404(Document, id=document_id, patient__user=request.user)

            if hasattr(document, 'medical_event'):

                medical_event = document.medical_event
                medical_event_id = medical_event.id
                medical_event.delete()
                document.delete()

                print(
                    f"DEBUG: MedicalEvent ID {medical_event_id} and Document ID {document_id} deleted successfully by user {request.user.username}.")
            else:
                document.delete()
                print(
                    f"DEBUG: Document ID {document_id} (no linked event) deleted successfully by user {request.user.username}.")

            return JsonResponse({
                'status': 'success',
                'message': _('Документът и свързаните с него данни бяха успешно изтрити.'),
                'redirect_url': str(reverse('medj:history'))
            })
        except Document.DoesNotExist:
            print(f"ERROR: Attempted to delete non-existent or unauthorized document ID: {document_id}.")
            return JsonResponse(
                {'status': 'error', 'message': _('Документът не е намерен или нямате право да го изтриете.')},
                status=404)
        except Exception as e:
            print(f"CRITICAL ERROR: Failed to delete document ID {document_id}: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': _('Невалидна заявка.')}, status=400)


@login_required
def upload_review_page(request):
    return render(request, 'subpages/upload_review.html')


# --- API Endpoints for AJAX calls ---
@csrf_exempt
@login_required
def perform_ocr(request):
    # --- DEBUGGING START ---
    print("\n--- DEBUGGING PERFORM OCR ---")
    print(f"DEBUG: Request method: {request.method}")
    print(f"DEBUG: request.FILES content: {request.FILES}")
    print(f"DEBUG: request.FILES.get('document'): {request.FILES.get('document')}")
    # --- DEBUGGING END ---

    if request.method == 'POST' and request.FILES.get('document'):
        uploaded_file = request.FILES['document']

        file_content = uploaded_file.read()
        file_hash = hashlib.sha256(file_content).hexdigest()

        if Document.objects.filter(file_hash=file_hash).exists():
            print(f"DEBUG: Duplicate file detected. Hash: {file_hash}")
            return JsonResponse(
                {'status': 'error', 'message': _('Този документ вече е качен. Моля, изберете друг файл.'),
                 'file_hash': file_hash}, status=409)

        uploaded_file.seek(0)

        try:
            ocr_text = perform_ocr_space(uploaded_file)

            if not ocr_text:
                print("DEBUG: OCR returned no text.")
                return JsonResponse({'status': 'error', 'message': _('Не е намерен текст в документа.')}, status=400)

            patient_profile, created = PatientProfile.objects.get_or_create(user=request.user)
            if created:
                print(f"DEBUG: Created PatientProfile for user: {request.user.username} during OCR.")

            document = Document.objects.create(
                patient=patient_profile,
                file=uploaded_file,
                file_hash=file_hash,
            )
            print(f"DEBUG: Document saved to DB. ID: {document.id}, Path: {document.file.path}")

            return JsonResponse({
                'status': 'success',
                'ocr_text_for_display': ocr_text,
                'file_hash': file_hash,
                'document_id': document.id
            })

        except Exception as e:
            print(f"CRITICAL ERROR during perform_ocr process: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    print("DEBUG: Request method is not POST or document file is missing in request.FILES.")
    return JsonResponse({'status': 'error', 'message': _('Невалидна заявка или липсващ файл.')}, status=400)


@csrf_exempt
@login_required
def analyze_document(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            edited_text = data.get('edited_text', '')
            event_type_title_str = data.get('event_type')
            category_name = data.get('category')
            specialty_name = data.get('specialist')
            file_hash = data.get('file_hash')

            category = MedicalCategory.objects.get(name=category_name) if category_name else None
            specialty = MedicalSpecialty.objects.get(name=specialty_name) if specialty_name else None

            patient_profile = request.user.patientprofile
            existing_document = Document.objects.filter(file_hash=file_hash).first()

            if not existing_document:
                print(f"ERROR: analyze_document: Document with hash {file_hash} not found.")
                return JsonResponse({'status': 'error', 'message': _('Липсващ документ с посочения хеш.')}, status=400)

            anonymized_text = anonymizer.anonymize_text(edited_text)

            # --- DEBUGGING START ---
            print("\n--- DEBUGGING ANALYZE DOCUMENT ---")
            print(f"DEBUG: OPENAI_API_KEY is set: {bool(settings.OPENAI_API_KEY)}")
            print(f"DEBUG: Length of anonymized_text: {len(anonymized_text)}")
            print(f"DEBUG: Anonymized text snippet: '{anonymized_text[:500]}...'")
            print(f"DEBUG: Category for GPT: {category_name}")

            if not anonymized_text.strip():
                print(
                    "ERROR: Anonymized text is empty or contains only whitespace. GPT will not have content to analyze.")
                return JsonResponse({'status': 'error', 'message': _(
                    'Не е намерен съдържателен текст за анализ от AI. Моля, проверете документа.')}, status=400)
            # --- DEBUGGING END ---

            gpt_response_data = {}
            try:
                gpt_response_data = call_gpt_for_document(anonymized_text,
                                                          category_name if category_name else "general", {})
                if not isinstance(gpt_response_data, dict) or not gpt_response_data:
                    print(f"ERROR: call_gpt_for_document returned non-dict or empty data: {gpt_response_data}")
                    return JsonResponse({'status': 'error', 'message': _(
                        'Анализът от AI върна празни или невалидни данни. Моля, опитайте отново или проверете API.')},
                                        status=500)
            except Exception as e:
                print(f"CRITICAL ERROR: Failed to get response from GPT: {e}")
                return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

            # --- DEBUGGING GPT Response Data ---
            print("\n--- GPT Response Data (analyze_document) ---")
            try:
                print(json.dumps(gpt_response_data, indent=2, ensure_ascii=False))
            except Exception as json_e:
                print(f"ERROR: Could not pretty print GPT response: {json_e}. Raw data: {gpt_response_data}")
            print("--- END GPT Response Data ---")
            # --- END DEBUGGING ---

            # --- DEBUGGING GPT JSON Save START ---
            print("\n--- DEBUGGING GPT JSON Save ---")
            if gpt_response_data:
                try:
                    # Generate a unique filename using document ID and a timestamp
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

                    original_filename_base = os.path.splitext(os.path.basename(existing_document.file.name))[0]

                    json_filename = f"{original_filename_base}_{existing_document.id}_{timestamp}_gpt_response.json"

                    json_content = json.dumps(gpt_response_data, indent=2, ensure_ascii=False)

                    print(f"DEBUG: Attempting to save JSON file. Filename: {json_filename}")
                    print(f"DEBUG: JSON content length: {len(json_content)} bytes")
                    print(f"DEBUG: Target directory: {os.path.join(settings.MEDIA_ROOT, 'gpt_json_responses')}")

                    target_dir = os.path.join(settings.MEDIA_ROOT, 'gpt_json_responses')
                    if not os.path.exists(target_dir):
                        print(f"DEBUG: Creating target directory: {target_dir}")
                        os.makedirs(target_dir, exist_ok=True)
                    if not os.access(target_dir, os.W_OK):
                        print(f"ERROR: Directory is not writable: {target_dir}. Check permissions!")
                        raise Exception("Директорията за запис на JSON файлове не е достъпна за запис.")

                    existing_document.gpt_json_file.save(json_filename, ContentFile(json_content))
                    existing_document.save()

                    print(f"DEBUG: Successfully saved GPT JSON to: {existing_document.gpt_json_file.path}")

                except Exception as e:
                    print(f"ERROR: Failed to save GPT JSON file: {e}")
                    existing_document.processing_error_message = _(f"Грешка при запис на GPT JSON: {e}")
                    existing_document.save()
            else:
                print("WARNING: GPT response data was empty, not saving JSON file.")
            print("--- DEBUGGING GPT JSON Save END ---")

            # Extract data from GPT's JSON response
            final_summary = gpt_response_data.get('summary', str(_('Няма обобщение.')))
            event_date_str = gpt_response_data.get('event_date')
            detected_specialty_str = gpt_response_data.get('detected_specialty')
            suggested_tags_list = gpt_response_data.get('suggested_tags', [])
            blood_test_results_list = gpt_response_data.get('blood_test_results', [])
            diagnosis_content = gpt_response_data.get('diagnosis')
            treatment_plan_content = gpt_response_data.get('treatment_plan')
            html_table = gpt_response_data.get('html_table',
                                               '<table><tr><td>' + str(_('Няма таблица.')) + '</td></tr></table>')

            # --- DEBUGGING EXTRACTED DATA START ---
            print("\n--- DEBUGGING EXTRACTED DATA ---")
            print(f"DEBUG: Extracted final_summary: '{final_summary[:100]}...'")
            print(f"DEBUG: Extracted event_date_str: '{event_date_str}'")
            print(f"DEBUG: Extracted detected_specialty_str: '{detected_specialty_str}'")
            print(f"DEBUG: Extracted suggested_tags_list: {str(suggested_tags_list)}")
            print(f"DEBUG: Extracted blood_test_results_list: {str(blood_test_results_list)}")
            print(f"DEBUG: Extracted diagnosis_content: '{str(diagnosis_content)[:100]}...'")
            print(f"DEBUG: Extracted treatment_plan_content: '{str(treatment_plan_content)[:100]}...'")


            event_date_obj = None
            if event_date_str:
                try:
                    event_date_obj = datetime.strptime(event_date_str, '%Y-%m-%d').date()
                except ValueError:
                    print(f"Warning: Could not parse event_date: {event_date_str}")

            detected_specialty_obj = None
            if detected_specialty_str:
                detected_specialty_obj, created = MedicalSpecialty.objects.get_or_create(name=detected_specialty_str)

            medical_event_obj, created = MedicalEvent.objects.get_or_create(
                patient=patient_profile,
                source_document=existing_document,
                defaults={
                    'event_type_title': event_type_title_str,
                    'category': category,
                    'specialty': specialty or detected_specialty_obj,
                    'summary': final_summary,
                    'event_date': event_date_obj if event_date_obj else date.today(),
                    'created_at': timezone.now(),
                    'updated_at': timezone.now(),
                }
            )

            if not created:
                medical_event_obj.event_type_title = event_type_title_str
                medical_event_obj.category = category
                medical_event_obj.specialty = specialty or detected_specialty_obj
                medical_event_obj.summary = final_summary
                medical_event_obj.event_date = event_date_obj if event_date_obj else medical_event_obj.event_date or date.today()
                medical_event_obj.updated_at = timezone.now()
                medical_event_obj.save()

            print(f"MedicalEvent created/updated with ID: {medical_event_obj.id}")
            print(f"Attempting to process {len(blood_test_results_list)} blood test results.")
            print(f"MedicalEvent created/updated with ID: {medical_event_obj.id}")
            print(f"Attempting to process {len(blood_test_results_list)} blood test results.")

            for res_data in blood_test_results_list:
                indicator_name_raw = res_data.get('indicator_name')
                value_raw = res_data.get('value')
                unit_raw = res_data.get('unit')
                reference_range_raw = res_data.get('reference_range', '')

                # Ensure all values are strings and strip whitespace
                indicator_name = str(indicator_name_raw).strip() if indicator_name_raw else ''
                value = str(value_raw).strip() if value_raw else ''
                unit = str(unit_raw).strip() if unit_raw else ''
                reference_range = str(reference_range_raw).strip() if reference_range_raw else ''

                if indicator_name and value:

                    existing_bt_result = BloodTestResult.objects.filter(
                        medical_event=medical_event_obj,
                        indicator_name=indicator_name,
                        unit=unit
                    ).first()

                    if existing_bt_result:

                        existing_bt_result.value = value


                        if not existing_bt_result.unit and unit:
                            existing_bt_result.unit = unit


                        if not existing_bt_result.reference_range and reference_range:
                            existing_bt_result.reference_range = reference_range

                        existing_bt_result.save()
                        print(
                            f"Updated existing BloodTestResult for Event {medical_event_obj.id}: {indicator_name}: {value} {unit} (Ref: {reference_range})")
                    else:

                        BloodTestResult.objects.create(
                            medical_event=medical_event_obj,
                            indicator_name=indicator_name,
                            value=value,
                            unit=unit,
                            reference_range=reference_range
                        )
                        print(
                            f"Created new BloodTestResult for Event {medical_event_obj.id}: {indicator_name}: {value} {unit} (Ref: {reference_range})")
                else:
                    print(
                        f"Skipping BloodTestResult for Event {medical_event_obj.id} due to missing indicator_name or value: {res_data}")

            for tag_name in suggested_tags_list:
                tag_name = str(tag_name).strip()
                if tag_name:
                    tag, created = DocumentTag.objects.get_or_create(name=tag_name)
                    medical_event_obj.tags.add(tag)
                    print(f"Added tag: {tag_name}")

            doctor_patterns = [
                r'(д-р|доктор)\s+([А-Я][а-я]+(?:\s+[А-Я][а-я]+)*)',
                r'\b([А-Я][а-я]+\s+[А-Я][а-я]+(?:\s+[А-Я][а-я]+)?)\b(?=\s*(?:д-р|доктор|специалист))'
            ]

            found_doctors = set()
            for pattern in doctor_patterns:
                matches = re.findall(pattern, edited_text, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        name = match[-1].strip()
                    else:
                        name = match.strip()

                    if name and len(name.split()) >= 2:
                        found_doctors.add(name)

            for doc_name in found_doctors:
                doc_name = str(doc_name).strip()
                if doc_name:
                    practitioner, created = Practitioner.objects.get_or_create(name=doc_name)
                    medical_event_obj.practitioners.add(practitioner)
                    print(f"Added practitioner: {doc_name}")

            if diagnosis_content:
                NarrativeSectionResult.objects.create(
                    medical_event=medical_event_obj,
                    title=_('Диагноза'),
                    content=str(diagnosis_content)
                )
                print(f"Added diagnosis: {str(diagnosis_content)[:50]}...")
            if treatment_plan_content:
                NarrativeSectionResult.objects.create(
                    medical_event=medical_event_obj,
                    title=_('План за лечение'),
                    content=str(treatment_plan_content)
                )
                print(f"Added treatment plan: {str(treatment_plan_content)[:50]}...")

            return JsonResponse({
                'status': 'success',
                'message': _('Документът е успешно анализиран и запазен!'),
                'new_document_id': {
                    'summary': final_summary,
                    'html_table': html_table,
                    'event_id': medical_event_obj.id,
                }
            })

        except json.JSONDecodeError:
            print("Error: Invalid JSON format from request body.")
            return JsonResponse({'status': 'error', 'message': _('Невалиден JSON формат.')}, status=400)
        except MedicalCategory.DoesNotExist:
            print(f"Error: Selected category '{category_name}' does not exist.")
            return JsonResponse({'status': 'error', 'message': _('Избраната категория не съществува.')}, status=400)
        except MedicalSpecialty.DoesNotExist:
            print(f"Error: Selected specialty '{specialty_name}' does not exist.")
            return JsonResponse({'status': 'error', 'message': _('Избраната специалност не съществува.')}, status=400)
        except Exception as e:
            print(f"Critical error during analyze_document: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    print("Error: Invalid request to analyze_document.")
    return JsonResponse({'status': 'error', 'message': _('Невалидна заявка.')}, status=400)


@login_required
def history_page(request):
    user_events = MedicalEvent.objects.filter(patient=request.user.patientprofile).order_by('-created_at')
    context = {
        'medical_events': user_events
    }
    return render(request, 'main/history.html', context)

# --- History of uploaded documents ---
@login_required
def upload_history_page(request): # Renamed view
    documents = Document.objects.filter(patient__user=request.user).order_by('-uploaded_at')
    context = {
        'documents': documents
    }
    return render(request, 'subpages/upload_history.html', context)


@login_required
def dashboard_page(request):
    patient_profile = request.user.patientprofile

    unique_indicators = BloodTestResult.objects.filter(
        medical_event__patient=patient_profile
    ).values_list('indicator_name', flat=True).distinct().order_by('indicator_name')

    all_blood_results = BloodTestResult.objects.filter(
        medical_event__patient=patient_profile
    ).order_by('medical_event__event_date', 'indicator_name')

    chart_data = {}
    for result in all_blood_results:
        indicator = result.indicator_name
        event_date = result.medical_event.event_date.strftime("%Y-%m-%d") if result.medical_event.event_date else "N/A"

        try:
            value = float(str(result.value).replace(',', '.'))
        except ValueError:
            value = None

        if indicator not in chart_data:
            chart_data[indicator] = []

        chart_data[indicator].append({
            'date': event_date,
            'value': value,
            'unit': result.unit,
            'reference_range': result.reference_range
        })

    context = {
        'unique_indicators_json': json.dumps(list(unique_indicators)),
        'all_blood_results_json': json.dumps(chart_data),
        'MESSAGES': json.dumps({
            'select_indicator': str(_('Изберете показател(и)')),
            'no_data_for_indicator': str(_('Няма данни за избрания показател.')),
            'no_blood_data': str(_('Все още няма качени данни за кръвни изследвания.')),
            'no_blood_data_upload_link': str(_('Качете първия си документ от тук.')),
        })
    }
    return render(request, 'main/dashboard.html', context)


@login_required
def casefiles_page(request):
    return render(request, 'main/casefiles.html')


@login_required
def doctors_page(request):
    doctors_list = Practitioner.objects.all().order_by('name')
    context = {'doctors': doctors_list}
    return render(request, 'subpages/doctors.html', context)


@login_required
def personalcard_page(request):
    return render(request, 'main/personalcard.html')


@login_required
def profile_page(request):
    return render(request, 'subpages/profile.html')


@login_required
def document_detail_page(request, event_id):
    try:
        medical_event = MedicalEvent.objects.get(id=event_id, patient=request.user.patientprofile)
        context = {
            'medical_event': medical_event,
            'blood_results': medical_event.blood_test_results.all(),
            'narrative_sections': medical_event.narrative_section_results.all(),
            'practitioners_for_event': medical_event.practitioners.all(),
            'tags_for_event': medical_event.tags.all(),
        }
        return render(request, 'subpages/event_detail.html', context)
    except MedicalEvent.DoesNotExist:
        return HttpResponse(_("Медицинско събитие не е намерено."), status=404)


@login_required
def upload_review_page(request):
    return render(request, 'subpages/upload_review.html')


@login_required
def get_specialties_for_category(request):
    specialties = MedicalSpecialty.objects.all().values('id', 'name')
    return JsonResponse(list(specialties), safe=False)


# --- Export View ---
@login_required
def export_medical_events_to_excel(request):
    wb = Workbook()
    ws = wb.active
    ws.title = str(_("Медицински Събития"))

    columns = [
        str(_("ID Събитие")),
        str(_("Тип Събитие")),
        str(_("Категория")),
        str(_("Специалност")),
        str(_("Дата на Събитието")),
        str(_("Обобщение")),
        str(_("Дата на Качване")),
        str(_("Хеш на Документ")),
        str(_("Лекари")),
        str(_("Тагове")),
    ]
    ws.append(columns)

    header_font = Font(bold=True)
    for col_idx in range(1, len(columns) + 1):
        ws.cell(row=1, column=col_idx).font = header_font
        ws.cell(row=1, column=col_idx).alignment = Alignment(horizontal='center', vertical='center')
        ws.cell(row=1, column=col_idx).border = Border(bottom=Side(style='thin'))

    print("\n--- DEBUGGING EXCEL EXPORT ---")
    try:
        patient_profile = request.user.patientprofile
        print(f"DEBUG: Exporting data for patient: {patient_profile.user.username}")
        medical_events = MedicalEvent.objects.filter(patient=patient_profile).order_by('-event_date')
        print(f"DEBUG: Found {medical_events.count()} medical events for this patient.")

        if not medical_events.exists():
            print("DEBUG: No medical events found. Excel will be empty except headers.")
            pass

        for event in medical_events:
            print(
                f"DEBUG: Processing Event ID: {event.id}, Type: {event.event_type_title}, Summary: {event.summary[:50]}...")

            category_name = event.category.name if event.category else ""
            specialty_name = event.specialty.name if event.specialty else ""
            document_hash = event.source_document.file_hash if event.source_document else ""

            practitioners = ", ".join([p.name for p in event.practitioners.all()])
            tags = ", ".join([t.name for t in event.tags.all()])

            ws.append([
                event.id,
                event.get_event_type_title_display(),
                category_name,
                specialty_name,
                event.event_date.strftime("%Y-%m-%d") if event.event_date else "",
                event.summary,
                event.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                document_hash,
                practitioners,
                tags,
            ])
            print(f"DEBUG: Added event row for ID {event.id}.")

            blood_results = event.blood_test_results.all()
            print(f"DEBUG: Event ID {event.id} has {blood_results.count()} blood test results.")
            if blood_results:
                ws.append([str(_("Кръвни резултати:")), "", "", "", "", "", "", "", "", ""])
                ws.append(
                    [str(_("Показател")), str(_("Стойност")), str(_("Мерна Единица")), str(_("Реф. Граници")), "", "",
                     "", "", "", ""])
                for br in blood_results:
                    ws.append([
                        str(br.indicator_name),
                        str(br.value),
                        str(br.unit),
                        str(br.reference_range),
                        "", "", "", "", "", ""
                    ])
                    print(f"DEBUG: Added BloodTestResult: {br.indicator_name}: {br.value} {br.unit}")

    except Exception as e:
        print(f"CRITICAL ERROR during Excel export loop: {e}")
        raise e
    print("--- END DEBUGGING EXCEL EXPORT ---")

    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if cell.value is not None:  # Ensure value is not None before checking length
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
            except TypeError:  # Handle cases where cell.value might not be directly convertible to str
                pass
        adjusted_width = (max_length + 2)
        if adjusted_width > 100:
            adjusted_width = 100
        ws.column_dimensions[column].width = adjusted_width

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="медицински_събития.xlsx"'
    wb.save(response)

    return response

def test_upload_view(request):
    if request.method == 'POST':
        print("\n--- DEBUGGING TEST_UPLOAD_VIEW ---")
        print(f"DEBUG: Test Request method: {request.method}")
        print(f"DEBUG: Test request.FILES content: {request.FILES}")
        print(f"DEBUG: Test request.FILES.get('test_file'): {request.FILES.get('test_file')}")

        if 'test_file' in request.FILES:
            uploaded_file = request.FILES['test_file']
            # Save the file to media/test_uploads
            save_path = os.path.join(settings.MEDIA_ROOT, 'test_uploads', uploaded_file.name)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            print(f"DEBUG: Test file saved to: {save_path}")
            return HttpResponse("File uploaded successfully to test_uploads!", status=200)
        else:
            print("DEBUG: Test file NOT found in request.FILES.")
            return HttpResponse("File upload FAILED: No file found.", status=400)
    return render(request, 'temp_test_upload.html')
