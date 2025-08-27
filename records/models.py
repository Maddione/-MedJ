from __future__ import annotations

import hashlib
import json
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
from django.db import models, transaction
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver
from parler.models import TranslatableModel, TranslatedFields
import uuid
from django.utils import timezone


class User(AbstractUser):
    USER_TYPES = (
        ("patient", "Patient"),
        ("practitioner", "Practitioner"),
    )
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default="patient")

    def __str__(self):
        return self.username


class PatientProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    phone_number = models.CharField(max_length=64, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    blood_type = models.CharField(max_length=8, null=True, blank=True)

    def __str__(self):
        return f"PatientProfile<{self.user}>"


class PractitionerProfile(models.Model):
    PRACTITIONER_TYPES = (
        ("physician", "Physician"),
        ("nurse", "Nurse"),
        ("other", "Other"),
    )
    full_name = models.CharField(max_length=255)
    practitioner_type = models.CharField(max_length=20, choices=PRACTITIONER_TYPES, default="physician")
    specialty = models.ForeignKey("MedicalSpecialty", null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.full_name


class MedicalCategory(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Medical Category"
        verbose_name_plural = "Medical Categories"

    def __str__(self):
        return self.name


class MedicalSpecialty(TranslatableModel):
    translations = TranslatedFields(
        name=models.CharField(max_length=255),
        description=models.TextField(blank=True, null=True),
    )

    class Meta:
        verbose_name = "Medical Specialty"
        verbose_name_plural = "Medical Specialties"

    def __str__(self):
        return self.safe_translation_getter("name", any_language=True) or f"Specialty {self.pk}"


class DocumentType(TranslatableModel):
    slug = models.SlugField(max_length=255, unique=True)
    translations = TranslatedFields(
        name=models.CharField(max_length=255),
        description=models.TextField(blank=True, null=True),
        icon=models.CharField(max_length=64, blank=True, null=True),
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Document Type"
        verbose_name_plural = "Document Types"

    def __str__(self):
        return self.safe_translation_getter("name", any_language=True) or self.slug


class Tag(models.Model):
    CATEGORY_CHOICES = (
        ("generic", "Generic"),
        ("specialty", "Specialty"),
        ("doctor", "Doctor"),
        ("medication", "Medication"),
        ("auto", "Auto"),
        ("manual", "Manual"),
    )
    name = models.CharField(max_length=255, unique=True)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, default="generic")

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"

    def __str__(self):
        return f"#{self.name}"


class MedicalEvent(models.Model):
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE)
    specialty = models.ForeignKey(MedicalSpecialty, on_delete=models.PROTECT)
    event_date = models.DateField()
    summary = models.TextField(blank=True, null=True)
    practitioners = models.ManyToManyField(PractitionerProfile, blank=True)
    tags = models.ManyToManyField(Tag, through="EventTag", blank=True)

    class Meta:
        ordering = ["-event_date"]

    def __str__(self):
        name = self.specialty.safe_translation_getter("name", any_language=True)
        return f"Event<{self.patient.user.username}, {name}, {self.event_date:%Y-%m-%d}>"


class EventTag(models.Model):
    event = models.ForeignKey(MedicalEvent, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)


class Document(models.Model):
    KIND_CHOICES = (
        ("image", "Image"),
        ("pdf", "PDF"),
        ("other", "Other"),
    )
    medical_event = models.ForeignKey(MedicalEvent, on_delete=models.CASCADE, related_name="documents")
    doc_type = models.ForeignKey(DocumentType, on_delete=models.PROTECT)
    document_date = models.DateField()
    file = models.FileField(
        upload_to="documents/",
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "png", "jpg", "jpeg"])],
    )
    doc_kind = models.CharField(max_length=16, choices=KIND_CHOICES, default="pdf")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    practitioner = models.ForeignKey(PractitionerProfile, null=True, blank=True, on_delete=models.SET_NULL)
    original_ocr_text = models.TextField(blank=True, null=True)
    sha256 = models.CharField(max_length=64, db_index=True, blank=True)
    tags = models.ManyToManyField(Tag, through="DocumentTag", blank=True)

    class Meta:
        ordering = ["-document_date", "-uploaded_at"]

    def __str__(self):
        return f"Document<{self.pk} - {self.file.name}>"

    def compute_sha256(self):
        if not self.file:
            return None
        h = hashlib.sha256()
        for chunk in self.file.chunks():
            h.update(chunk)
        return h.hexdigest()


class DocumentTag(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    is_inherited = models.BooleanField(default=False)
    added_at = models.DateTimeField(auto_now_add=True)


class Diagnosis(models.Model):
    medical_event = models.ForeignKey(MedicalEvent, on_delete=models.CASCADE, related_name="diagnoses")
    diagnosis_text = models.TextField()
    icd10_code = models.CharField(max_length=16, blank=True, null=True)
    diagnosed_at = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.diagnosis_text[:40]


class TreatmentPlan(models.Model):
    medical_event = models.ForeignKey(MedicalEvent, on_delete=models.CASCADE, related_name="treatment_plans")
    plan_text = models.TextField()
    medications_list = models.TextField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)


