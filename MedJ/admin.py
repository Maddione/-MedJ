# MedJ/admin.py
from django.contrib import admin
from .models import (
    PatientProfile,
    Document,
    MedicalCategory,
    MedicalSpecialty,
    Practitioner,
    MedicalEvent,
    BloodTestResult,
    NarrativeSectionResult,
    DocumentTag
)


# Инлайн администратори, за да виждаме резултатите в страницата на събитието
class BloodTestResultInline(admin.TabularInline):
    model = BloodTestResult
    extra = 1  # Показва 1 празен ред за добавяне


class NarrativeSectionResultInline(admin.TabularInline):
    model = NarrativeSectionResult
    extra = 1


@admin.register(MedicalEvent)
class MedicalEventAdmin(admin.ModelAdmin):
    # Коригиран list_display: премахнахме 'specialty' и добавихме 'category'
    list_display = ('event_date', 'patient', 'get_event_type_title_display', 'category', 'created_at')

    # Коригиран list_filter: премахнахме 'specialty' и добавихме 'category'
    list_filter = ('event_type_title', 'category', 'event_date')

    search_fields = ('summary', 'patient__user__username')
    date_hierarchy = 'event_date'

    # Добавяме инлайн формите за свързаните резултати
    inlines = [BloodTestResultInline, NarrativeSectionResultInline]

    # Позволява лесно добавяне на тагове и лекари
    filter_horizontal = ('tags', 'practitioners')

    # Помощна функция за показване на пълното име на типа събитие
    def get_event_type_title_display(self, obj):
        return obj.get_event_type_title_display()

    get_event_type_title_display.short_description = 'Тип на събитието'


# Регистрираме и останалите модели, за да са достъпни в админ панела
@admin.register(Practitioner)
class PractitionerAdmin(admin.ModelAdmin):
    list_display = ('name', 'title', 'specialty')
    search_fields = ('name',)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'uploaded_at')
    search_fields = ('patient__user__username',)


# Проста регистрация за останалите модели
admin.site.register(PatientProfile)
admin.site.register(MedicalCategory)
admin.site.register(MedicalSpecialty)
admin.site.register(DocumentTag)