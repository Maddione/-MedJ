from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from parler.models import TranslatableModel, TranslatedFields


class PatientProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="patient_profile")
    first_name_bg = models.CharField(max_length=120, blank=True, null=True)
    middle_name_bg = models.CharField(max_length=120, blank=True, null=True)
    last_name_bg = models.CharField(max_length=120, blank=True, null=True)
    first_name_en = models.CharField(max_length=120, blank=True, null=True)
    middle_name_en = models.CharField(max_length=120, blank=True, null=True)
    last_name_en = models.CharField(max_length=120, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    phone_number = models.CharField(max_length=64, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    share_enabled = models.BooleanField(default=False)
    share_token = models.CharField(max_length=64, blank=True, null=True, unique=True)

    def __str__(self):
        return self.user.get_username()


class MedicalCategory(TranslatableModel):
    translations = TranslatedFields(
        name=models.CharField(max_length=255, unique=True),
        description=models.TextField(blank=True, null=True),
    )
    slug = models.SlugField(max_length=255, unique=True, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.slug:
            name = self.safe_translation_getter("name", any_language=True) or ""
            self.slug = slugify(name)[:255] or None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.safe_translation_getter("name", any_language=True) or "Category"


class MedicalSpecialty(TranslatableModel):
    translations = TranslatedFields(
        name=models.CharField(max_length=255, unique=True),
        description=models.TextField(blank=True, null=True),
    )
    slug = models.SlugField(max_length=255, unique=True, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.slug:
            name = self.safe_translation_getter("name", any_language=True) or ""
            self.slug = slugify(name)[:255] or None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.safe_translation_getter("name", any_language=True) or "Specialty"


class DocumentType(TranslatableModel):
    translations = TranslatedFields(
        name=models.CharField(max_length=255, unique=True),
        description=models.TextField(blank=True, null=True),
    )
    slug = models.SlugField(max_length=255, unique=True, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.slug:
            name = self.safe_translation_getter("name", any_language=True) or ""
            self.slug = slugify(name)[:255] or None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.safe_translation_getter("name", any_language=True) or "DocumentType"


class TagKind(models.TextChoices):
    SPECIALTY = "specialty", "specialty"
    CATEGORY = "category", "category"
    DOC_TYPE = "doc_type", "doc_type"
    DOC_KIND = "doc_kind", "doc_kind"
    INDICATOR = "indicator", "indicator"
    DOCTOR = "doctor", "doctor"
    TIME = "time", "time"
    FILE_TYPE = "file_type", "file_type"
    SYSTEM = "system", "system"


class Tag(TranslatableModel):
    translations = TranslatedFields(name=models.CharField(max_length=255))
    slug = models.SlugField(max_length=255, unique=True)
    kind = models.CharField(max_length=32, choices=TagKind.choices, default=TagKind.SYSTEM)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.safe_translation_getter("name", any_language=True) or self.slug


class MedicalEvent(models.Model):
    patient = models.ForeignKey("records.PatientProfile", on_delete=models.CASCADE, related_name="events")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="events")
    specialty = models.ForeignKey("records.MedicalSpecialty", on_delete=models.PROTECT, related_name="events")
    category = models.ForeignKey("records.MedicalCategory", on_delete=models.PROTECT, related_name="events", blank=True, null=True)
    doc_type = models.ForeignKey("records.DocumentType", on_delete=models.PROTECT, related_name="events", blank=True, null=True)
    event_date = models.DateField()
    summary = models.CharField(max_length=255, blank=True, null=True)
    tags = models.ManyToManyField("records.Tag", through="records.EventTag", related_name="events", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient_id}-{self.event_date}"


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
    date_created = models.DateField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to="documents/")
    file_size = models.BigIntegerField(blank=True, null=True)
    file_mime = models.CharField(max_length=120, blank=True, null=True)
    doc_kind = models.CharField(max_length=16, choices=DOC_KIND_CHOICES, default="other")
    sha256 = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    original_ocr_text = models.TextField(blank=True, null=True)
    summary = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    tags = models.ManyToManyField("records.Tag", through="records.DocumentTag", related_name="documents", blank=True)

    def __str__(self):
        return f"{self.id}"

    def attach_permanent_tag(self, tag):
        DocumentTag.objects.get_or_create(document=self, tag=tag, defaults={"is_inherited": False, "is_permanent": True})

    def attach_editable_tag(self, tag):
        DocumentTag.objects.get_or_create(document=self, tag=tag, defaults={"is_inherited": False, "is_permanent": False})


class DocumentTag(models.Model):
    document = models.ForeignKey("records.Document", on_delete=models.CASCADE)
    tag = models.ForeignKey("records.Tag", on_delete=models.CASCADE)
    is_inherited = models.BooleanField(default=False)
    is_permanent = models.BooleanField(default=False)

    class Meta:
        unique_together = ("document", "tag")


class Diagnosis(models.Model):
    medical_event = models.ForeignKey("records.MedicalEvent", on_delete=models.CASCADE, related_name="diagnoses")
    code = models.CharField(max_length=64)
    description = models.CharField(max_length=255, blank=True, null=True)


class NarrativeNote(models.Model):
    medical_event = models.ForeignKey("records.MedicalEvent", on_delete=models.CASCADE, related_name="notes")
    title = models.CharField(max_length=255)
    content = models.TextField()


class Medication(models.Model):
    medical_event = models.ForeignKey("records.MedicalEvent", on_delete=models.CASCADE, related_name="medications")
    name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=255, blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)


class LabIndicator(TranslatableModel):
    translations = TranslatedFields(name=models.CharField(max_length=255))
    slug = models.SlugField(max_length=255, unique=True)
    unit = models.CharField(max_length=64, blank=True, null=True)
    reference_low = models.FloatField(blank=True, null=True)
    reference_high = models.FloatField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base = self.safe_translation_getter("name", any_language=True) or ""
            self.slug = slugify(base)[:255] or None
        super().save(*args, **kwargs)


class LabIndicatorAlias(models.Model):
    indicator = models.ForeignKey("records.LabIndicator", on_delete=models.CASCADE, related_name="aliases")
    alias = models.CharField(max_length=255, db_index=True)
    alias_norm = models.SlugField(max_length=255, db_index=True)

    class Meta:
        unique_together = ("indicator", "alias_norm")


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
        return "normal"


class ShareLink(models.Model):
    STATUS_CHOICES = (("active", "active"), ("revoked", "revoked"))
    OBJECT_CHOICES = (("document", "document"), ("event", "event"))
    FORMAT_CHOICES = (("pdf", "pdf"), ("csv", "csv"), ("html", "html"))
    token = models.CharField(max_length=64, unique=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="share_links")
    object_type = models.CharField(max_length=16, choices=OBJECT_CHOICES)
    object_id = models.PositiveIntegerField()
    scope = models.CharField(max_length=255, blank=True, null=True)
    format = models.CharField(max_length=8, choices=FORMAT_CHOICES, default="html")
    expires_at = models.DateTimeField(blank=True, null=True)
    password_hash = models.CharField(max_length=128, blank=True, null=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="active")
    created_at = models.DateTimeField(auto_now_add=True)


class OcrLog(models.Model):
    SOURCE_CHOICES = (("vision", "vision"), ("flask", "flask"))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name="ocr_logs")
    document = models.ForeignKey("records.Document", on_delete=models.SET_NULL, blank=True, null=True, related_name="ocr_logs")
    source = models.CharField(max_length=16, choices=SOURCE_CHOICES)
    duration_ms = models.PositiveIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


def get_indicator_canonical_tag(indicator):
    from django.utils.text import slugify
    if indicator is None:
        return None
    try:
        name = getattr(indicator, "safe_translation_getter", lambda *a, **k: None)("name", any_language=True) or getattr(indicator, "name", "") or ""
    except Exception:
        name = getattr(indicator, "name", "") or ""
    base = slugify(name) or f"indicator-{getattr(indicator, 'id', '') or 'x'}"
    slug = f"indicator:{base}"
    try:
        return Tag.objects.get(slug=slug)
    except Tag.DoesNotExist:
        t = Tag.objects.create(slug=slug, kind=TagKind.SYSTEM, is_active=True)
        try:
            t.set_current_language("bg")
        except Exception:
            pass
        if name:
            try:
                t.name = name
                t.save(update_fields=["name"])
            except Exception:
                pass
        return t
