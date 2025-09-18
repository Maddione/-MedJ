import hashlib
from django.core.management.base import BaseCommand
from django.db import IntegrityError
from django.db.models import Q
from records.models import Document


class Command(BaseCommand):
    help = "Compute and backfill SHA-256 content hashes for existing documents."

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=200,
            help="Number of documents to iterate per database batch (default: 200).",
        )

    def handle(self, *args, **options):
        batch_size = max(1, int(options.get("batch_size") or 200))
        qs = (
            Document.objects.filter(Q(content_hash__isnull=True) | Q(content_hash=""))
            .select_related("owner")
            .order_by("id")
        )
        total = qs.count()
        if not total:
            self.stdout.write(self.style.SUCCESS("All documents already have a content hash."))
            return

        processed = 0
        updated = 0
        skipped = 0
        duplicates = 0

        for doc in qs.iterator(chunk_size=batch_size):
            processed += 1
            file_field = doc.file
            if not file_field:
                skipped += 1
                continue

            try:
                file_field.open("rb")
            except Exception as exc:
                skipped += 1
                self.stderr.write(f"Failed to open file for document {doc.id}: {exc}")
                continue

            hasher = hashlib.sha256()
            try:
                for chunk in file_field.chunks():
                    hasher.update(chunk)
            finally:
                try:
                    file_field.close()
                except Exception:
                    pass

            digest = hasher.hexdigest()
            if not digest:
                skipped += 1
                continue

            if doc.content_hash == digest and doc.sha256 == digest:
                continue

            doc.content_hash = digest
            if not doc.sha256:
                doc.sha256 = digest

            try:
                doc.save(update_fields=["content_hash", "sha256"])
                updated += 1
            except IntegrityError:
                dup = (
                    Document.objects.filter(owner=doc.owner, content_hash=digest)
                    .exclude(pk=doc.pk)
                    .first()
                )
                if dup:
                    duplicates += 1
                    self.stderr.write(
                        f"Duplicate detected for owner {doc.owner_id}: doc {doc.pk} duplicates {dup.pk}"
                    )
                    continue
                raise

        summary = (
            f"Processed {processed} of {total} documents. Updated: {updated}. "
            f"Skipped: {skipped}. Duplicates: {duplicates}."
        )
        if updated:
            self.stdout.write(self.style.SUCCESS(summary))
        else:
            self.stdout.write(summary)
