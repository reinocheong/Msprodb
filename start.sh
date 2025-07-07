#!/bin/sh
set -e

# Start the Gunicorn server with production-ready settings
# - Bind to the PORT environment variable provided by Render
# - Use a reasonable number of workers
# - Log access and errors to stdout to be captured by Render's log stream
exec gunicorn wsgi:app \
    --bind 0.0.0.0:$PORT \
    --workers 3 \
    --timeout 120 \
    --log-level=info \
    --access-logfile='-' \
    --error-logfile='-'
