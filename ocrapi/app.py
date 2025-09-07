import os
import io
from flask import Flask, request, jsonify
from PIL import Image
import pytesseract

try:
    import fitz
except Exception:
    fitz = None

app = Flask(__name__)

def ocr_image_bytes(b):
    try:
        img = Image.open(io.BytesIO(b))
        return pytesseract.image_to_string(img) or ""
    except Exception:
        return ""

def ocr_pdf_bytes(b):
    if not fitz:
        return ""
    try:
        doc = fitz.open(stream=b, filetype="pdf")
        out = []
        for page in doc:
            pix = page.get_pixmap()
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            out.append(pytesseract.image_to_string(img) or "")
        return "\n".join([t.strip() for t in out if t]).strip()
    except Exception:
        return ""

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/ocr", methods=["POST"])
def ocr():
    f = request.files.get("file")
    if not f:
        return jsonify({"ocr_text": "", "source": "flask"}), 400
    name = (f.filename or "").lower()
    data = f.read()
    text = ""
    if name.endswith(".pdf"):
        text = ocr_pdf_bytes(data)
    else:
        text = ocr_image_bytes(data)
    return jsonify({"ocr_text": text or "", "source": "flask"}), 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
