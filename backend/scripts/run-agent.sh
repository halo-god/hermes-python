#!/usr/bin/env bash
set -euo pipefail

echo "→ Agent Runner waiting for PostgreSQL & Redis..."
python -m app.wait_for_services

echo "→ Starting Agent Runner (ACP gateway)..."
exec python -m agent_runner.runner
