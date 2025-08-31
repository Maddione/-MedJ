#!/usr/bin/env sh
set -e

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-medj}"
DB_USER="${POSTGRES_USER:-medj}"
DB_PASSWORD="${POSTGRES_PASSWORD:-}"

python - <<'PY'
import os, time, sys
try:
    import psycopg
except Exception:
    sys.exit(0)
host=os.getenv("DB_HOST","db")
port=int(os.getenv("DB_PORT","5432"))
user=os.getenv("POSTGRES_USER","medj")
password=os.getenv("POSTGRES_PASSWORD","")
db=os.getenv("POSTGRES_DB","medj")
for _ in range(60):
    try:
        with psycopg.connect(host=host, port=port, user=user, password=password, dbname=db, connect_timeout=3):
            sys.exit(0)
    except Exception:
        time.sleep(1)
print("DB not reachable", file=sys.stderr)
sys.exit(1)
PY

mkdir -p /app/theme/static/css/dist

if [ "${TAILWIND_WATCH}" = "1" ]; then
  /usr/local/bin/tailwindcss -i /app/theme/static_src/styles.css -o /app/theme/static/css/dist/output.css --watch --poll &
else
  /usr/local/bin/tailwindcss -i /app/theme/static_src/styles.css -o /app/theme/static/css/dist/output.css
fi

python manage.py migrate --noinput
exec python manage.py runserver 0.0.0.0:8000
