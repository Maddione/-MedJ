import os
import json
from datetime import datetime
from django.utils.translation import gettext as _l

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

_client = None


def _read_file_value(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def _resolve_openai_key():
    v = os.getenv("OPENAI_API_KEY", "").strip()
    if v and len(v) > 20 and "\n" not in v and " " not in v and not os.path.isfile(v):
        return v
    if v and os.path.isfile(v):
        file_val = _read_file_value(v)
        if file_val:
            return file_val
    f = os.getenv("OPENAI_API_KEY_FILE", "").strip()
    if f and os.path.isfile(f):
        file_val = _read_file_value(f)
        if file_val:
            return file_val
    rel = "secrets/openai-key.txt"
    if os.path.isfile(rel):
        file_val = _read_file_value(rel)
        if file_val:
            return file_val
    return ""


def _get_client():
    global _client
    if _client is not None:
        return _client
    api_key = _resolve_openai_key()
    if not api_key or OpenAI is None:
        _client = None
        return None
    _client = OpenAI(api_key=api_key)
    return _client


def _today_iso():
    return datetime.utcnow().strftime("%Y-%m-%d")


def analyze_text_with_llm(anon_text: str, specialty):
    client = _get_client()
    if client is None:
        t = _today_iso()
        return {
            "summary": anon_text[:300],
            "data": {
                "summary": anon_text[:300],
                "event_date": t,
                "detected_specialty": getattr(specialty, "slug", "unknown"),
                "suggested_tags": [],
                "blood_test_results": [],
                "diagnosis": "",
                "treatment_plan": "",
                "doctors": [],
                "date_created": t,
            },
        }
    spec_name = getattr(specialty, "name", getattr(specialty, "slug", ""))
    system_prompt = (
        "Върни единствено валиден JSON в следния формат. "
        "Полета: summary, data.summary, data.event_date(YYYY-MM-DD), data.detected_specialty, data.suggested_tags[], "
        "data.blood_test_results[{indicator_name,value,unit,reference_range,measured_at(YYYY-MM-DDTHH:MM:SS)}], "
        "data.diagnosis, data.treatment_plan, data.doctors[], data.date_created(YYYY-MM-DD). "
        "Всички текстове да са на български."
    )
    user_prompt = f"Анализирай текста по специалност: {spec_name}.\nТекст:\n{anon_text}"
    try:
        completion = client.chat.completions.create(
            model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o"),
            response_format={"type": "json_object"},
            max_tokens=3000,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        )
        content = completion.choices[0].message.content
        data = json.loads(content)
        return data
    except Exception:
        t = _today_iso()
        return {
            "summary": anon_text[:300],
            "data": {
                "summary": anon_text[:300],
                "event_date": t,
                "detected_specialty": getattr(specialty, "slug", "unknown"),
                "suggested_tags": [],
                "blood_test_results": [],
                "diagnosis": "",
                "treatment_plan": "",
                "doctors": [],
                "date_created": t,
            },
        }
