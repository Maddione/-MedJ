FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app/ocrapi

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /app/requirements.txt

COPY docker/ocrapi/entrypoint.dev.sh /app/ocrapi/entrypoint.dev.sh
RUN sed -i 's/\r$//' /app/ocrapi/entrypoint.dev.sh && chmod +x /app/ocrapi/entrypoint.dev.sh

EXPOSE 5000
ENTRYPOINT ["sh","-lc","/app/ocrapi/entrypoint.dev.sh"]
