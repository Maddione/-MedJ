from __future__ import annotations
import io, os, json, uuid, requests
from decimal import Decimal
from pathlib import Path
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone

from ..models import PatientProfile, Tag, DocumentTag

User = get_user_model()

def get_or_create_patient_profile(user):
    profile, _ = PatientProfile.objects.get_or_create(user=user)
    return profile

def require_patient_profile(user):
    profile, _ = PatientProfile.objects.get_or_create(user=user)
    return profile

def safe_translated(obj, field="name"):
    try:
        return obj.safe_translation_getter(field, any_language=True)
    except Exception:
        return getattr(obj, field, "") or ""

def get_patient(user):
    return PatientProfile.objects.filter(user=user).first()

def parse_multi(get, key):
    raw = get.getlist(key) or [get.get(key, "")]
    out = []
    for v in raw:
        if not v:
            continue
        for p in str(v).split(","):
            p = p.strip()
            if p:
                out.append(p)
    return out

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

def call_ocr_api(file_path, doc_type_name="", specialty_name=""):
    url = os.environ.get("OCR_API_URL", getattr(settings, "OCR_API_URL", "http://ocrapi:5000/ocr"))
    try:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f)}
            data = {}
            if doc_type_name: data["doc_type"] = doc_type_name
            if specialty_name: data["specialty"] = specialty_name
            r = requests.post(url, files=files, data=data, timeout=90)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def add_tag(name: str, *objs):
    nm = (name or "").strip()
    if not nm:
        return
    try:
        t, _ = Tag.objects.get_or_create(name=nm)
        for o in objs:
            try:
                o.tags.add(t)
            except Exception:
                pass
    except Exception:
        pass

def parse_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None

def save_temp_upload(uploaded_file) -> str:
    tmp_dir = "temp_uploads"
    os.makedirs(os.path.join(settings.MEDIA_ROOT, tmp_dir), exist_ok=True)
    tmp_name = f"{uuid.uuid4()}_{uploaded_file.name}"
    tmp_rel_path = os.path.join(tmp_dir, tmp_name).replace("\\", "/")
    with default_storage.open(tmp_rel_path, "wb+") as dest:
        for chunk in uploaded_file.chunks():
            dest.write(chunk)
    return tmp_rel_path

def load_temp_file_bytes(tmp_rel_path: str) -> bytes:
    with default_storage.open(tmp_rel_path, "rb") as f:
        return f.read()

try:
    from ocrapi.vision_handler import extract_text_from_image as ocr_extract_text
except Exception:
    ocr_extract_text = None

try:
    from ocrapi.anonymizer import anonymize_text as anonymize_text_fn
except Exception:
    anonymize_text_fn = None

try:
    from ocrapi.gpt_client import analyze_document as gpt_analyze_document
except Exception:
    gpt_analyze_document = None

def ocr_from_storage(tmp_rel_path: str) -> str:
    if not ocr_extract_text:
        return ""
    try:
        abs_path = default_storage.path(tmp_rel_path)
    except Exception:
        abs_path = None
    if not abs_path:
        from tempfile import NamedTemporaryFile
        with default_storage.open(tmp_rel_path, "rb") as src, NamedTemporaryFile(delete=False, suffix=".bin") as tf:
            tf.write(src.read())
            abs_path = tf.name
    try:
        return ocr_extract_text(abs_path) or ""
    except Exception:
        return ""

def anonymize(text: str) -> str:
    if anonymize_text_fn:
        try:
            return anonymize_text_fn(text)
        except Exception:
            return text
    return text

def gpt_analyze(ocr_text: str, doc_kind: str, file_type: str, specialty_name: str) -> dict:
    if gpt_analyze_document:
        try:
            return gpt_analyze_document(
                ocr_text=ocr_text,
                doc_kind=doc_kind,
                file_type=file_type,
                specialty=specialty_name,
            )
        except Exception:
            return {}
    return {}


def get_or_create_tags(names, doc_type=None, specialty=None, default="test_type"):
    """Връща списък от Tag обекти; не чупи при празни/дублирани."""
    out = []
    for nm in names or []:
        nm = (nm or "").strip()
        if not nm:
            continue
        t, _ = Tag.objects.get_or_create(name=nm, defaults={"category": default})
        out.append(t)
    return out
