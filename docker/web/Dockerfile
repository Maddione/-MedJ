FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Системни зависимости по нужда на проекта (psycopg, pillow и т.н.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl libpq-dev git \
    && rm -rf /var/lib/apt/lists/*

# Инсталация на Python зависимости
# Ако имаш lock/constraints, смени имената по проекта
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /app/requirements.txt

# Код на приложението
COPY . /app

# Entrypoint скриптът, към който сочи Compose
RUN chmod +x /app/docker/web/entrypoint.dev.sh

EXPOSE 8000

ENTRYPOINT ["/app/docker/web/entrypoint.dev.sh"]
