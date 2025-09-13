# MedJ — Персонален здравен дневник

MedJ е Django приложение за централизирано съхранение, обработка и визуализация на лична медицинска информация. Поддържа OCR (Google Cloud Vision с Flask fallback), анонимизация преди AI анализ, структурирани данни (лабораторни), споделяне и експорт (PDF/CSV).

## Съдържание

* [Технологии](#технологии)
* [Каноничен поток](#каноничен-поток)
* [Политики и формати](#политики-и-формати)
* [Инсталация](#инсталация)
* [Конфигурация на среда](#конфигурация-на-среда)
* [Старт на средата за разработка](#старт-на-средата-за-разработка)
* [Основни страници](#основни-страници)
* [API ендпойнти](#api-ендпойнти)
* [Експорт](#експорт)
* [Споделяне](#споделяне)
* [UI насоки](#ui-насоки)
* [Тестове и CI](#тестове-и-ci)
* [Често срещани проблеми](#често-срещани-проблеми)
* [Автор](#автор)

## Технологии

*Django 5.x приложение (medj, records)
*OCR микросървис ocrapi с Google Cloud Vision
*База: PostgreSQL за продукция, SQLite за разработка
*Статика: предварително налични CSS/JS активи, без NPM билд стъпки
*Docker Compose оркестрация

Коренът съдържа основните директории: medj/, records/, ocrapi/, docker/, theme/static/, scripts/, tools/. 
GitHub
## Каноничен поток

### 1) Upload & OCR

* UI: Category → Specialty → Doc Type → File → File Kind.
* Ако има Events със същата комбинация (Category+Specialty+Doc Type), показва се dropdown за избор по `event_date`.
* Backend: `POST /api/upload/ocr/` първо Vision OCR, при неуспех Flask OCR.
* Отговор: `{"ocr_text":"...", "source":"vision|flask"}` и editable поле за OCR текста.

### 2) Analyze (с анонимизация)

* Backend: `POST /api/upload/analyze/`
* Вход: редактираният OCR текст + `specialty_id`.
* Анонимизацията се прилага преди подаване към LLM.
* Отговор:

```json
{
  "summary": "...",
  "data": {
    "summary": "...",
    "event_date": "YYYY-MM-DD",
    "detected_specialty": "...",
    "suggested_tags": ["..."],
    "blood_test_results": [
      {"indicator_name":"...","value":"...","unit":"...","reference_range":"...","measured_at":"YYYY-MM-DDTHH:mm:ss"}
    ],
    "diagnosis": "...",
    "treatment_plan": "...",
    "doctors": ["..."],
    "date_created": "YYYY-MM-DD"
  }
}
```

* UI: editable поле за Summary.

### 3) Confirm & Save

* Backend: `POST /api/upload/confirm/`
* Транзакционно:

  * Ако не е избрано Event → създава ново с `event_date = today`.
  * Document се свързва към Event и пази финален текст, summary, файл, mime, size, owner.
  * Ако `analysis.data.date_created` е подадено → запис в `date_created` и авто-таг `date:dd-mm-yyyy`.
  * Тагове:

    * Перманентни: `document_kind`, `specialty`, `category`, `doc_type`, `creation date(dd-mm-yyyy)` (не-редактируеми).
    * Редактируеми: от `suggested_tags` или въведени от потребителя.
    * Наследяване само Document → Event (union).
  * Лабораторни: нормализация към `LabIndicator` и `LabTestMeasurement` (float стойности, референтни граници, `measured_at`), FK към Event.
* Отговор: `{"ok": true, "event_id": ..., "document_id": ...}`
* UI: редирект към `/upload/history/`.

### 4) History & Casefiles

* `/upload/history/` — списък на Documents с филтри.
* `/casefiles/` — списък на Events, групиращи Document-и.

### 5) Sharing & Export

* ShareLink: токен, срок, парола, scope, формат; публичен read-only `/s/<token>/`.
* Export: PDF (с темплейти), CSV (`dd-mm-yyyy`).

## Политики и формати

* Анонимизация: винаги преди AI; потребителските редакции се пазят.
* Дати: вътрешно ISO; външно навсякъде `dd-mm-yyyy`.
* Събития: Event е родител; множество Documents към едно Event.
* Тагове: перманентни vs. редактируеми; наследяване само Document → Event.
* Лабораторни: единна таблица; `measured_at` нормализиран; подходящ за времеви серии.

## Инсталация

```bash
git clone https://github.com/Maddione/MedJ.git
cd MedJ
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Конфигурация на среда

```bash
DJANGO_SECRET_KEY=<secret>
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

DATABASE_URL=sqlite:///db.sqlite3
OPENAI_API_KEY=<key>

GOOGLE_CLOUD_PROJECT=<gcp-project-id>
GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/medj_vision_sa
OCR_SERVICE_URL=http://ocrapi:8001

```

PDF темплейти:

* `records/pdf_templates/pdf-template-twopage-bg.pdf`
* `records/pdf_templates/pdf-template-twopage-eng.pdf`
## Docker Compose

```bash
services:
  web:
    env_file: .env
    volumes:
      - ./:/app
    depends_on:
      - db
      - ocrapi

  db:
    image: postgres:16

  ocrapi:
    env_file: .env
    environment:
      - GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/medj_vision_sa
      - GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT}
    volumes:
      - C:\medj\secrets\gcp\medj-vision-sa.json:/run/secrets/medj_vision_sa:ro

```
## Старт на средата за разработка

```bash
docker compose up -d db
docker compose up --build web ocrapi
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py collectstatic --noinput
```

Админ: `http://localhost:8000/admin/`

## Основни страници

* `/upload/`
* `/upload/history/`
* `/casefiles/`
* `/s/<token>/`

## API ендпойнти

### Upload/Analyze/Confirm

* `POST /api/upload/ocr/`
* `POST /api/upload/analyze/`
* `POST /api/upload/confirm/`
* `GET  /api/events/suggest/?category_id=&specialty_id=&doc_type_id=`

### Share

* `POST /api/share/create/`
* `GET  /api/share/history/`
* `POST /api/share/revoke/<token>/`
* `GET  /api/share/qr/<token>.png`
* Публичен: `GET /s/<token>/`

### Export

* `GET /api/export/csv/?event_id=...`
* PDF: именовани маршрути, използвани от UI:

  * `document_export_pdf`
  * `event_export_pdf`

## Експорт

### CSV (лабораторни)

Формат на редовете:

```
event_id,event_date,indicator_name,value,unit,reference_low,reference_high,measured_at,tags
```

Всички дати в CSV са `dd-mm-yyyy`.

### PDF

Рендер на съдържание върху `pdf-template-twopage-<bg|eng>.pdf`. Всички визуализирани дати са `dd-mm-yyyy`.

## Споделяне

`ShareLink` полета:

* `token, owner, object_type (event|document), object_id, scope, format, expires_at, password_hash, created_at, status`

Ендпойнти:

* Създаване: `POST /api/share/create/` → връща URL `/s/<token>/` и QR PNG
* История: `GET /api/share/history/`
* Отмяна: `POST /api/share/revoke/<token>/`

## UI насоки

### Идентификатори и селектори (Upload)

* Избори: `#categorySelect` или `#sel_category`, `#specialtySelect` или `#sel_specialty`, `#docTypeSelect` или `#sel_doc_type`
* Файл: `#fileInput` или `#file_input`
* File Kind: `#fileKindSelect` или `#file_kind`
* Съществуващо събитие: `#existingEventWrap` + `#existingEventSelect`
* Редакция: `#ocrText`, `#summaryText`
* Бутони: `#btnOCR`, `#btnAnalyze`, `#btnConfirm` (съвместим и с `#btn_upload`)

### Цветова тема

```
--color-sitebg: #EAEBDA
--color-blockbg: #FDFEE9
--color-primary: #43B8CF
--color-primaryDark: #0A4E75
--color-success: #15BC11
--color-danger: #D84137
```

## Тестове и CI

Локално:

```bash
docker compose exec web python manage.py test -v 2
```

GitHub Actions:

* `.github/workflows/django.yml`

Покритие:

* Upload: OCR/Analyze/Confirm/Suggest
* Confirm: перманентни и редактируеми тагове, наследяване Document→Event, labs нормализация, `date_created`
* Share: create/history/revoke, публичен `/s/<token>/`
* Export: CSV и PDF

## Често срещани проблеми

* Vision OCR не връща текст: проверете `GOOGLE_APPLICATION_CREDENTIALS`.
* Flask OCR недостъпен: проверете `OCR_SERVICE_URL` и `/ocr`.
* LLM ключ: задайте `OPENAI_API_KEY` или `OPENAI_API_KEY_FILE`.
* Несъответствие на ID-та в Upload HTML/JS: поддържат се `sel_*` и новите ID-та.
* Дати: външно винаги `dd-mm-yyyy`.

## Автор
Таня Узунова. Дипломна работа „Персонален здравен дневник“.

Таня Узунова, 961324004, ТУ-София
Магистърска теза „Персонален здравен дневник – цялата медицинска информация на едно място“.
