import os
import io
from PIL import Image
import base64
import requests
import json

from google.cloud import vision
from google.oauth2 import service_account

GOOGLE_CLOUD_VISION_KEY = os.environ.get('GOOGLE_CLOUD_VISION_KEY')
VISION_CLIENT = None
if GOOGLE_CLOUD_VISION_KEY:
    try:
        if os.path.exists(GOOGLE_CLOUD_VISION_KEY):
            credentials = service_account.Credentials.from_service_account_file(GOOGLE_CLOUD_VISION_KEY)
        else:
            credentials_info = json.loads(GOOGLE_CLOUD_VISION_KEY)
            credentials = service_account.Credentials.from_service_account_info(credentials_info)

        VISION_CLIENT = vision.ImageAnnotatorClient(credentials=credentials)
    except Exception as e:
        VISION_CLIENT = None
else:
    pass


def extract_text_from_image(image_path: str) -> str:
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found at {image_path}")

    if VISION_CLIENT:
        try:
            with io.open(image_path, 'rb') as image_file:
                content = image_file.read()
            image = vision.Image(content=content)
            response = VISION_CLIENT.document_text_detection(image=image)
            return response.full_text_annotation.text
        except Exception as e:
            pass

    raise RuntimeError("Нито един конфигуриран OCR метод не успя да извлече текст от изображението.")


def perform_ocr_space(file_path: str) -> str:
    return extract_text_from_image(file_path)