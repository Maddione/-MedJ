#!/usr/bin/env sh
set -eu

cd /app/ocrapi 2>/dev/null || cd /app

APP_MODULE="${FLASK_APP:-app:app}"
PORT="${FLASK_RUN_PORT:-5000}"
export FLASK_DEBUG="${FLASK_DEBUG:-0}"

if [ -n "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]; then
  for _ in $(seq 1 30); do
    [ -f "${GOOGLE_APPLICATION_CREDENTIALS}" ] && break
    sleep 1
  done
fi

exec python -m flask --app "${APP_MODULE}" run --host=0.0.0.0 --port="${PORT}"
