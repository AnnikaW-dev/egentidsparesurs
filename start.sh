#!/usr/bin/env bash
# Render start: migrate, ensure admin + content, then Gunicorn.
# Do not let optional seed failures prevent the app from starting.
set -o errexit

echo "Preparing media directory..."
# Prefer MEDIA_ROOT from env; fall back to ./media if disk path is missing.
MEDIA_DIR="${MEDIA_ROOT:-media}"
mkdir -p "$MEDIA_DIR" || mkdir -p media

echo "Running database migrations..."
python manage.py migrate --no-input

echo "Ensuring superuser (from DJANGO_SUPERUSER_* env)..."
python manage.py ensure_superuser || true

# Seed when empty OR when SEED_ON_DEPLOY=true (idempotent update_or_create).
echo "Ensuring starter content if needed..."
python manage.py ensure_site_content || true

exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}"
