#!/usr/bin/env bash
# Render start: migrate, ensure admin user, optional seed, then Gunicorn.
set -o errexit

echo "Running database migrations..."
python manage.py migrate --no-input

# Creates admin from env when Shell is unavailable (Render free plan).
python manage.py ensure_superuser

# Optional first-time content — set SEED_ON_DEPLOY=true once in Render env, then turn off.
if [ "${SEED_ON_DEPLOY:-}" = "true" ] || [ "${SEED_ON_DEPLOY:-}" = "1" ]; then
  echo "Seeding starter content (SEED_ON_DEPLOY)..."
  python manage.py seed_site
fi

exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}"
