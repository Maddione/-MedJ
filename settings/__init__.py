import os

env = os.getenv('ENVIRONMENT', 'dev')

if env == 'prod':
    from .prod import *
else:
    from .dev import *