import os
import json
import openai
from openai import OpenAI
from django.utils.translation import gettext as _l  # Добавено за преводи

client = None
try:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(_l("OPENAI_API_KEY environment variable not set."))
    client = OpenAI(api_key=api_key)
except Exception as e:
    pass


def call_gpt_for_document(text: str, user_context: dict) -> dict:
    if not client:
        raise ConnectionError(_l("OpenAI клиентът не е инициализиран правилно. Проверете API ключа."))

    event_type = user_context.get('event_type', _l('неизвестен'))
    category_name = user_context.get('category_name', _l('неизвестна'))
    specialty_name = user_context.get('specialty_name', _l('неизвестна'))

    system_prompt = f"""
Ти си експертен асистент за обработка на медицински документи по {specialty_name}. Твоята задача е да извличаш, структурираш и обобщаваш ключова медицинска информация от предоставените текстове от {category_name}.
Изключително важно е да даваш отговорите само на български език.
Използвай предоставения контекст от потребителя за {event_type} за да направиш анализа по-прецизен и фокусиран.

Очаквай следните ключове в JSON отговора:
- "summary": Кратко, обобщено резюме на документа на български език (2-3 изречения).
- "event_date": Датата на събитието, ако е налична (форматYYYY-MM-DD). Ако няма, използвай текущата дата.
- "detected_specialty": Медицинска специалност, ако може да бъде извлечена (напр. "Кардиология", "Пулмология").
- "suggested_tags": Списък от 3 до 5 подходящи тага (напр. ["Пневмония", "Болнично лечение", "Антибиотик", "Левкоцити"]).

В допълнение, ако документът съдържа структурирани данни, върни ги под ключ "structured_data" като списък от обекти. Всеки обект в този списък трябва да има поле "type", което да указва вида на данните, и специфични полета за този тип.

Поддържани типове "structured_data":

1.  Ако документът е лабораторно изследване (категория: "Кръвни изследвания", "Изследване на урина" и т.н.):
    type: "blood_test_panel"
    panel_name: Име на панела (ако е налично, напр. "ПКК", "Биохимия")
    results: Списък от обекти, всеки с:
        indicator_name: Име на показателя (напр. "Левкоцити (WBC)", "Хемоглобин (HGB)")
        value: Стойност (напр. "12.5", "142")
        unit: Мерна единица (напр. "x10^9/L", "g/L")
        reference_range: Референтни граници (напр. "4.0 - 10.0", "135 - 175")
        is_abnormal: Boolean (true/false) дали стойността е извън референтните граници.
        notes: Допълнителни бележки за резултата (ако има)

2.  Ако документът е епикриза или друг дълъг текстов документ (категория: "Епикриза", "Амбулаторен лист", "Консултация"):
    type: "narrative_section"
    section_title: Заглавие на секцията (напр. "Диагноза при приемане", "Проведено лечение", "Заключение и препоръки")
    section_content: Съдържание на секцията.

3.  Ако се разпознае лекар (напр. "Д-р Иван Иванов"):
    type: "detected_practitioner"
    name: Пълно име на лекаря (напр. "Иван Иванов", "Мария Петрова")
    title: Титла (напр. "Д-р", "Проф.", "Доц.", "Асистент", "Мед. сестра")
    inferred_specialty: Изведена специалност от текста (ако може да се определи, напр. "Пулмология", "Кардиология")

4.  Ако се разпознае Диагноза:
    type: "diagnosis"
    diagnosis_text: Пълен текст на диагнозата
    icd10_code: Код по МКБ-10 (ако е наличен)
    date: Дата на диагностициране (форматYYYY-MM-DD)

5.  Ако се разпознае План за лечение:
    type: "treatment_plan"
    plan_text: Пълен текст на плана за лечение
    medications: Списък от лекарства (напр. ["Аугментин", "Парацетамол"])
    start_date: Начална дата на лечение (форматYYYY-MM-DD)
    end_date: Крайна дата на лечение (форматYYYY-MM-DD)

Винаги връщай валиден JSON. Ако не можеш да извлечеш определен ключ, го изключи от JSON-а или го остави празен стринг/списък, но не връщай null.
Използвай български език за всички извлечени текстови полета и резюме.
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
        raise ConnectionError(_l(f"Грешка при комуникация с OpenAI: {e}"))
    except json.JSONDecodeError:
        raise ValueError(_l("Грешка: Отговорът от AI не е в очаквания JSON формат."))
    except Exception as e:
        raise Exception(_l(f"Неочаквана грешка в gpt_client: {e}"))