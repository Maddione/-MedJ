import io, os, re

def _read_entries(text):
    entries, buf = [], []
    for line in text.splitlines(keepends=True):
        if line.strip() == "" and buf:
            entries.append(buf); buf=[]
        else:
            buf.append(line)
    if buf:
        entries.append(buf)
    return entries

def _collect_quoted(lines, start_idx):
    # Събира "..." редовете (включително последващи) в една стойност
    out = []
    i = start_idx
    first = True
    while i < len(lines):
        s = lines[i].lstrip()
        if first:
            first = False
        else:
            if not s.startswith('"'):
                break
        m = re.match(r'^(?:msgctxt|msgid|msgid_plural|msgstr(?:\[\d+\])?)?\s*"(?P<q>.*)"\s*$', lines[i].rstrip("\r\n"))
        if m:
            out.append(m.group("q"))
            i += 1
        else:
            break
    return "".join(out), i

def _entry_key(entry_lines):
    # ключ = msgctxt + \x04 + msgid (ако има контекст) или само msgid
    msgctxt_val = None
    msgid_val = None
    i = 0
    while i < len(entry_lines):
        line = entry_lines[i]
        s = line.lstrip()
        if s.startswith("msgctxt "):
            _, j = _collect_quoted(entry_lines, i)
            msgctxt_val, _ = _collect_quoted(entry_lines, i)
            i = j; continue
        if s.startswith("msgid "):
            msgid_val, j = _collect_quoted(entry_lines, i)
            i = j; continue
        i += 1
    if msgid_val is None:
        return None
    if msgid_val == "":
        return ""  # header
    if msgctxt_val is not None:
        return f"{msgctxt_val}\x04{msgid_val}"
    return msgid_val

def dedup_po(path, lang):
    with io.open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    entries = _read_entries(text)
    seen = set()
    out_lines = []

    # Коректен header винаги първи:
    header = [
        'msgid ""\n',
        'msgstr ""\n',
        '"Project-Id-Version: MedJ\\n"\n',
        f'"Language: {lang}\\n"\n',
        '"MIME-Version: 1.0\\n"\n',
        '"Content-Type: text/plain; charset=UTF-8\\n"\n',
        '"Content-Transfer-Encoding: 8bit\\n"\n',
        '"Plural-Forms: nplurals=2; plural=(n != 1);\\n"\n',
        "\n"
    ]
    out_lines.extend(header)

    for entry in entries:
        key = _entry_key(entry)
        if key is None:
            # непознат блок -> запази
            out_lines.extend(entry)
            if not entry[-1].endswith("\n"):
                out_lines.append("\n")
            out_lines.append("\n")
            continue
        if key == "":
            # прескачаме всички оригинални header-и (вече написахме нов)
            continue
        if key in seen:
            # дубликат -> пропусни
            continue
        seen.add(key)
        # нормализирай: гарантирай празен ред след всяка ентри
        if entry and not entry[-1].endswith("\n"):
            entry[-1] += "\n"
        out_lines.extend(entry)
        if not (entry and entry[-1].strip() == ""):
            out_lines.append("\n")

    fixed = "".join(out_lines)
    # редуцирай множествени празни редове
    fixed = re.sub(r"\n{3,}", "\n\n", fixed)

    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(fixed)

# Пътища от твоя лог
dedup_po(r"C:\Users\444\PychamProjects\MedJ2.1\locale\bg\LC_MESSAGES\django.po", "bg")
dedup_po(r"C:\Users\444\PychamProjects\MedJ2.1\locale\en\LC_MESSAGES\django.po", "en")
print("Dedup complete.")
