FROM python:3.12-alpine
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
RUN apk add --no-cache tesseract-ocr tesseract-ocr-data-eng tesseract-ocr-data-bul poppler-utils libstdc++ libgcc
WORKDIR /app
COPY ocrapi/requirements-ocr.txt /app/requirements-ocr.txt
RUN pip install --no-cache-dir -r /app/requirements-ocr.txt
COPY ocrapi/ /app/
ENTRYPOINT ["/app/entrypoint.dev.sh"]
