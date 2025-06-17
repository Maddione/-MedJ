import io
import os
import re
import uuid
from dotenv import load_dotenv
from google.cloud import vision
from django.conf import settings

load_dotenv()

credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if credentials_path:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
    client = vision.ImageAnnotatorClient()
else:
    client = None

TEMP_UPLOAD_DIR = os.path.join(settings.MEDIA_ROOT, 'temp_ocr_uploads')
os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)


def extract_text_from_image(image_path):
    """Извлича текст от изображение чрез Google Cloud Vision API."""
    if client is None:
        print("Error: Google Cloud Vision клиентът не е инициализиран. Проверете GOOGLE_APPLICATION_CREDENTIALS.")
        return ""

    try:
        with io.open(image_path, 'rb') as image_file:
            content = image_file.read()

        image = vision.Image(content=content)
        response = client.text_detection(image=image)

        texts = response.text_annotations
        if texts:
            return texts[0].description
        return ""
    except Exception as e:
        print(f"Error extracting text from image with Vision API: {e}")
        return ""


def perform_ocr_space(uploaded_file) -> str:
    """
    Извършва OCR върху качен файл (изображение или PDF) и връща извлечения текст.
    Временно записва файла на диск за обработка от Vision API.
    """
    if client is None:
        return "Google Cloud Vision API клиентът не е конфигуриран."

    unique_filename = str(uuid.uuid4()) + os.path.splitext(uploaded_file.name)[1]
    temp_file_path = os.path.join(TEMP_UPLOAD_DIR, unique_filename)

    with open(temp_file_path, 'wb+') as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)

    extracted_text = ""
    try:
        extracted_text = extract_text_from_image(temp_file_path)
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

    return extracted_text


def extract_medical_fields_from_text(text):
    """
    Търси ключови медицински стойности в текста и ги връща като речник.
    """
    fields = {
        "TSH": r"TSH\s*[:=]?\s*(\d+[.,]?\d*)",
        "Глюкоза": r"Глюкоза\s*[:=]?\s*(\d+[.,]?\d*)",
        "Дата": r"(\d{2}[./-]\d{2}[./-]\d{4})"
    }

    results = {}
    for key, pattern in fields.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            results[key] = match.group(1).replace(",", ".")
    return results