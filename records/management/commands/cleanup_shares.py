from django.core.management.base import BaseCommand
from django.utils import timezone
from records.models import ShareToken

class Command(BaseCommand):
    help = "Deactivate expired share tokens"

    def handle(self, *args, **options):
        now = timezone.now()
        qs = ShareToken.objects.filter(is_active=True, expires_at__lte=now)
        count = qs.update(is_active=False)
        self.stdout.write(self.style.SUCCESS(f"Deactivated {count} expired share tokens"))
