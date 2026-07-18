#!/usr/bin/env bash
# Render start: migrate DB then run Gunicorn.
set -o errexit

echo "Running database migrations..."
python manage.py migrate --no-input

# Bind to Render's PORT (default 8000 locally).
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}"
