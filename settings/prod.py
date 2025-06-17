from .base import *
import os

# --- СИГУРНОСТ ЗА ПРОДУКЦИЯ ---
DEBUG = False

ALLOWED_HOSTS = ['medj.eu', 'www.medj.eu']

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- НАСТРОЙКИ ЗА СИГУРНОСТ ---

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True