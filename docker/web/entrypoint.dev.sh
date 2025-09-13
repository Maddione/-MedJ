#!/usr/bin/env sh
set -eu
cd /app

if [ -n "${DB_HOST:-}" ]; then
  tries=30
  while [ "$tries" -gt 0 ]; do
    python - <<'PY'
import os, socket, sys
h=os.environ.get("DB_HOST","db"); p=int(os.environ.get("DB_PORT","5432"))
s=socket.socket(); s.settimeout(2)
try: s.connect((h,p)); sys.exit(0)
except Exception: sys.exit(1)
PY
    [ $? -eq 0 ] && break
    tries=$((tries-1))
    sleep 1
  done
fi

python manage.py migrate --noinput || true

if command -v tailwindcss >/dev/null 2>&1; then
  mkdir -p theme/static/css/dist
  tailwindcss -i /app/theme/static_src/styles.css -o /app/theme/static/css/dist/output.css || true
fi

python manage.py collectstatic --noinput || true
python manage.py compilemessages || true

if [ -n "${RUN_INITIAL_SEED:-}" ]; then
  python manage.py sync_taxonomy_tags || true
  python manage.py seed_initial_data || true
  python manage.py import_lab_indicators_csv /app/data/labtests-database.csv || true
fi

if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_EMAIL:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
  python manage.py createsuperuser --noinput || true
fi

exec python manage.py runserver 0.0.0.0:8000