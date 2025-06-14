import os
import json
import hashlib
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.files.storage import default_storage
from django.utils.translation import gettext as _
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect

from ocrapi.vision_handler import extract_text_from_image
from ocrapi.gpt_client import call_gpt_for_document, extract_medical_fields_from_text
from ocrapi.anonymizer import anonymize_text
from .forms import CustomUserCreationForm
from .models import MedicalEvent, MedicalDocument, Tag


def landing_page(request):
    if request.user.is_authenticated:
        return redirect('medj:dashboard')
    return render(request, 'basetemplates/landingpage.html')


@csrf_protect
def login_view(request):
    if request.user.is_authenticated: return redirect('medj:dashboard')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('medj:dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})


@csrf_protect
def register(request):
    if request.user.is_authenticated: return redirect('medj:dashboard')
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('medj:dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    return redirect('medj:landingpage')


@login_required
def dashboard(request): return render(request, 'main/dashboard.html')


@login_required
def upload_page(request): return render(request, 'main/upload.html')


@login_required
def upload_history(request):
    user_documents = MedicalDocument.objects.filter(event__user=request.user).order_by('-uploaded_at')
    return render(request, 'main/history.html', {'documents': user_documents})


@login_required
def document_detail_view(request, doc_id):
    document = get_object_or_404(MedicalDocument, id=doc_id, event__user=request.user)
    return render(request, 'subpages/document_detail.html', {'document': document})


@login_required
def casefiles(request): return render(request, 'main/casefiles.html')


@login_required
def personalcard(request): return render(request, 'main/personalcard.html')


@login_required
def profile(request): return render(request, 'subpages/profile.html')


@login_required
def doctors(request): return render(request, 'subpages/doctors.html')


@login_required
@require_POST
def perform_ocr(request):
    temp_file_path = None
    try:
        uploaded_file = request.FILES.get('document')
        if not uploaded_file:
            return JsonResponse({'status': 'error', 'message': 'Файлът не беше получен.'}, status=400)
        file_content = uploaded_file.read()
        file_hash = hashlib.sha256(file_content).hexdigest()
        if MedicalDocument.objects.filter(file_hash=file_hash, event__user=request.user).exists():
            return JsonResponse({'status': 'error', 'message': 'Този документ вече е качен от Вас.'}, status=409)
        uploaded_file.seek(0)
        file_name = default_storage.save(f"temp/{uploaded_file.name}", uploaded_file)
        temp_file_path = default_storage.path(file_name)
        raw_text = extract_text_from_image(temp_file_path)
        if not raw_text:
            raise ValueError('Не беше разчетен текст от документа.')
        return JsonResponse({'status': 'success', 'ocr_text': raw_text, 'file_hash': file_hash})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Грешка при OCR обработка: {str(e)}'}, status=500)
    finally:
        if temp_file_path and default_storage.exists(file_name):
            default_storage.delete(file_name)


@login_required
@require_POST
def analyze_document(request):
    try:
        data = json.loads(request.body)
        edited_text = data.get('edited_text')
        category = data.get('category')
        specialist = data.get('specialist')
        file_hash = data.get('file_hash')

        if not all([edited_text, category, specialist, file_hash]):
            return JsonResponse({'status': 'error', 'message': 'Липсват данни в заявката.'}, status=400)
        if MedicalDocument.objects.filter(file_hash=file_hash, event__user=request.user).exists():
            return JsonResponse({'status': 'error', 'message': 'Този документ вече е записан (повторна проверка).'},
                                status=409)

        anonymized_text = anonymize_text(edited_text)
        extracted_fields = extract_medical_fields_from_text(anonymized_text)
        gpt_result = call_gpt_for_document(anonymized_text, category, extracted_fields)

        try:
            event_date_str = gpt_result.get("json_data", {}).get("date")
            event_date = timezone.datetime.strptime(event_date_str,
                                                    "%Y-%m-%d").date() if event_date_str else timezone.now().date()
        except (ValueError, TypeError):
            event_date = timezone.now().date()

        medical_event = MedicalEvent.objects.create(user=request.user, date=event_date,
                                                    title=f"{category} от {event_date.strftime('%d.%m.%Y')}")

        new_document = MedicalDocument.objects.create(
            event=medical_event,
            summary=gpt_result.get("summary", "Няма налично обобщение."),
            html_content=gpt_result.get("html_table", ""),
            json_content=gpt_result.get("json_data", {}),
            file_hash=file_hash
        )

        category_tag, _ = Tag.objects.get_or_create(name=category)
        specialist_tag, _ = Tag.objects.get_or_create(name=specialist)
        new_document.tags.add(category_tag, specialist_tag)

        return JsonResponse({'status': 'success', 'new_document_id': gpt_result})

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Невалиден JSON формат на заявката.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Грешка при анализ с AI: {str(e)}'}, status=500)