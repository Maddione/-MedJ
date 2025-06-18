# MedJ/models.py

from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _


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
    gpt_json_file = models.FileField(upload_to='gpt_json_responses/', null=True, blank=True)

    def __str__(self):
        return f"Document {self.id} for {self.patient.user.username}"


class MedicalCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = _("Медицинска Категория")
        verbose_name_plural = _("Медицински Категории")

    def __str__(self):
        return self.name


class MedicalSpecialty(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = _("Медицинска Специалност")
        verbose_name_plural = _("Медицински Специалности")

    def __str__(self):
        return self.name


class MedicalEvent(models.Model):
    class EventType(models.TextChoices):
        EXAMINATION = 'EX', _('Преглед')
        LAB_TEST = 'LT', _('Лабораторни Изследвания')
        CONSULTATION = 'CO', _('Консултация')
        EPICRISIS = 'EP', _('Епикриза')
        PRESCRIPTION = 'PR', _('Рецепта')
        VACCINATION = 'VA', _('Ваксинация')
        HOSPITALIZATION = 'HO', _('Хоспитализация')
        OTHER = 'OT', _('Друго')

    patient = models.ForeignKey('PatientProfile', on_delete=models.CASCADE, related_name='medical_events')
    source_document = models.OneToOneField('Document', on_delete=models.SET_NULL, null=True, blank=True,
                                           related_name='medicalevent')
    event_type_title = models.CharField(max_length=2, choices=EventType.choices, default=EventType.OTHER)
    category = models.ForeignKey(MedicalCategory, on_delete=models.SET_NULL, null=True, blank=True,
                                 verbose_name=_("Категория"))
    specialty = models.ForeignKey(MedicalSpecialty, on_delete=models.SET_NULL, null=True, blank=True,
                                  verbose_name=_("Специалност"))
    event_date = models.DateField(null=True, blank=True, verbose_name=_("Дата на събитието"))
    summary = models.TextField(blank=True, verbose_name=_("Обобщение"))
    diagnosis = models.TextField(blank=True, verbose_name=_("Диагноза"))
    treatment_plan = models.TextField(blank=True, verbose_name=_("План за лечение"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tags = models.ManyToManyField('DocumentTag', blank=True, verbose_name=_("Тагове"))
    practitioners = models.ManyToManyField('Practitioner', related_name='events', blank=True,
                                           verbose_name=_("Практикуващи лекари"))

    class Meta:
        ordering = ['-event_date', '-created_at']
        verbose_name = _("Медицинско Събитие")
        verbose_name_plural = _("Медицински Събития")

    def __str__(self):
        return f"{self.get_event_type_title_display()} for {self.patient.user.username} on {self.event_date}"


class DocumentTag(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = _("Таг на Документ")
        verbose_name_plural = _("Тагове на Документи")

    def __str__(self):
        return self.name


# --- NEW MODELS FOR BLOOD TESTS ---

class LabIndicator(models.Model):
    """
    Дефинира уникален лабораторен показател (напр. "Хемоглобин", "Глюкоза").
    Всяка мерна единица за един и същ показател се третира като отделен запис тук.
    """
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='lab_indicators',
                                verbose_name=_("Пациент"))
    indicator_name = models.CharField(max_length=200, verbose_name=_("Име на показателя"))
    unit = models.CharField(max_length=50, blank=True, verbose_name=_("Мерна единица"))
    reference_range = models.CharField(max_length=100, blank=True, verbose_name=_("Референтни граници"))

    class Meta:
        # Един показател с една мерна единица е уникален за даден пациент
        unique_together = ('patient', 'indicator_name', 'unit')
        verbose_name = _("Лабораторен Показател")
        verbose_name_plural = _("Лабораторни Показатели")

    def __str__(self):
        return f"{self.indicator_name} ({self.unit if self.unit else _('Без мерна единица')})"


class BloodTestMeasurement(models.Model):
    """
    Представлява едно конкретно измерване на лабораторен показател.
    Свързан е с LabIndicator (за показателя) и MedicalEvent (за контекста/датата).
    """
    indicator = models.ForeignKey(LabIndicator, on_delete=models.CASCADE, related_name='measurements',
                                  verbose_name=_("Показател"))
    medical_event = models.ForeignKey(MedicalEvent, on_delete=models.CASCADE, related_name='blood_test_measurements',
                                      verbose_name=_("Медицинско събитие"))
    value = models.CharField(max_length=100, verbose_name=_("Стойност"))

    class Meta:
        # Един запис на измерване е уникален за дадено събитие и показател
        unique_together = ('medical_event', 'indicator')
        verbose_name = _("Измерване на Кръвен Резултат")
        verbose_name_plural = _("Измервания на Кръвни Резултати")
        ordering = ['-medical_event__event_date']  # За да можем да ги визуализираме хронологично

    def __str__(self):
        return f"{self.indicator.indicator_name}: {self.value} {self.indicator.unit} on {self.medical_event.event_date}"


# --- OLD BloodTestResult model is REMOVED/COMMENTED OUT ---
# class BloodTestResult(models.Model):
#     medical_event = models.ForeignKey(MedicalEvent, on_delete=models.CASCADE, related_name='blood_test_results')
#     indicator_name = models.CharField(max_length=200)
#     value = models.CharField(max_length=100)
#     unit = models.CharField(max_length=50)
#     reference_range = models.CharField(max_length=100, blank=True)
#     class Meta:
#         unique_together = ('medical_event', 'indicator_name', 'unit')
#     def __str__(self):
#         return f"{self.indicator_name}: {self.value} {self.unit}"


class NarrativeSectionResult(models.Model):
    medical_event = models.ForeignKey(MedicalEvent, on_delete=models.CASCADE, related_name='narrative_sections')
    section_title = models.CharField(max_length=200, verbose_name=_("Заглавие на секция"))
    section_text = models.TextField(verbose_name=_("Текст на секция"))

    class Meta:
        verbose_name = _("Резултат от Наративна Секция")
        verbose_name_plural = _("Резултати от Наративни Секции")

    def __str__(self):
        return f"{self.section_title} for {self.medical_event}"


class Practitioner(models.Model):
    name = models.CharField(max_length=200, verbose_name=_("Име"))
    title = models.CharField(max_length=50, blank=True, default='Д-р', verbose_name=_("Титла"))
    specialty = models.ForeignKey('MedicalSpecialty', on_delete=models.SET_NULL, null=True, blank=True,
                                  verbose_name=_("Специалност"))

    # medical_events = models.ManyToManyField('MedicalEvent', related_name='practitioners_for_event', blank=True) # This ManyToMany is managed from MedicalEvent
    class Meta:
        verbose_name = _("Практикуващ Лекар")
        verbose_name_plural = _("Практикуващи Лекари")

    def __str__(self):
        return f"{self.title} {self.name}"