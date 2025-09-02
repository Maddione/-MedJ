import os
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings

class Command(BaseCommand):
    def handle(self, *args, **opts):
        call_command("migrate", database="default")
        if "backup" in settings.DATABASES:
            call_command("migrate", database="backup")
        path = os.environ.get("LABTESTS_CSV_PATH")
        if path and os.path.exists(path):
            call_command("import_lab_indicators_csv", path, "--update")
            call_command("canonicalize_indicator_tags")
        call_command("sync_taxonomy_tags")
        su_user = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        su_email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
        su_pass = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        if su_user and su_pass:
            try:
                from django.contrib.auth import get_user_model
                U = get_user_model()
                if not U.objects.filter(username=su_user).exists():
                    U.objects.create_superuser(username=su_user, email=su_email or "", password=su_pass)
            except Exception:
                pass
