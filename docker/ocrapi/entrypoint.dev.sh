#!/usr/bin/env bash
set -euo pipefail

cd /app/ocrapi

# Диагностика за креденшъли и бекенд
echo "OCR_BACKEND=${OCR_BACKEND:-unset}"
echo "GOOGLE_APPLICATION_CREDENTIALS=${GOOGLE_APPLICATION_CREDENTIALS:-unset}"
echo "GCP_PROJECT=${GCP_PROJECT:-unset}"

# Бърз импорт тест за Vision (не фейлва контейнера)
python - <<'PY' || true
try:
  import google.cloud.vision as v  # noqa
  print("google-cloud-vision import: OK")
except Exception as e:
  print("google-cloud-vision import: FAIL ->", e)
PY

# Flask dev server (както е в Compose)
exec python -m flask run --host=0.0.0.0 --port=5000
