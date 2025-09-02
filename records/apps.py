from django.apps import AppConfig
from django.db.models.signals import post_migrate

class RecordsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "records"

    def ready(self):
        from . import signals
        from .signals import post_migrate_sync
        post_migrate.connect(post_migrate_sync, sender=self, weak=False)
