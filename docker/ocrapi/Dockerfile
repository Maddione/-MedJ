FROM python:3.12-alpine
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apk add --no-cache tesseract-ocr tesseract-ocr-data poppler-utils wget ca-certificates && \
    mkdir -p /usr/share/tessdata && \
    wget -qO /usr/share/tessdata/eng.traineddata https://github.com/tesseract-ocr/tessdata_fast/raw/main/eng.traineddata && \
    wget -qO /usr/share/tessdata/bul.traineddata https://github.com/tesseract-ocr/tessdata_fast/raw/main/bul.traineddata
WORKDIR /app
COPY ocrapi/requirements-ocr.txt /app/requirements-ocr.txt
RUN pip install --no-cache-dir -r /app/requirements-ocr.txt
COPY ocrapi/ /app/
COPY docker/ocrapi/entrypoint.dev.sh /usr/local/bin/ocrapi-entrypoint
RUN sed -i 's/\r$//' /usr/local/bin/ocrapi-entrypoint && chmod +x /usr/local/bin/ocrapi-entrypoint
ENTRYPOINT ["/usr/local/bin/ocrapi-entrypoint"]
