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

if [ -f theme/static/css/styles.css ]; then
  mkdir -p static/css
  ensure_tailwind
  tailwindcss -i theme/static/css/styles.css -o static/css/tailwind.css --minify || true
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
  tailwindcss -i theme/static/css/styles.css -o static/css/tailwind.css --watch --poll &
fi

exec python manage.py runserver 0.0.0.0:8000
