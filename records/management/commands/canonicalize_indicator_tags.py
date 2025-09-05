from django.core.management.base import BaseCommand
from django.db.models import Exists, OuterRef

from records.models import (
    LabIndicator,
    DocumentTag,
    get_indicator_canonical_tag,
)

class Command(BaseCommand):
    help = (
        "Ensure every LabIndicator has a canonical Tag and optionally replace any "
        "non-canonical indicator tags on documents with the canonical one.\n\n"
        "Usage:\n"
        "  manage.py canonicalize_indicator_tags              # full pass\n"
        "  manage.py canonicalize_indicator_tags --only-missing  # only create missing canonical tags, do not touch documents"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--only-missing",
            action="store_true",
            help="Only create missing canonical tags for indicators. Do not rewrite document tags."
        )

    def handle(self, *args, **opts):
        only_missing = opts.get("only_missing", False)

        created_canonical = 0
        touched_docs = 0
        replaced_links = 0

        for ind in LabIndicator.objects.all().iterator():
            tag = get_indicator_canonical_tag(ind)
            if tag:
                created_canonical += 1

        if only_missing:
            self.stdout.write(self.style.SUCCESS(f"Canonical tags ensured for indicators: {created_canonical}"))
            return

        indicators = LabIndicator.objects.all()
        for ind in indicators.iterator():
            canonical = get_indicator_canonical_tag(ind)
            if not canonical:
                continue

            qs_links = (
                DocumentTag.objects
                .filter(tag__indicator=ind)
                .exclude(tag=canonical)
            )
            count = qs_links.count()
            if count:

                doc_ids = list(qs_links.values_list("document_id", flat=True))
                for doc_id in doc_ids:
                    DocumentTag.objects.get_or_create(document_id=doc_id, tag=canonical, defaults={"is_inherited": False})
                replaced_links += count

                qs_links.delete()
                touched_docs += len(set(doc_ids))

        self.stdout.write(self.style.SUCCESS(
            f"Canonical tags ensured: {created_canonical}; "
            f"documents touched: {touched_docs}; "
            f"replaced links: {replaced_links}"
        ))
