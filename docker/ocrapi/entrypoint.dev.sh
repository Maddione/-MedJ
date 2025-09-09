#!/usr/bin/env sh
set -e


cd /app

APP_MODULE="${FLASK_APP:-ocrapi.app}"
export FLASK_DEBUG="${FLASK_DEBUG:-0}"

echo "FLASK_APP=${APP_MODULE}"
echo "GOOGLE_APPLICATION_CREDENTIALS=${GOOGLE_APPLICATION_CREDENTIALS:-unset}"
echo "PORT=${PORT:-5000}"

exec python -m flask --app "${APP_MODULE}" run --host=0.0.0.0 --port="${PORT:-5000}"