from django.contrib import admin
from parler.admin import TranslatableAdmin
from .models import (
    User, PatientProfile, MedicalCategory,
    MedicalSpecialty, DocumentType, Tag, MedicalEvent, EventTag,
    Document, DocumentTag, Diagnosis, TreatmentPlan, NarrativeSectionResult,
    Medication, LabIndicator, LabTestMeasurement, ShareToken, UiLabel
)

admin.site.register(User)
admin.site.register(PatientProfile)
admin.site.register(MedicalCategory)
admin.site.register(Tag)
admin.site.register(MedicalEvent)
admin.site.register(EventTag)
admin.site.register(Document)
admin.site.register(DocumentTag)
admin.site.register(Diagnosis)
admin.site.register(TreatmentPlan)
admin.site.register(NarrativeSectionResult)
admin.site.register(Medication)
admin.site.register(LabIndicator)
admin.site.register(LabTestMeasurement)
admin.site.register(ShareToken)


@admin.register(MedicalSpecialty)
class MedicalSpecialtyAdmin(TranslatableAdmin):
    list_display = ('name',)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('translations')


@admin.register(DocumentType)
class DocumentTypeAdmin(TranslatableAdmin):
    list_display = ('name', 'slug', 'is_active')

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('translations')


@admin.register(UiLabel)
class UiLabelAdmin(TranslatableAdmin):
    list_display = ('slug', 'text')

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('translations')