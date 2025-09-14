#!/usr/bin/env sh
set -eu

log(){ printf '[ocrapi] %s\n' "$*"; }

CRED_FILE="${GOOGLE_APPLICATION_CREDENTIALS:-}"
CRED_INLINE="${GOOGLE_CLOUD_VISION_KEY:-}"

if [ -z "$CRED_FILE" ] && [ -z "$CRED_INLINE" ]; then
  log "ERROR: липсва GOOGLE_APPLICATION_CREDENTIALS или GOOGLE_CLOUD_VISION_KEY"; exit 1
fi
if [ -n "$CRED_FILE" ] && [ ! -f "$CRED_FILE" ]; then
  log "ERROR: ключов файл не съществува: $CRED_FILE"; ls -la "$(dirname "$CRED_FILE")" || true; exit 1
fi
if ! command -v tesseract >/dev/null 2>&1; then log "ERROR: липсва tesseract"; exit 1; fi

python - <<'PY'
import os, importlib
mods = ["flask","PIL","pytesseract","google.cloud.vision","pdf2image"]
for m in mods:
    try:
        importlib.import_module(m)
        print("[ocrapi] pydep OK:", m)
    except Exception as e:
        print("[ocrapi] pydep FAIL:", m, e)
print("[ocrapi] GOOGLE_APPLICATION_CREDENTIALS=", os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
print("[ocrapi] INLINE_KEY_SET=", bool(os.environ.get("GOOGLE_CLOUD_VISION_KEY")))
PY

if [ -f /app/ocrapi/app.py ]; then
  cd /app/ocrapi
  export FLASK_APP="app:app"
else
  cd /app
  export FLASK_APP="${FLASK_APP:-app:app}"
fi

export FLASK_ENV="${FLASK_ENV:-development}"
export FLASK_RUN_HOST="${FLASK_RUN_HOST:-0.0.0.0}"
export FLASK_RUN_PORT="${FLASK_RUN_PORT:-5000}"
export FLASK_DEBUG=0

exec flask run --host="$FLASK_RUN_HOST" --port="$FLASK_RUN_PORT" --no-reload
