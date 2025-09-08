#!/bin/sh
set -eu
cd /app
until pg_isready -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}"; do
  echo "db:${POSTGRES_PORT} - no response"
  sleep 1
done
echo "db:${POSTGRES_PORT} - accepting connections"
python manage.py makemigrations --noinput || true
python manage.py migrate --database=default --noinput || true
python manage.py sync_taxonomy_tags || true
python manage.py seed_initial_data || true
python manage.py import_lab_indicators_csv /app/data/labtests-database.csv || true
python manage.py compilemessages -l bg -l en || true
mkdir -p /app/theme/static/css/dist
tailwindcss -i /app/theme/static/css/styles.css -o /app/theme/static/css/dist/output.css
tailwindcss -i /app/theme/static/css/styles.css -o /app/theme/static/css/dist/output.css --watch --poll="${TAILWIND_WATCH_POLL:-500}" &
python manage.py collectstatic --noinput || true
python manage.py backfill_event_tags || true
python manage.py optimize_indexes || true
python manage.py expire_shares || true
if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ]; then
  python manage.py createsuperuser --noinput || true
fi
exec python manage.py runserver 0.0.0.0:8000
