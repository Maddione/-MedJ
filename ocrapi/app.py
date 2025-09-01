import os
import io
import re
import json
from flask import Flask, request, jsonify
from google.cloud import vision
from google.oauth2 import service_account
from PIL import Image
from openai import OpenAI

app = Flask(__name__)

def build_vision_client():
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    alt = os.getenv("GOOGLE_CLOUD_VISION_KEY", "").strip()
    if cred_path and os.path.exists(cred_path):
        creds = service_account.Credentials.from_service_account_file(cred_path)
        return vision.ImageAnnotatorClient(credentials=creds)
    if alt:
        if os.path.exists(alt):
            creds = service_account.Credentials.from_service_account_file(alt)
            return vision.ImageAnnotatorClient(credentials=creds)
        try:
            info = json.loads(alt)
            creds = service_account.Credentials.from_service_account_info(info)
            return vision.ImageAnnotatorClient(credentials=creds)
        except Exception:
            pass
    return vision.ImageAnnotatorClient()

def anonymize_text(text: str) -> str:
    patterns = {
        r'\b\d{10}\b': '[ANON_EGN]',
        r'\b\+?\d{10,14}\b': '[ANON_PHONE]',
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b': '[ANON_EMAIL]',
        r'\b\d{1,4}\s*(?:ул\.|улица|бул\.|булевард|пл\.|площад|кв\.|квартал|ж\.к\.|жилищен комплекс)\b[^,;.]*?(?:,\s*\d{1,})?\s*,\s*(?:[А-Я][а-я]+(?:\s+[А-Я][а-я]+)*)?(?:,\s*\d{4})?\b': '[ANON_ADDRESS]',
        r'\b\d{4}\s*(?:[А-Я][а-я]+(?:\s+[А-Я][а-я]+)*)?(?:,\s*блок\s*\d{1,})?(?:,\s*вх\.\s*[А-Я])?(?:,\s*ет\.\s*\d{1,})?(?:,\s*ап\.\s*\d{1,})?\b': '[ANON_ADDRESS]',
        r'\b\d{4}\b': '[ANON_ZIP]',
        r'\b(?:УИН|ИН|ЗКН|ПК|ЕИК)\s*:\s*\d+\b': '[ANON_IDENTIFIER]',
        r'\b(тел\.|телефон|факс)\s*:\s*[\d\s\-\+]+\b': '[ANON_CONTACT]',
        r'\b(УМБАЛ|МБАЛ|ДКЦ|МЦ|СБАЛ|КОЦ|ДПБ|ЦПЗ|РЗИ|НЦЗПБ|ВМА|МВР-МБЛ|Токуда|Пирогов|Аджибадем|Софиямед|Сити Клиник|Анадолу|Сердика|Вита|Щерев|Майчин дом|Първа градска|Втора градска|Трета градска|Четвърта градска|Пета градска|Шеста градска|Седма градска|Осма градска|Девета градска|Десета градска)\b': '[ANON_HOSPITAL]',
        r'\bфактура\s*№\s*\d+\b': '[ANON_INVOICE_NUMBER]',
        r'\bинв\.\s*№\s*\d+\b': '[ANON_INVOICE_NUMBER]',
        r'\bдоговор\s*№\s*\d+\b': '[ANON_CONTRACT_NUMBER]',
        r'\bпротокол\s*№\s*\d+\b': '[ANON_PROTOCOL_NUMBER]',
        r'\bпаспорт\s*№\s*\w+\s+\d+\b': '[ANON_PASSPORT_ID]',
        r'\bлична\s*карта\s*№\s*\w+\s+\d+\b': '[ANON_ID_CARD]',
        r'\bсерия\s+\w+\s+№\s*\d+\b': '[ANON_DOCUMENT_ID]',
        r'\b№\s*\d+\s*(?:от|на|за)\s*\d{2}\.\d{2}\.\d{4}\b': '[ANON_DOCUMENT_ID_DATE]',
        r'(?<!д-р\s)(?<!доктор\s)(?<!проф\.\s)(?<!професор\s)(?<!доц\.\s)(?<!доцент\s)(?<!асистент\s)\b([А-Я][а-я]+(?:\s+[А-Я][а-я]+){1,2})\b(?=\s*(?:на\s+\d{2}\s*години|мъж|жена|дете|пациент|ЕГН|ЛНЧ|\d{10,}))': '[ANON_PERSON_NAME]',
        r'\b(?:\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})\b': '[ANON_DATE]'
    }
    out = text
    for p, r in patterns.items():
        out = re.sub(p, r, out, flags=re.IGNORECASE | re.UNICODE)
    return out

