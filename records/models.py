from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from parler.models import TranslatableModel, TranslatedFields
from django.db import models
from django.contrib.auth.models import User
import secrets


class User(AbstractUser):
    email = models.EmailField(_("email address"), unique=True, blank=True, null=True)
    phone = models.CharField(max_length=32, blank=True, null=True)
    email_verified = models.BooleanField(default=False)

class PatientProfile(models.Model):
    GENDER_CHOICES = (("m", _("Мъж")), ("f", _("Жена")), ("o", _("Друг")))
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="patient_profile")
    first_name_bg = models.CharField(max_length=120)
    middle_name_bg = models.CharField(max_length=120, blank=True, null=True)
    last_name_bg = models.CharField(max_length=120)
    first_name_en = models.CharField(max_length=120, blank=True, null=True)
    middle_name_en = models.CharField(max_length=120, blank=True, null=True)
    last_name_en = models.CharField(max_length=120, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    phone_number = models.CharField(max_length=64, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    blood_type = models.CharField(max_length=8, blank=True, null=True)
    share_token = models.CharField(max_length=64, unique=True, blank=True, null=True)
    share_enabled = models.BooleanField(default=False)

    def full_name(self, language_code="bg"):
        if language_code and language_code.lower().startswith("en") and self.first_name_en and self.last_name_en:
            parts = [self.first_name_en, self.middle_name_en or "", self.last_name_en]
        else:
            parts = [self.first_name_bg, self.middle_name_bg or "", self.last_name_bg]
        return " ".join([p for p in parts if p])
    def __str__(self):
        return self.full_name()

    def ensure_share_token(self):
        if not self.share_token:
            self.share_token = secrets.token_urlsafe(20)

class MedicalCategory(TranslatableModel):
    translations = TranslatedFields(
        name=models.CharField(max_length=255, unique=True, verbose_name=_("Category Name")),
        description=models.TextField(blank=True, null=True, verbose_name=_("Description")),
    )
    slug = models.SlugField(max_length=255, unique=True, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    def __str__(self):
        return self.safe_translation_getter("name", any_language=True) or "Unnamed Category"
    def save(self, *args, **kwargs):
        if not self.slug:
            base = self.safe_translation_getter("name", any_language=True) or ""
            self.slug = slugify(base)[:255] or None
        super().save(*args, **kwargs)
    class Meta:
        verbose_name = _("Medical Category")
        verbose_name_plural = _("Medical Categories")
        ordering = ("order", "id")

class MedicalSpecialty(TranslatableModel):
    translations = TranslatedFields(
        name=models.CharField(max_length=255, unique=True, verbose_name=_("Specialty Name")),
        description=models.TextField(blank=True, null=True, verbose_name=_("Description")),
    )
    slug = models.SlugField(max_length=255, unique=True, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.slug:
            name = self.safe_translation_getter("name", any_language=True) or ""
            self.slug = slugify(name)[:255] or None
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.safe_translation_getter("name", any_language=True) or "Unnamed Specialty"

    class Meta:
        verbose_name = _("Medical Specialty")
        verbose_name_plural = _("Medical Specialties")
        ordering = ("order", "id")

class DocumentType(TranslatableModel):
    translations = TranslatedFields(
        name=models.CharField(max_length=255, unique=True, verbose_name=_("Document Type Name")),
        description=models.TextField(blank=True, null=True, verbose_name=_("Description")),
    )
    slug = models.SlugField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return self.safe_translation_getter("name", any_language=True)

class TagKind(models.TextChoices):
    SPECIALTY = "specialty", _("Специалност")
    CATEGORY = "category", _("Категория")
    DOC_TYPE = "doc_type", _("Вид документ")
    INDICATOR = "indicator", _("Лабораторен показател")
    DOCTOR = "doctor", _("Доктор")
    TIME = "time", _("Време")
    DOC_KIND = "doc_kind", _("Тип съдържание")
    FILE_TYPE = "file_type", _("Файлов тип")
    SYSTEM = "system", _("Системен")

class Tag(TranslatableModel):
    translations = TranslatedFields(name=models.CharField(max_length=255, verbose_name=_("Name")))
    slug = models.SlugField(max_length=255, unique=True)
    kind = models.CharField(max_length=32, choices=TagKind.choices, default=TagKind.SYSTEM)
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return self.safe_translation_getter("name", any_language=True)

class MedicalEvent(models.Model):
    patient = models.ForeignKey("records.PatientProfile", on_delete=models.CASCADE, related_name="events")
    specialty = models.ForeignKey("records.MedicalSpecialty", on_delete=models.PROTECT, related_name="events")
    event_date = models.DateField()
    summary = models.CharField(max_length=255, blank=True, null=True)
    tags = models.ManyToManyField("records.Tag", through="records.EventTag", related_name="events", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.patient} · {self.event_date}"

class EventTag(models.Model):
    event = models.ForeignKey("records.MedicalEvent", on_delete=models.CASCADE)
    tag = models.ForeignKey("records.Tag", on_delete=models.CASCADE)
    class Meta:
        unique_together = ("event", "tag")

class Document(models.Model):
    DOC_KIND_CHOICES = (("image", "image"), ("pdf", "pdf"), ("other", "other"))
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="documents")
    medical_event = models.ForeignKey("records.MedicalEvent", on_delete=models.CASCADE, related_name="documents", blank=True, null=True)
    specialty = models.ForeignKey("records.MedicalSpecialty", on_delete=models.PROTECT, related_name="documents")
    category = models.ForeignKey("records.MedicalCategory", on_delete=models.PROTECT, related_name="documents")
    doc_type = models.ForeignKey("records.DocumentType", on_delete=models.PROTECT, related_name="documents")
    document_date = models.DateField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to="documents/", validators=[FileExtensionValidator(["pdf", "png", "jpg", "jpeg"])])
    doc_kind = models.CharField(max_length=16, choices=DOC_KIND_CHOICES, default="other")
    file_mime = models.CharField(max_length=120, blank=True, null=True)
    summary = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    original_ocr_text = models.TextField(blank=True, null=True)
    sha256 = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    tags = models.ManyToManyField("records.Tag", through="records.DocumentTag", related_name="documents", blank=True)
    def __str__(self):
        return f"{self.id}"
    def save(self, *args, **kwargs):
        creating = self._state.adding
        if creating and not self.medical_event_id and hasattr(self.owner, "patient_profile"):
            event_date = self.document_date or timezone.now().date()
            self.medical_event = MedicalEvent.objects.create(
                patient=self.owner.patient_profile,
                specialty=self.specialty,
                event_date=event_date,
            )
        super().save(*args, **kwargs)

class DocumentTag(models.Model):
    document = models.ForeignKey("records.Document", on_delete=models.CASCADE)
    tag = models.ForeignKey("records.Tag", on_delete=models.CASCADE)
    is_inherited = models.BooleanField(default=False)
    class Meta:
        unique_together = ("document", "tag")

class DocumentShare(models.Model):
    document = models.ForeignKey("records.Document", on_delete=models.CASCADE, related_name="shares")
    token = models.UUIDField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    def is_expired(self):
        return bool(self.expires_at and timezone.now() > self.expires_at)

class ShareToken(DocumentShare):
    class Meta:
        proxy = True

class Diagnosis(models.Model):
    medical_event = models.ForeignKey("records.MedicalEvent", on_delete=models.CASCADE, related_name="diagnoses")
    code = models.CharField(max_length=64)
    text = models.TextField(blank=True, null=True)
    diagnosed_at = models.DateTimeField(blank=True, null=True)

class TreatmentPlan(models.Model):
    medical_event = models.ForeignKey("records.MedicalEvent", on_delete=models.CASCADE, related_name="treatments")
    plan_text = models.TextField()
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

class NarrativeSectionResult(models.Model):
    medical_event = models.ForeignKey("records.MedicalEvent", on_delete=models.CASCADE, related_name="narratives")
    title = models.CharField(max_length=255)
    content = models.TextField()

class Medication(models.Model):
    medical_event = models.ForeignKey("records.MedicalEvent", on_delete=models.CASCADE, related_name="medications")
    name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=255, blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

class LabIndicator(TranslatableModel):
    translations = TranslatedFields(
        name=models.CharField(max_length=255, verbose_name=_("Indicator Name"))
    )
    slug = models.SlugField(max_length=255, unique=True)
    unit = models.CharField(max_length=64, blank=True, null=True)
    reference_low = models.FloatField(blank=True, null=True)
    reference_high = models.FloatField(blank=True, null=True)
    def __str__(self):
        return self.safe_translation_getter("name", any_language=True)

        def save(self, *args, **kwargs):

            if not self.slug:
                try:
                    base = self.safe_translation_getter("name", any_language=True) or ""
                except Exception:
                    base = ""

                from django.utils.text import slugify as _slugify
                from uuid import uuid4 as _uuid4
                self.slug = (_slugify(base)[:255] if base else f"indicator-{_uuid4().hex[:12]}")
            creating = not self.pk or self._state.adding

            super().save(*args, **kwargs)

            try:
                base2 = self.safe_translation_getter("name", any_language=True) or ""
            except Exception:
                base2 = ""
            if base2:
                from django.utils.text import slugify as _slugify2
                final = _slugify2(base2)[:255]
                if final and self.slug != final:
                    self.slug = final
                    super().save(update_fields=["slug"])

    @classmethod
    def resolve(cls, label):
        q = (label or "").strip()
        if not q:
            return None
        obj = cls.objects.filter(translations__name__iexact=q).first()
        if obj:
            return obj
        obj = cls.objects.filter(slug=slugify(q)).first()
        if obj:
            return obj
        alias = LabIndicatorAlias.objects.filter(alias_norm=slugify(q)).select_related("indicator").first()
        return alias.indicator if alias else None

class LabIndicatorAlias(models.Model):
    indicator = models.ForeignKey("records.LabIndicator", on_delete=models.CASCADE, related_name="aliases")
    alias_raw = models.CharField(max_length=255)
    alias_norm = models.SlugField(max_length=255, unique=True)
    def save(self, *args, **kwargs):
        self.alias_norm = slugify(self.alias_raw)[:255]
        super().save(*args, **kwargs)
    def __str__(self):
        return self.alias_raw

class LabTestMeasurement(models.Model):
    medical_event = models.ForeignKey("records.MedicalEvent", on_delete=models.CASCADE, related_name="labtests")
    indicator = models.ForeignKey("records.LabIndicator", on_delete=models.PROTECT, related_name="measurements")
    value = models.FloatField()
    measured_at = models.DateTimeField()

    @property
    def abnormal_flag(self):
        lo = self.indicator.reference_low
        hi = self.indicator.reference_high
        v = self.value
        if v is None or (lo is None and hi is None):
            return None
        if lo is not None and v < lo:
            return "low"
        if hi is not None and v > hi:
            return "high"
        return None

    @property
    def is_abnormal(self):
        return self.abnormal_flag is not None

def get_indicator_canonical_tag(indicator):
    from parler.utils.context import switch_language
    name_bg = indicator.safe_translation_getter("name", language_code="bg", any_language=True)
    name_en = indicator.safe_translation_getter("name", language_code="en-us", any_language=True)
    slug = f"indicator-{indicator.slug}"
    tag, _ = Tag.objects.get_or_create(slug=slug, defaults={"kind": TagKind.INDICATOR, "is_active": True})
    with switch_language(tag, "bg"):
        tag.name = name_bg or name_en or indicator.slug
        tag.save()
    if name_en:
        with switch_language(tag, "en-us"):
            tag.name = name_en
            tag.save()
    return tag
