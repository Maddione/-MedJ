import os
import io
import json

from google.cloud import vision
from google.oauth2 import service_account

try:
    from .anonymizer import anonymize_text
except Exception:  # pragma: no cover
    def anonymize_text(text: str) -> str:
        return text

GOOGLE_CLOUD_VISION_KEY = os.environ.get("GOOGLE_CLOUD_VISION_KEY")
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

VISION_CLIENT = None


def _init_vision_client():
    """Lazily construct the Vision API client if credentials are configured."""
    global VISION_CLIENT
    if VISION_CLIENT is not None:
        return VISION_CLIENT

    creds_source = GOOGLE_CLOUD_VISION_KEY or GOOGLE_APPLICATION_CREDENTIALS
    if not creds_source:
        return None

    try:
        if os.path.exists(creds_source):
            credentials = service_account.Credentials.from_service_account_file(creds_source)
        else:
            credentials = service_account.Credentials.from_service_account_info(json.loads(creds_source))
        VISION_CLIENT = vision.ImageAnnotatorClient(credentials=credentials)
    except Exception:
        VISION_CLIENT = None
    return VISION_CLIENT



def extract_text_from_image(image_path: str) -> str:
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found at {image_path}")

    client = _init_vision_client()
    if client:
        try:
            with io.open(image_path, "rb") as image_file:
                content = image_file.read()
            image = vision.Image(content=content)
            response = client.document_text_detection(image=image)

            full_text = ""
            if getattr(response, "full_text_annotation", None) and getattr(response.full_text_annotation, "text", None):
                full_text = response.full_text_annotation.text or ""
            elif getattr(response, "text_annotations", None):
                full_text = (response.text_annotations[0].description or "") if response.text_annotations else ""

            return anonymize_text(full_text)
        except Exception:
            pass

    raise RuntimeError("Нито един конфигуриран OCR метод не успя да извлече текст от изображението.")


def perform_ocr_space(file_path: str) -> str:
    return extract_text_from_image(file_path)