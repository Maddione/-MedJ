FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev curl ca-certificates dumb-init && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt
COPY . /app
RUN chmod +x docker/web/entrypoint.dev.sh
EXPOSE 8000
ENTRYPOINT ["dumb-init","docker/web/entrypoint.dev.sh"]
