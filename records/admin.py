from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from parler.admin import TranslatableAdmin
from .models import (
    PatientProfile, MedicalCategory, MedicalSpecialty, DocumentType, Tag,
    MedicalEvent, EventTag, Document, DocumentTag, Diagnosis, TreatmentPlan,
    NarrativeSectionResult, Medication, LabIndicator, LabTestMeasurement,
    DocumentShare, ShareToken, LabIndicatorAlias
)

User = get_user_model()

@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "email_verified", "is_staff", "is_active")
    search_fields = ("username", "email")
    fieldsets = DjangoUserAdmin.fieldsets + (("Profile", {"fields": ("phone", "email_verified")}),)

@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "first_name_bg", "last_name_bg", "date_of_birth", "gender")
    search_fields = ("user__username", "user__email", "first_name_bg", "last_name_bg")

@admin.register(MedicalCategory)
class MedicalCategoryAdmin(TranslatableAdmin):
    list_display = ("__str__", "slug", "is_active", "order")
    list_filter = ("is_active",)
    search_fields = ("translations__name", "slug")
    ordering = ("order", "id")

@admin.register(MedicalSpecialty)
class MedicalSpecialtyAdmin(TranslatableAdmin):
    list_display = ("__str__", "is_active", "order")
    list_filter = ("is_active",)
    search_fields = ("translations__name",)
    ordering = ("order", "id")

@admin.register(DocumentType)
class DocumentTypeAdmin(TranslatableAdmin):
    list_display = ("__str__", "slug", "is_active")
    list_filter = ("is_active",)
    search_fields = ("translations__name", "slug")

@admin.register(Tag)
class TagAdmin(TranslatableAdmin):
    list_display = ("__str__", "slug", "kind", "is_active")
    list_filter = ("kind", "is_active")
    search_fields = ("translations__name", "slug")

@admin.register(MedicalEvent)
class MedicalEventAdmin(admin.ModelAdmin):
    list_display = ("id", "patient", "specialty", "event_date", "created_at")
    list_filter = ("specialty", "event_date", "created_at")
    search_fields = ("patient__user__username", "patient__first_name_bg", "patient__last_name_bg")

@admin.register(EventTag)
class EventTagAdmin(admin.ModelAdmin):
    list_display = ("event", "tag")
    list_filter = ("tag__kind",)
    search_fields = ("event__patient__user__username", "tag__translations__name")

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "medical_event", "specialty", "category", "doc_type", "document_date", "uploaded_at")
    list_filter = ("specialty", "category", "doc_type", "doc_kind", "uploaded_at")
    search_fields = ("owner__username", "summary", "notes", "original_ocr_text")
    readonly_fields = ("sha256",)

@admin.register(DocumentTag)
class DocumentTagAdmin(admin.ModelAdmin):
    list_display = ("document", "tag", "is_inherited")
    list_filter = ("is_inherited", "tag__kind")
    search_fields = ("document__owner__username", "tag__translations__name")

@admin.register(Diagnosis)
class DiagnosisAdmin(admin.ModelAdmin):
    list_display = ("medical_event", "code", "diagnosed_at")
    search_fields = ("code", "text")

@admin.register(TreatmentPlan)
class TreatmentPlanAdmin(admin.ModelAdmin):
    list_display = ("medical_event", "start_date", "end_date")

@admin.register(NarrativeSectionResult)
class NarrativeSectionResultAdmin(admin.ModelAdmin):
    list_display = ("medical_event", "title")

@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ("medical_event", "name", "start_date", "end_date")

class LabIndicatorAliasInline(admin.TabularInline):
    model = LabIndicatorAlias
    extra = 1

@admin.register(LabIndicator)
class LabIndicatorAdmin(TranslatableAdmin):
    inlines = [LabIndicatorAliasInline]
    list_display = ("__str__", "unit", "reference_low", "reference_high")
    search_fields = ("translations__name",)

@admin.register(LabTestMeasurement)
class LabTestMeasurementAdmin(admin.ModelAdmin):
    list_display = ("medical_event", "indicator", "value", "measured_at", "is_abnormal")
    list_filter = ("indicator", "measured_at")

@admin.register(DocumentShare)
class DocumentShareAdmin(admin.ModelAdmin):
    list_display = ("document", "token", "created_at", "expires_at", "is_active")
    readonly_fields = ("token", "created_at")

@admin.register(ShareToken)
class ShareTokenAdmin(admin.ModelAdmin):
    list_display = ("document", "token", "created_at", "expires_at", "is_active")
