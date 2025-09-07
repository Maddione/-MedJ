FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

ARG TAILWIND_ARCH=linux-x64

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl ca-certificates dumb-init gettext \
 && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-${TAILWIND_ARCH} -o /usr/local/bin/tailwindcss \
 && chmod +x /usr/local/bin/tailwindcss

# Tailwind CLI (arch-aware бинар)
RUN set -eux; arch="$(uname -m)"; \
    case "$arch" in \
      x86_64) f=tailwindcss-linux-x64 ;; \
      aarch64|arm64) f=tailwindcss-linux-arm64 ;; \
      *) f=tailwindcss-linux-x64 ;; \
    esac; \
    curl -fsSL -o /usr/local/bin/tailwindcss \
      "https://github.com/tailwindlabs/tailwindcss/releases/latest/download/${f}" && \
    chmod +x /usr/local/bin/tailwindcss


WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt

COPY . /app
RUN chmod +x docker/web/entrypoint.dev.sh

EXPOSE 8000
ENTRYPOINT ["dumb-init","docker/web/entrypoint.dev.sh"]
