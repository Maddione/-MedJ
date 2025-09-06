import re
from django.utils.translation import gettext as _l


def anonymize_text(text: str) -> str:
    patterns = {
        r'\b\d{10}\b': _l('[ANON_EGN]'),
        r'\b\+?\d{10,14}\b': _l('[ANON_PHONE]'),
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b': _l('[ANON_EMAIL]'),
        r'\b\d{1,4}\s*(?:ул\.|улица|бул\.|булевард|пл\.|площад|кв\.|квартал|ж\.к\.|жилищен комплекс)\b[^,;.]*?(?:,\s*\d{1,})?\s*,\s*(?:[А-Я][а-я]+(?:\s+[А-Я][а-я]+)*)?(?:,\s*\d{4})?\b': _l('[ANON_ADDRESS]'),
        r'\b\d{4}\s*(?:[А-Я][а-я]+(?:\s+[А-Я][а-я]+)*)?(?:,\s*блок\s*\d{1,})?(?:,\s*вх\.\s*[А-Я])?(?:,\s*ет\.\s*\d{1,})?(?:,\s*ап\.\s*\d{1,})?\b': _l('[ANON_ADDRESS]'),
        r'\b\d{4}\b': _l('[ANON_ZIP]'),
        r'\b(?:УИН|ИН|ЗКН|ПК|ЕИК)\s*:\s*\d+\b': _l('[ANON_IDENTIFIER]'),
        r'\b(тел\.|тел\.|телефон|факс)\s*:\s*[\d\s\-\+]+\b': _l('[ANON_CONTACT]'),
        r'\b(УМБАЛ|МБАЛ|ДКЦ|МЦ|СБАЛ|КОЦ|ДПБ|ЦПЗ|РЗИ|НЦЗПБ|ВМА|МВР-МБЛ|Токуда|Пирогов|Аджибадем|Софиямед|Сити Клиник|Анадолу|Сердика|Вита|Щерев|Майчин дом|Първа градска|Втора градска|Трета градска|Четвърта градска|Пета градска|Шеста градска|Седма градска|Осма градска|Девета градска|Десета градска)\b': _l('[ANON_HOSPITAL]'),
        r'\bфактура\s*№\s*\d+\b': _l('[ANON_INVOICE_NUMBER]'),
        r'\bинв\.\s*№\s*\d+\b': _l('[ANON_INVOICE_NUMBER]'),
        r'\bдоговор\s*№\s*\d+\b': _l('[ANON_CONTRACT_NUMBER]'),
        r'\bпротокол\s*№\s*\d+\b': _l('[ANON_PROTOCOL_NUMBER]'),
        r'\bпаспорт\s*№\s*\w+\s+\d+\b': _l('[ANON_PASSPORT_ID]'),
        r'\bлична\s*карта\s*№\s*\w+\s+\d+\b': _l('[ANON_ID_CARD]'),
        r'\bсерия\s+\w+\s+№\s*\d+\b': _l('[ANON_DOCUMENT_ID]'),
        r'\b№\s*\d+\s*(?:от|на|за)\s*\d{2}\.\d{2}\.\d{4}\b': _l('[ANON_DOCUMENT_ID_DATE]'),
        r'(?<!д-р\s)(?<!доктор\s)(?<!проф\.\s)(?<!професор\s)(?<!доц\.\s)(?<!доцент\s)(?<!асистент\s)\b([А-Я][а-я]+(?:\s+[А-Я][а-я]+){1,2})\b(?=\s*(?:на\s+\d{2}\s*години|мъж|жена|дете|пациент|ЕГН|ЛНЧ|\d{10,}))': _l('[ANON_PERSON_NAME]'),
        r'\b(?:\d{2}\.\d{2}\.\d{4}|\d{2}-\d{2}-\d{4}|\d{4}-\d{2}-\d{2})\b': _l('[ANON_DATE]'),
    }
    anonymized_text = text or ""
    for pattern, replacement in patterns.items():
        anonymized_text = re.sub(pattern, replacement, anonymized_text, flags=re.IGNORECASE | re.UNICODE)
    return anonymized_text
