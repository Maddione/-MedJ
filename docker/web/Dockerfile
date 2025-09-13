FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl libpq-dev git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /app/requirements.txt

COPY docker/web/entrypoint.dev.sh /app/entrypoint.dev.sh
RUN sed -i 's/\r$//' /app/entrypoint.dev.sh && chmod +x /app/entrypoint.dev.sh

EXPOSE 8000
ENTRYPOINT ["sh","-lc","/app/entrypoint.dev.sh"]
