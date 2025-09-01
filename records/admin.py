from django.contrib import admin
from django.utils.translation import gettext_lazy as _l
from parler.admin import TranslatableAdmin
from .models import (
    User, PatientProfile, MedicalCategory,
    MedicalSpecialty, DocumentType, Tag, MedicalEvent, EventTag,
    Document, DocumentTag, Diagnosis, TreatmentPlan, NarrativeSectionResult,
    Medication, LabIndicator, LabTestMeasurement, ShareToken, UiLabel
)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "is_staff", "is_active")
    search_fields = ("username", "email")


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "date_of_birth", "blood_type")
    search_fields = ("user__username", "user__email")


@admin.register(MedicalCategory)
class MedicalCategoryAdmin(TranslatableAdmin):
    list_display = ("name", "slug", "is_active")
    list_filter = ("is_active",)
    search_fields = ("translations__name",)


@admin.register(MedicalSpecialty)
class MedicalSpecialtyAdmin(TranslatableAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("translations__name",)


@admin.register(DocumentType)
class DocumentTypeAdmin(TranslatableAdmin):
    list_display = ("name", "slug", "is_active")
    list_filter = ("is_active",)
    search_fields = ("translations__name",)


@admin.register(UiLabel)
class UiLabelAdmin(TranslatableAdmin):
    list_display = ("slug", "get_text")
    search_fields = ("slug", "translations__text")
    def get_text(self, obj):
        return obj.safe_translation_getter("text", any_language=True)
    get_text.short_description = _l("Text")


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "category")
    list_filter = ("category",)
    search_fields = ("name",)


@admin.register(MedicalEvent)
class MedicalEventAdmin(admin.ModelAdmin):
    list_display = ("id", "patient", "specialty", "event_date")
    list_filter = ("specialty", "event_date")
    search_fields = ("patient__user__username", "summary")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "medical_event", "doc_type", "document_date", "uploaded_at")
    list_filter = ("doc_type", "document_date", "uploaded_at")
    search_fields = ("owner__username", "summary", "notes", "original_ocr_text")
    readonly_fields = ("sha256",)


@admin.register(EventTag)
class EventTagAdmin(admin.ModelAdmin):
    list_display = ("event", "tag")
    list_filter = ("tag__category",)
    search_fields = ("event__patient__user__username", "tag__name")


@admin.register(DocumentTag)
class DocumentTagAdmin(admin.ModelAdmin):
    list_display = ("document", "tag", "is_inherited")
    list_filter = ("is_inherited", "tag__category")
    search_fields = ("document__owner__username", "tag__name")


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


@admin.register(LabIndicator)
class LabIndicatorAdmin(admin.ModelAdmin):
    list_display = ("name", "unit", "reference_low", "reference_high")
    search_fields = ("name",)


@admin.register(LabTestMeasurement)
class LabTestMeasurementAdmin(admin.ModelAdmin):
    list_display = ("medical_event", "indicator", "value", "measured_at")
    list_filter = ("indicator", "measured_at")
    search_fields = ("medical_event__patient__user__username", "indicator__name")


@admin.register(ShareToken)
class ShareTokenAdmin(admin.ModelAdmin):
    list_display = ("document", "token", "created_at", "expires_at", "is_active")
    readonly_fields = ("token", "created_at")
