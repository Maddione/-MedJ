import re


def anonymize_text(text):
    """
    Finds and replaces Personal Identifiable Information (PII) in a given text.
    Handles EGN, phone numbers, addresses, and emails.
    """
    if not text:
        return ""

    simple_egn_pattern = r'\b\d{10}\b'

    phone_pattern = r'(\+359|0)8[789]\d{1,7}\b|(\+359|0)\s?8[789]\d\s?\d{3}\s?\d{3}\b'

    address_pattern = r'(?i).*(адрес|гр\.|с\.|ж\.к\.|кв\.|ул\.|бул\.).*'

    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

    text = re.sub(simple_egn_pattern, '[ЕГН]', text)
    text = re.sub(phone_pattern, '[ТЕЛЕФОН]', text)
    text = re.sub(address_pattern, '[АДРЕС]', text)
    text = re.sub(email_pattern, '[ИМЕЙЛ]', text)

    return text