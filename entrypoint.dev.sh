#!/usr/bin/env sh
set -e

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-medj}"
DB_USER="${POSTGRES_USER:-medj}"
DB_PASSWORD="${POSTGRES_PASSWORD:-}"

echo "Waiting for database at ${DB_HOST}:${DB_PORT} ..."
python - <<'PY'
import os, time, sys
import psycopg
host=os.getenv("DB_HOST","db")
port=int(os.getenv("DB_PORT","5432"))
user=os.getenv("POSTGRES_USER","medj")
password=os.getenv("POSTGRES_PASSWORD","")
db=os.getenv("POSTGRES_DB","medj")
for _ in range(60):
    try:
        with psycopg.connect(host=host, port=port, user=user, password=password, dbname=db, connect_timeout=3):
            print("Database is up.")
            sys.exit(0)
    except Exception:
        time.sleep(1)
print("Database NOT reachable, giving up.", file=sys.stderr)
sys.exit(1)
PY

echo "Applying migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Django dev server..."
exec python manage.py runserver 0.0.0.0:8000
