import re
from records.models import LabIndicator, DocumentTag, get_indicator_canonical_tag

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

def canonical_indicator_tags_from_tokens(tokens):
    out = []
    seen_ids = set()
    for tok in tokens or []:
        ind = LabIndicator.resolve(tok)
        if not ind:
            continue
        tag = get_indicator_canonical_tag(ind)
        if tag.pk not in seen_ids:
            out.append(tag)
            seen_ids.add(tag.pk)
    return out

def attach_canonical_indicator_tags(document, tokens):
    tags = canonical_indicator_tags_from_tokens(tokens)
    for t in tags:
        DocumentTag.objects.get_or_create(document=document, tag=t, defaults={"is_inherited": False})
    return tags
