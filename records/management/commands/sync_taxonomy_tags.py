from django.core.management.base import BaseCommand
from records.models import MedicalCategory, MedicalSpecialty, DocumentType
from records.templatetags.tags import ensure_tag, TagKind

def best_name(obj, lang_code: str) -> str:
    try:
        val = obj.safe_translation_getter("name", language_code=lang_code, any_language=True)
        if val:
            return str(val)
    except Exception:
        pass
    slug = getattr(obj, "slug", None)
    if slug:
        return str(slug)
    return f"{obj._meta.model_name}-{obj.pk or 'new'}"

class Command(BaseCommand):
    def handle(self, *args, **opts):
        made = 0
        for obj in MedicalCategory.objects.all():
            name_bg = best_name(obj, "bg")
            name_en = best_name(obj, "en-us")
            ensure_tag(TagKind.CATEGORY, name_bg, name_en, getattr(obj, "slug", None)); made += 1

        for obj in MedicalSpecialty.objects.all():
            name_bg = best_name(obj, "bg")
            name_en = best_name(obj, "en-us")
            ensure_tag(TagKind.SPECIALTY, name_bg, name_en); made += 1

        for obj in DocumentType.objects.all():
            name_bg = best_name(obj, "bg")
            name_en = best_name(obj, "en-us")
            ensure_tag(TagKind.DOC_TYPE, name_bg, name_en, getattr(obj, "slug", None)); made += 1

        self.stdout.write(self.style.SUCCESS(f"Synced tags for taxonomy objects: {made}"))
