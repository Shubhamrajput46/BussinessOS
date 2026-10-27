#!/bin/sh
set -e

# Wait for MySQL when a database host is configured
if [ -n "$DB_HOST" ]; then
    echo "Waiting for database at $DB_HOST:${DB_PORT:-3306} ..."
    i=0
    until nc -z "$DB_HOST" "${DB_PORT:-3306}"; do
        i=$((i+1))
        [ "$i" -gt 60 ] && echo "Database not reachable" && exit 1
        sleep 2
    done
fi

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    python manage.py migrate --noinput
fi

# Gunicorn worker count can be tuned from the environment
if [ "$1" = "gunicorn" ]; then
    exec "$@" --workers "${GUNICORN_WORKERS:-3}" --timeout 60
fi
exec "$@"
