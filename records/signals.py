import hashlib
import mimetypes
from django.utils import timezone
from django.utils.text import slugify
from parler.utils.context import switch_language
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.conf import settings
from django.db import models, transaction
from django.contrib.auth import get_user_model
from .models import (
    Document,
    DocumentTag,
    MedicalEvent,
    Tag,
    TagKind,
    MedicalCategory,
    MedicalSpecialty,
    DocumentType,
    LabIndicator,
    LabIndicatorAlias,
    get_indicator_canonical_tag,
)
from .services.labs_utils import tokenize_text, attach_canonical_indicator_tags
from .utils.db_checks import has_table, has_field

def _safe_name_or_slug(instance, lang=None, fallback_slug=True):
    name = instance.safe_translation_getter("name", language_code=lang, any_language=True)
    if name:
        return name
    if fallback_slug and getattr(instance, "slug", None):
        return instance.slug
    return "unnamed"

def ensure_tag(kind, name_bg, name_en=None, slug=None):
    if not getattr(settings, "MEDJ_TAG_SYNC_ENABLED", True):
        return None
    if not has_table("records_tag"):
        return None
    if not has_field("records_tag", "slug"):
        return None
    s = (slug or slugify(name_bg) or "tag")[:255]
    tag, created = Tag.objects.get_or_create(slug=s, defaults={"kind": kind, "is_active": True})
    if created:
        with switch_language(tag, "bg"):
            tag.name = name_bg or s
            tag.save()
        if name_en:
            with switch_language(tag, "en-us"):
                tag.name = name_en or s
                tag.save()
    return tag

@receiver(post_save, sender=MedicalCategory)
def create_category_tag(sender, instance, created, **kwargs):
    name_bg = _safe_name_or_slug(instance, "bg")
    name_en = instance.safe_translation_getter("name", language_code="en-us", any_language=True)
    ensure_tag(TagKind.CATEGORY, name_bg, name_en, getattr(instance, "slug", None))

@receiver(post_save, sender=MedicalSpecialty)
def create_specialty_tag(sender, instance, created, **kwargs):
    name_bg = instance.safe_translation_getter("name", language_code="bg", any_language=True) or instance.slug or "unnamed"
    name_en = instance.safe_translation_getter("name", language_code="en-us", any_language=True)
    ensure_tag(TagKind.SPECIALTY, name_bg, name_en, getattr(instance, "slug", None))


@receiver(post_save, sender=DocumentType)
def create_doctype_tag(sender, instance, created, **kwargs):
    name_bg = _safe_name_or_slug(instance, "bg")
    name_en = instance.safe_translation_getter("name", language_code="en-us", any_language=True)
    ensure_tag(TagKind.DOC_TYPE, name_bg, name_en, getattr(instance, "slug", None))

@receiver(post_save, sender=LabIndicator)
def create_indicator_tag(sender, instance, created, **kwargs):
    get_indicator_canonical_tag(instance)

@receiver(post_save, sender=get_user_model())
def ensure_patient_profile(sender, instance, created, **kwargs):
    if not created:
        return
    from .models import PatientProfile
    PatientProfile.objects.get_or_create(
        user=instance,
        defaults={"first_name_bg": instance.first_name or "", "last_name_bg": instance.last_name or ""},
    )

@receiver(post_save, sender=Document)
def document_post_save(sender, instance, created, **kwargs):
    if instance.file and not instance.sha256:
        h = hashlib.sha256()
        for chunk in instance.file.chunks():
            h.update(chunk)
        instance.sha256 = h.hexdigest()
        if not instance.file_mime:
            instance.file_mime = mimetypes.guess_type(instance.file.name)[0]
        instance.save(update_fields=["sha256", "file_mime"])
    if instance.medical_event_id:
        for t in instance.medical_event.tags.all():
            DocumentTag.objects.get_or_create(document=instance, tag=t, defaults={"is_inherited": True})
    if instance.specialty_id:
        name_bg = _safe_name_or_slug(instance.specialty, "bg")
        name_en = instance.specialty.safe_translation_getter("name", language_code="en-us", any_language=True)
        t = ensure_tag(TagKind.SPECIALTY, name_bg, name_en)
        if t:
            DocumentTag.objects.get_or_create(document=instance, tag=t, defaults={"is_inherited": False})
    if instance.category_id:
        name_bg = _safe_name_or_slug(instance.category, "bg")
        name_en = instance.category.safe_translation_getter("name", language_code="en-us", any_language=True)
        t = ensure_tag(TagKind.CATEGORY, name_bg, name_en, getattr(instance.category, "slug", None))
        if t:
            DocumentTag.objects.get_or_create(document=instance, tag=t, defaults={"is_inherited": False})
    if instance.doc_type_id:
        name_bg = _safe_name_or_slug(instance.doc_type, "bg")
        name_en = instance.doc_type.safe_translation_getter("name", language_code="en-us", any_language=True)
        t = ensure_tag(TagKind.DOC_TYPE, name_bg, name_en, getattr(instance.doc_type, "slug", None))
        if t:
            DocumentTag.objects.get_or_create(document=instance, tag=t, defaults={"is_inherited": False})
    dk = instance.doc_kind or "other"
    t = ensure_tag(TagKind.DOC_KIND, dk, dk, f"doc-kind-{dk}")
    if t:
        DocumentTag.objects.get_or_create(document=instance, tag=t, defaults={"is_inherited": False})
    ft = (instance.file_mime.split("/")[-1] if instance.file_mime else None) or instance.file.name.split(".")[-1].lower()
    t = ensure_tag(TagKind.FILE_TYPE, ft, ft, f"filetype-{ft}")
    if t:
        DocumentTag.objects.get_or_create(document=instance, tag=t, defaults={"is_inherited": False})
    d = instance.document_date or instance.uploaded_at.date() if instance.uploaded_at else timezone.now().date()
    t = ensure_tag(TagKind.TIME, f"date:{d.isoformat()}", f"date:{d.isoformat()}", f"date-{d.isoformat()}")
    if t:
        DocumentTag.objects.get_or_create(document=instance, tag=t, defaults={"is_inherited": False})
    text = (instance.original_ocr_text or "") + " " + (instance.summary or "")
    tokens = tokenize_text(text)
    attach_canonical_indicator_tags(instance, tokens)

