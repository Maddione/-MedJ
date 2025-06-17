from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import PatientProfile, Document, MedicalCategory, MedicalSpecialty, MedicalEvent, DocumentTag, BloodTestResult, Practitioner, NarrativeSectionResult

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

@admin.register(BloodTestResult)
class BloodTestResultAdmin(admin.ModelAdmin):
    list_display = ('medical_event', 'indicator_name', 'value', 'unit', 'reference_range')
    list_filter = ('medical_event__event_date', 'indicator_name')
    search_fields = ('indicator_name', 'medical_event__patient__user__username')
    raw_id_fields = ('medical_event',) # For better performance with many events

@admin.register(Practitioner)
class PractitionerAdmin(admin.ModelAdmin):
    list_display = ('name', 'title', 'specialty')
    search_fields = ('name', 'specialty__name')
    filter_horizontal = ('medical_events',) # For ManyToMany

@admin.register(DocumentTag)
class DocumentTagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(NarrativeSectionResult)
class NarrativeSectionResultAdmin(admin.ModelAdmin):
    list_display = ('medical_event', 'title')
    search_fields = ('title', 'content', 'medical_event__patient__user__username')
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

class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    fieldsets = BaseUserAdmin.fieldsets + (
        (None, {'fields': ('email',)}),
    )
