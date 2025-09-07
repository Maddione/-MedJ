#!/bin/sh
set -eu

cd /app

if [ -f "theme/static_src/styles.css" ]; then
  mkdir -p theme/static/css/dist
  build_needed=1
  if [ -f "theme/static/css/dist/output.css" ] && [ "theme/static/css/dist/output.css" -nt "theme/static_src/styles.css" ]; then
    build_needed=0
  fi
  if [ "$build_needed" -eq 1 ]; then
    if command -v tailwindcss >/dev/null 2>&1; then
      tailwindcss -i /app/theme/static_src/styles.css -o /app/theme/static/css/dist/output.css
    elif command -v npx >/dev/null 2>&1; then
      npx tailwindcss -i /app/theme/static_src/styles.css -o /app/theme/static/css/dist/output.css
    fi
  fi
fi

if command -v msgfmt >/dev/null 2>&1; then
  python manage.py compilemessages -l bg -l en || true
fi

python manage.py collectstatic --noinput
python manage.py runserver 0.0.0.0:8000
