#!/usr/bin/env python3
"""
Auto-translate PO files (BG -> EN or any pair) with placeholders protection.

Usage examples:
1) Превод "на място" (само празни msgstr):
   python tools/auto_translate_po.py --src locale/bg/LC_MESSAGES/django.po --src-lang bg --dst-lang en --provider deepl --only-empty

2) Изгради EN файла от BG (align + translate):
   python tools/auto_translate_po.py \
     --src locale/bg/LC_MESSAGES/django.po \
     --dst locale/en/LC_MESSAGES/django.po \
     --src-lang bg --dst-lang en \
     --provider deepl --only-empty

3) Презапиши и уже преведените (ако искаш да обновиш всичко):
   python tools/auto_translate_po.py --src ...bg.po --dst ...en.po --src-lang bg --dst-lang en --provider deepl --overwrite
"""

from __future__ import annotations
import argparse
import os
import re
import sys
from typing import List, Tuple, Dict, Optional

try:
    import polib
except Exception as e:
    print("polib е нужен: pip install polib", file=sys.stderr)
    raise

# --- Optional providers ---
PROVIDER = None
HAS_GOOGLE = False
try:
    import deepl
except Exception:
    deepl = None

try:
    from googletrans import Translator as GoogleTranslator
    HAS_GOOGLE = True
except Exception:
    HAS_GOOGLE = False

PLACEHOLDER_PATTERNS = [
    r"%\([A-Za-z_][A-Za-z0-9_]*\)s",  # %(name)s
    r"%[sdif]",                        # %s %d %i %f
    r"\{[A-Za-z_][A-Za-z0-9_]*\}",     # {name}
    r"\{\{.*?\}\}",                    # {{ var }}
    r"\{%.*?%\}",                      # {% tag %}
    r"<[^>]+>",                        # <b>...</b>
]

SMART_MAP = {
    "“": '"', "”": '"', "„": '"',
    "’": "'", "‘": "'",
    "\u00A0": " ",   # NBSP
    "\ufeff": "",    # BOM
}

def normalize_quotes(s: str) -> str:
    for k, v in SMART_MAP.items():
        s = s.replace(k, v)
    return s

def protect_placeholders(text: str) -> Tuple[str, Dict[str, str]]:
    tokens: Dict[str, str] = {}
    idx = 0

    def repl(m):
        nonlocal idx
        key = f"__PH_{idx}__"
        tokens[key] = m.group(0)
        idx += 1
        return key

    combined = re.compile("|".join(PLACEHOLDER_PATTERNS), re.DOTALL)
    protected = combined.sub(repl, text)
    return protected, tokens

def restore_placeholders(text: str, tokens: Dict[str, str]) -> str:
    for key, val in tokens.items():
        text = text.replace(key, val)
    return text

def translate_batch_deepl(texts: List[str], src_lang: str, dst_lang: str) -> List[str]:
    api_key = os.getenv("DEEPL_API_KEY", "")
    if not api_key or deepl is None:
        raise RuntimeError("DEEPL_API_KEY не е зададен или пакетът deepl липсва.")
    translator = deepl.Translator(api_key)
    # DeepL приема списък и връща списък
    res = translator.translate_text(
        texts,
        source_lang=src_lang.upper(),
        target_lang=dst_lang.upper(),
        preserve_formatting=True,
        formality="prefer_more" if dst_lang.lower().startswith("en") else "default",
    )
    # res може да е обект или списък в зависимост от броя
    if isinstance(res, list):
        return [r.text for r in res]
    return [res.text]

def translate_batch_google(texts: List[str], src_lang: str, dst_lang: str) -> List[str]:
    if not HAS_GOOGLE:
        raise RuntimeError("googletrans липсва (pip install googletrans==4.0.0rc1)")
    tr = GoogleTranslator()
    out = []
    for t in texts:
        out.append(tr.translate(t, src=src_lang, dest=dst_lang).text)
    return out

def translate_texts(texts: List[str], src_lang: str, dst_lang: str, provider: str) -> List[str]:
    if not texts:
        return []
    if provider == "deepl":
        return translate_batch_deepl(texts, src_lang, dst_lang)
    elif provider == "google":
        return translate_batch_google(texts, src_lang, dst_lang)
    else:
        raise ValueError(f"Непознат provider: {provider}")

def set_plural_header_en(po: polib.POFile):
    # Увери се, че EN header е разумен. Не пипай ако вече има.
    h = po.metadata or {}
    if "Plural-Forms" not in h or not h["Plural-Forms"]:
        h["Plural-Forms"] = "nplurals=2; plural=(n != 1);"
    if "Language" not in h or not h["Language"]:
        h["Language"] = "en"
    po.metadata = h

def load_or_create_po(path: str) -> polib.POFile:
    pofile: Optional[polib.POFile] = None
    try:
        pofile = polib.pofile(path)
    except FileNotFoundError:
        pofile = polib.POFile()
    except Exception as e:
        print(f"[WARN] Проблем с '{path}': {e}. Създавам нов .po.", file=sys.stderr)
        pofile = polib.POFile()
    return pofile

