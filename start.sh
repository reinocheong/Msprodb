#!/bin/sh
set -e
echo "--- Running start.sh ---"
echo "Step 1: Initializing database..."
python init_db.py
echo "Step 2: Starting Gunicorn server..."
gunicorn --bind 0.0.0.0:${PORT:-5000} wsgi:app
