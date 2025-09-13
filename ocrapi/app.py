from flask import Flask, request, jsonify
import os, base64, io, json
from PIL import Image
from google.cloud import vision
from google.oauth2 import service_account

app = Flask(__name__)


def _vision_client() -> vision.ImageAnnotatorClient | None:
    """Create a Vision client using available credentials.

    Looks for a path in ``GOOGLE_APPLICATION_CREDENTIALS`` or a JSON string
    in ``GOOGLE_CLOUD_VISION_KEY``. If neither works, fall back to the
    default credentials chain.
    """

    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    creds_json = os.environ.get("GOOGLE_CLOUD_VISION_KEY")

    for candidate in (creds_path, creds_json):
        if not candidate:
            continue
        try:
            if os.path.exists(candidate):
                creds = service_account.Credentials.from_service_account_file(candidate)
            else:
                creds = service_account.Credentials.from_service_account_info(json.loads(candidate))
            return vision.ImageAnnotatorClient(credentials=creds)
        except Exception:
            continue

    try:
        return vision.ImageAnnotatorClient()
    except Exception:
        return None


VISION_CLIENT = _vision_client()


def _vision(image_bytes: bytes) -> str:
    if not VISION_CLIENT:
        raise RuntimeError("vision client not configured")

    image = vision.Image(content=image_bytes)
    resp = VISION_CLIENT.document_text_detection(image=image)
    if resp.error.message:
        raise RuntimeError(resp.error.message)
    if getattr(resp, "full_text_annotation", None) and getattr(resp.full_text_annotation, "text", ""):
        return resp.full_text_annotation.text or ""
    arr = getattr(resp, "text_annotations", None)
    if arr and len(arr) > 0 and getattr(arr[0], "description", ""):
        return arr[0].description or ""
    return ""

def _tesseract(image_bytes):
    import pytesseract, cv2, numpy as np
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        with Image.open(io.BytesIO(image_bytes)) as im:
            im = im.convert("RGB")
            buf = io.BytesIO()
            im.save(buf, format="PNG")
            arr = np.frombuffer(buf.getvalue(), dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return pytesseract.image_to_string(gray) or ""

def healthz() -> tuple[dict, int]:
    """Lightweight readiness probe for the OCR service."""
    return jsonify(status="ok"), 200

@app.post("/ocr")
def ocr():
    if "file" in request.files:
        image_bytes = request.files["file"].read()
    else:
        data = request.get_json(silent=True) or {}
        b64 = data.get("image_base64", "")
        if not b64:
            return jsonify(error="no file or image_base64"), 400
        image_bytes = base64.b64decode(b64)
    try:
        txt = _vision(image_bytes)
        if txt.strip():
            return jsonify(engine="vision", ocr_text=txt.strip()), 200
        raise RuntimeError("empty")
    except Exception:
        try:
            txt = _tesseract(image_bytes)
            return jsonify(engine="tesseract", ocr_text=(txt or "").strip()), 200
        except Exception as e:
            return jsonify(error="ocr_failed", detail=str(e)), 500

