from django.contrib import admin
from .models import (
    PatientProfile, MedicalCategory, MedicalSpecialty, DocumentType,
    Tag, MedicalEvent, EventTag, Document, DocumentTag,
    Diagnosis, NarrativeNote, Medication,
    LabIndicator, LabIndicatorAlias, LabTestMeasurement,
    ShareLink, OcrLog, Practitioner, DocumentPractitioner
)

@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "share_enabled", "share_token")
    search_fields = ("user__username", "user__email")

@admin.register(MedicalCategory)
class MedicalCategoryAdmin(admin.ModelAdmin):
    list_display = ("slug", "is_active", "order")
    list_filter = ("is_active",)
    search_fields = ("translations__name",)

@admin.register(MedicalSpecialty)
class MedicalSpecialtyAdmin(admin.ModelAdmin):
    list_display = ("slug", "is_active", "order")
    list_filter = ("is_active",)
    search_fields = ("translations__name",)

@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ("slug", "is_active", "order")
    list_filter = ("is_active",)
    search_fields = ("translations__name",)

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("slug", "kind", "is_active")
    list_filter = ("kind", "is_active")
    search_fields = ("slug", "translations__name")

@admin.register(MedicalEvent)
class MedicalEventAdmin(admin.ModelAdmin):
    list_display = ("id", "patient", "owner", "specialty", "category", "doc_type", "event_date", "created_at")
    list_filter = ("specialty", "category", "doc_type", "event_date")
    search_fields = ("patient__user__username",)

@admin.register(EventTag)
class EventTagAdmin(admin.ModelAdmin):
    list_display = ("event", "tag")
    list_filter = ("tag__kind",)

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "medical_event", "specialty", "category", "doc_type", "date_created", "uploaded_at", "doc_kind")
    list_filter = ("specialty", "category", "doc_type", "doc_kind", "uploaded_at")
    search_fields = ("id", "sha256")

@admin.register(DocumentTag)
class DocumentTagAdmin(admin.ModelAdmin):
    list_display = ("document", "tag", "is_inherited", "is_permanent")
    list_filter = ("is_inherited", "is_permanent", "tag__kind")

@admin.register(Diagnosis)
class DiagnosisAdmin(admin.ModelAdmin):
    list_display = ("medical_event", "code", "description")
    search_fields = ("code", "description")

@admin.register(NarrativeNote)
class NarrativeNoteAdmin(admin.ModelAdmin):
    list_display = ("medical_event", "title")

@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ("medical_event", "name", "dose", "frequency")

@admin.register(LabIndicator)
class LabIndicatorAdmin(admin.ModelAdmin):
    list_display = ("slug", "unit", "reference_low", "reference_high", "is_active")
    list_filter = ("is_active",)
    search_fields = ("slug", "translations__name")

@admin.register(LabIndicatorAlias)
class LabIndicatorAliasAdmin(admin.ModelAdmin):
    list_display = ("indicator", "alias", "alias_norm")
    search_fields = ("alias_raw", "normalized", "indicator__translations__name", "indicator__slug")

@admin.register(LabTestMeasurement)
class LabTestMeasurementAdmin(admin.ModelAdmin):
    list_display = ("medical_event", "indicator", "value", "measured_at")
    list_filter = ("indicator", "measured_at")

@admin.register(ShareLink)
class ShareLinkAdmin(admin.ModelAdmin):
    list_display = ("token", "owner", "object_type", "object_id", "format", "status", "expires_at", "created_at")
    list_filter = ("object_type", "format", "status")

@admin.register(OcrLog)
class OcrLogAdmin(admin.ModelAdmin):
    list_display = ("user", "document", "source", "duration_ms", "created_at")
    list_filter = ("source", "created_at")

@admin.register(Practitioner)
class PractitionerAdmin(admin.ModelAdmin):
    list_display = ("full_name", "specialty", "owner", "is_active", "created_at")
    list_filter = ("is_active", "specialty")
    search_fields = ("full_name", "owner__username")

@admin.register(DocumentPractitioner)
class DocumentPractitionerAdmin(admin.ModelAdmin):
    list_display = ("document", "practitioner", "role", "is_primary")
    list_filter = ("role", "is_primary")
    search_fields = ("document__id", "practitioner__full_name")
