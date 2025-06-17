import re
from datetime import datetime


def parse_lab_report(text: str) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("Описание")]
    data = {}
    year = datetime.now().year
    # Дата
    date_iso = None
    for line in lines:
        m = re.search(r'\b(\d{2}\.\d{2}\.\d{4})\b', line)
        if m:
            date_iso = datetime.strptime(m.group(1), "%d.%m.%Y").strftime("%d-%m-%Y")
            break
    if not date_iso:
        for line in lines:
            m = re.search(r'\b(\d{2}\.\d{2})\b', line)
            if m:
                try:
                    date_iso = datetime.strptime(f"{m.group(1)}.{year}", "%d.%m.%Y").strftime("%d-%m-%Y")
                    break
                except ValueError:
                    continue
    if date_iso:
        data["date"] = date_iso

    unit_map = {"9/1": "g/l", "G/I": "G/l", "T/I": "T/l", "L/L": "L/L"}
    pattern = re.compile(
        r'^[–-]?\s*(?P<name>.+?)\s+'
        r'(?P<unit>[^\d\s]+)\s+'
        r'(?P<value>[-+]?\d+[\.,]?\d*)\s*'
        r'(?P<status>High|Low|Normal)?\s+'
        r'(?P<ref>[\d\.\- ]+)$'
    )
    for line in lines:
        m = pattern.match(line)
        if m:
            name = m.group("name").rstrip(':')
            raw_unit = m.group("unit")
            unit = unit_map.get(raw_unit, raw_unit)
            value = float(m.group("value").replace(',', '.'))
            status = m.group("status") or None
            reference = m.group("ref").strip()
            data[name] = {"unit": unit, "value": value, "status": status, "reference": reference}
    return data
