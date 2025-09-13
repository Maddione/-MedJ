FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl libpq-dev gettext git \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel \
 && pip install -r /app/requirements.txt

COPY . /app
COPY docker/web/entrypoint.dev.sh /usr/local/bin/web-entrypoint
RUN sed -i 's/\r$//' /usr/local/bin/web-entrypoint && chmod +x /usr/local/bin/web-entrypoint

EXPOSE 8000
ENTRYPOINT ["/usr/local/bin/web-entrypoint"]