@receiver(m2m_changed, sender=MedicalEvent.tags.through)
def event_tags_changed(sender, instance, action, reverse, model, pk_set, **kwargs):
    if action in ("post_add", "post_remove", "post_clear"):
        current = set(instance.tags.values_list("pk", flat=True))
        for doc in instance.documents.all():
            inherited = set(
                DocumentTag.objects.filter(document=doc, is_inherited=True).values_list("tag_id", flat=True)
            )
            to_add = current - inherited
            to_del = inherited - current
            for tag_id in to_add:
                DocumentTag.objects.get_or_create(document=doc, tag_id=tag_id, defaults={"is_inherited": True})
            if to_del:
                DocumentTag.objects.filter(document=doc, tag_id__in=to_del, is_inherited=True).delete()

def _model_defaults(instance):
    defaults = {}
    for field in instance._meta.concrete_fields:
        if isinstance(field, models.AutoField):
            continue
        if isinstance(field, models.ForeignKey):
            defaults[field.attname] = getattr(instance, field.attname)
        else:
            defaults[field.name] = getattr(instance, field.name)
    return defaults

def _mirror_user_to_backup(user_obj, alias):
    U = get_user_model()
    pk = getattr(user_obj, U._meta.pk.attname)
    defaults = {}
    for f in U._meta.concrete_fields:
        if isinstance(f, models.AutoField):
            continue
        if isinstance(f, models.ForeignKey):
            defaults[f.attname] = getattr(user_obj, f.attname)
        else:
            defaults[f.name] = getattr(user_obj, f.name)
    U.objects.using(alias).update_or_create(pk=pk, defaults=defaults)

@receiver(post_save)
def backup_post_save(sender, instance, using, **kwargs):
    if using != "default":
        return
    if sender._meta.app_label != "records":
        return
    if sender.__name__.lower().endswith("translation"):
        return
    alias = getattr(settings, "BACKUP_DB_ALIAS", None)
    if not alias or alias not in settings.DATABASES:
        return
    def run():
        U = get_user_model()
        for field in sender._meta.fields:
            rel = getattr(field, "remote_field", None)
            if rel and rel.model == U:
                u = getattr(instance, field.name, None)
                if u:
                    _mirror_user_to_backup(u, alias)
        pk = getattr(instance, instance._meta.pk.attname)
        defaults = _model_defaults(instance)
        sender.objects.using(alias).update_or_create(pk=pk, defaults=defaults)
    transaction.on_commit(run)

@receiver(post_delete)
def backup_post_delete(sender, instance, using, **kwargs):
    if using != "default":
        return
    if sender._meta.app_label != "records":
        return
    if sender.__name__.lower().endswith("translation"):
        return
    alias = getattr(settings, "BACKUP_DB_ALIAS", None)
    if not alias or alias not in settings.DATABASES:
        return
    pk = getattr(instance, instance._meta.pk.attname)
    def run():
        try:
            sender.objects.using(alias).get(pk=pk).delete()
        except sender.DoesNotExist:
            pass
    transaction.on_commit(run)

def post_migrate_sync(sender, app_config, verbosity, interactive, using, plan, apps, **kwargs):
    from django.core.management import call_command
    if not getattr(settings, "MEDJ_TAG_SYNC_ENABLED", True):
        return
    call_command("sync_taxonomy_tags")
