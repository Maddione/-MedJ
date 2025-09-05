#!/bin/sh
set -e

python - <<'PY'
import os, time, sys, psycopg2
host = os.getenv("DB_HOST", "db")
port = os.getenv("DB_PORT", "5432")
for _ in range(60):
    try:
        psycopg2.connect(
            host=host,
            port=port,
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            dbname=os.getenv("POSTGRES_DB"),
        ).close()
        print("Database is up.")
        sys.exit(0)
    except psycopg2.OperationalError:
        time.sleep(1)
print("Database not reachable.", file=sys.stderr)
sys.exit(1)
PY

mkdir -p /app/theme/static/css/dist

if ! command -v tailwindcss >/dev/null 2>&1; then
  if command -v curl >/dev/null 2>&1; then
    curl -sL https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64 -o /usr/local/bin/tailwindcss
    chmod +x /usr/local/bin/tailwindcss
  elif command -v wget >/dev/null 2>&1; then
    wget -qO /usr/local/bin/tailwindcss https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64
    chmod +x /usr/local/bin/tailwindcss
  fi
fi

if command -v tailwindcss >/dev/null 2>&1 && [ -f /app/theme/static_src/styles.css ]; then
  tailwindcss -i /app/theme/static_src/styles.css -o /app/theme/static/css/dist/output.css
fi

python manage.py migrate --noinput || true
python manage.py collectstatic --noinput || true
python manage.py seed_initial_data || true
python manage.py shell -c "from django.contrib.auth import get_user_model; U=get_user_model(); U.objects.filter(username='admin').exists() or U.objects.create_superuser('admin','admin@example.com','adminpass')"
[ -f /app/data/labtests-database.csv ] && python manage.py import_lab_indicators_csv /app/data/labtests-database.csv || true

exec python manage.py runserver 0.0.0.0:8000
