from __future__ import annotations
import hashlib
import uuid
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models, transaction
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _l
from parler.models import TranslatableModel, TranslatedFields


class User(AbstractUser):
    USER_TYPES = (("patient", "Patient"),)
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default="patient")
    def __str__(self) -> str:
        return self.username


class PatientProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="patientprofile")
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    phone_number = models.CharField(max_length=64, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    blood_type = models.CharField(max_length=8, null=True, blank=True)
    def __str__(self) -> str:
        return f"Profile of {self.user.username}"


class MedicalCategory(TranslatableModel):
    translations = TranslatedFields(
        name=models.CharField(max_length=255, unique=True, verbose_name=_l("Category Name")),
        description=models.TextField(blank=True, null=True, verbose_name=_l("Description")),
    )
    slug = models.SlugField(max_length=255, unique=True, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    def __str__(self) -> str:
        return self.safe_translation_getter("name", any_language=True) or "Unnamed Category"
    class Meta:
        verbose_name = _l("Medical Category")
        verbose_name_plural = _l("Medical Categories")


class MedicalSpecialty(TranslatableModel):
    translations = TranslatedFields(
        name=models.CharField(max_length=255, unique=True, verbose_name=_l("Specialty Name")),
        description=models.TextField(blank=True, null=True, verbose_name=_l("Description")),
    )
    is_active = models.BooleanField(default=True, verbose_name=_l("Is Active"))
    def __str__(self) -> str:
        return self.safe_translation_getter("name", any_language=True) or "Unnamed Specialty"
    class Meta:
        verbose_name = _l("Medical Specialty")
        verbose_name_plural = _l("Medical Specialties")


class DocumentType(TranslatableModel):
    translations = TranslatedFields(
        name=models.CharField(max_length=255, unique=True, verbose_name=_l("Document Type Name")),
        description=models.TextField(blank=True, null=True, verbose_name=_l("Description")),
    )
    slug = models.SlugField(max_length=255, unique=True, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    def __str__(self) -> str:
        return self.safe_translation_getter("name", any_language=True) or "Unnamed Type"
    class Meta:
        verbose_name = _l("Document Type")
        verbose_name_plural = _l("Document Types")


class Tag(models.Model):
    CATEGORY_CHOICES = (
        ("specialty", "Specialty"),
        ("test_type", "Test Type"),
        ("doctor", "Doctor"),
        ("time", "Time"),
    )
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, db_index=True)
    def __str__(self) -> str:
        return self.name


class MedicalEvent(models.Model):
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name="medical_events")
    specialty = models.ForeignKey(MedicalSpecialty, on_delete=models.SET_NULL, null=True, blank=True)
    event_date = models.DateField()
    summary = models.TextField(blank=True, null=True)
    tags = models.ManyToManyField(Tag, through="EventTag", related_name="medical_events")
    def __str__(self) -> str:
        spec = self.specialty or "-"
        return f"{spec} event for {self.patient.user.username} on {self.event_date}"
    class Meta:
        indexes = [
            models.Index(fields=["patient", "event_date"]),
        ]
        ordering = ["-event_date", "id"]


class EventTag(models.Model):
    event = models.ForeignKey(MedicalEvent, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    class Meta:
        unique_together = ("event", "tag")


class Document(models.Model):
    KIND_CHOICES = (("image", "Image"), ("pdf", "PDF"), ("other", "Other"))
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    medical_event = models.ForeignKey(MedicalEvent, on_delete=models.CASCADE, related_name="documents")
    doc_type = models.ForeignKey(DocumentType, on_delete=models.PROTECT)
    document_date = models.DateField()
    file = models.FileField(upload_to="documents/", validators=[FileExtensionValidator(allowed_extensions=["pdf", "png", "jpg", "jpeg"])])
    doc_kind = models.CharField(max_length=16, choices=KIND_CHOICES, default="pdf")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    summary = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    original_ocr_text = models.TextField(blank=True, null=True)
    sha256 = models.CharField(max_length=64, db_index=True, blank=True)
    tags = models.ManyToManyField(Tag, through="DocumentTag", blank=True)
    class Meta:
        ordering = ["-document_date", "-uploaded_at"]
        indexes = [
            models.Index(fields=["owner", "uploaded_at"]),
            models.Index(fields=["document_date"]),
        ]
    def __str__(self):
        return f"Document<{self.pk} - {self.file.name}>"
    def compute_sha256(self):
        if not self.file:
            return None
        h = hashlib.sha256()
        self.file.open()
        for chunk in self.file.chunks():
            h.update(chunk)
        self.file.close()
        return h.hexdigest()


class DocumentTag(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    is_inherited = models.BooleanField(default=False)
    class Meta:
        unique_together = ("document", "tag")


class DocumentShare(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    def is_expired(self) -> bool:
        return self.expires_at < timezone.now()


class ShareToken(DocumentShare):
    class Meta:
        proxy = True
        verbose_name = _l("Share Token")
        verbose_name_plural = _l("Share Tokens")


class Diagnosis(models.Model):
    medical_event = models.ForeignKey(MedicalEvent, on_delete=models.CASCADE, related_name="diagnoses")
    code = models.CharField(max_length=32, blank=True, null=True)
    text = models.TextField()
    diagnosed_at = models.DateField(null=True, blank=True)
    def __str__(self) -> str:
        return self.code or self.text[:50]


class TreatmentPlan(models.Model):
    medical_event = models.ForeignKey(MedicalEvent, on_delete=models.CASCADE, related_name="treatment_plans")
    plan_text = models.TextField()
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    def __str__(self) -> str:
        return f"Plan for event {self.medical_event_id}"


class NarrativeSectionResult(models.Model):
    medical_event = models.ForeignKey(MedicalEvent, on_delete=models.CASCADE, related_name="narrative_sections")
    title = models.CharField(max_length=255)
    content = models.TextField()
    def __str__(self) -> str:
        return self.title


class Medication(models.Model):
    medical_event = models.ForeignKey(MedicalEvent, on_delete=models.CASCADE, related_name="medications")
    name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=255, blank=True, null=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    def __str__(self) -> str:
        return self.name


class LabIndicator(models.Model):
    name = models.CharField(max_length=255, unique=True)
    unit = models.CharField(max_length=64, blank=True, null=True)
    reference_low = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    reference_high = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    def __str__(self) -> str:
        return self.name


class LabTestMeasurement(models.Model):
    medical_event = models.ForeignKey(MedicalEvent, on_delete=models.CASCADE, related_name="lab_measurements")
    indicator = models.ForeignKey(LabIndicator, on_delete=models.CASCADE, related_name="measurements")
    value = models.DecimalField(max_digits=12, decimal_places=4, validators=[MinValueValidator(Decimal("0"))])
    measured_at = models.DateField(null=True, blank=True)
    def __str__(self) -> str:
        return f"{self.indicator.name}: {self.value}"
    @property
    def is_abnormal(self) -> bool:
        if self.indicator.reference_low is not None and self.value < self.indicator.reference_low:
            return True
        if self.indicator.reference_high is not None and self.value > self.indicator.reference_high:
            return True
        return False


class UiLabel(TranslatableModel):
    slug = models.SlugField(max_length=255, unique=True)
    translations = TranslatedFields(
        text=models.CharField(max_length=1024, verbose_name=_l("Text")),
    )
    def __str__(self) -> str:
        return self.slug


@receiver(post_save, sender=Document)
def _document_post_save(sender, instance: Document, created, **kwargs):
    if not created:
        return
    with transaction.atomic():
        if not instance.sha256:
            try:
                h = hashlib.sha256()
                instance.file.open("rb")
                for chunk in iter(lambda: instance.file.read(4096), b""):
                    h.update(chunk)
                instance.file.close()
                instance.sha256 = h.hexdigest()
                Document.objects.filter(pk=instance.pk).update(sha256=instance.sha256)
            except Exception:
                pass
    event_tag_ids = EventTag.objects.filter(event=instance.medical_event).values_list("tag_id", flat=True)
    bulk = []
    for tag_id in event_tag_ids:
        if not DocumentTag.objects.filter(document=instance, tag_id=tag_id).exists():
            bulk.append(DocumentTag(document=instance, tag_id=tag_id, is_inherited=True))
    if bulk:
        DocumentTag.objects.bulk_create(bulk)


@receiver(m2m_changed, sender=MedicalEvent.tags.through)
def _event_tags_changed(sender, instance, action, reverse, model, pk_set, **kwargs):
    if reverse or not pk_set:
        return
    if not isinstance(instance, MedicalEvent):
        return
    doc_qs = instance.documents.all().only("id")
    tag_ids = list(pk_set)
    if action == "post_add":
        bulk = []
        for doc in doc_qs:
            existing = set(
                DocumentTag.objects.filter(document=doc, tag_id__in=tag_ids).values_list("tag_id", flat=True)
            )
            for tag_id in tag_ids:
                if tag_id not in existing:
                    bulk.append(DocumentTag(document=doc, tag_id=tag_id, is_inherited=True))
        if bulk:
            DocumentTag.objects.bulk_create(bulk)
    elif action == "post_remove":
        for doc in doc_qs:
            DocumentTag.objects.filter(document=doc, tag_id__in=tag_ids, is_inherited=True).delete()
