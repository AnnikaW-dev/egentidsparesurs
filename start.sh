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

# Seed missing pages; do not overwrite admin CMS on every restart.
echo "Ensuring starter content if needed..."
if ! python manage.py ensure_site_content; then
  echo "WARNING: ensure_site_content failed — pages may show 'Webbplatsen förbereds'."
  echo "Fix: open Render Shell and run: python manage.py seed_site"
fi

echo "Checking email configuration..."
python manage.py check_email_config || true

exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}"
