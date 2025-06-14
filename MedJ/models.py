from django.contrib.auth.models import User
from django.db import models


# Общ таг – за категоризиране на събития, документи, лекари и др.
class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


# Профил на пациента – разширение на User
class PatientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Мъж'), ('female', 'Жена')], blank=True)
    height_cm = models.PositiveIntegerField(null=True, blank=True)
    weight_kg = models.PositiveIntegerField(null=True, blank=True)
    blood_group = models.CharField(max_length=5, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=200, blank=True)
    insurance_region = models.CharField(max_length=100, blank=True)
    personal_doctor = models.ForeignKey('Doctor', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Профил на {self.user.username}"


# Лекар, без потребителски акаунт
class Doctor(models.Model):
    name = models.CharField(max_length=100)
    specialty = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=200, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)

    def __str__(self):
        return f"{self.name} ({self.specialty})"


# Медицинско събитие – преглед, ваксинация, изследване и др.
class MedicalEvent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    title = models.CharField(max_length=200)
    category = models.ForeignKey(Tag, on_delete=models.SET_NULL, null=True, related_name='events')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.title} на {self.date.strftime('%d.%m.%Y')}"


# Качен файл – изображение или PDF
class MedicalDocument(models.Model):
    event = models.ForeignKey(MedicalEvent, on_delete=models.CASCADE, related_name='documents')

    file = models.FileField(upload_to='documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    extracted_text = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    html_content = models.TextField(blank=True, null=True, verbose_name="HTML съдържание")
    json_content = models.JSONField(blank=True, null=True, verbose_name="JSON данни")

    # --- НОВО ПОЛЕ ЗА ЗАСИЧАНЕ НА ДУБЛИКАТИ ---
    file_hash = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        db_index=True,
        help_text="SHA-256 hash of the file content"
    )

    def __str__(self):
        return f"Документ за {self.event.title}"


# Кръвна стойност от изследване
class BloodTestResult(models.Model):
    document = models.ForeignKey(MedicalDocument, on_delete=models.CASCADE, related_name='blood_results')
    parameter = models.CharField(max_length=100)
    value = models.FloatField()
    unit = models.CharField(max_length=20, blank=True)
    reference_range = models.CharField(max_length=100, blank=True)
    measured_at = models.DateField()

    def __str__(self):
        return f"{self.parameter} = {self.value} {self.unit}"


# Предстоящо назначение (видимо в Табло)
class UpcomingAppointment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField()
    notes = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"Преглед при {self.doctor} на {self.date}"


# Рецепта с лекарство и срок
class Prescription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    medicine_name = models.CharField(max_length=100)
    dose = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return f"{self.medicine_name} ({self.dose})"
