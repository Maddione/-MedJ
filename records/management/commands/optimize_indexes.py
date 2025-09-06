from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    def handle(self, *args, **options):
        vendor = connection.vendor
        with connection.cursor() as c:
            if vendor in ("postgresql", "sqlite"):
                c.execute("CREATE INDEX IF NOT EXISTS records_sharelink_token_idx ON records_sharelink (token)")
                c.execute("CREATE INDEX IF NOT EXISTS records_sharelink_owner_idx ON records_sharelink (owner_id)")
                c.execute("CREATE INDEX IF NOT EXISTS records_labtestmeasurement_event_measured_idx ON records_labtestmeasurement (medical_event_id, measured_at)")
            elif vendor == "mysql":
                c.execute("CREATE INDEX records_sharelink_token_idx ON records_sharelink (token)")
                c.execute("CREATE INDEX records_sharelink_owner_idx ON records_sharelink (owner_id)")
                c.execute("CREATE INDEX records_labtestmeasurement_event_measured_idx ON records_labtestmeasurement (medical_event_id, measured_at)")
