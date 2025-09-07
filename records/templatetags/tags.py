from django import template
from records.models import Tag, TagKind

register = template.Library()

def ensure_tag(kind, name_bg, name_en, slug=None):
    if slug:
        tag, _ = Tag.objects.get_or_create(slug=slug, defaults={"kind": kind, "is_active": True})
    else:
        base = (name_en or name_bg or "").strip().lower().replace(" ", "-")
        base = base[:200] if base else f"{kind}"
        tag, _ = Tag.objects.get_or_create(slug=f"{kind}:{base}"[:255], defaults={"kind": kind, "is_active": True})
    try:
        tag.set_current_language("bg")
        if name_bg:
            tag.name = name_bg
            tag.save()
    except Exception:
        pass
    try:
        tag.set_current_language("en-us")
        if name_en:
            tag.name = name_en
            tag.save()
    except Exception:
        pass
    return tag
