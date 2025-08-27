from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent

def as_bool(val: str, default=False):
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "y", "on"}

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-dev-key")

DEBUG = as_bool(os.getenv("DJANGO_DEBUG", os.getenv("DEBUG", "1")), default=True)

ALLOWED_HOSTS = (
    os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",")
    if os.getenv("DJANGO_ALLOWED_HOSTS") else []
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "records",
    "parler",
    "tailwind",
    "theme",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "medj.urls"
WSGI_APPLICATION = "medj.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

if os.getenv("POSTGRES_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "medj"),
            "USER": os.getenv("POSTGRES_USER", "medj"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", "medjpass"),
            "HOST": os.getenv("POSTGRES_HOST", "db"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "records.User"

LANGUAGE_CODE = "bg"
LANGUAGES = [
    ("bg", "Bulgarian"),
    ("en", "English"),
]

PARLER_DEFAULT_LANGUAGE_CODE = "bg"
PARLER_LANGUAGES = {
    None: (
        {"code": "bg"},
        {"code": "en"},
    ),
    "default": {
        "fallbacks": ["bg"],
        "hide_untranslated": False,
    },
}

LOCALE_PATHS = [os.path.join(BASE_DIR, "locale")]

TIME_ZONE = "Europe/Sofia"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = []
for p in [BASE_DIR / "static"]:
     if p.exists():
         STATICFILES_DIRS.append(p)

STATIC_ROOT = BASE_DIR / "staticfiles_collected"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

TAILWIND_APP_NAME = "theme"
