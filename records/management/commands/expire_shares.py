from django.core.management.base import BaseCommand
from django.utils.timezone import now
from records.models import ShareLink

class Command(BaseCommand):
    def handle(self, *args, **options):
        qs = ShareLink.objects.filter(status="active", expires_at__lt=now())
        for s in qs:
            s.status = "expired"
            s.save(update_fields=["status"])
