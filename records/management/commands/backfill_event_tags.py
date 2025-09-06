from django.core.management.base import BaseCommand
from django.utils.timezone import now
from records.models import Document, Tag, DocumentTag, TagKind

class Command(BaseCommand):
    def handle(self, *args, **options):
        qs = Document.objects.select_related("medical_event","category","specialty","doc_type").all()
        for d in qs:
            ev = d.medical_event
            if not ev:
                continue
            slugs = []
            if getattr(d, "doc_kind", None):
                slugs.append(("permanent:document_kind:"+str(d.doc_kind).lower(), str(d.doc_kind)))
            if d.specialty_id:
                nm = ""
                try:
                    nm = d.specialty.safe_translation_getter("name", any_language=True) or d.specialty.name
                except Exception:
                    nm = ""
                slugs.append(("permanent:specialty:"+str(d.specialty_id), nm or "specialty"))
            if d.category_id:
                nm = ""
                try:
                    nm = d.category.safe_translation_getter("name", any_language=True) or d.category.name
                except Exception:
                    nm = ""
                slugs.append(("permanent:category:"+str(d.category_id), nm or "category"))
            if d.doc_type_id:
                nm = ""
                try:
                    nm = d.doc_type.safe_translation_getter("name", any_language=True) or d.doc_type.name
                except Exception:
                    nm = ""
                slugs.append(("permanent:doc_type:"+str(d.doc_type_id), nm or "doc_type"))
            src_date = getattr(d, "date_created", None) or getattr(ev, "event_date", None) or now().date()
            try:
                dd = src_date.strftime("%d-%m-%Y")
                slugs.append(("permanent:date:"+dd, "date:"+dd))
            except Exception:
                pass
            for slug, label in slugs:
                try:
                    tag = Tag.objects.get(slug=slug)
                except Tag.DoesNotExist:
                    tag = Tag.objects.create(slug=slug, kind=TagKind.SYSTEM, is_active=True)
                    try:
                        tag.set_current_language("bg")
                        tag.name = label or slug
                        tag.save()
                    except Exception:
                        pass
                try:
                    DocumentTag.objects.get_or_create(document=d, tag=tag, defaults={"is_inherited": False, "is_permanent": True})
                except Exception:
                    pass
                try:
                    ev.tags.add(tag)
                except Exception:
                    pass
