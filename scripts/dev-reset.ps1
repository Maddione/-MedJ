$compose="docker/compose/docker-compose.dev.yml"
docker compose -f $compose down -v --remove-orphans
docker system prune -af --volumes
Get-ChildItem -Recurse -Include *.pyc -Force | Remove-Item -Force
Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
Remove-Item .\records\migrations\* -Exclude __init__.py -Force
Remove-Item .\db.sqlite3 -ErrorAction Ignore
Remove-Item .\backup.sqlite3 -ErrorAction Ignore
docker compose -f $compose build --no-cache
docker compose -f $compose up -d db
docker compose -f $compose run --rm --no-deps --entrypoint sh web -lc "python manage.py makemigrations"
docker compose -f $compose run --rm --no-deps --entrypoint sh web -lc "python manage.py migrate --database=default"
docker compose -f $compose run --rm --no-deps --entrypoint sh web -lc "python manage.py migrate --database=backup"
docker compose -f $compose run --rm --no-deps --entrypoint sh web -lc "python manage.py sync_taxonomy_tags"
docker compose -f $compose run --rm --no-deps --entrypoint sh web -lc "python manage.py seed_initial_data"
docker compose -f $compose run --rm --no-deps --entrypoint sh web -lc "python manage.py import_lab_indicators_csv /app/data/labtests-database.csv"
docker compose -f $compose run --rm --no-deps --entrypoint sh web -lc "python manage.py compilemessages -l bg -l en"
docker compose -f $compose run --rm --no-deps --entrypoint sh web -lc "tailwindcss -i /app/theme/static_src/styles.css -o /app/theme/static/css/dist/output.css"
docker compose -f $compose run --rm --no-deps -e DJANGO_SUPERUSER_USERNAME=admin -e DJANGO_SUPERUSER_EMAIL=admin@example.com -e DJANGO_SUPERUSER_PASSWORD=admin --entrypoint sh web -lc "python manage.py createsuperuser --noinput"
docker compose -f $compose up -d web
docker compose -f $compose logs -f web
