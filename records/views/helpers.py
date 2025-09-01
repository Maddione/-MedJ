import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.base import File

from records.models import PatientProfile, Tag


def get_patient(user):
    return PatientProfile.objects.filter(user=user).first()

def media_tmp_dir() -> Path:
    root = Path(getattr(settings, "MEDIA_ROOT", "/app/media"))
    tmp = root / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    return tmp

def save_tmp(upload_file) -> tuple[str, Path]:
    ext = Path(upload_file.name).suffix or ""
    name = f"{uuid.uuid4().hex}{ext}"
    dest = media_tmp_dir() / name
    with open(dest, "wb") as out:
        for chunk in upload_file.chunks():
            out.write(chunk)
    return name, dest

def to_django_file(tmp_path: Path, name: str | None = None) -> File:
    return File(open(tmp_path, "rb"), name=(name or tmp_path.name))

def safe_name(obj, field="name"):
    try:
        return obj.safe_translation_getter(field, any_language=True) or ""
    except Exception:
        return getattr(obj, field, "") or ""

def add_tag(name: str, *objs):
    nm = (name or "").strip()
    if not nm:
        return
    t, _ = Tag.objects.get_or_create(name=nm)
    for o in objs:
        try:
            o.tags.add(t)
        except Exception:
            pass
