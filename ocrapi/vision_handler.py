import os
import io
import json
from typing import Optional
from PIL import Image
from google.cloud import vision
from google.oauth2 import service_account

try:
    from .anonymizer import anonymize_text
except Exception:
    try:
        from anonymizer import anonymize_text
    except Exception:
        def anonymize_text(x: str) -> str:
            return x

def _lang_hints():
    env = os.environ.get("GOOGLE_VISION_LANGUAGE_HINTS", "en,bg")
    return [x.strip() for x in env.split(",") if x.strip()]

def _tess_langs():
    return os.environ.get("TESSERACT_LANGS", "eng+bul")

def build_client() -> Optional[vision.ImageAnnotatorClient]:
    cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    cred_json = os.environ.get("GOOGLE_CLOUD_VISION_KEY")
    if cred_json:
        try:
            info = json.loads(cred_json)
            creds = service_account.Credentials.from_service_account_info(info)
            return vision.ImageAnnotatorClient(credentials=creds)
        except Exception:
            pass
    if cred_path and os.path.exists(cred_path):
        try:
            creds = service_account.Credentials.from_service_account_file(cred_path)
            return vision.ImageAnnotatorClient(credentials=creds)
        except Exception:
            pass
    try:
        return vision.ImageAnnotatorClient()
    except Exception:
        return None

def extract_text_from_image_bytes(b: bytes, client: Optional[vision.ImageAnnotatorClient]) -> str:
    if client:
        try:
            img = vision.Image(content=b)
            ctx = vision.ImageContext(language_hints=_lang_hints())
            r = client.document_text_detection(image=img, image_context=ctx)
            if getattr(r, "error", None) and getattr(r.error, "message", ""):
                raise RuntimeError(r.error.message)
            fta = getattr(r, "full_text_annotation", None)
            if fta and getattr(fta, "text", None):
                return anonymize_text(fta.text or "")
            tas = getattr(r, "text_annotations", None)
            if tas:
                t = tas[0].description if tas else ""
                return anonymize_text(t or "")
        except Exception:
            pass
    import pytesseract
    im = Image.open(io.BytesIO(b))
    txt = pytesseract.image_to_string(im, lang=_tess_langs(), config="--psm 6") or ""
    return anonymize_text(txt)

def extract_text_from_pdf_bytes(b: bytes, client: Optional[vision.ImageAnnotatorClient]) -> str:
    from pdf2image import convert_from_bytes
    pages = convert_from_bytes(b, dpi=400, fmt="png")
    out = []
    for p in pages:
        buf = io.BytesIO()
        p.save(buf, format="PNG")
        out.append(extract_text_from_image_bytes(buf.getvalue(), client))
    return anonymize_text("\n".join([x for x in out if x]))
