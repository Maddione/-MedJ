#!/usr/bin/env bash
set -euo pipefail

log(){ printf '[ocrapi] %s\n' "$*"; }

CRED_FILE="${GOOGLE_APPLICATION_CREDENTIALS:-}"
CRED_INLINE="${GOOGLE_CLOUD_VISION_KEY:-}"

if [[ -z "${CRED_FILE}" && -z "${CRED_INLINE}" ]]; then
  log "ERROR: липсва GOOGLE_APPLICATION_CREDENTIALS или GOOGLE_CLOUD_VISION_KEY"; exit 1
fi
if [[ -n "${CRED_FILE}" && ! -f "${CRED_FILE}" ]]; then
  log "ERROR: ключов файл не съществува: ${CRED_FILE}"; ls -la "$(dirname "${CRED_FILE}")" || true; exit 1
fi

command -v tesseract >/dev/null || { log "ERROR: липсва tesseract"; exit 1; }
command -v pdftoppm  >/dev/null || log "WARN: липсва poppler-utils (PDF OCR може да е ограничен)"

python - <<'PY'
import os, importlib
mods = ["flask","pillow","pytesseract","google.cloud.vision","pdf2image"]
for m in mods:
    try: importlib.import_module(m); print("[ocrapi] pydep OK:", m)
    except Exception as e: print("[ocrapi] pydep FAIL:", m, e)
print("[ocrapi] GOOGLE_APPLICATION_CREDENTIALS=", os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
print("[ocrapi] INLINE_KEY_SET=", bool(os.environ.get("GOOGLE_CLOUD_VISION_KEY")))
PY

export FLASK_APP="${FLASK_APP:-app:app}"
export FLASK_ENV="${FLASK_ENV:-development}"
export FLASK_RUN_HOST="${FLASK_RUN_HOST:-0.0.0.0}"
export FLASK_RUN_PORT="${FLASK_RUN_PORT:-5000}"

exec python -m flask run --host="$FLASK_RUN_HOST" --port="$FLASK_RUN_PORT"
