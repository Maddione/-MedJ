from .base import *

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

INTERNAL_IPS = ["127.0.0.1"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "no-reply@medj.local"

CSRF_TRUSTED_ORIGINS = ["http://localhost:8000", "http://127.0.0.1:8000"]

STATIC_URL = "/static/"
MEDIA_URL = "/media/"

OCR_API_URL = os.environ.get("OCR_API_URL", "http://ocrapi:5000/ocr")
