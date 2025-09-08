import io, json, os, time, logging
from flask import Flask, request, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)

# Логиране
LOG_LEVEL = os.getenv("OCRAPI_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("ocrapi")

BACKEND = os.getenv("OCR_BACKEND", "vision").lower()  # vision|tesseract
GCP_PROJECT = os.getenv("GCP_PROJECT", "")
GCP_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

def ocr_with_vision(content_bytes, mime_type):
    start = time.time()
    try:
        from google.cloud import vision  # requires google-cloud-vision
    except Exception as e:
        log.exception("Vision SDK import failed")
        return {"error": f"vision_sdk_import_failed: {e}"}, 0

    try:
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=content_bytes)
        resp = client.document_text_detection(image=image)
        duration = int((time.time() - start) * 1000)
        if resp.error.message:
            log.error("Vision error: %s", resp.error.message)
            return {"error": f"vision_error: {resp.error.message}"}, duration
        text = (resp.full_text_annotation.text or "").strip()
        return {"ocr_text": text, "source": "google_vision"}, duration
    except Exception as e:
        duration = int((time.time() - start) * 1000)
        log.exception("Vision call failed")
        return {"error": f"vision_call_failed: {e}"}, duration

def ocr_with_tesseract(content_bytes, mime_type):
    start = time.time()
    try:
        import pytesseract
        from PIL import Image
    except Exception as e:
        log.exception("Tesseract/PIL import failed")
        return {"error": f"tesseract_import_failed: {e}"}, 0
    try:
        img = Image.open(io.BytesIO(content_bytes))
        text = pytesseract.image_to_string(img)
        duration = int((time.time() - start) * 1000)
        return {"ocr_text": (text or "").strip(), "source": "tesseract"}, duration
    except Exception as e:
        duration = int((time.time() - start) * 1000)
        log.exception("Tesseract call failed")
        return {"error": f"tesseract_failed: {e}"}, duration

@app.post("/ocr")
def ocr():
    # Лог вход
    log.info("OCR request: args=%s form=%s content_length=%s", dict(request.args), list(request.form.keys()), request.content_length)
    f = request.files.get("file")
    if not f:
        log.warning("missing file")
        return jsonify({"error":"missing_file"}), 400
    file_bytes = f.read()
    mime = f.mimetype or "application/octet-stream"
    kind = request.form.get("file_kind","")
    meta = {
        "med_category": request.form.get("med_category",""),
        "specialty": request.form.get("specialty",""),
        "doc_type": request.form.get("doc_type",""),
        "file_kind": kind
    }
    log.info("meta=%s backend=%s project=%s creds=%s", meta, BACKEND, GCP_PROJECT, bool(GCP_CREDENTIALS))

    if BACKEND == "tesseract":
        data, duration = ocr_with_tesseract(file_bytes, mime)
    else:
        data, duration = ocr_with_vision(file_bytes, mime)

    data["duration_ms"] = duration
    ok = bool(data.get("ocr_text"))
    status = 200 if ok else 502
    # Лог изход
    log.info("OCR response: ok=%s, duration_ms=%s, keys=%s", ok, duration, list(data.keys()))
    return jsonify(data), status

@app.get("/healthz")
def healthz():
    return jsonify({"ok": True, "backend": BACKEND, "project": GCP_PROJECT, "creds": bool(GCP_CREDENTIALS)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
