import io, re, os

HEADERS = {
 "bg": (
  'msgid ""\n'
  'msgstr ""\n'
  '"Project-Id-Version: MedJ\\n"\n'
  '"Report-Msgid-Bugs-To: \\n"\n'
  '"POT-Creation-Date: 2025-09-05 00:00+0000\\n"\n'
  '"PO-Revision-Date: 2025-09-05 00:00+0000\\n"\n'
  '"Last-Translator: MedJ Team <translations@medj.local>\\n"\n'
  '"Language-Team: Bulgarian <translations@medj.local>\\n"\n'
  '"Language: bg\\n"\n'
  '"MIME-Version: 1.0\\n"\n'
  '"Content-Type: text/plain; charset=UTF-8\\n"\n'
  '"Content-Transfer-Encoding: 8bit\\n"\n'
  '"Plural-Forms: nplurals=2; plural=(n != 1);\\n"\n'
  '"X-Generator: django-admin makemessages\\n"\n'
  '\n'
 ),
 "en": (
  'msgid ""\n'
  'msgstr ""\n'
  '"Project-Id-Version: MedJ\\n"\n'
  '"Report-Msgid-Bugs-To: \\n"\n'
  '"POT-Creation-Date: 2025-09-05 00:00+0000\\n"\n'
  '"PO-Revision-Date: 2025-09-05 00:00+0000\\n"\n'
  '"Last-Translator: MedJ Team <translations@medj.local>\\n"\n'
  '"Language-Team: English <translations@medj.local>\\n"\n'
  '"Language: en\\n"\n'
  '"MIME-Version: 1.0\\n"\n'
  '"Content-Type: text/plain; charset=UTF-8\\n"\n'
  '"Content-Transfer-Encoding: 8bit\\n"\n'
  '"Plural-Forms: nplurals=2; plural=(n != 1);\\n"\n'
  '"X-Generator: django-admin makemessages\\n"\n'
  '\n'
 ),
}

# заменя първия header блок (между msgstr "" и първия празен ред) с коректния
PATTERN = re.compile(r'(?s)^msgid\s+""\s*msgstr\s+""(.*?)\r?\n\r?\n')

def patch_header(path, lang):
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with io.open(path, "r", encoding="utf-8", errors="replace") as f:
        data = f.read()

    if PATTERN.search(data):
        data = PATTERN.sub(HEADERS[lang], data, count=1)
    else:
        data = HEADERS[lang] + data

    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(data)

patch_header(r"C:\Users\444\PychamProjects\MedJ2.1\locale\bg\LC_MESSAGES\django.po", "bg")
patch_header(r"C:\Users\444\PychamProjects\MedJ2.1\locale\en\LC_MESSAGES\django.po", "en")
print("Header patch complete.")
