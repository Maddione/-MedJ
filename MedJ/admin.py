# MedJ/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
# Updated import: Removed BloodTestResult, added LabIndicator, BloodTestMeasurement
from .models import PatientProfile, Document, MedicalCategory, MedicalSpecialty, MedicalEvent, DocumentTag, Practitioner, NarrativeSectionResult, LabIndicator, BloodTestMeasurement


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'date_of_birth')
    search_fields = ('user__username',)

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'file_hash', 'uploaded_at', 'gpt_json_file')
    list_filter = ('uploaded_at',)
    search_fields = ('file_hash', 'patient__user__username')

@admin.register(MedicalCategory)
class MedicalCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(MedicalSpecialty)
class MedicalSpecialtyAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# Removed BloodTestResultAdmin
# @admin.register(BloodTestResult)
# class BloodTestResultAdmin(admin.ModelAdmin):
#     list_display = ('medical_event', 'indicator_name', 'value', 'unit', 'reference_range')
#     list_filter = ('medical_event__event_date', 'indicator_name')
#     search_fields = ('indicator_name', 'medical_event__patient__user__username')
#     raw_id_fields = ('medical_event',) # For better performance with many events

# New Admin registration for LabIndicator
@admin.register(LabIndicator)
class LabIndicatorAdmin(admin.ModelAdmin):
    list_display = ('patient', 'indicator_name', 'unit', 'reference_range')
    list_filter = ('patient', 'indicator_name', 'unit')
    search_fields = ('indicator_name', 'unit', 'patient__user__username')
    raw_id_fields = ('patient',) # Use raw_id_fields for ForeignKey to PatientProfile

# New Admin registration for BloodTestMeasurement
@admin.register(BloodTestMeasurement)
class BloodTestMeasurementAdmin(admin.ModelAdmin):
    list_display = ('medical_event', 'indicator', 'value')
    list_filter = ('medical_event__event_date', 'indicator__indicator_name', 'indicator__unit')
    search_fields = ('value', 'indicator__indicator_name', 'indicator__unit', 'medical_event__patient__user__username')
    raw_id_fields = ('medical_event', 'indicator') # Use raw_id_fields for ForeignKeys


@admin.register(Practitioner)
class PractitionerAdmin(admin.ModelAdmin):
    list_display = ('name', 'title', 'specialty')
    search_fields = ('name', 'specialty__name')
    # The 'medical_events' M2M field was removed from Practitioner model,
    # so filter_horizontal should also be removed or updated if a new M2M is added.
    # For now, commenting it out as it would cause an error.
    # filter_horizontal = ('medical_events',)


@admin.register(DocumentTag)
class DocumentTagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(NarrativeSectionResult)
class NarrativeSectionResultAdmin(admin.ModelAdmin):
    list_display = ('medical_event', 'section_title') # Changed 'title' to 'section_title' based on models.py
    search_fields = ('section_title', 'section_text', 'medical_event__patient__user__username') # Changed 'content' to 'section_text'
    raw_id_fields = ('medical_event',)

@admin.register(MedicalEvent)
class MedicalEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'event_type_title', 'category', 'specialty', 'event_date', 'summary_snippet', 'source_document', 'created_at')
    list_filter = ('event_type_title', 'category', 'specialty', 'event_date', 'created_at')
    search_fields = ('summary', 'patient__user__username', 'source_document__file_hash', 'tags__name', 'practitioners__name')
    date_hierarchy = 'event_date'
    raw_id_fields = ('patient', 'source_document')
    filter_horizontal = ('tags', 'practitioners')

    def summary_snippet(self, obj):
        return obj.summary[:50] + '...' if len(obj.summary) > 50 else obj.summary
    summary_snippet.short_description = 'Summary'

# Assuming CustomUserCreationForm handles email in registration.
# If User model is extended or has custom fields, ensure they are handled here.
# Otherwise, this class might not be strictly necessary if BaseUserAdmin is sufficient.
# No changes here for now.
# class UserAdmin(BaseUserAdmin):
#     list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
#     fieldsets = BaseUserAdmin.fieldsets + (
#         (None, {'fields': ('email',)}),
#     )