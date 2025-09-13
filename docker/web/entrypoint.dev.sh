#!/usr/bin/env sh
set -eu

cd /app

python manage.py migrate --noinput
python manage.py collectstatic --noinput || true
python manage.py compilemessages || true

if [ -n "${RUN_INITIAL_SEED:-}" ]; then
  python manage.py sync_taxonomy_tags || true
  python manage.py seed_initial_data   || true
  python manage.py import_lab_indicators_csv /app/data/labtests-database.csv || true
fi

if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_EMAIL:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
  python manage.py createsuperuser --noinput || true
fi

exec python manage.py runserver 0.0.0.0:8000
