# tools/extract_template_strings_to_bg_po.py
# Скриптът сканира .html шаблони, намира {% trans %} и {% blocktrans %},
# събира низовете и ги добавя в locale/bg/LC_MESSAGES/django.po
# (ако ги няма), като задава msgstr = msgid. Запазва референции (файл:ред).

import sys
import re
import pathlib
import polib
from collections import defaultdict

TRANS_DOUBLE = re.compile(r'{%\s*trans\s+"([^"]+)"\s*%}')
TRANS_SINGLE = re.compile(r"{%\s*trans\s+'([^']+)'\s*%}")

# blocktrans c/без plural; DOTALL, за да хване много редове
BLOCKTRANS = re.compile(
    r'{%\s*blocktrans(?:\s+[^%}]*)?%}(.*?)(?:{%\s*plural\s*%}(.*?))?{%\s*endblocktrans\s*%}',
    re.DOTALL,
)

def iter_templates(roots):
    for root in roots:
        root_p = pathlib.Path(root)
        if not root_p.exists():
            continue
        for path in root_p.rglob("*.html"):
            # Пропусни статика, node_modules и т.н., ако са в пътя към шаблоните
            if any(seg in {"node_modules", ".venv", "static", "dist"} for seg in path.parts):
                continue
            yield path

def normalize_block_text(txt: str) -> str:
    # Запази {{ variables }}, но нормализирай whitespace
    # (без да „смачква“ смислови нови редове)
    # Минимално почистване: strip краищата и свий поредни whitespace в едно пространство.
    txt = txt.strip()
    # Запази плейсхолдерите; компресираме само „чистия“ текст
    # Проста компресия:
    txt = re.sub(r'[ \t\r\f\v]+', ' ', txt)
    txt = re.sub(r'\n\s*', '\n', txt)  # почисти trailing space по редовете
    return txt

def extract_strings_from_file(fpath: pathlib.Path):
    content = fpath.read_text(encoding="utf-8", errors="ignore")
    results = []

    # {% trans "..." %} / {% trans '...' %}
    for m in TRANS_DOUBLE.finditer(content):
        s = m.group(1).strip()
        # Потърси приблизителен номер на ред
        line = content.count("\n", 0, m.start()) + 1
        if s:
            results.append((s, line))

    for m in TRANS_SINGLE.finditer(content):
        s = m.group(1).strip()
        line = content.count("\n", 0, m.start()) + 1
        if s:
            results.append((s, line))

    # {% blocktrans %} ... {% endblocktrans %}
    for m in BLOCKTRANS.finditer(content):
        singular = normalize_block_text(m.group(1) or "")
        plural = m.group(2)
        line = content.count("\n", 0, m.start()) + 1
        if singular:
            results.append((singular, line))
        # Ако имаме plural секция, може да я добавим като отделен entry (не е пълноценно plural за .po,
        # но все пак ще се преведе вместо да се изгуби). По желание – коментирай ако не искаш:
        if plural:
            plural_norm = normalize_block_text(plural)
            if plural_norm and plural_norm != singular:
                results.append((plural_norm, line))

    return results

def ensure_po(path_po: pathlib.Path) -> polib.POFile:
    path_po.parent.mkdir(parents=True, exist_ok=True)
    if not path_po.exists():
        po = polib.POFile()
        po.metadata = {
            "Project-Id-Version": "medj",
            "MIME-Version": "1.0",
            "Content-Type": "text/plain; charset=UTF-8",
            "Content-Transfer-Encoding": "8bit",
            "Language": "bg",
        }
        po.save(path_po.as_posix())
    return polib.pofile(path_po.as_posix())

def main():
    if len(sys.argv) < 3:
        print("Usage: python extract_template_strings_to_bg_po.py <path/to/locale/bg/LC_MESSAGES/django.po> <templates_dir1> [templates_dir2 ...]")
        sys.exit(1)

    po_path = pathlib.Path(sys.argv[1])
    template_roots = sys.argv[2:]

    po = ensure_po(po_path)

    # Бърз индекс за съществуващи msgid, за да не дублираме
    existing = {(e.msgctxt or "", e.msgid): e for e in po}

    # Събираме всички открити низове с референции
    bucket = defaultdict(list)  # msgid -> list of (file, line)

    for tpath in iter_templates(template_roots):
        for s, line in extract_strings_from_file(tpath):
            if s:
                bucket[s].append((tpath.as_posix(), line))

    added = 0
    updated_refs = 0

    for msgid, occ in bucket.items():
        key = ("", msgid)
        if key in existing:
            # Добави/освежи референциите (без да дублираш)
            entry = existing[key]
            occ_set = set(entry.occurrences or [])
            new = [(f, str(l)) for (f, l) in occ]
            for it in new:
                if it not in occ_set:
                    occ_set.add(it)
            entry.occurrences = sorted(list(occ_set))
            updated_refs += 1
        else:
            entry = polib.POEntry(
                msgid=msgid,
                msgstr=msgid,  # попълваме като BG версия = оригинала
                occurrences=[(f, str(l)) for (f, l) in occ],
                comment="AUTO-ADDED by template scan",
            )
            po.append(entry)
            added += 1

    # Запис без wrap за стабилен diff
    try:
        po.save(po_path.as_posix(), no_wrap=True)  # нови polib версии
    except TypeError:
        po.save(po_path.as_posix())
    print(f"[OK] Scanned templates: {len(list(iter_templates(template_roots)))} files")
    print(f"    Entries added: {added}")
    print(f"    Entries with updated refs: {updated_refs}")

if __name__ == "__main__":
    main()
