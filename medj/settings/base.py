from pathlib import Path
import os
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent.parent

def as_bool(val: str, default=False):
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "y", "on"}

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-dev-key")
DEBUG = as_bool(os.getenv("DJANGO_DEBUG", os.getenv("DEBUG", "1")), default=True)
ALLOWED_HOSTS = (
    os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",")
    if os.getenv("DJANGO_ALLOWED_HOSTS")
    else []
)
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "parler",
    "tailwind",
    "theme",
    "records",
    "django_browser_reload",
    "widget_tweaks",
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
    "django_browser_reload.middleware.BrowserReloadMiddleware",
]
ROOT_URLCONF = "medj.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "records" / "templates"],
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
WSGI_APPLICATION = "medj.wsgi.application"
ASGI_APPLICATION = "medj.asgi.application"
DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.getenv("DB_NAME", BASE_DIR / "db.sqlite3"),
    }
}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "bg"
LANGUAGES = [
    ("bg", _("Bulgarian")),
    ("en", "English"),
]
LOCALE_PATHS = [os.path.join(BASE_DIR, "locale")]
TIME_ZONE = "Europe/Sofia"
USE_I18N = True
USE_L10N = True
USE_TZ = True
AUTH_USER_MODEL = "records.User"
STATIC_URL = "/static/"
STATICFILES_DIRS = []
_static = BASE_DIR / "theme" / "static"
if _static.exists():
    STATICFILES_DIRS.append(_static)
STATIC_ROOT = BASE_DIR / "staticfiles_collected"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
TAILWIND_APP_NAME = "theme"
LOGIN_URL = "medj:login"
LOGIN_REDIRECT_URL = "medj:dashboard"
LOGOUT_REDIRECT_URL = "medj:landing"

PARLER_LANGUAGES = {
    None: (
        {'code': 'bg',},
        {'code': 'en',},
    ),
    'default': {
        'fallback': 'bg',
        'hide_untranslated': False,
    }
}