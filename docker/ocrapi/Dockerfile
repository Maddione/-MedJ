FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y build-essential tesseract-ocr libtesseract-dev && rm -rf /var/lib/apt/lists/*
COPY ocrapi/requirements-ocr.txt /tmp/requirements-ocr.txt
RUN pip install --no-cache-dir -r /tmp/requirements-ocr.txt
COPY . .
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]
