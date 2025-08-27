import os

env = os.getenv('DJANGO_ENVIRONMENT', 'dev')

if env == 'prod':
    from .prod import *
else:
    from .dev import *
