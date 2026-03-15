#!/bin/sh
set -e

# Try alembic upgrade. If it fails (e.g. tables already exist but
# alembic_version_admin is missing), stamp head and retry.
if ! alembic upgrade head 2>/dev/null; then
  echo "Alembic upgrade failed — stamping head for first-time setup"
  alembic stamp head
  alembic upgrade head
fi

exec uvicorn main:app --host 0.0.0.0 --port 8000
