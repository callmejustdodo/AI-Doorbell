#!/usr/bin/env bash
# First-time GCP project setup: enables APIs, creates tfstate bucket, provisions infra.
# Usage: ./scripts/setup.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load .env
if [ -f "$PROJECT_ROOT/.env" ]; then
  set -a; source "$PROJECT_ROOT/.env"; set +a
fi

PROJECT_ID="${GCP_PROJECT_ID:-molthome}"
REGION="${GCP_REGION:-asia-northeast3}"

echo "==> Setting up GCP project: $PROJECT_ID ($REGION)"

# 1. Set active project
gcloud config set project "$PROJECT_ID"

# 2. Enable required APIs
echo "==> Enabling APIs..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com \
  iam.googleapis.com \
  cloudbuild.googleapis.com \
  --quiet

# 3. Create Terraform state bucket (if not exists)
TFSTATE_BUCKET="ai-doorbell-tfstate"
if ! gcloud storage buckets describe "gs://$TFSTATE_BUCKET" --project="$PROJECT_ID" &>/dev/null; then
  echo "==> Creating Terraform state bucket..."
  gcloud storage buckets create "gs://$TFSTATE_BUCKET" \
    --project="$PROJECT_ID" \
    --location="$REGION" \
    --uniform-bucket-level-access \
    --quiet
  gcloud storage buckets update "gs://$TFSTATE_BUCKET" \
    --versioning --quiet
else
  echo "==> Terraform state bucket already exists"
fi

# 4. Create terraform.tfvars from .env
TFVARS="$PROJECT_ROOT/infra/terraform.tfvars"
echo "==> Generating $TFVARS from .env..."
cat > "$TFVARS" <<EOF
project_id            = "$PROJECT_ID"
region                = "$REGION"
gemini_api_key        = "$GEMINI_API_KEY"
telegram_bot_token    = "$TELEGRAM_BOT_TOKEN"
telegram_chat_id      = "$TELEGRAM_CHAT_ID"
google_client_id      = "$GOOGLE_CLIENT_ID"
google_client_secret  = "$GOOGLE_CLIENT_SECRET"
google_refresh_token  = "$GOOGLE_REFRESH_TOKEN"
owner_name            = "${OWNER_NAME:-Kyuhee}"
language              = "${LANGUAGE:-en}"
delivery_instructions = "${DELIVERY_INSTRUCTIONS:-Please leave it at the door}"
EOF

# 5. Terraform init + apply
echo "==> Provisioning infrastructure with Terraform..."
cd "$PROJECT_ROOT/infra"
terraform init -input=false
terraform apply -auto-approve

# 6. Print outputs
echo ""
echo "========================================="
echo "  GCP infrastructure provisioned!"
echo ""
terraform output
echo ""
echo "  Next: ./scripts/deploy.sh"
echo "========================================="
