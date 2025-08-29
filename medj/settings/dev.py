from .base import *

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


INSTALLED_APPS.append("django_browser_reload")
MIDDLEWARE.append("django_browser_reload.middleware.BrowserReloadMiddleware")
INTERNAL_IPS = ["127.0.0.1"]