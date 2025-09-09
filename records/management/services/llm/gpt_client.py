import os, json
from datetime import datetime

def _system_prompt():
    return (
        "Върни САМО JSON. "
        "{"
        "\"summary\":\"\","
        "\"event_date\":\"\","
        "\"detected_specialty\":\"\","
        "\"suggested_tags\":[],"
        "\"blood_test_results\":[{\"indicator_name\":\"\",\"value\":\"\",\"unit\":\"\",\"reference_range\":\"\"}],"
        "\"diagnosis\":\"\","
        "\"treatment_plan\":\"\","
        "\"doctors\":[]"
        "}"
    )

def _fallback(text, specialty_name):
    t = (text or "").strip()
    lines = [x.strip() for x in t.replace("\r","").split("\n") if x.strip()]
    summary = " ".join(lines[:6])[:800]
    date = ""
    import re
    m = re.search(r"\b(20\d{2}|19\d{2})[-./](0?[1-9]|1[0-2])[-./](0?[1-9]|[12]\d|3[01])\b", t)
    if m:
        try:
            d = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()
            date = d.isoformat()
        except Exception:
            date = ""
    data = {"summary": summary, "event_date": date, "detected_specialty": specialty_name or "", "suggested_tags": [], "blood_test_results": [], "diagnosis": "", "treatment_plan": "", "doctors": []}
    return {"summary": summary, "data": data}

def analyze_text_with_llm(text, specialty_name):
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    if not api_key:
        return _fallback(text, specialty_name)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        sys = _system_prompt()
        resp = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            max_tokens=1200,
            messages=[{"role": "system", "content": sys}, {"role": "user", "content": text}]
        )
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        return {"summary": (data.get("summary") or ""), "data": data}
    except Exception:
        return _fallback(text, specialty_name)
