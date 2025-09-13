FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app/ocrapi

RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl git && rm -rf /var/lib/apt/lists/*

COPY ocrapi/requirments-ocr.txt /app/ocrapi/requirments-ocr.txt

RUN pip install --upgrade pip setuptools wheel \
 && pip install -r /app/ocrapi/requirments-ocr.txt

COPY docker/ocrapi/entrypoint.dev.sh /usr/local/bin/ocrapi-entrypoint
RUN sed -i 's/\r$//' /usr/local/bin/ocrapi-entrypoint && sed -i '1s/^\xEF\xBB\xBF//' /usr/local/bin/ocrapi-entrypoint && chmod +x /usr/local/bin/ocrapi-entrypoint

EXPOSE 5000

ENTRYPOINT ["sh","-lc","/app/docker/ocrapi/entrypoint.dev.sh"]