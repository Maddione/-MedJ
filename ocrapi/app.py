from flask import Flask, request, jsonify
from google.cloud import vision
import base64

app = Flask(__name__)
vision_client = vision.ImageAnnotatorClient()

@app.route("/ocr", methods=["POST"])
def ocr():
    image = vision.Image()

    if "file" in request.files:
        content = request.files["file"].read()
        image.content = content
    else:
        data = request.get_json(silent=True) or {}
        img_b64 = data.get("image_b64")
        if not img_b64:
            return jsonify({"error": "No file or image_b64 provided"}), 400
        image.content = base64.b64decode(img_b64)

    response = vision_client.text_detection(image=image)
    if response.error.message:
        return jsonify({"error": response.error.message}), 500

    annotations = response.text_annotations
    full_text = annotations[0].description if annotations else ""

    return jsonify({
        "summary": "OCR ok",
        "data": {
            "full_text": full_text,
            "n_annotations": len(annotations),
        }
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(5000))
