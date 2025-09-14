from flask import Flask, request, jsonify
import os, io, json, base64, re, uuid, time, logging
from PIL import Image, ImageOps, ImageFilter
from google.cloud import vision
from google.oauth2 import service_account
from .normalizer import normalize_ocr_text, load_lab_db

try:
    from .anonymizer import anonymize_text
except Exception:
    def anonymize_text(x: str) -> str: return x

LEVEL = os.environ.get("OCR_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("ocrapi")

app = Flask(__name__)

def _lang_hints():
    env = os.environ.get("GOOGLE_VISION_LANGUAGE_HINTS", "en,bg")
    return [x.strip() for x in env.split(",") if x.strip()]

def _tess_langs():
    return os.environ.get("TESSERACT_LANGS", "eng+bul")

def build_client() -> vision.ImageAnnotatorClient | None:
    p = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    j = os.environ.get("GOOGLE_CLOUD_VISION_KEY")
    if j:
        try:
            info = json.loads(j)
            creds = service_account.Credentials.from_service_account_info(info)
            return vision.ImageAnnotatorClient(credentials=creds)
        except Exception as e:
            log.error("vision inline-cred fail: %s", e)
    if p and os.path.exists(p):
        try:
            creds = service_account.Credentials.from_service_account_file(p)
            return vision.ImageAnnotatorClient(credentials=creds)
        except Exception as e:
            log.error("vision file-cred fail: %s", e)
    try:
        return vision.ImageAnnotatorClient()
    except Exception as e:
        log.error("vision default client fail: %s", e)
        return None

def _preprocess_image_bytes(b: bytes) -> bytes:
    im = Image.open(io.BytesIO(b))
    if im.mode not in ("L", "RGB"): im = im.convert("RGB")
    w, h = im.size
    if w < 1600:
        scale = 1600.0 / float(w)
        im = im.resize((int(w*scale), int(h*scale)), Image.BICUBIC)
    im = im.convert("L")
    im = ImageOps.autocontrast(im, cutoff=2)
    im = im.filter(ImageFilter.UnsharpMask(radius=1.0, percent=120, threshold=2))
    buf = io.BytesIO(); im.save(buf, format="PNG")
    return buf.getvalue()

def _vision_once(payload: bytes, client, rid: str, tag: str):
    if not client: return ""
    try:
        t0 = time.perf_counter()
        img = vision.Image(content=payload)
        ctx = vision.ImageContext(language_hints=_lang_hints())
        r = client.document_text_detection(image=img, image_context=ctx)
        dt = (time.perf_counter()-t0)*1000
        if getattr(r, "error", None) and getattr(r.error, "message", ""):
            log.warning("%s vision.%s error=%s dt=%.1fms", rid, tag, r.error.message, dt)
            return ""
        text = ""
        fta = getattr(r, "full_text_annotation", None)
        if fta and getattr(fta, "text", None):
            text = fta.text or ""
        elif getattr(r, "text_annotations", None):
            tas = r.text_annotations
            text = tas[0].description if tas else ""
        text = anonymize_text((text or "").strip())
        log.info("%s vision.%s len=%d dt=%.1fms", rid, tag, len(text), dt)
        return text
    except Exception as e:
        log.exception("%s vision.%s exception: %s", rid, tag, e)
        return ""

def _vision_image(b, client, rid: str):
    txt = _vision_once(_preprocess_image_bytes(b), client, rid, "pre")
    if not txt:
        txt = _vision_once(b, client, rid, "raw")
    return txt

def _tess_once(payload: bytes, cfg: str, rid: str, tag: str):
    import pytesseract
    t0 = time.perf_counter()
    im = Image.open(io.BytesIO(payload))
    try:
        t = pytesseract.image_to_string(im, lang=_tess_langs(), config=cfg) or ""
        t = anonymize_text(t.strip())
        dt = (time.perf_counter()-t0)*1000
        log.info("%s tesseract.%s len=%d cfg='%s' dt=%.1fms", rid, tag, len(t), cfg, dt)
        return t
    except Exception as e:
        log.exception("%s tesseract.%s exception: %s", rid, tag, e)
        return ""

def _tess_image(b, rid: str):
    cfg = "--psm 6 -c preserve_interword_spaces=1"
    txt = _tess_once(_preprocess_image_bytes(b), cfg, rid, "pre")
    if not txt:
        txt = _tess_once(b, cfg, rid, "raw")
    return txt

def _image_ocr(b, client, rid: str):
    v = _vision_image(b, client, rid)
    t = _tess_image(b, rid)
    out = v if len(v) >= len(t) else t
    log.info("%s choose=%s vlen=%d tlen=%d", rid, ("vision" if out is v else "tesseract"), len(v), len(t))
    return out

def _pdf_ocr(b, client, rid: str):
    from pdf2image import convert_from_bytes
    pages = convert_from_bytes(b, dpi=400, fmt="png")
    log.info("%s pdf pages=%d", rid, len(pages))
    out = []
    for idx, p in enumerate(pages, 1):
        buf = io.BytesIO(); p.save(buf, format="PNG")
        log.info("%s page=%d size=%d", rid, idx, len(buf.getvalue()))
        out.append(_image_ocr(buf.getvalue(), client, rid))
    txt = "\n".join([x for x in out if x]).strip()
    log.info("%s pdf-ocr total_len=%d", rid, len(txt))
    return txt

def _decode_payload_file(req, rid: str):
    f = req.files.get("file")
    b64 = req.form.get("image_base64") or (req.json.get("image_base64") if req.is_json else None)
    kind = (req.form.get("file_kind") or (req.json.get("file_kind") if req.is_json else None) or "").lower()
    if f:
        data = f.read(); name = f.filename or ""
        k = "pdf" if name.lower().endswith(".pdf") else (kind or "image")
        log.info("%s decode file name=%s size=%d kind=%s", rid, name, len(data), k)
        return data, k
    if b64:
        try:
            data = base64.b64decode(b64)
            log.info("%s decode base64 size=%d kind=%s", rid, len(data), kind or "image")
            return data, (kind or "image")
        except Exception as e:
            log.error("%s decode base64 fail: %s", rid, e)
            return b"", ""
    log.warning("%s decode empty payload", rid)
    return b"", ""

_unit_re = re.compile(r"\b(?:g/dL|mg/dL|µg/dL|ug/dL|ng/mL|pg/mL|IU/L|mIU/L|U/L|kU/L|mmol/L|mol/L|mEq/L|µmol/L|nmol/L|pmol/L|fL|pg|%)\b|×10\^3/µL|×10\^6/µL")

def _metrics(text: str, csv_path: str):
    try:
        names, _ = load_lab_db(csv_path)
    except Exception:
        names = []
    units_found = len(set(_unit_re.findall(text)))
    indicators_found = 0
    if names:
        t = text
        for n in names:
            if n and n in t:
                indicators_found += 1
    return units_found, indicators_found

@app.post("/ocr")
def ocr():
    rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    try:
        blob, kind = _decode_payload_file(request, rid)
        if not blob:
            log.warning("%s no_file", rid)
            return jsonify(error="no_file", rid=rid), 200

        client = build_client()
        csv_path = os.environ.get("LAB_DB_CSV", "/app/data/labtests-database.csv")

        if kind == "pdf":
            raw = _pdf_ocr(blob, client, rid)
            if not raw:
                log.warning("%s empty_ocr after pdf pipeline", rid)
                return jsonify(error="empty_ocr", stage="pdf_pipeline", rid=rid), 200
            txt = normalize_ocr_text(raw, csv_path) or raw
            u, i = _metrics(txt, csv_path)
            log.info("%s normalized len=%d units=%d indicators=%d", rid, len(txt), u, i)
            return jsonify(engine="vision+tesseract", ocr_text=txt, units_found=u, indicators_found=i, rid=rid), 200

        raw = _image_ocr(blob, client, rid)
        if not raw:
            log.warning("%s empty_ocr after image pipeline", rid)
            return jsonify(error="empty_ocr", stage="image_pipeline", rid=rid), 200
        txt = normalize_ocr_text(raw, csv_path) or raw
        u, i = _metrics(txt, csv_path)
        eng = "vision" if client else "tesseract"
        log.info("%s normalized len=%d units=%d indicators=%d", rid, len(txt), u, i)
        return jsonify(engine=eng, ocr_text=txt, units_found=u, indicators_found=i, rid=rid), 200

    except Exception as ex:
        log.exception("%s ocr_unhandled: %s", rid, ex)
        return jsonify(error="ocr_unhandled", detail=str(ex), rid=rid), 200
