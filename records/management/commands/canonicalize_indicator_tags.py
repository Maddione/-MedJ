from django.core.management.base import BaseCommand
from records.models import LabIndicator, get_indicator_canonical_tag

class Command(BaseCommand):
    def handle(self, *args, **opts):
        n = 0
        for ind in LabIndicator.objects.all():
            get_indicator_canonical_tag(ind)
            n += 1
        self.stdout.write(self.style.SUCCESS(f"Canonical tags refreshed: {n}"))
