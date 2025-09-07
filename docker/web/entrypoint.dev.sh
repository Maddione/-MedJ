#!/bin/sh
set -e
if [ "$1" = "bash" ] || [ "$1" = "sh" ]; then
  exec "$@"
fi
python manage.py runserver 0.0.0.0:8000
