#!/bin/sh
set -e
python - <<'PY'
import os,time,psycopg2
host=os.getenv("DB_HOST","db")
port=int(os.getenv("DB_PORT","5432"))
user=os.getenv("POSTGRES_USER")
pwd=os.getenv("POSTGRES_PASSWORD")
db=os.getenv("POSTGRES_DB")
for _ in range(120):
    try:
        psycopg2.connect(host=host,port=port,user=user,password=pwd,dbname=db).close()
        break
    except Exception:
        time.sleep(1)
PY
python manage.py compilemessages -l bg -l en || true
mkdir -p /app/theme/static/css/dist
tailwindcss -i /app/theme/static_src/styles.css -o /app/theme/static/css/dist/output.css --minify
tailwindcss -i /app/theme/static_src/styles.css -o /app/theme/static/css/dist/output.css --watch &
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py runserver 0.0.0.0:8000
