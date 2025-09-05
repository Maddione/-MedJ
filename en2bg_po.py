import io, os, re, datetime, sys

# === НАСТРОЙКА ===
# SEED_MODE = "copy"  -> msgstr = msgid (гарантира, че нищо не е празно визуално)
# SEED_MODE = "empty" -> msgstr остават празни (класически подход за преводачи)
SEED_MODE = "copy"

# >>> Път към твоя английски файл (ако е друг – променя се тук):
EN_PO = r"C:\Users\444\PychamProjects\MedJ2.1\locale\en\LC_MESSAGES\django.po"
BG_PO = r"C:\Users\444\PychamProjects\MedJ2.1\locale\bg\LC_MESSAGES\django.po"

os.makedirs(os.path.dirname(BG_PO), exist_ok=True)

def now():
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M+0000")

HEADER_BG = (
    'msgid ""\n'
    'msgstr ""\n'
    '"Project-Id-Version: MedJ\\n"\n'
    '"Report-Msgid-Bugs-To: \\n"\n'
    f'"POT-Creation-Date: {now()}\\n"\n'
    f'"PO-Revision-Date: {now()}\\n"\n'
    '"Last-Translator: MedJ Team <translations@medj.local>\\n"\n'
    '"Language-Team: Bulgarian <translations@medj.local>\\n"\n'
    '"Language: bg\\n"\n'
    '"MIME-Version: 1.0\\n"\n'
    '"Content-Type: text/plain; charset=UTF-8\\n"\n'
    '"Content-Transfer-Encoding: 8bit\\n"\n'
    '"Plural-Forms: nplurals=2; plural=(n != 1);\\n"\n'
    '"X-Generator: en2bg-po-seeder\\n"\n'
    '\n'
)

def read_entries(po_text):
    entries, buf = [], []
    for line in po_text.splitlines(keepends=True):
        if line.strip() == "" and buf:
            entries.append(buf); buf=[]
        else:
            buf.append(line)
    if buf:
        entries.append(buf)
    return entries

def collect_quoted(lines, start_idx):
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

def entry_key(entry_lines):
    msgctxt_val = None
    msgid_val = None
    i = 0
    while i < len(entry_lines):
        line = entry_lines[i]
        s = line.lstrip()
        if s.startswith("msgctxt "):
            msgctxt_val, j = collect_quoted(entry_lines, i)
            i = j; continue
        if s.startswith("msgid "):
            msgid_val, j = collect_quoted(entry_lines, i)
            i = j; continue
        i += 1
    if msgid_val is None:
        return None
    if msgid_val == "":
        return ""
    return (msgctxt_val or "") + "\x04" + msgid_val

def extract_msgid_plural(entry_lines):
    msgid, msgid_plural = None, None
    i = 0
    while i < len(entry_lines):
        s = entry_lines[i].lstrip()
        if s.startswith("msgid "):
            msgid, i = collect_quoted(entry_lines, i); continue
        if s.startswith("msgid_plural "):
            msgid_plural, i = collect_quoted(entry_lines, i); continue
        i += 1
    return msgid, msgid_plural

def is_msgstr_line(s):
    return s.startswith("msgstr")  # covers msgstr and msgstr[n]

def build_bg_entry(entry_lines):
    # Не пипаме коментари, msgctxt, msgid/msgid_plural – само msgstr редовете.
    msgid, msgid_plural = extract_msgid_plural(entry_lines)

    result = []
    i = 0
    while i < len(entry_lines):
        line = entry_lines[i]
        s = line.lstrip()

        # прескачаме EN header entries (те ще бъдат заменени с HEADER_BG извън тази функция)
        if i == 0 and line.startswith('msgid ""'):
            return None

        if is_msgstr_line(s):
            m = re.match(r'^(\s*msgstr(?:\[\d+\])?\s*)"[^"]*"\s*$', line.rstrip("\r\n"))
            if not m:
                result.append(line); i += 1; continue

            # избор на стойност според SEED_MODE
            if SEED_MODE == "copy":
                val = msgid or ""
            else:
                val = ""

            # ако имаме plural и това е msgstr[1], може да предпочетем msgid_plural (ако съществува)
            if "msgstr[1]" in m.group(1) and (msgid_plural and SEED_MODE == "copy"):
                val = msgid_plural

            result.append(f'{m.group(1)}"{val}"\n')
            i += 1
            # копирай потенциални продължения "..." след msgstr ред – но ние вече генерирахме финална стойност → пропускаме
            while i < len(entry_lines) and entry_lines[i].lstrip().startswith('"'):
                i += 1
            continue

        result.append(line)
        i += 1

    # гарантирай празен ред след entry
    if result and result[-1].strip() != "":
        result.append("\n")
    return result

def convert_en_to_bg(en_po_path, bg_po_path):
    with io.open(en_po_path, "r", encoding="utf-8", errors="replace") as f:
        po_text = f.read()

    entries = read_entries(po_text)
    out = [HEADER_BG]

    seen = set()
    for e in entries:
        key = entry_key(e)
        if key == "":
            continue
        if key in seen:
            continue
        seen.add(key)
        bg = build_bg_entry(e)
        if bg is None:
            continue
        out.extend(bg)

    with io.open(bg_po_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("".join(out))

convert_en_to_bg(EN_PO, BG_PO)
print("BG .po generated at:", BG_PO)
