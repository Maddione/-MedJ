from .base import *

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

INTERNAL_IPS = ["127.0.0.1"]

STATIC_URL = "/static/"

OCR_API_URL = os.environ.get("OCR_API_URL", "http://ocrapi:5000/ocr")
