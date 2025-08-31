#!/usr/bin/env sh
set -euo pipefail

log() { printf "\033[1;36m[entrypoint]\033[0m %s\n" "$*"; }

APP_DIR="/app"
IN="theme/static_src/styles.css"
OUT_DIR="theme/static/css/dist"
OUT="$OUT_DIR/output.css"

log "Node: $(node -v 2>/dev/null || echo 'missing') | npm: $(npm -v 2>/dev/null || echo 'missing')"
log "Tailwind CLI: $(tailwindcss -v 2>/dev/null || echo 'missing')"

# Увери се, че входният файл съществува
if [ ! -f "$IN" ]; then
  log "ERROR: липсва входен файл $IN. Провери мапинга/пътя."
  exit 1
fi

# Директория за изхода
mkdir -p "$OUT_DIR"

# Билд на Tailwind
if command -v tailwindcss >/dev/null 2>&1; then
  log "Билдвам Tailwind → $OUT"
  tailwindcss -i "$IN" -o "$OUT" --minify
else
  log "ERROR: липсва tailwindcss CLI. Инсталирай го в image-а."
  exit 1
fi

# collectstatic → да попадне в /staticfiles
log "Събирам static файловете"
python manage.py collectstatic --noinput

# миграции (по избор – няма да прекъсне при грешка)
python manage.py migrate --noinput || true

# По желание: watch режим (за dev)
if [ "${TAILWIND_WATCH:-0}" = "1" ]; then
  log "Пускам Tailwind в --watch (bg)"
  tailwindcss -i "$IN" -o "$OUT" --watch --minify &
fi

# Django dev server
log "Стартирам Django на 0.0.0.0:8000"
python manage.py runserver 0.0.0.0:8000
