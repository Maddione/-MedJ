from .base import *
DEBUG = True
ALLOWED_HOSTS = ["*", "localhost", "127.0.0.1"]
CSRF_TRUSTED_ORIGINS = ["http://localhost:8000", "http://127.0.0.1:8000"]
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = False
DATABASES["default"]["HOST"] = os.environ.get("POSTGRES_HOST", "db")
DATABASES["default"]["PORT"] = os.environ.get("POSTGRES_PORT", "5432")
DATABASES["default"]["NAME"] = os.environ.get("POSTGRES_DB", "medj")
DATABASES["default"]["USER"] = os.environ.get("POSTGRES_USER", "medj")
DATABASES["default"]["PASSWORD"] = os.environ.get("POSTGRES_PASSWORD", "medj")

DATABASES["backup"] = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": BASE_DIR / "backup.sqlite3",
}
