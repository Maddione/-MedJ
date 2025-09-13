#!/usr/bin/env sh
set -eu

cd /app

if [ -f theme/static/css/styles.css ]; then
  mkdir -p static/css
  if command -v tailwindcss >/dev/null 2>&1; then
    tailwindcss -i theme/static/css/styles.css -o static/css/tailwind.css --minify || true
  fi
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput || true
python manage.py compilemessages || true

if [ -n "${RUN_INITIAL_SEED:-}" ]; then
  python manage.py sync_taxonomy_tags || true
  python manage.py seed_initial_data || true
  python manage.py import_lab_indicators_csv /app/data/labtests-database.csv || true
  python manage.py optimize_indexes || true
  python manage.py backfill_event_tags || true
fi

if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_EMAIL:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
  python manage.py createsuperuser --noinput || true
fi

if [ "${TAILWIND_WATCH:-1}" = "1" ] && [ -f theme/static/css/styles.css ] && command -v tailwindcss >/dev/null 2>&1; then
  tailwindcss -i theme/static/css/styles.css -o static/css/tailwind.css --watch --poll &
fi

exec python manage.py runserver 0.0.0.0:8000
