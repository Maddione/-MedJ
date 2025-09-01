from __future__ import annotations
import re
from typing import Iterable, Optional
from django.utils.text import slugify
from ..models import Tag, MedicalSpecialty, DocumentType


KW_TIME = {
    "профилакти", "профилактичен", "скрининг", "скрийнинг",
    "консултац", "преглед", "контролен", "контролен преглед",
    "ваксин", "имуниз",
}
KW_DOCTOR = {"д-р", "д-р.", "dr", "doc", "лекар", "проф.", "доц."}

def _looks_like_doctor(label: str) -> bool:
    s = label.lower()
    if any(k in s for k in KW_DOCTOR):
        return True

    return bool(re.search(r"(д[\.\-]?\s*р|dr\.?)\s+\S+", s))

def _is_time_like(label: str) -> bool:
    s = label.lower()
    return any(k in s for k in KW_TIME)

def _matches_specialty(label: str, specialty: Optional[MedicalSpecialty]) -> bool:
    if not specialty:
        return False
    spec_name = (specialty.safe_translation_getter("name", any_language=True) or "").strip().lower()
    return bool(spec_name) and spec_name in label.lower()

def _doc_type_hint_category(doc_type: Optional[DocumentType]) -> Optional[str]:
    if not doc_type:
        return None
    slug = getattr(doc_type, "slug", "") or slugify(str(doc_type))
    if any(k in slug for k in ("blood", "hematology", "kravni", "lab")):
        return "test_type"
    if any(k in slug for k in ("referral", "napravlenie", "direction")):
        return "time"
    return None

def categorize_tag(
    name: str,
    *,
    doc_type: Optional[DocumentType] = None,
    specialty: Optional[MedicalSpecialty] = None,
    default: str = "test_type",
) -> str:
    label = (name or "").strip()
    if not label:
        return default

    if _looks_like_doctor(label):
        return "doctor"

    if _is_time_like(label):
        return "time"

    if _matches_specialty(label, specialty):
        return "specialty"

    hinted = _doc_type_hint_category(doc_type)
    if hinted:
        return hinted

    return default

def get_or_create_tag(
    name: str,
    *,
    doc_type: Optional[DocumentType] = None,
    specialty: Optional[MedicalSpecialty] = None,
    default: str = "test_type",
) -> Tag:
    cat = categorize_tag(name, doc_type=doc_type, specialty=specialty, default=default)
    obj, _ = Tag.objects.get_or_create(name=name.strip(), defaults={"category": cat})

    return obj

def get_or_create_tags(
    names: Iterable[str],
    *,
    doc_type: Optional[DocumentType] = None,
    specialty: Optional[MedicalSpecialty] = None,
    default: str = "test_type",
) -> list[Tag]:
    out: list[Tag] = []
    seen = set()
    for raw in names or []:
        if not raw:
            continue
        name = raw.strip()
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        out.append(get_or_create_tag(name, doc_type=doc_type, specialty=specialty, default=default))
    return out
