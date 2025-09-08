FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FLASK_APP=app.py \
    FLASK_RUN_HOST=0.0.0.0 \
    FLASK_RUN_PORT=5000 \
    OCRAPI_LOG_LEVEL=INFO

WORKDIR /app/ocrapi

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential tesseract-ocr libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

# Минималните зависимости; адаптирай ако имаш отделен requirements
RUN pip install --upgrade pip && \
    pip install flask google-cloud-vision pillow pytesseract

# Код на ocrapi (очаква се app.py тук)
COPY ocrapi/ /app/ocrapi/

COPY docker/ocrapi/entrypoint.dev.sh /app/ocrapi/entrypoint.dev.sh
RUN chmod +x /app/ocrapi/entrypoint.dev.sh

EXPOSE 5000

ENTRYPOINT ["/app/ocrapi/entrypoint.dev.sh"]
