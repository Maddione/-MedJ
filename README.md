# MedJ — Персонален здравен дневник

MedJ е Django-базиран уебсайт за централизирано съхранение, обработка и визуализация на лична медицинска информация. 
Чрез използване на OCR (Google Cloud Vision API) и AI проектът автоматизира извличането на данни от документи и представянето им по ясен и споделяем начин.

## Технологии

- Python 3.x
- Django
- Google Cloud Vision API
- PostgreSQL / SQLite
- Git
- HTML + CSS (Django Templates)

## Основни функционалности

- Качване на PDF или изображения на медицински документи
- OCR обработка чрез Google Cloud Vision API
- Автоматично извличане на стойности (например TSH, глюкоза)
- Обобщения и групиране по медицински отрасъл и тип документ
- Визуализация на стойности по дати (например кръвни показатели)
- Потребителски профили с възможност за родител/настойник режим
- Генериране на PDF или QR линк с избрана информация


## Автор - Таня Узунова, 961324004 ТУ-София

Този проект е част от магистърска теза:
„Персонален здравен дневник – цялата медицинска информация на едно място“


## Примерен изглед на сайта ##

![websitecolors](https://github.com/user-attachments/assets/a0784770-071b-4d4e-a519-ac74ab4039ad)
![upload-afet-ocr](https://github.com/user-attachments/assets/011274bc-5226-4c22-9d00-42776c4d36e8)
![profiledropdownmenu](https://github.com/user-attachments/assets/526f5094-d962-4ecc-b58c-9f258ccd55cb)
![personalinformationcard](https://github.com/user-attachments/assets/a7915f53-fef0-4af5-9fdc-3ecc5c11800e)
![medicalcasehistory](https://github.com/user-attachments/assets/4e393101-11a3-43e2-87d1-623f24bb18b0)
![login-register](https://github.com/user-attachments/assets/fd089184-9619-4c1e-a71b-e62c2230e644)
![landingpage](https://github.com/user-attachments/assets/cf90b97d-9db2-4654-9658-d4206852bc90)
![historyofuploads](https://github.com/user-attachments/assets/91cb51aa-74b0-4ae2-985f-40be6b933373)
![documentuploadupdated](https://github.com/user-attachments/assets/1775d46c-3c33-40cc-b097-3c2811234f03)
![dashboard](https://github.com/user-attachments/assets/e9651707-84a9-497e-b7ec-f57fa5fa06ed)


## Инструкции за локално стартиране на MedJ2.0

Този документ описва стъпките, необходими за клониране и стартиране на проекта **MedJ2.0** (Персонален здравен дневник) отделно на вашата машина.

---

### 1. Изисквания

* **Python** (версия 3.10 или по-нова)
* **pip** (управление на пакети за Python)
* **virtualenv** или **venv**
* **Git**
* **PostgreSQL** (препоръчително) или друга базa данни, съвместима с Django

---

### 2. Клониране на репото

```bash
# Клонирайте репозитория
git clone https://github.com/Maddione/MedJ2.0.git
cd MedJ2.0
```

---

### 3. Създаване на виртуално средище

```bash
# Създайте и активирайте виртуално средище
python3 -m venv venv
source venv/bin/activate      # Linux/macOS
venv\\Scripts\\activate     # Windows
```

---

### 4. Инсталиране на зависимости

```bash
# Обновете pip и инсталирайте необходимите пакети
pip install --upgrade pip
pip install -r requirements.txt
```

---

### 5. Настройка на конфигурационен файл

1. Копирайте `.env.example` в `.env`:

   ```bash
   cp .env.example .env
   ```
2. Отворете `.env` и задайте следните променливи:

   * `SECRET_KEY` – генерирайте нова стойност (напр. чрез Django `startproject` или онлайн генератор)
   * `DEBUG` – `True` за разработка, `False` за продукция
   * `DATABASE_URL` – URL за достъп до вашата база данни (PostgreSQL):

     ```
     DATABASE_URL=postgres://USER:PASSWORD@HOST:PORT/DBNAME
     ```
   * Други специфични променливи (имейл сървър, S3, др.)

---

### 6. Миграции и създаване на суперпотребител

```bash
# Приложете миграциите
python manage.py migrate

# Създайте суперпотребител за администраторски достъп
python manage.py createsuperuser
```

---

### 7. Стартиране на сървъра в режим разработка

```bash
python manage.py runserver
```

* По подразбиране приложението ще е достъпно на `http://127.0.0.1:8000/`.

---

### 8. Допълнителни стъпки

* **Събиране на статични файлове (при нужда)**:

  ```bash
  python manage.py collectstatic
  ```
* **Използване на Docker** (ако проектът поддържа Docker):

  ```bash
  docker-compose up --build
  ```

---

### 9. Често срещани проблеми

* **Грешка при връзка с базата данни**: Проверете `DATABASE_URL` и инсталирането на драйвер (напр. `psycopg2-binary`).
* **Липсващи зависимости**: Уверете се, че `requirements.txt` е актуален и изпълнете `pip install -r requirements.txt`.

---

### 10. Полезни команди

| Команда                           | Описание                                        |
| --------------------------------- | ----------------------------------------------- |
| `python manage.py makemigrations` | Създава нови миграции на базата данни           |
| `python manage.py test`           | Стартира тестовете                              |
| `python manage.py shell`          | Отваря интерактивен Python shell с Django среда |

---

### Контакти

При въпроси или проблеми, моля, отворете **Issue** в GitHub: [https://github.com/Maddione/MedJ2.0/issues](https://github.com/Maddione/MedJ2.0/issues)

