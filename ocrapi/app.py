from flask import Flask, request, jsonify
import os, io, json, base64, re
from PIL import Image, ImageOps, ImageFilter
from google.cloud import vision
from google.oauth2 import service_account
from .normalizer import normalize_ocr_text, load_lab_db

try:
    from .anonymizer import anonymize_text
except Exception:
    def anonymize_text(x: str) -> str: return x

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
        except Exception: pass
    if p and os.path.exists(p):
        try:
            creds = service_account.Credentials.from_service_account_file(p)
            return vision.ImageAnnotatorClient(credentials=creds)
        except Exception: pass
    try: return vision.ImageAnnotatorClient()
    except Exception: return None

def _preprocess_image_bytes(b: bytes) -> bytes:
    im = Image.open(io.BytesIO(b))
    if im.mode not in ("L", "RGB"): im = im.convert("RGB")
    w, h = im.size
    if w < 1600:
        scale = 1600.0 / float(w)
        im = im.resize((int(w*scale), int(h*scale)), Image.BICUBIC)
    im = im.convert("L")
    im = ImageOps.autocontrast(im, cutoff=2)
    im = im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=150, threshold=2))
    im = im.point(lambda p: 255 if p > 180 else 0, mode="1")
    buf = io.BytesIO(); im.save(buf, format="PNG")
    return buf.getvalue()

def _vision_image(b, client):
    if not client: return ""
    try:
        pb = _preprocess_image_bytes(b)
        img = vision.Image(content=pb)
        ctx = vision.ImageContext(language_hints=_lang_hints())
        r = client.document_text_detection(image=img, image_context=ctx)
        if getattr(r, "error", None) and getattr(r.error, "message", ""):
            raise RuntimeError(r.error.message)
        fta = getattr(r, "full_text_annotation", None)
        if fta and getattr(fta, "text", None):
            return anonymize_text((fta.text or "").strip())
        tas = getattr(r, "text_annotations", None)
        if tas:
            return anonymize_text((tas[0].description or "").strip())
    except Exception:
        pass
    return ""

def _tess_image(b):
    import pytesseract
    pb = _preprocess_image_bytes(b)
    im = Image.open(io.BytesIO(pb))
    cfg = "--psm 6 -c preserve_interword_spaces=1"
    txt = pytesseract.image_to_string(im, lang=_tess_langs(), config=cfg) or ""
    return anonymize_text(txt.strip())

def _image_ocr(b, client):
    txt = _vision_image(b, client)
    if not txt:
        txt = _tess_image(b)
    return txt

def _pdf_ocr(b, client):
    from pdf2image import convert_from_bytes
    pages = convert_from_bytes(b, dpi=400, fmt="png")
    out = []
    for p in pages:
        buf = io.BytesIO(); p.save(buf, format="PNG")
        out.append(_image_ocr(buf.getvalue(), client))
    return "\n".join([x for x in out if x]).strip()

def _decode_payload_file(req):
    f = req.files.get("file")
    b64 = req.form.get("image_base64") or (req.json.get("image_base64") if req.is_json else None)
    kind = (req.form.get("file_kind") or (req.json.get("file_kind") if req.is_json else None) or "").lower()
    if f:
        data = f.read(); name = f.filename or ""
        return data, ("pdf" if name.lower().endswith(".pdf") else (kind or "image"))
    if b64:
        try: return base64.b64decode(b64), (kind or "image")
        except Exception: return b"", ""
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
    try:
        blob, kind = _decode_payload_file(request)
        if not blob:
            return jsonify(error="no_file"), 200
        client = build_client()
        csv_path = os.environ.get("LAB_DB_CSV", "/app/data/labtests-database.csv")
        if kind == "pdf":
            raw = _pdf_ocr(blob, client)
            if not raw:
                return jsonify(error="empty_ocr"), 200
            txt = normalize_ocr_text(raw, csv_path)
            u, i = _metrics(txt, csv_path)
            return jsonify(engine="vision+tesseract", ocr_text=txt, units_found=u, indicators_found=i), 200
        raw = _image_ocr(blob, client)
        if not raw:
            return jsonify(error="empty_ocr"), 200
        txt = normalize_ocr_text(raw, csv_path)
        u, i = _metrics(txt, csv_path)
        eng = "vision" if client else "tesseract"
        return jsonify(engine=eng, ocr_text=txt, units_found=u, indicators_found=i), 200
    except Exception as ex:
        return jsonify(error="ocr_unhandled", detail=str(ex)), 200
