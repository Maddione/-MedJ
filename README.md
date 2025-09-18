# MedJ — Персонален здравен дневник

MedJ е Django приложение за централизирано съхранение, обработка и визуализация на лична медицинска информация.
Поддържа OCR микросървис (`ocrapi`) за извличане на текст и анонимизация преди AI анализ.

## Предварителни изисквания
- Git
- Docker Desktop с Docker Compose v2

## Стартиране на проекта

### 1) Клониране

```bash
git clone https://github.com/Maddione/-MedJ.git
cd .\-MedJ
````

### 2) Env и Secrets

**Windows PowerShell**

```powershell
New-Item -ItemType Directory -Force .\secrets | Out-Null
ni .\secrets\django-key.txt,.\secrets\openai-key.txt,.\secrets\gcp-vision.json -ItemType File -Force | Out-Null
```

**macOS/Linux**

```bash
mkdir -p docker/env secrets
touch secrets/django-key.txt secrets/openai-key.txt secrets/gcp-vision.json
```

Попълнете реални стойности в `secrets/`. Примерните env ключове са в `docker/env/*.env.example`.

### 3) Build

```bash
docker compose -f docker/compose/docker-compose.dev.yml build
```

### 4) Старт

```bash
docker compose -f docker/compose/docker-compose.dev.yml up -d db ocrapi web
```

### 5) Проверка

```bash
docker compose -f docker/compose/docker-compose.dev.yml ps
docker compose -f docker/compose/docker-compose.dev.yml logs -f web
docker compose -f docker/compose/docker-compose.dev.yml logs -f ocrapi
```

### 6) Достъп

* Приложение: [http://localhost:8000](http://localhost:8000)
* Админ: [http://localhost:8000/admin](http://localhost:8000/admin)
* OCR API: [http://localhost:5000](http://localhost:5000)

### 7) Тестове

```bash
docker compose -f docker/compose/docker-compose.dev.yml --project-directory . run --rm --no-deps --entrypoint sh web -lc "python manage.py test"
```

### 8) Спиране

```bash
docker compose -f docker/compose/docker-compose.dev.yml --project-directory . down -v
```

## Конфигурация на среда

Основните променливи са в `docker/env/web.dev.env.example` и `docker/env/ocr.dev.env.example`. Ключови параметри:

* **Web (Django)**

  * База за development: PostgreSQL през `db` контейнера. (`DATABASE_URL=postgres://medj:medj@db:5432/medj`);
  * OCR URL: `http://ocrapi:5000` или ендпойнт `http://ocrapi:5000/ocr` ;

* **OCR API (Flask)**

  * Порт: `5000` (local → `http://localhost:5000`);
  * `GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/gcloudvision-service-key.json`;

## Docker Compose

Ползвайте `docker/compose/docker-compose.dev.yml`.

* `db`: Postgres 15, healthcheck, volume `postgres_data`;
* `ocrapi`: порт 5000, secrets в `/secrets`, healthcheck `/healthz`;
* `web`: миграции + collectstatic при старт, порт 8000;

## Каноничен поток

Upload → OCR → Analyze → Confirm → History/Casefiles → Share/Export.

## Основни страници

* `/upload/`
* `/upload/history/`
* `/casefiles/`
* Публично споделяне: `/s/<token>/`

## Подстраници

### Documents

* `records/templates/subpages/documentsubpages/document_detail.html` — детайлен изглед на единичен документ, достъпен през `/documents/<id>/`. Свързани шаблони: `document_edit.html`, `document_edit_tags.html`, `document_export_pdf.html`, `document_move.html`.
* `records/templates/subpages/documentsubpages/document_edit.html` — редакция на метаданните (тип, дата, заглавие) от бутона „Редакция“ в детайла.
* `records/templates/subpages/documentsubpages/document_edit_tags.html` — управление на таговете на документа от детайлния изглед.
* `records/templates/subpages/documentsubpages/document_export_pdf.html` — експорт на документа или summary в PDF формат от детайла.
* `records/templates/subpages/documentsubpages/document_move.html` — преместване на документ към друго събитие, достъпно от детайлния изглед.

### Events

* `records/templates/subpages/eventsubpages/event_detail.html` — детайл на `MedicalEvent`, достъпен от документите или историята на събитията.
* `records/templates/subpages/eventsubpages/event_edit_tags.html` — управление на тагове за събитие.
* `records/templates/subpages/eventsubpages/event_export_pdf.html` — експорт на събитие в PDF.
* `records/templates/subpages/eventsubpages/event_history.html` — история на промените за дадено събитие.
* `records/templates/subpages/eventsubpages/medical_event_form.html` — форма за създаване/редакция на събитие.
* `records/templates/subpages/eventsubpages/medical_event_confirm_delete.html` — потвърждение за изтриване на събитие.

### Lab tests

* `records/templates/subpages/labtestssubpages/labtests.html` — списък с лабораторни панели и резултати.
* `records/templates/subpages/labtestssubpages/labtest_edit.html` — редакция на конкретен лабораторен тест.
* `records/templates/subpages/labtestssubpages/labtests_export_csv.html` — експорт на лабораторни данни в CSV.

### Други

* `records/templates/subpages/doctors.html` — списък и управление на лекари.
* `records/templates/subpages/personalcard_public.html` — публичен read-only изглед на личния картон за споделяне.
* `records/templates/subpages/profile_settings.html` — настройки на профила.
* `records/templates/subpages/share_history.html` — история на споделянията.
* `records/templates/subpages/share_public.html` — публична страница за споделен ресурс.
* `records/templates/subpages/share_view.html` — визуализация на споделените данни.
* `records/templates/subpages/csv_print.html` — помощник за печат и експорт в CSV.

## API ендпойнти

### Upload/Analyze/Confirm

* `POST /api/upload/ocr/`
* `POST /api/upload/analyze/`
* `POST /api/upload/confirm/`

### Share

* `POST /api/share/create/`
* `GET  /api/share/history/`
* `POST /api/share/revoke/<token>/`
* Публично: `GET /s/<token>/`

### Export

* `GET /api/export/csv/?event_id=...`
* PDF: `document_export_pdf`, `event_export_pdf`

## Експорт

### CSV (лабораторни)

```
event_id,event_date,indicator_name,value,unit,reference_low,reference_high,measured_at,tags
```

Дати: `dd-mm-yyyy`.

### PDF

Рендер върху `pdf-template-twopage-<bg|eng>.pdf`.

## Често срещани проблеми

* OCR не тръгва: валидирайте `GOOGLE_APPLICATION_CREDENTIALS` и наличността на файла в `/secrets`;
* Web не се вдига: проверете миграции и логовете на `web` и `db`. Миграциите се пускат автоматично при старт;
* Невалиден OCR URL: използвайте `http://ocrapi:5000` от вътрешната мрежа на Compose, не `8001`.

## Автор
Таня Узунова. Дипломна работа „Персонален здравен дневник“.

Таня Узунова, 961324004, ТУ-София Магистърска теза „Персонален здравен дневник – цялата медицинска информация на едно място“.
