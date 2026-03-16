#!/usr/bin/env bash
# Local development server only.
# Usage: ./scripts/run.sh
set -e
cd "$(dirname "$0")/.."

PORT=${PORT:-8080}

if [ -f .env ]; then
  set -a; source .env; set +a
fi

echo "Starting AI Doorbell on http://localhost:$PORT"
exec python -m uvicorn backend.main:app --host 0.0.0.0 --port "$PORT" --reload
