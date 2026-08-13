#!/usr/bin/env bash

set -e

echo "Running Database Migrations..."
alembic upgrade head

echo "Running RBAC Seeding..."
python -m app.db.seed rbac

echo "Pre-start script completed successfully!"

# Execute the CMD (e.g. uvicorn app.main:app --host 0.0.0.0 --port 8000)
exec "$@"
