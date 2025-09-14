from flask import Flask, request, jsonify
import os
import io
import json
import base64
from PIL import Image
from google.cloud import vision
from google.oauth2 import service_account

try:
    from anonymizer import anonymize_text
except Exception:
    def anonymize_text(x: str) -> str:
        return x

try:
    from vision_handler import build_client, extract_text_from_image_bytes, extract_text_from_pdf_bytes
except Exception:
    def build_client() -> vision.ImageAnnotatorClient | None:
        creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        creds_json = os.environ.get("GOOGLE_CLOUD_VISION_KEY")
        if creds_json:
            try:
                info = json.loads(creds_json)
                creds = service_account.Credentials.from_service_account_info(info)
                return vision.ImageAnnotatorClient(credentials=creds)
            except Exception:
                pass
        if creds_path and os.path.exists(creds_path):
            try:
                creds = service_account.Credentials.from_service_account_file(creds_path)
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
        try:
            from pdf2image import convert_from_bytes
            pages = convert_from_bytes(b, dpi=300, fmt="png")
            out = []
            for p in pages:
                buf = io.BytesIO()
                p.save(buf, format="PNG")
                out.append(extract_text_from_image_bytes(buf.getvalue(), client))
            return anonymize_text("\n".join([x for x in out if x]))
        except Exception:
            raise

app = Flask(__name__)

def _decode_payload_file(req) -> tuple[bytes, str]:
    f = req.files.get("file")
    b64 = req.form.get("image_base64") or req.json.get("image_base64") if req.is_json else None
    kind = (req.form.get("file_kind") or req.json.get("file_kind") if req.is_json else None or "").lower()
    if f:
        data = f.read()
        name = f.filename or ""
        if name.lower().endswith(".pdf"):
            return data, "pdf"
        return data, kind or "image"
    if b64:
        try:
            data = base64.b64decode(b64)
            return data, kind or "image"
        except Exception:
            return b"", ""
    return b"", ""

@app.post("/ocr")
def ocr():
    blob, kind = _decode_payload_file(request)
    if not blob:
        return jsonify(error="no_file"), 400
    client = build_client()
    if kind == "pdf":
        try:
            txt = extract_text_from_pdf_bytes(blob, client)
            if not txt or not txt.strip():
                raise RuntimeError("empty")
            return jsonify(engine="vision", ocr_text=txt.strip()), 200
        except Exception as e:
            try:
                from pdf2image import convert_from_bytes
                import pytesseract
                pages = convert_from_bytes(blob, dpi=300, fmt="png")
                out = []
                for p in pages:
                    buf = io.BytesIO()
                    p.save(buf, format="PNG")
                    out.append(pytesseract.image_to_string(Image.open(io.BytesIO(buf.getvalue()))))
                txt = "\n".join([x for x in out if x]).strip()
                if not txt:
                    raise RuntimeError("empty")
                return jsonify(engine="tesseract", ocr_text=anonymize_text(txt)), 200
            except Exception as ex:
                return jsonify(error="ocr_failed", detail=str(ex)), 500
    try:
        txt = extract_text_from_image_bytes(blob, client)
        if not txt or not txt.strip():
            raise RuntimeError("empty")
        return jsonify(engine="vision", ocr_text=txt.strip()), 200
    except Exception:
        try:
            import pytesseract
            txt = pytesseract.image_to_string(Image.open(io.BytesIO(blob))) or ""
            return jsonify(engine="tesseract", ocr_text=anonymize_text(txt.strip())), 200
        except Exception as e:
            return jsonify(error="ocr_failed", detail=str(e)), 500
