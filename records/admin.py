from django.contrib import admin
from parler.admin import TranslatableAdmin
from .models import (
    User,
    PatientProfile,
    MedicalCategory,
    MedicalSpecialty,
    DocumentType,
    Tag,
    PractitionerProfile,
    MedicalEvent,
    EventTag,
    Document,
    DocumentTag,
    NarrativeSectionResult,
    Diagnosis,
    TreatmentPlan,
    Medication,
    LabIndicator,
    LabTestMeasurement,
    ShareToken,
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "user_type", "is_staff", "is_active")
    list_filter = ("user_type", "is_staff", "is_active")
    search_fields = ("username", "email")


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "date_of_birth", "gender")
    search_fields = ("user__username", "user__email")


@admin.register(MedicalCategory)
class MedicalCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)


@admin.register(MedicalSpecialty)
class MedicalSpecialtyAdmin(TranslatableAdmin):
    list_display = ("name",)
    search_fields = ("translations__name",)


@admin.register(DocumentType)
class DocumentTypeAdmin(TranslatableAdmin):
    list_display = ("name", "slug", "is_active")
    list_editable = ("is_active",)
    search_fields = ("translations__name", "slug")



@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "category")
    list_filter = ("category",)
    search_fields = ("name",)


class EventTagInline(admin.TabularInline):
    model = EventTag
    extra = 0


@admin.register(PractitionerProfile)
class PractitionerProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "practitioner_type", "specialty")
    list_filter = ("practitioner_type", "specialty")
    search_fields = ("full_name",)


@admin.register(MedicalEvent)
class MedicalEventAdmin(admin.ModelAdmin):
    list_display = ("event_date", "patient", "specialty")
    list_filter = ("event_date", "specialty")
    search_fields = ("patient__user__username", "summary")
    date_hierarchy = "event_date"
    filter_horizontal = ("practitioners",)
    inlines = [EventTagInline]


class DocumentTagInline(admin.TabularInline):
    model = DocumentTag
    extra = 0


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "medical_event", "doc_type", "doc_kind", "document_date", "uploaded_at", "practitioner")
    list_filter = ("doc_kind", "doc_type")
    search_fields = ("medical_event__patient__user__username", "file")
    date_hierarchy = "document_date"
    inlines = [DocumentTagInline]


@admin.register(NarrativeSectionResult)
class NarrativeSectionResultAdmin(admin.ModelAdmin):
    list_display = ("medical_event", "section_title")
    search_fields = ("section_title", "section_content")


@admin.register(Diagnosis)
class DiagnosisAdmin(admin.ModelAdmin):
    list_display = ("medical_event", "diagnosis_text", "icd10_code", "diagnosed_at")
    search_fields = ("diagnosis_text", "icd10_code")
    date_hierarchy = "diagnosed_at"


@admin.register(TreatmentPlan)
class TreatmentPlanAdmin(admin.ModelAdmin):
    list_display = ("medical_event", "start_date", "end_date")
    search_fields = ("plan_text",)
    date_hierarchy = "start_date"


@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(LabIndicator)
class LabIndicatorAdmin(admin.ModelAdmin):
    list_display = ("code", "name_bg", "name_en", "default_unit")
    search_fields = ("code", "name_bg", "name_en")


@admin.register(LabTestMeasurement)
class LabTestMeasurementAdmin(admin.ModelAdmin):
    list_display = ("indicator", "event", "document", "measured_at", "value_si", "unit_si", "is_abnormal")
    list_filter = ("indicator", "is_abnormal")
    search_fields = ("event__patient__user__username", "document__file")
    date_hierarchy = "measured_at"

@admin.register(ShareToken)
class ShareTokenAdmin(admin.ModelAdmin):
    list_display = ("token", "scope", "patient", "expires_at", "is_active", "times_used")
    list_filter = ("scope", "is_active")
    search_fields = ("token",)