class NarrativeSectionResult(models.Model):
    medical_event = models.ForeignKey(MedicalEvent, on_delete=models.CASCADE, related_name="narrative_sections")
    section_title = models.CharField(max_length=255)
    section_content = models.TextField()


class Medication(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class LabIndicator(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name_bg = models.CharField(max_length=255, blank=True, null=True)
    name_en = models.CharField(max_length=255, blank=True, null=True)
    aliases_json = models.TextField(blank=True, null=True)
    default_unit = models.CharField(max_length=32, blank=True, null=True)
    default_ref_low = models.FloatField(blank=True, null=True)
    default_ref_high = models.FloatField(blank=True, null=True)
    ref_notes = models.TextField(blank=True, null=True)

    def aliases(self) -> list[str]:
        if not self.aliases_json:
            return []
        try:
            return json.loads(self.aliases_json)
        except Exception:
            return []

    def __str__(self):
        return self.code


class LabTestMeasurement(models.Model):
    REF_SOURCES = (
        ("document", "From Document"),
        ("patient", "From Patient Profile"),
        ("indicator_default", "Indicator Default"),
        ("lab_profile", "Lab Profile"),
    )
    event = models.ForeignKey(MedicalEvent, on_delete=models.CASCADE, related_name="lab_measurements")
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="lab_measurements")
    indicator = models.ForeignKey(LabIndicator, on_delete=models.PROTECT, related_name="measurements")
    measured_at = models.DateField()
    value_raw = models.CharField(max_length=64, blank=True, null=True)
    unit_raw = models.CharField(max_length=32, blank=True, null=True)
    value_si = models.FloatField(blank=True, null=True)
    unit_si = models.CharField(max_length=32, blank=True, null=True)
    ref_low_si = models.FloatField(blank=True, null=True)
    ref_high_si = models.FloatField(blank=True, null=True)
    ref_source = models.CharField(max_length=32, choices=REF_SOURCES, default="indicator_default")
    is_abnormal = models.BooleanField(null=True)
    source_row_json = models.TextField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["event", "measured_at"]),
            models.Index(fields=["indicator", "measured_at"]),
            models.Index(fields=["is_abnormal"]),
        ]
        ordering = ["-measured_at", "-id"]


@receiver(post_save, sender=Document)
def _document_post_save(sender, instance: Document, created, **kwargs):
    if created:
        if not instance.sha256 and instance.file:
            try:
                instance.sha256 = instance.compute_sha256()
                Document.objects.filter(pk=instance.pk).update(sha256=instance.sha256)
            except Exception:
                pass
        if instance.practitioner_id:
            instance.medical_event.practitioners.add(instance.practitioner_id)
        event_tag_ids = EventTag.objects.filter(event=instance.medical_event).values_list("tag_id", flat=True)
        bulk = []
        for tag_id in event_tag_ids:
            if not DocumentTag.objects.filter(document=instance, tag_id=tag_id).exists():
                bulk.append(DocumentTag(document=instance, tag_id=tag_id, is_inherited=True))
        if bulk:
            DocumentTag.objects.bulk_create(bulk)


@receiver(post_delete, sender=Document)
def _document_post_delete(sender, instance: Document, **kwargs):
    if instance.practitioner_id:
        still_used = Document.objects.filter(
            medical_event=instance.medical_event,
            practitioner=instance.practitioner_id
        ).exists()
        if not still_used:
            instance.medical_event.practitioners.remove(instance.practitioner_id)


@receiver(m2m_changed, sender=EventTag)
def _event_tags_changed(sender, instance, action, reverse, model, pk_set, **kwargs):
    if action not in {"post_add", "post_remove"} or reverse or not pk_set:
        return
    if not isinstance(instance, MedicalEvent):
        return
    doc_qs = instance.documents.all().only("id")
    tag_ids = list(pk_set)
    if action == "post_add":
        bulk = []
        for doc in doc_qs:
            existing = set(DocumentTag.objects.filter(document=doc, tag_id__in=tag_ids).values_list("tag_id", flat=True))
            for tag_id in tag_ids:
                if tag_id not in existing:
                    bulk.append(DocumentTag(document=doc, tag_id=tag_id, is_inherited=True))
        if bulk:
            DocumentTag.objects.bulk_create(bulk)
    elif action == "post_remove":
        for doc in doc_qs:
            DocumentTag.objects.filter(document=doc, tag_id__in=tag_ids, is_inherited=True).delete()

class ShareToken(models.Model):
    SCOPE_CHOICES = (
        ("document", "Document"),
        ("event", "Event"),
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    scope = models.CharField(max_length=16, choices=SCOPE_CHOICES)
    document = models.ForeignKey("Document", null=True, blank=True, on_delete=models.CASCADE, related_name="share_tokens")
    event = models.ForeignKey("MedicalEvent", null=True, blank=True, on_delete=models.CASCADE, related_name="share_tokens")
    patient = models.ForeignKey("PatientProfile", on_delete=models.CASCADE, related_name="share_tokens")
    allow_download = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    times_used = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["token"]),
            models.Index(fields=["scope", "is_active"]),
            models.Index(fields=["expires_at"]),
        ]

    def is_valid(self):
        return self.is_active and timezone.now() < self.expires_at

    def __str__(self):
        return f"{self.scope}:{self.token}"
