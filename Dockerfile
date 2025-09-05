FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    dumb-init \
    gettext \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libffi8 \
    libxml2 \
    libxslt1.1 \
    fonts-dejavu \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sL https://github.com/tailwindlabs/tailwindcss/releases/download/v4.1.12/tailwindcss-linux-x64 -o /usr/local/bin/tailwindcss && chmod +x /usr/local/bin/tailwindcss

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

EXPOSE 8000

ENTRYPOINT ["/usr/bin/dumb-init","--","/app/entrypoint.dev.sh"]
