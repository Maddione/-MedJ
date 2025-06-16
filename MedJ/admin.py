from django.contrib import admin
from .models import (
    PatientProfile,
    Document,
    MedicalCategory,
    MedicalSpecialty,
    MedicalEvent,
    DocumentTag,
    BloodTestResult,
    Practitioner,
    NarrativeSectionResult
)

@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'date_of_birth']
    search_fields = ['user__username']

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['id', 'patient', 'file', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['patient__user__username']

@admin.register(MedicalCategory)
class MedicalCategoryAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(MedicalSpecialty)
class MedicalSpecialtyAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(MedicalEvent)
class MedicalEventAdmin(admin.ModelAdmin):
    list_display = ['id', 'patient', 'get_event_type_title_display', 'category', 'specialty', 'event_date']
    list_filter = ['category', 'specialty', 'event_date']
    search_fields = ['patient__user__username', 'summary']
    # 'tags' и 'practitioners' вече са ManyToManyField в MedicalEvent, така че filter_horizontal работи
    filter_horizontal = ['tags', 'practitioners']

@admin.register(DocumentTag)
class DocumentTagAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(BloodTestResult)
class BloodTestResultAdmin(admin.ModelAdmin):
    list_display = ['medical_event', 'indicator_name', 'value', 'unit']
    list_filter = [('medical_event__event_date', admin.DateFieldListFilter)]
    search_fields = ['indicator_name', 'medical_event__summary']

@admin.register(Practitioner)
class PractitionerAdmin(admin.ModelAdmin):
    list_display = ['name', 'title', 'specialty']
    search_fields = ['name', 'specialty__name']
    list_filter = ['specialty']
    # Ако искате да управлявате свързаните MedicalEvent от Practitioner Admin
    filter_horizontal = ['medical_events'] # Ако искате да го добавите тук

@admin.register(NarrativeSectionResult)
class NarrativeSectionResultAdmin(admin.ModelAdmin):
    list_display = ['medical_event', 'title']
    search_fields = ['title', 'content', 'medical_event__summary']