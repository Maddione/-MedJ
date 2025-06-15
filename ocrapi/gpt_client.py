import os
import json
import openai
from django.conf import settings

try:
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
except Exception as e:
    print(f"Грешка при инициализация на OpenAI: {e}")
    client = None

def extract_medical_fields_from_text(text: str) -> dict:
    print("DEBUG: extract_medical_fields_from_text беше извикана, но е празна.")
    return {}

def call_gpt_for_document(text: str, category: str, extracted_fields: dict) -> dict:
    if not client:
        raise ConnectionError("OpenAI клиентът не е инициализиран правилно. Проверете API ключа.")
    system_prompt = f"""
Ти си експертен асистент за обработка на медицински документи. Твоята задача е да анализираш предоставения текст от медицински документ, който е от категория '{category}', и да върнеш информацията в стриктен JSON формат.
JSON отговорът трябва да съдържа следните три ключа на най-горно ниво:
1. "summary": Кратко обобщение на документа от 1-2 изречения на български език.
2. "html_table": HTML таблица (<table>...</table>) с два основни стълба: "Показател" и "Стойност/Резултат". Включи най-важните медицински показатели от документа.
3. "json_data": JSON обект, съдържащ структурирани данни. Задължително включи поле "date" (във формат YYYY-MM-DD). Всички имена на хора трябва да бъдат анонимизирани.
"""
    try:
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
        return json.loads(response_content)
    except Exception as e:
        raise Exception(f"Неочаквана грешка в gpt_client: {e}")


def call_gpt_for_document(text: str, category: str, extracted_fields: dict) -> dict:
    """
    Изпраща обработения текст към GPT за анализ и структуриране.

    :param text: Анонимизираният текст от документа.
    :param category: Категорията на документа (напр. 'blood_test').
    :param`  extracted_fields: Предварително извлечени полета (в момента празен речник).
    :return: Речник с обобщение, HTML таблица и JSON данни.
    """
    if not client:
        raise ConnectionError("OpenAI клиентът не е инициализиран правилно. Проверете API ключа.")

    # --- Дефиниране на System Prompt ---
    # Това е инструкцията, която казва на AI как да се държи и какъв да е форматът на отговора.
    system_prompt = f"""
Ти си експертен асистент за обработка на медицински документи. Твоята задача е да анализираш предоставения текст от медицински документ, който е от категория '{category}', и да върнеш информацията в стриктен JSON формат.

JSON отговорът трябва да съдържа следните три ключа на най-горно ниво:
1.  "summary": Кратко обобщение на документа от 1-2 изречения на български език.
2.  "html_table": HTML таблица (<table>...</table>) с два основни стълба: "Показател" и "Стойност/Резултат". Включи най-важните медицински показатели от документа.
3.  "json_data": JSON обект, съдържащ структурирани данни. Задължително включи поле "date" (във формат YYYY-MM-DD), ако има дата на документа. Включи и други релевантни полета според документа (напр. "doctor_name", "patient_name", специфични кръвни показатели като "hemoglobin", "glucose" и т.н.). Всички имена на хора трябва да бъдат анонимизирани до "Пациент" или "Лекар".

Пример за структура на "json_data" за кръвно изследване:
{{
  "date": "2024-05-15",
  "laboratory": "Цибалаб",
  "hemoglobin": "145 g/L",
  "leukocytes": "7.5 G/L"
}}
"""

    try:
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
        return json.loads(response_content)

    except openai.APIError as e:
        # Специфична грешка от OpenAI (напр. невалиден ключ, претоварен сървър)
        print(f"OpenAI API Error: {e}")
        raise ConnectionError(f"Грешка при комуникация с OpenAI: {e}")
    except json.JSONDecodeError:
        # Грешка, ако AI върне нещо, което не е валиден JSON
        raise ValueError("Грешка: Отговорът от AI не е в очаквания JSON формат.")
    except Exception as e:
        # Всички други неочаквани грешки
        raise Exception(f"Неочаквана грешка в gpt_client: {e}")