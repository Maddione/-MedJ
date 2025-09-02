from pathlib import Path
import os
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-secret-key")
DEBUG = False
ALLOWED_HOSTS = []

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
    "records.apps.RecordsConfig",
    "django_browser_reload",
    "widget_tweaks",
]
MEDJ_TAG_SYNC_ENABLED = True

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
    "records.middleware.onboarding.OnboardingMiddleware",

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
                "django.template.context_processors.i18n",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
            ],
        },
    },
]

WSGI_APPLICATION = "MedJ2.wsgi.application"

AUTH_USER_MODEL = "records.User"
AUTHENTICATION_BACKENDS = [
    "records.auth_backends.EmailOrUsernameBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "bg"
LANGUAGES = [
    ("bg", _("Български")),
    ("en-us", "English (US)"),
]
USE_I18N = True
LOCALE_PATHS = [BASE_DIR / "locale"]

TIME_ZONE = "Europe/Sofia"
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
TAILWIND_APP_NAME = "theme"

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/login/"

SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 7200
SESSION_SAVE_EVERY_REQUEST = True

PARLER_LANGUAGES = {
    None: (
        {"code": "bg"},
        {"code": "en-us"},
    ),
    "default": {
        "fallbacks": ["bg"],
        "hide_untranslated": False,
        "default": True,
    },
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "medj"),
        "USER": os.environ.get("POSTGRES_USER", "medj"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "medj"),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": int(os.environ.get("POSTGRES_PORT", "5432")),
    },
    "backup": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "backup.sqlite3",
    },
}
BACKUP_DB_ALIAS = "backup"

WSGI_APPLICATION = "medj.wsgi.application"

