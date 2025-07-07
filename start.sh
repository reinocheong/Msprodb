#!/bin/sh
set -e

# Apply database migrations
flask db upgrade

# Start the Gunicorn server with production-ready settings
exec gunicorn wsgi:app \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --timeout 120 \
    --log-level=info \
    --access-logfile='-' \
    --error-logfile='-'
