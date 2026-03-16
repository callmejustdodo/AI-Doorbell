#!/usr/bin/env bash
# Tear down all GCP resources: Cloud Run, secrets, buckets, registry.
# Usage: ./scripts/destroy.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load .env
if [ -f "$PROJECT_ROOT/.env" ]; then
  set -a; source "$PROJECT_ROOT/.env"; set +a
fi

PROJECT_ID="${GCP_PROJECT_ID:-molthome}"

echo "==> Destroying all Terraform-managed resources ($PROJECT_ID)..."

# Remove Telegram webhook
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
  echo "==> Removing Telegram webhook..."
  curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook?url=" | python3 -m json.tool
fi

# Terraform destroy
cd "$PROJECT_ROOT/infra"
terraform destroy -auto-approve

echo ""
echo "==> All resources destroyed."
