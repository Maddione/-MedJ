# ---- Base image ----
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/usr/local/bin:${PATH}"

WORKDIR /app

# ---- System deps + Node.js 20 + Tailwind CLI v4 ----
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates gnupg build-essential \
    && rm -rf /var/lib/apt/lists/*

# NodeSource setup for Node.js 20
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get update && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Tailwind v4 CLI (глобално, без node_modules в проекта)
RUN npm i -g @tailwindcss/cli@latest

# ---- Python deps ----
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r /app/requirements.txt

# ---- Project files ----
# Важно: увери се, че следните пътища съществуват в репото ти
COPY . /app

# (По избор) билд на Tailwind по време на build — ако искаш артефактът да е наличен веднага
# Ако тези файлове не са копирани горе, премахни този RUN
RUN if command -v tailwindcss >/dev/null 2>&1; then \
      echo "Building Tailwind at build time..."; \
      mkdir -p /app/theme/static/css/dist && \
      tailwindcss \
        -i theme/static_src/styles.css \
        -o theme/static/css/dist/output.css \
        --minify || true ; \
    fi

# Entrypoint
COPY entrypoint.dev.sh /app/entrypoint.dev.sh
RUN chmod +x /app/entrypoint.dev.sh

EXPOSE 8000
CMD ["/app/entrypoint.dev.sh"]
