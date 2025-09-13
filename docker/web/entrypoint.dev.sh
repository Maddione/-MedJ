#!/usr/bin/env sh
set -eu

cd /app

ensure_tailwind() {
  if command -v tailwindcss >/dev/null 2>&1; then
    return 0
  fi
  case "$(uname -s)-$(uname -m)" in
    Linux-x86_64)  BIN="tailwindcss-linux-x64" ;;
    Linux-aarch64) BIN="tailwindcss-linux-arm64" ;;
    Linux-arm64)   BIN="tailwindcss-linux-arm64" ;;
    *)             BIN="tailwindcss-linux-x64" ;;
  esac
  curl -fsSL "https://github.com/tailwindlabs/tailwindcss/releases/download/v4.0.0/${BIN}" -o /usr/local/bin/tailwindcss
  chmod +x /usr/local/bin/tailwindcss
}

mkdir -p /app/secrets
if [ -n "${DJANGO_SECRET_KEY_FILE:-}" ] && [ ! -f "$DJANGO_SECRET_KEY_FILE" ]; then
  python - <<'PY'
import os, secrets
p=os.environ.get("DJANGO_SECRET_KEY_FILE","/app/secrets/django-key.txt")
os.makedirs(os.path.dirname(p), exist_ok=True)
open(p,"w").write(secrets.token_urlsafe(64))
PY
fi
if [ -n "${OPENAI_API_KEY:-}" ] && [ -n "${OPENAI_API_KEY_FILE:-}" ] && [ ! -f "$OPENAI_API_KEY_FILE" ]; then
  mkdir -p "$(dirname "$OPENAI_API_KEY_FILE")"
  printf "%s" "$OPENAI_API_KEY" > "$OPENAI_API_KEY_FILE"
fi

if [ -f theme/static/css/styles.css ]; then
  ensure_tailwind
  mkdir -p theme/static/css/dist static/css
  tailwindcss -i theme/static/css/styles.css -o theme/static/css/dist/output.css --minify || true
  cp -f theme/static/css/dist/output.css static/css/tailwind.css || true
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput || true
python manage.py compilemessages || true

if [ -n "${RUN_INITIAL_SEED:-}" ]; then
  python manage.py sync_taxonomy_tags || true
  python manage.py seed_initial_data || true
  python manage.py import_lab_indicators_csv /app/data/labtests-database.csv || true
  python manage.py optimize_indexes || true
  python manage.py backfill_event_tags || true
fi

if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_EMAIL:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
  python manage.py createsuperuser --noinput || true
fi

if [ "${TAILWIND_WATCH:-1}" = "1" ] && [ -f theme/static/css/styles.css ]; then
  ensure_tailwind
  tailwindcss -i theme/static/css/styles.css -o theme/static/css/dist/output.css --watch --poll &
fi

exec python manage.py runserver 0.0.0.0:8000
