from .base import *

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

INSTALLED_APPS = [
    *INSTALLED_APPS,
    "django_browser_reload",
]

MIDDLEWARE = [
    *MIDDLEWARE,
    "django_browser_reload.middleware.BrowserReloadMiddleware",
]
