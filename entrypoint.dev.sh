#!/bin/sh
set -e

python - <<'PY'
import os, time, sys, psycopg2
host = os.getenv("DB_HOST", "db")
port = os.getenv("DB_PORT", "5432")
for _ in range(60):
    try:
        psycopg2.connect(host=host, port=port, user=os.getenv("POSTGRES_USER"), password=os.getenv("POSTGRES_PASSWORD"), dbname=os.getenv("POSTGRES_DB"))
        print("Database is up.")
        sys.exit(0)
    except psycopg2.OperationalError:
        time.sleep(1)
print("Database not reachable.", file=sys.stderr)
sys.exit(1)
PY

mkdir -p /app/theme/static/css/dist

echo "Starting Tailwind CSS v4 watcher..."
tailwindcss \
  -i /app/theme/static_src/styles.css \
  -o /app/theme/static/css/dist/output.css \
  --content "/app/records/templates/**/*.html" \
  --watch \
  --poll &

echo "Applying migrations..."
python manage.py migrate --noinput

echo "Seeding database..."
python manage.py seed_initial_data || true

echo "Creating default superuser..."
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin','admin@example.com','adminpass')"


echo "Starting Django development server..."
exec python manage.py runserver 0.0.0.0:8000
