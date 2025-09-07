import os
import json
import re
from django.conf import settings
from django.utils import timezone

from records.models import LabIndicator, DocumentTag, get_indicator_canonical_tag


LOG_DIRNAME = "logs"
LOG_FILENAME = "unmatched_indicators.jsonl"


def _log_unmatched_indicator(token: str, context: dict | None = None) -> None:

    try:
        base = getattr(settings, "MEDIA_ROOT", None) or os.path.join(settings.BASE_DIR, "media")
        log_dir = os.path.join(base, LOG_DIRNAME)
        os.makedirs(log_dir, exist_ok=True)
        path = os.path.join(log_dir, LOG_FILENAME)

        payload = {
            "ts": timezone.now().isoformat(),
            "token": (token or "").strip(),
        }
        if context:

            payload.update({
                "source": context.get("source"),
                "document_id": context.get("document_id"),
                "user_id": context.get("user_id"),
                "extra": context.get("extra"),
            })

        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:

        pass


def tokenize_text(text):
    if not text:
        return []
    raw = re.findall(r"[A-Za-zА-Яа-я0-9\-\+\./%()]{2,}", text)
    uniq = []
    seen = set()
    for r in raw:
        k = r.strip()
        if not k:
            continue
        low = k.lower()
        if low not in seen:
            seen.add(low)
            uniq.append(k)
    return uniq


def canonical_indicator_tags_from_tokens(tokens, *, context: dict | None = None):

    if not tokens:
        return []
    out = []
    seen_ids = set()
    for tok in tokens:
        tok = (tok or "").strip()
        if not tok:
            continue
        ind = LabIndicator.resolve(tok)
        if not ind:

            _log_unmatched_indicator(tok, context=context)
            continue

        tag = get_indicator_canonical_tag(ind)
        if tag.pk not in seen_ids:
            out.append(tag)
            seen_ids.add(tag.pk)
    return out


def attach_canonical_indicator_tags(document, tokens):

    ctx = {
        "source": "upload",
        "document_id": getattr(document, "pk", None),
        "user_id": getattr(getattr(document, "owner", None), "pk", None), # ако имате owner
    }
    tags = canonical_indicator_tags_from_tokens(tokens, context=ctx)
    for t in tags:
        DocumentTag.objects.get_or_create(
            document=document, tag=t, defaults={"is_inherited": False}
        )
    return tags
