import os
import io
import json
from PIL import Image
from google.cloud import vision
from google.oauth2 import service_account

try:
    from anonymizer import anonymize_text
except Exception:
    def anonymize_text(x: str) -> str:
        return x

def build_client() -> vision.ImageAnnotatorClient | None:
    p = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    j = os.environ.get("GOOGLE_CLOUD_VISION_KEY")
    if j:
        try:
            info = json.loads(j)
            creds = service_account.Credentials.from_service_account_info(info)
            return vision.ImageAnnotatorClient(credentials=creds)
        except Exception:
            pass
    if p and os.path.exists(p):
        try:
            creds = service_account.Credentials.from_service_account_file(p)
            return vision.ImageAnnotatorClient(credentials=creds)
        except Exception:
            pass
    try:
        return vision.ImageAnnotatorClient()
    except Exception:
        return None

def extract_text_from_image_bytes(b: bytes, client: vision.ImageAnnotatorClient | None) -> str:
    if client:
        try:
            img = vision.Image(content=b)
            r = client.document_text_detection(image=img)
            if getattr(r, "error", None) and getattr(r.error, "message", ""):
                raise RuntimeError(r.error.message)
            if getattr(r, "full_text_annotation", None) and getattr(r.full_text_annotation, "text", None):
                return anonymize_text(r.full_text_annotation.text or "")
            if getattr(r, "text_annotations", None):
                t = r.text_annotations[0].description if r.text_annotations else ""
                return anonymize_text(t or "")
        except Exception:
            pass
    try:
        import pytesseract
        im = Image.open(io.BytesIO(b))
        return anonymize_text(pytesseract.image_to_string(im) or "")
    except Exception:
        raise

def extract_text_from_pdf_bytes(b: bytes, client: vision.ImageAnnotatorClient | None) -> str:
    from pdf2image import convert_from_bytes
    pages = convert_from_bytes(b, dpi=300, fmt="png")
    out = []
    for p in pages:
        buf = io.BytesIO()
        p.save(buf, format="PNG")
        out.append(extract_text_from_image_bytes(buf.getvalue(), client))
    return anonymize_text("\n".join([x for x in out if x]))