def build_dst_from_src(src_po: polib.POFile, dst_po: polib.POFile) -> polib.POFile:
    # Подравнява dst по src: добавя липсващи msgid от src в dst.
    existing = {(e.msgctxt, e.msgid): e for e in dst_po}
    for e in src_po:
        key = (e.msgctxt, e.msgid)
        if key not in existing:
            new_e = polib.POEntry(
                msgid=e.msgid,
                msgctxt=e.msgctxt,
                occurrences=e.occurrences,
                msgid_plural=e.msgid_plural,
            )
            dst_po.append(new_e)
    return dst_po

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="Изходен .po (BG)")
    ap.add_argument("--dst", help="Целеви .po (EN). Ако липсва, превеждаме src in-place.")
    ap.add_argument("--src-lang", default="bg", help="Код на изходния език (напр. bg)")
    ap.add_argument("--dst-lang", default="en", help="Код на целевия език (напр. en)")
    ap.add_argument("--provider", choices=["deepl", "google"], default="deepl")
    ap.add_argument("--overwrite", action="store_true", help="Презапиши и вече преведените.")
    ap.add_argument("--only-empty", action="store_true", help="Превеждай само празни msgstr.")
    ap.add_argument("--batch-size", type=int, default=40)
    ap.add_argument("--dict-csv", help="CSV (src;dst) за твърди терминологични замени преди превод.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    # Зареди PO
    src_po = polib.pofile(args.src)
    if args.dst:
        dst_po = load_or_create_po(args.dst)
        # Подравняване по msgid (копира липсващите ключове от src)
        dst_po = build_dst_from_src(src_po, dst_po)
        # Header за EN
        if args.dst_lang.lower().startswith("en"):
            set_plural_header_en(dst_po)
    else:
        dst_po = src_po  # in-place превод

    # Зареди терминологичен CSV речник (по избор)
    term_map: Dict[str, str] = {}
    if args.dict_csv:
        import csv
        with open(args.dict_csv, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=";")
            for row in reader:
                if len(row) >= 2 and row[0].strip():
                    term_map[row[0]] = row[1]

    # Събери кандидати за превод
    candidates: List[Tuple[polib.POEntry, Optional[int]]] = []
    for e in dst_po:
        # Прескачай празни msgid-та (заглавие и т.н.)
        if not e.msgid.strip():
            continue

        # plural?
        if e.msgid_plural:
            # Считай, че index 0 е ед.ч., index 1 е мн.ч. (EN)
            nforms = max([int(i) for i in e.msgstr_plural.keys()] + [1])
            # Превеждаме двата източника: msgid и msgid_plural
            need_sg = (args.overwrite or args.only_empty and not e.msgstr_plural.get(0)) or (not args.only_empty and not e.msgstr_plural.get(0))
            need_pl = (args.overwrite or args.only_empty and not e.msgstr_plural.get(1)) or (not args.only_empty and not e.msgstr_plural.get(1))
            if need_sg:
                candidates.append((e, 0))
            if need_pl:
                candidates.append((e, 1))
        else:
            need = True
            if args.only_empty and e.msgstr:
                need = False
            if not args.overwrite and e.msgstr:
                # ако не искаме overwrite и има msgstr, прескачаме
                need = False
            if need:
                candidates.append((e, None))

    # Пакетиране и превод
    def preproc(s: str) -> Tuple[str, Dict[str, str]]:
        s = normalize_quotes(s)
        # твърди терминологични замени преди превод
        for k, v in term_map.items():
            s = s.replace(k, v)
        return protect_placeholders(s)

    batched_texts: List[str] = []
    batched_refs: List[Tuple[polib.POEntry, Optional[int], Dict[str,str]]] = []

    changed = 0

    def flush_batch():
        nonlocal changed, batched_texts, batched_refs
        if not batched_texts:
            return
        translations = translate_texts(batched_texts, args.src_lang, args.dst_lang, args.provider)
        for (entry, idx, tokens), tr in zip(batched_refs, translations):
            tr = restore_placeholders(tr, tokens)
            tr = tr.strip()
            if args.dry_run:
                continue
            if idx is None:
                entry.msgstr = tr
            else:
                # plural index
                entry.msgstr_plural[idx] = tr
            changed += 1
        batched_texts = []
        batched_refs = []

    for entry, idx in candidates:
        src_text = entry.msgid if idx in (None, 0) else entry.msgid_plural
        protected, tokens = preproc(src_text)
        batched_texts.append(protected)
        batched_refs.append((entry, idx, tokens))
        if len(batched_texts) >= args.batch_size:
            flush_batch()
    flush_batch()

    # Запиши
    if args.dry_run:
        print(f"[DRY] Щяха да се запишат ~{changed} превода.")
        return

    # Всички записи остават „unfuzzy“
    for e in dst_po:
        if e.fuzzy:
            e.flags.discard("fuzzy")

    # Запазване (съвместимо със стари polib)
    try:
        dst_po.save(args.dst or args.src, no_wrap=True)
    except TypeError:
        dst_po.save(args.dst or args.src)

    print(f"[OK] Преведени/обновени записи: {changed}")
    print(f"[OUT] {args.dst or args.src}")
    print("Сега компилирай съобщенията:  manage.py compilemessages -l bg -l en")
    print("Пример (в Docker): dc run --rm --no-deps --entrypoint sh web -lc \"python manage.py compilemessages -l bg -l en\"")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
