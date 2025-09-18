from __future__ import annotations

import json

from django.core.management.base import BaseCommand
from django.db import transaction

from records.models import Document
from records.utils.analysis import (
    compose_analysis_text,
    normalize_analysis_payload,
    render_analysis_tables,
    word_count,
)


class Command(BaseCommand):
    help = "Backfill Document.analysis_html and analysis_text from stored analysis notes."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Only report the documents that would be updated.")
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Optional cap on the number of documents to process.",
        )

    def handle(self, *args, **options):
        dry_run: bool = options.get("dry_run", False)
        limit: int | None = options.get("limit")
        updated = 0
        processed = 0

        qs = Document.objects.all().order_by("id")
        if limit is not None:
            if limit <= 0:
                qs = qs.none()
            else:
                qs = qs[:limit]

        for doc in qs.iterator():
            processed += 1
            payload = {}
            raw_notes = getattr(doc, "notes", None)
            if isinstance(raw_notes, dict):
                payload = raw_notes
            elif isinstance(raw_notes, str) and raw_notes.strip():
                try:
                    payload = json.loads(raw_notes)
                except Exception:
                    payload = {}
            analysis_payload = normalize_analysis_payload(payload.get("analysis"))
            if not analysis_payload:
                continue
            summary = (analysis_payload.get("summary") or doc.summary or "").strip()
            if summary:
                analysis_payload["summary"] = summary
                analysis_payload["summary_word_count"] = word_count(summary)
            html = render_analysis_tables(analysis_payload)
            text = compose_analysis_text(analysis_payload, summary)
            has_changes = False
            update_fields: list[str] = []
            if html and html != (doc.analysis_html or ""):
                has_changes = True
                if not dry_run:
                    doc.analysis_html = html
                    update_fields.append("analysis_html")
            if text and text != (doc.analysis_text or ""):
                has_changes = True
                if not dry_run:
                    doc.analysis_text = text
                    update_fields.append("analysis_text")
            if summary and summary != (doc.summary or ""):
                has_changes = True
                if not dry_run:
                    doc.summary = summary
                    update_fields.append("summary")
            if has_changes:
                updated += 1
                self.stdout.write(f"Document #{doc.id} will be updated ({', '.join(update_fields) or 'no fields'})")
                if not dry_run and update_fields:
                    with transaction.atomic():
                        doc.save(update_fields=update_fields)
        if dry_run:
            self.stdout.write(self.style.WARNING(f"Dry run completed. {updated} documents require updates."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Backfill complete. Updated {updated} documents (processed {processed})."))
