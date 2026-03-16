#!/usr/bin/env bash
# Build, push, and deploy AI Doorbell to GCP Cloud Run.
# Assumes infrastructure already provisioned via ./scripts/setup.sh
# Usage: ./scripts/deploy.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load .env
if [ -f "$PROJECT_ROOT/.env" ]; then
  set -a; source "$PROJECT_ROOT/.env"; set +a
fi

PROJECT_ID="${GCP_PROJECT_ID:-molthome}"
REGION="${GCP_REGION:-asia-northeast3}"
SERVICE_NAME="ai-doorbell"
REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/ai-doorbell"
IMAGE="${REGISTRY}/backend:latest"

echo "==> Deploying $SERVICE_NAME ($PROJECT_ID / $REGION)"

# 1. Docker auth
echo "==> Configuring Docker for Artifact Registry..."
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# 2. Build & push
echo "==> Building Docker image..."
cd "$PROJECT_ROOT"
docker build --platform linux/amd64 -t "$IMAGE" .

echo "==> Pushing to Artifact Registry..."
docker push "$IMAGE"

# 3. Deploy new image to Cloud Run
echo "==> Updating Cloud Run service..."
gcloud run services update "$SERVICE_NAME" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --image="$IMAGE" \
  --quiet

# 4. Get service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --format="value(status.url)")

# 5. Set Telegram webhook
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
  echo "==> Setting Telegram webhook..."
  curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
    -H "Content-Type: application/json" \
    -d "{\"url\": \"${SERVICE_URL}/api/telegram/webhook\", \"allowed_updates\": [\"callback_query\", \"message\"]}" | python3 -m json.tool
fi

echo ""
echo "========================================="
echo "  Deployed!"
echo "  URL: $SERVICE_URL"
echo "========================================="
