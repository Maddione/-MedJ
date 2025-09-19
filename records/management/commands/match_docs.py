import json
import mimetypes
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import now

from records.models import Document  # records_document

def guess_mime(path: Path) -> str:
    mt, _ = mimetypes.guess_type(path.name)
    return mt or "application/octet-stream"

class Command(BaseCommand):
    help = "Match local media/documents files to records_document by sha256, fix paths, and optionally create missing docs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--map",
            default="document_file_map.json",
            help="JSON от PowerShell join-а: [{id, sha256, file_db, file_local, title}]",
        )
        parser.add_argument(
            "--media-root",
            default="media/documents",
            help="Локална папка с файловете (от гледна точка на контейнера/web).",
        )
        parser.add_argument(
            "--create-missing",
            action="store_true",
            help="Създава записи за файлове, които ги няма в БД.",
        )
        parser.add_argument(
            "--defaults",
            default="owner_id=3,category_id=6,doc_type_id=1,specialty_id=3",
            help="Дефолти за нови записи: owner_id=...,category_id=...,doc_type_id=...,specialty_id=...",
        )
        parser.add_argument("--dry-run", action="store_true", help="Само показва промените.")

    def handle(self, *args, **opts):
        mp = Path(opts["map"])
        media_root = Path(opts["media_root"])
        if not mp.exists():
            self.stderr.write(self.style.ERROR(f"Map file not found: {mp}"))
            return

        with mp.open("r", encoding="utf-8") as f:
            items = json.load(f)

        # Индекси
        by_sha = {}
        for d in Document.objects.all().only("id", "sha256", "file", "title"):
            if d.sha256:
                by_sha.setdefault(d.sha256, []).append(d)

        # parse defaults
        defaults = {}
        for kv in opts["defaults"].split(","):
            k, v = kv.split("=", 1)
            defaults[k.strip()] = int(v.strip())

        updates, duplicates, not_found_local, created = [], [], [], []

        @transaction.atomic
        def apply():
            for it in items:
                sha = (it.get("sha256") or "").strip()
                file_local = it.get("file_local")
                if not sha:
                    continue

                # 1) актуализация на съществуващ запис/и
                docs = by_sha.get(sha, [])
                if docs:
                    if len(docs) > 1:
                        duplicates.append(
                            {"sha256": sha, "ids": [d.id for d in docs]}
                        )
                    for d in docs:
                        # желан относителен път в медия
                        if file_local:
                            desired = f"documents/{file_local}"
                            full = media_root / file_local
                        else:
                            desired = d.file  # няма ново име
                            full = media_root / Path(d.file).name

                        size = full.stat().st_size if full.exists() else None
                        mime = guess_mime(full)

                        changed = {}
                        if file_local and d.file != desired:
                            changed["file"] = (d.file, desired)
                            d.file = desired
                        if size and getattr(d, "file_size", None) != size:
                            changed["file_size"] = (getattr(d, "file_size", None), size)
                            d.file_size = size
                        if (getattr(d, "file_mime", "") or "") != mime:
                            changed["file_mime"] = (getattr(d, "file_mime", ""), mime)
                            d.file_mime = mime
                        if not d.title and it.get("title"):
                            changed["title"] = (d.title, it["title"])
                            d.title = it["title"]

                        if changed:
                            updates.append({"id": d.id, "changes": changed})
                            if not opts["dry_run"]:
                                d.save()

                        if not full.exists():
                            not_found_local.append({"id": d.id, "expected": str(full)})

                # 2) създаване на липсващ запис (ако е позволено)
                elif opts["create-missing"] and file_local:
                    full = media_root / file_local
                    if not full.exists():
                        not_found_local.append({"sha256": sha, "expected": str(full)})
                        continue
                    d = Document(
                        document_date=now().date(),
                        date_created=now().date(),
                        uploaded_at=now(),
                        file=f"documents/{file_local}",
                        file_size=full.stat().st_size,
                        file_mime=guess_mime(full),
                        doc_kind="image" if guess_mime(full).startswith("image/") else "file",
                        sha256=sha,
                        summary="",
                        notes="",
                        category_id=defaults["category_id"],
                        doc_type_id=defaults["doc_type_id"],
                        medical_event_id=None,
                        owner_id=defaults["owner_id"],
                        specialty_id=defaults["specialty_id"],
                        title=it.get("title") or Path(file_local).stem,
                    )
                    created.append({"file": d.file, "sha256": sha})
                    if not opts["dry_run"]:
                        d.save()

        apply()

        # Изход
        self.stdout.write(self.style.SUCCESS(f"Updated: {len(updates)}"))
        self.stdout.write(self.style.WARNING(f"Duplicates (same sha256): {len(duplicates)}"))
        self.stdout.write(self.style.WARNING(f"Local files missing: {len(not_found_local)}"))
        if opts["create-missing"]:
            self.stdout.write(self.style.SUCCESS(f"Created new: {len(created)}"))

        # Детайлни отчети
        self.stdout.write("\n== Updates ==")
        for u in updates:
            self.stdout.write(f"- id {u['id']}: {u['changes']}")
        self.stdout.write("\n== Duplicates ==")
        for d in duplicates:
            self.stdout.write(f"- sha256 {d['sha256']} -> ids {d['ids']}")
        self.stdout.write("\n== Missing local files ==")
        for m in not_found_local:
            self.stdout.write(f"- {m}")
        if created:
            self.stdout.write("\n== Created ==")
            for c in created:
                self.stdout.write(f"- {c}")
