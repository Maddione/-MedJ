FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev curl ca-certificates dumb-init gettext libcairo2 libgdk-pixbuf-2.0-0 libpango-1.0-0 libpangocairo-1.0-0 fonts-dejavu && rm -rf /var/lib/apt/lists/*
RUN set -eux; arch="$(uname -m)"; case "$arch" in x86_64) f=tailwindcss-linux-x64;; aarch64) f=tailwindcss-linux-arm64;; *) f=tailwindcss-linux-x64;; esac; curl -L -o /usr/local/bin/tailwindcss "https://github.com/tailwindlabs/tailwindcss/releases/latest/download/$f"; chmod +x /usr/local/bin/tailwindcss
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt
COPY . /app
RUN chmod +x /app/docker/web/entrypoint.dev.sh
EXPOSE 8000
ENTRYPOINT ["/usr/bin/dumb-init","--","/app/docker/web/entrypoint.dev.sh"]
