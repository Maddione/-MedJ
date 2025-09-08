#!/usr/bin/env bash
set -euo pipefail

cd /app

# Изчакай DB при нужда (проста ретрия логика)
if [ -n "${DB_HOST:-}" ]; then
  for i in {1..30}; do
    python - <<'PY'
import os, sys, socket
host=os.environ.get("DB_HOST","db"); port=int(os.environ.get("DB_PORT","5432"))
s=socket.socket();
try:
  s.settimeout(2); s.connect((host,port)); print("db ok")
except Exception as e:
  print("db wait:", e); sys.exit(1)
PY
    if [ $? -eq 0 ]; then break; fi
    sleep 1
  done
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput || true
python manage.py compilemessages || true

# Django dev server
exec python manage.py runserver 0.0.0.0:8000
