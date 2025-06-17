import os
import json
import openai
from django.conf import settings

try:
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    print("DEBUG: OpenAI client initialized successfully.")
except Exception as e:
    print(f"ERROR: Failed to initialize OpenAI client: {e}")
    client = None

def call_gpt_for_document(text: str, category: str, extracted_fields: dict) -> dict:
    if not client:
        print("ERROR: OpenAI client is not initialized when call_gpt_for_document is called.")
        raise ConnectionError("OpenAI клиентът не е инициализиран правилно. Проверете API ключа.")

    system_prompt = f"""
Ти си експертен асистент за обработка на медицински документи. Твоята задача е да анализираш предоставения текст от медицински документ, който е от категория '{category}', и да върнеш информацията в **строго един JSON обект**.

Този **единствен JSON обект** трябва да съдържа следните ключове на най-горно ниво:
1.  "summary": Кратко обобщение на документа от 1-2 изречения на български език.
2.  "html_table": HTML таблица (<table>...</table>) с два основни стълба: "Показател" и "Стойност/Резултат". Включи най-важните медицински показатели от документа.
3.  "event_date": Датата на медицинското събитие във формат ISO-MM-DD. Ако не е изрично посочена, използвай текущата дата.
4.  "detected_specialty": Медицинската специалност, свързана с документа (напр. "Ендокринология", "Кардиология").
5.  "suggested_tags": Масив от низове, съдържащи ключови думи/тагове, свързани със събитието (напр. ["Кръвни изследвания", "Щитовидна жлеза", "TSH"]).
6.  "blood_test_results": Масив от JSON обекти за кръвни изследвания. Всеки обект трябва да има ключове: "indicator_name", "value", "unit", "reference_range" (ако е налично). Ако документът не е кръвно изследване, този масив трябва да е празен: [].
7.  "diagnosis": Стринг с основната диагноза от документа, ако е приложимо. Ако не е, остави го празен стринг: "".
8.  "treatment_plan": Стринг с плана за лечение/препоръки от документа, ако е приложимо. Ако не е, остави го празен стринг: "".

Всички имена на хора (пациенти, лекари) в "summary", "html_table", "diagnosis", "treatment_plan" и други генерирани текстове трябва да бъдат анонимизирани до "Пациент" или "Лекар".

Пример за структура на JSON обект за кръвно изследване:
```json
{{
  "summary": "Пациентът е провел рутинни кръвни изследвания. Наблюдават се леко завишени стойности на TSH, което налага консултация с ендокринолог. Другите показатели са в норма.",
  "html_table": "<table><thead><tr><th>Показател</th><th>Стойност/Резултат</th></tr></thead><tbody><tr><td>Хемоглобин</td><td>145 g/L</td></tr><tr><td>TSH</td><td>5.1 mU/L</td></tr><tr><td>Глюкоза</td><td>5.4 mmol/L</td></tr></tbody></table>",
  "event_date": "2025-05-20",
  "detected_specialty": "Ендокринология",
  "suggested_tags": ["Хормони", "Щитовидна жлеза", "TSH"],
  "blood_test_results": [
    {{
      "indicator_name": "TSH",
      "value": "5.1",
      "unit": "mU/L",
      "reference_range": "0.4 - 4.0"
    }},
    {{
      "indicator_name": "Глюкоза",
      "value": "5.4",
      "unit": "mmol/L",
      "reference_range": "3.9 - 6.1"
    }}
  ],
  "diagnosis": "",
  "treatment_plan": ""
}}
```
"""
    try:
        print(f"DEBUG: Sending to GPT-4o. Category: {category}, Text length: {len(text)} chars. Text snippet: {text[:200]}...")
        completion = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            max_tokens=3000,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Ето текста за анализ:\n\n{text}"}
            ]
        )

        response_content = completion.choices[0].message.content
        print(f"DEBUG: Raw GPT response content type: {str(type(response_content))}")
        print(f"DEBUG: Raw GPT response content: {response_content[:1000]}...")

        parsed_json = json.loads(response_content)
        print("DEBUG: GPT response successfully parsed as JSON.")
        return parsed_json

    except openai.APIError as e:
        print(f"ERROR: OpenAI API Error in call_gpt_for_document: {e}")
        raise ConnectionError(f"Грешка при комуникация с OpenAI: {e}")
    except json.JSONDecodeError as e:
        print(f"ERROR: JSON Decode Error in call_gpt_for_document: {e}. Raw content was: {response_content[:1000]}...")
        return {}
    except Exception as e:
        print(f"CRITICAL ERROR: Unexpected error in gpt_client: {e}")
        raise Exception(f"Неочаквана грешка в gpt_client: {e}")


