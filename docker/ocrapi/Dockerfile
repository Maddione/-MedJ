FROM python:3.12-alpine

WORKDIR /app

RUN apk add --no-cache tesseract-ocr tesseract-ocr-data poppler-utils
RUN apk add --no-cache tesseract-ocr-eng || true && apk add --no-cache tesseract-ocr-bul || true

COPY requirements-ocr.txt /app/requirements-ocr.txt
RUN pip install --no-cache-dir -r /app/requirements-ocr.txt

COPY ocrapi/ /app/
COPY docker/ocrapi/entrypoint.dev.sh /usr/local/bin/ocrapi-entrypoint
RUN chmod +x /usr/local/bin/ocrapi-entrypoint

EXPOSE 5000
ENTRYPOINT ["/usr/local/bin/ocrapi-entrypoint"]
