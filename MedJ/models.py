# MedJ/models.py
from django.db import models
from django.contrib.auth.models import User


# --- ОСНОВНИ МОДЕЛИ ---

class PatientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_of_birth = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Profile of {self.user.username}"


class Document(models.Model):
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(upload_to='medical_documents/')
    file_hash = models.CharField(max_length=64, unique=True, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processing_error_message = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Document {self.id} for {self.patient.user.username}"


# --- ТАГОВЕ И КЛАСИФИКАТОРИ ---

class MedicalCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self): return self.name


class MedicalSpecialty(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self): return self.name


class DocumentTag(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self): return self.name


# --- НОВ МОДЕЛ ЗА ЛЕКАРИ ---
class Practitioner(models.Model):
    name = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=50, blank=True)  # Д-р, проф., доц.
    specialty = models.ForeignKey(MedicalSpecialty, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self): return f"{self.title} {self.name}"


# --- ОСНОВНИЯТ МОДЕЛ: "МЕДИЦИНСКИЯТ КАРТОН" ---

class MedicalEvent(models.Model):
    class EventType(models.TextChoices):
        MEDICAL_COMMISSION = 'MC', 'Мед. Комисия'
        CHECKUP = 'CHK', 'Преглед'
        CONSULTATION = 'CON', 'Консултация'
        INTERVENTION = 'INT', 'Интервенция'
        SESSION = 'SES', 'Сесия'
        OPERATION = 'OPR', 'Операция'
        TREATMENT = 'TRM', 'Лечение'
        SCREENING = 'SCR', 'Скрининг'
        CERTIFICATE_ISSUE = 'CERI', 'Издаване на удостоверение'
        HOSPITALIZATION = 'HOS', 'Хоспитализация'
        REFERRAL = 'REF', 'Направление'
        CONCLUSION = 'CONC', 'Заключение/Становище'
        CERTIFICATE = 'CERT', 'Сертификат'
        DOCUMENT = 'DOC', 'Документ'
        OTHER = 'OTH', 'Друго'

    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='medical_events')
    source_document = models.OneToOneField(Document, on_delete=models.SET_NULL, null=True, blank=True,
                                           related_name='medical_event')

    event_type_title = models.CharField(max_length=4, choices=EventType.choices, default=EventType.OTHER)
    category = models.ForeignKey(MedicalCategory, on_delete=models.SET_NULL, null=True, blank=True)

    event_date = models.DateField(null=True, blank=True)
    summary = models.TextField(blank=True)

    tags = models.ManyToManyField(DocumentTag, related_name='events', blank=True)
    # --- НОВА ВРЪЗКА КЪМ ЛЕКАРИ ---
    practitioners = models.ManyToManyField(Practitioner, related_name='medical_events', blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_event_type_title_display()} for {self.patient.user.username} on {self.event_date}"


# --- МОДЕЛИ ЗА СТРУКТУРИРАНИ РЕЗУЛТАТИ ---

class BloodTestResult(models.Model):
    medical_event = models.ForeignKey(MedicalEvent, on_delete=models.CASCADE, related_name='blood_test_results')
    indicator_name = models.CharField(max_length=200)
    value = models.CharField(max_length=100)
    unit = models.CharField(max_length=50)
    reference_range = models.CharField(max_length=100, blank=True)

    class Meta:
        unique_together = ('medical_event', 'indicator_name', 'unit')

    def __str__(self): return f"{self.indicator_name}: {self.value} {self.unit}"


# --- НОВ МОДЕЛ ЗА ТЕКСТОВИ СЕКЦИИ ---
class NarrativeSectionResult(models.Model):
    medical_event = models.ForeignKey(MedicalEvent, on_delete=models.CASCADE, related_name='narrative_sections')
    title = models.CharField(max_length=255)
    content = models.TextField()

    def __str__(self): return self.title