def summarize_document(text: str) -> str:
    """Извиква GPT за обобщение на текста."""
    if not client:
        return "Няма обобщение (OpenAI клиентът не е инициализиран)."
    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system",
                 "content": "Ти си помощник, който обобщава медицински текстове кратко и ясно на български."},
                {"role": "user", "content": f"Обобщи следния медицински текст кратко на български:\n\n{text}"}
            ],
            max_tokens=500
        )
        return str(completion.choices[0].message.content)
    except Exception as e:
        print(f"ERROR: Error summarizing document: {e}")
        return f"Грешка при обобщаване: {e}"


def extract_entities(text: str) -> dict:
    """Извиква GPT за извличане на ключови същности (диагнози, препоръки и т.н.)."""
    if not client:
        return {"error": "OpenAI клиентът не е инициализиран."}
    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system",
                 "content": "Ти си асистент, който извлича ключови същности (диагнози, препоръки, лекарства) от медицински текст и ги връща като JSON. Използвай ключове: 'Диагноза', 'Препоръки', 'Лекарства', 'ДатаНаСъбитието' (YYYY-MM-DD)."},
                {"role": "user", "content": f"Извлечи същности от следния медицински текст:\n\n{text}"}
            ],
            max_tokens=1000
        )
        return json.loads(str(completion.choices[0].message.content))
    except Exception as e:
        print(f"ERROR: Error extracting entities: {e}")
        return {"error": f"Грешка при извличане на същности: {e}"}


def analyze_lab_results(text: str) -> list:
    """Извиква GPT за анализ на лабораторни резултати и връща структуриран списък."""
    if not client:
        return [{"error": "OpenAI клиентът не е инициализиран."}]
    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system",
                 "content": "Ти си асистент, който извлича кръвни резултати от медицински текст. Върни списък от JSON обекти, всеки с ключове: 'indicator_name', 'value', 'unit', 'reference_range'. Ако няма референтен диапазон, остави празно."},
                {"role": "user", "content": f"Извлечи лабораторни резултати от следния текст:\n\n{text}"}
            ],
            max_tokens=1500
        )
        response_data = json.loads(str(completion.choices[0].message.content))
        if isinstance(response_data, list):
            return response_data
        elif isinstance(response_data, dict) and "results" in response_data:
            return response_data["results"]
        else:
            print(f"ERROR: Unexpected GPT response format for lab results: {response_data}")
            return []
    except Exception as e:
        print(f"ERROR: Error analyzing lab results: {e}")
        return [{"error": f"Грешка при анализ на лабораторни резултати: {e}"}]


def get_summary_and_html_table(text: str) -> dict:
    """
    Извиква GPT за генериране на обобщение и HTML таблица.
    Тази функция може да използва call_gpt_for_document, ако тя връща всичко необходимо.
    """
    if not client:
        return {"summary": "Няма обобщение (OpenAI клиентът не е инициализиран).",
                "html_table": "<table><tr><td>Няма таблица.</td></tr></table>"}

    try:
        gpt_output = call_gpt_for_document(text, "general", {})

        summary = str(gpt_output.get("summary", "Няма обобщение."))
        html_table = str(gpt_output.get("html_table", "<table><tr><td>Няма таблица.</td></tr></table>"))

        return {
            "summary": summary,
            "html_table": html_table
        }
    except Exception as e:
        print(f"ERROR: Error getting summary and HTML table: {e}")
        return {
            "summary": str(f"Грешка при генериране на обобщение и таблица: {e}"),
            "html_table": "<table><tr><td>Възникна грешка при генериране на таблица.</td></tr></table>"
        }