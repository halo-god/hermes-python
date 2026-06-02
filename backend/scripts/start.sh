#!/usr/bin/env bash
set -euo pipefail

echo "→ Waiting for PostgreSQL & Redis..."
python -m app.wait_for_services

echo "→ Running database migrations..."
alembic upgrade head

echo "→ Seeding bootstrap data..."
python -m app.seed

echo "→ Starting API (uvicorn)..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
