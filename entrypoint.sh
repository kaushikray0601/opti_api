#!/bin/bash
set -e

# Ensure runtime dirs exist and are writable (bind mounts & named volumes safe)
ensure_dir() {
  mkdir -p "$1"
  # chown can be expensive on huge trees; keep it focused to our two dirs.
  chown -R appuser:appgroup "$1" || true
  chmod -R u+rwX,g+rwX "$1" || true
}
ensure_dir /app/staticfiles
ensure_dir /app/mediafiles

# (optional) print who we are, helps debugging
id -u && id -g

# Now run collectstatic/migrate/etc as appuser safely
# Example:
# python manage.py collectstatic --noinput --clear
# python manage.py migrate --noinput
# If you launch gunicorn from docker-compose, just exec the command passed:



echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Applying database migrations..."
python manage.py migrate

echo "Starting server..."
exec "$@"