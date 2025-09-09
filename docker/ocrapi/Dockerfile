FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=ocrapi.app \
    FLASK_RUN_HOST=0.0.0.0 \
    FLASK_RUN_PORT=5000 \
    OCRAPI_LOG_LEVEL=INFO

WORKDIR /app/ocrapi

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential tesseract-ocr libtesseract-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY ocrapi/requirements-ocr.txt /app/ocrapi/
RUN pip install --upgrade pip && \
    pip install -r requirements-ocr.txt

COPY ocrapi/ /app/ocrapi/
# copy entrypoint script outside of the mounted /app volume
COPY docker/ocrapi/entrypoint.dev.sh /entrypoint.dev.sh
RUN chmod +x /entrypoint.dev.sh

EXPOSE 5000
ENTRYPOINT ["/entrypoint.dev.sh"]