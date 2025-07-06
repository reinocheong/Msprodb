#!/bin/sh
set -e
export FLASK_APP=wsgi.py
flask db upgrade
exec gunicorn wsgi:app --bind 0.0.0.0:${PORT:-5000}
