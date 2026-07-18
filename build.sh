#!/usr/bin/env bash
# Render build: install deps and collect static files.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
