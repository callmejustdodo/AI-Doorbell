#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

PROJECT_ID="molthome"
REGION="us-central1"
SERVICE_NAME="ai-doorbell"

# Load .env for secrets
if [ -f "$PROJECT_ROOT/.env" ]; then
  set -a
  source "$PROJECT_ROOT/.env"
  set +a
fi

echo "==> Deploying $SERVICE_NAME to Cloud Run ($PROJECT_ID / $REGION)..."

# Ensure required secrets exist in Secret Manager
echo "==> Updating secrets..."
for SECRET in gemini-api-key telegram-bot-token google-oauth-token; do
  if ! gcloud secrets describe "$SECRET" --project="$PROJECT_ID" --quiet 2>/dev/null; then
    gcloud secrets create "$SECRET" --project="$PROJECT_ID" --replication-policy=automatic --quiet
  fi
done

# Update secret values from .env
echo "$GEMINI_API_KEY" | gcloud secrets versions add gemini-api-key --project="$PROJECT_ID" --data-file=- --quiet 2>/dev/null || true
echo "$TELEGRAM_BOT_TOKEN" | gcloud secrets versions add telegram-bot-token --project="$PROJECT_ID" --data-file=- --quiet 2>/dev/null || true

# Update OAuth token if local file exists
if [ -f "$PROJECT_ROOT/token.json" ]; then
  gcloud secrets versions add google-oauth-token --project="$PROJECT_ID" --data-file="$PROJECT_ROOT/token.json" --quiet 2>/dev/null || true
fi

# Get service account email
SA_EMAIL="$(gcloud iam service-accounts list --project="$PROJECT_ID" --filter="displayName:ai-doorbell" --format="value(email)" 2>/dev/null || true)"
if [ -z "$SA_EMAIL" ]; then
  SA_EMAIL="489300437587-compute@developer.gserviceaccount.com"
fi

# Grant secret access to service account
for SECRET in gemini-api-key telegram-bot-token google-oauth-token; do
  gcloud secrets add-iam-policy-binding "$SECRET" \
    --project="$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/secretmanager.secretAccessor" \
    --quiet 2>/dev/null || true
done

echo "==> Building and deploying from source..."
cd "$PROJECT_ROOT"

gcloud run deploy "$SERVICE_NAME" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --source=. \
  --allow-unauthenticated \
  --port=8080 \
  --timeout=300 \
  --session-affinity \
  --max-instances=2 \
  --set-env-vars="TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID:-},OWNER_NAME=${OWNER_NAME:-Kyuhee},LANGUAGE=${LANGUAGE:-en},DELIVERY_INSTRUCTIONS=${DELIVERY_INSTRUCTIONS:-Please leave it at the door},GCP_PROJECT=$PROJECT_ID" \
  --set-secrets="GEMINI_API_KEY=gemini-api-key:latest,TELEGRAM_BOT_TOKEN=telegram-bot-token:latest" \
  --quiet

SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --project="$PROJECT_ID" --region="$REGION" --format="value(status.url)")

# Set Telegram webhook
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
  echo "==> Setting Telegram webhook..."
  curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
    -H "Content-Type: application/json" \
    -d "{\"url\": \"${SERVICE_URL}/api/telegram/webhook\", \"allowed_updates\": [\"callback_query\", \"message\"]}" | python3 -m json.tool
fi

echo ""
echo "==> Deployment complete!"
echo "    Service URL: $SERVICE_URL"
echo "    Open on your phone to test."
