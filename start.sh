#!/bin/sh
set -e
echo "--- Running start.sh ---"

export FLASK_APP=wsgi.py

echo "Step 1: Running database migrations..."
flask db upgrade

echo "Step 2: Starting Gunicorn server..."
gunicorn --bind 0.0.0.0:${PORT:-5000} wsgi:app
