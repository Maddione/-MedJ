import os
import io
from PIL import Image
import base64
import requests
import json

from google.cloud import vision
from google.oauth2 import service_account

GOOGLE_CLOUD_VISION_KEY = os.environ.get('GOOGLE_CLOUD_VISION_KEY')
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')

VISION_CLIENT = None

for candidate in (GOOGLE_CLOUD_VISION_KEY, GOOGLE_APPLICATION_CREDENTIALS):
    if not candidate:
        continue
    try:
        if os.path.exists(candidate):
            credentials = service_account.Credentials.from_service_account_file(candidate)
        else:
            credentials = service_account.Credentials.from_service_account_info(json.loads(candidate))
        VISION_CLIENT = vision.ImageAnnotatorClient(credentials=credentials)
        break
    except Exception:
        VISION_CLIENT = None

if VISION_CLIENT is None:
    try:
        VISION_CLIENT = vision.ImageAnnotatorClient()
    except Exception:
        VISION_CLIENT = None



def extract_text_from_image(image_path: str) -> str:
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found at {image_path}")

    if VISION_CLIENT:
        try:
            with io.open(image_path, 'rb') as image_file:
                content = image_file.read()
            image = vision.Image(content=content)
            response = VISION_CLIENT.document_text_detection(image=image)

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