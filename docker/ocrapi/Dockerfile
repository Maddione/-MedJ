FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr libtesseract-dev curl ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY ocrapi/requirements-ocr.txt /app/requirements-ocr.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r /app/requirements-ocr.txt
COPY ocrapi/ /app
EXPOSE 5000
CMD ["gunicorn","-b","0.0.0.0:5000","app:app"]
