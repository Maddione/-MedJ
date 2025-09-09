#!/usr/bin/env bash
set -euo pipefail
if [ -d "/app/ocrapi" ]; then cd /app/ocrapi; else cd /app; fi
export FLASK_DEBUG=${FLASK_DEBUG:-0}
detect=$(python - <<'PY'
import importlib, sys
candidates=["ocrapi.app","app"]
names=["app","flask_app","application"]
for modname in candidates:
    try:
        m=importlib.import_module(modname)
    except Exception:
        continue
    if hasattr(m,"create_app"):
        print(f"{modname}:create_app()"); sys.exit(0)
    for n in names:
        if hasattr(m,n):
            print(f"{modname}:{n}"); sys.exit(0)
print("")
PY
)
if [ -z "$detect" ]; then
  echo "Unable to detect Flask app module" >&2
  exit 1
fi
export FLASK_APP="$detect"
echo "FLASK_APP=${FLASK_APP}"
echo "GOOGLE_APPLICATION_CREDENTIALS=${GOOGLE_APPLICATION_CREDENTIALS:-unset}"
echo "PORT=${PORT:-5000}"
exec python -m flask run --host=0.0.0.0 --port="${PORT:-5000}"
