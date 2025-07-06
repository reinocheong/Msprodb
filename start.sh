#!/bin/sh
set -e
# The FLASK_APP environment variable is set in Render's environment settings.
# The database is now managed by the local import script, so upgrade is not needed on startup.
exec gunicorn wsgi:app --bind 0.0.0.0:${PORT:-10000} --timeout 120
