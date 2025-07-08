#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Run database migrations
echo "Running database migrations..."
flask db upgrade

# Start Gunicorn server with a longer timeout
echo "Starting Gunicorn server..."
gunicorn --workers 2 --timeout 120 --bind 0.0.0.0:$PORT wsgi:app

