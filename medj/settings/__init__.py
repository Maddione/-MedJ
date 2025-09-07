import os

env = os.getenv("DJANGO_ENVIRONMENT", "dev").strip().lower()

if env == "prod":
    from .prod import *
else:
    from .dev import *

AUTH_USER_MODEL = "auth.User"