def extract_blood_tests(text: str):
    results = []
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    rx = re.compile(r'^([A-Za-zА-Яа-я0-9 ./%\-\+\(\)]+?)\s*[:\-]?\s*([<>]?\s*[\d\.,]+)\s*([A-Za-zμµ/%\^\*\d\(\)\.-]+)?(?:\s*\(?\s*(\d[\d\.,]*)\s*[-–]\s*(\d[\d\.,]*)\s*\)?)?')
    for ln in lines:
        m = rx.match(ln)
        if not m:
            continue
        name = m.group(1).strip()
        val = (m.group(2) or "").replace(",", ".").replace(" ", "")
        unit = (m.group(3) or "").strip()
        low = m.group(4)
        high = m.group(5)
        ref = None
        if low and high:
            ref = f"{low} - {high}"
        if name and val:
            results.append({
                "indicator_name": name,
                "value": val,
                "unit": unit,
                "reference_range": ref
            })
    return results

def build_html_table(blood_tests):
    if not blood_tests:
        return ""
    rows = []
    rows.append("<table style='width:100%;border-collapse:collapse'>")
    rows.append("<thead><tr><th style='border:1px solid #ccc;padding:8px;text-align:left'>Показател</th><th style='border:1px solid #ccc;padding:8px;text-align:left'>Стойност</th><th style='border:1px solid #ccc;padding:8px;text-align:left'>Единица</th><th style='border:1px solid #ccc;padding:8px;text-align:left'>Реф. граници</th></tr></thead>")
    rows.append("<tbody>")
    for r in blood_tests:
        rows.append(
            f"<tr><td style='border:1px solid #ccc;padding:8px'>{r.get('indicator_name','')}</td><td style='border:1px solid #ccc;padding:8px'>{r.get('value','')}</td><td style='border:1px solid #ccc;padding:8px'>{r.get('unit','')}</td><td style='border:1px solid #ccc;padding:8px'>{r.get('reference_range','') or ''}</td></tr>"
        )
    rows.append("</tbody></table>")
    return "".join(rows)

def maybe_call_gpt(text: str, user_ctx: dict):
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    client = OpenAI(api_key=api_key)
    system_prompt = f"""
Ти си експертен асистент за обработка на медицински документи по {user_ctx.get('specialty_name','неизвестна')}.
Върни валиден JSON с ключове: summary, event_date, detected_specialty, suggested_tags, blood_test_results, diagnosis, treatment_plan, doctors.
Всички текстове да са на български.
"""
    user_msg = f"Категория: {user_ctx.get('category_name','неизвестна')}\nВид събитие: {user_ctx.get('event_type','неизвестен')}\nТекст:\n{text}"
    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            max_tokens=2800,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg}
            ]
        )
        content = resp.choices[0].message.content
        return json.loads(content)
    except Exception:
        return None

@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200

@app.post("/ocr")
def ocr():
    if "file" not in request.files:
        return jsonify({"error": "No file provided under form field 'file'"}), 400
    f = request.files["file"]
    filename = f.filename or "upload"
    content = f.read()
    try:
        Image.open(io.BytesIO(content)).verify()
    except Exception:
        return jsonify({"error": "Unsupported or corrupted image"}), 400

    client = build_vision_client()
    image = vision.Image(content=content)
    response = client.document_text_detection(image=image)
    if response.error.message:
        return jsonify({"error": response.error.message}), 500

    full_text = ""
    if response.full_text_annotation and response.full_text_annotation.text:
        full_text = response.full_text_annotation.text
    elif response.text_annotations:
        full_text = response.text_annotations[0].description or ""
    anon_text = anonymize_text(full_text)
    blood_tests = extract_blood_tests(anon_text)
    html_table = build_html_table(blood_tests)

    user_ctx = {
        "event_type": request.form.get("event_type", ""),
        "category_name": request.form.get("category_name", ""),
        "specialty_name": request.form.get("specialty_name", "")
    }
    gpt_json = maybe_call_gpt(anon_text, user_ctx)

    out = {
        "ok": True,
        "summary": summary,
        "event_date": event_date,
        "detected_specialty": detected_specialty,
        "suggested_tags": suggested_tags,
        "blood_test_results": blood_test_results,
        "diagnosis": diagnosis,
        "treatment_plan": treatment_plan,
        "data": {
            "raw_text": anon_text
        },
        "html_fragment": html_table,
        "anonymized": True
    }
    return jsonify(out)

    if gpt_json and isinstance(gpt_json, dict):
        if isinstance(gpt_json.get("blood_test_results"), list) and len(gpt_json["blood_test_results"]) >= len(blood_tests):
            out["blood_test_results"] = gpt_json["blood_test_results"]
            out["html_table"] = build_html_table(out["blood_test_results"])
        for k in ["summary", "event_date", "detected_specialty", "suggested_tags", "doctors", "diagnosis", "treatment_plan"]:
            if k in gpt_json and gpt_json[k] is not None:
                out[k] = gpt_json[k]
    else:
        out["summary"] = anon_text[:500]

    return jsonify(out), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
