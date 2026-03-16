# Deployment Guide

AI Doorbell uses **Terraform** for infrastructure provisioning and **shell scripts** for automated deployment to **Google Cloud Platform**.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Google Cloud Platform              │
│                                                      │
│  ┌──────────────┐   ┌───────────────────────────┐   │
│  │   Artifact    │   │       Cloud Run            │   │
│  │   Registry    │──▶│   ai-doorbell (WebSocket)  │   │
│  │   (Docker)    │   │   asia-northeast3 (Seoul)  │   │
│  └──────────────┘   └─────────┬─────────────────┘   │
│                               │                      │
│  ┌──────────────┐   ┌────────┴──────────────────┐   │
│  │   Secret      │   │      Cloud Storage         │   │
│  │   Manager     │   │   (screenshot bucket, 7d)  │   │
│  │   (5 secrets) │   └───────────────────────────┘   │
│  └──────────────┘                                    │
└─────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│  Gemini Live API │     │  Telegram Bot API │
│  (audio/video)   │     │  (alerts/commands)│
└─────────────────┘     └──────────────────┘
```

## Prerequisites

- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud`)
- [Terraform](https://developer.hashicorp.com/terraform/install) (>= 1.5)
- [Docker](https://docs.docker.com/get-docker/)
- A GCP project with billing enabled

## Configuration

All configuration lives in a single `.env` file at the project root:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `GCP_PROJECT_ID` | GCP project ID (default: `molthome`) |
| `GCP_REGION` | GCP region (default: `asia-northeast3`) |
| `GEMINI_API_KEY` | Google Gemini API key |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `TELEGRAM_CHAT_ID` | Telegram chat ID for alerts |
| `GOOGLE_CLIENT_ID` | Google OAuth2 client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth2 client secret |
| `GOOGLE_REFRESH_TOKEN` | Google OAuth2 refresh token |
| `OWNER_NAME` | Homeowner display name |
| `LANGUAGE` | Doorbell language (`en`, `ko`, etc.) |
| `DELIVERY_INSTRUCTIONS` | What to tell delivery drivers |

## Scripts

### 1. First-Time Setup — `./scripts/setup.sh`

Provisions all GCP infrastructure from scratch:

```bash
./scripts/setup.sh
```

What it does:
1. Sets active GCP project
2. Enables required APIs (Cloud Run, Artifact Registry, Secret Manager, Cloud Storage, IAM)
3. Creates a GCS bucket for Terraform remote state (versioned)
4. Generates `infra/terraform.tfvars` from `.env`
5. Runs `terraform init` + `terraform apply` to create:
   - **Artifact Registry** repository for Docker images
   - **Secret Manager** secrets (Gemini key, Telegram token, Google OAuth credentials)
   - **Cloud Run** service with session affinity and WebSocket support
   - **Cloud Storage** bucket for screenshots (auto-deleted after 7 days)
   - **IAM** service account with least-privilege access

### 2. Deploy — `./scripts/deploy.sh`

Builds and deploys the application:

```bash
./scripts/deploy.sh
```

What it does:
1. Authenticates Docker with Artifact Registry
2. Builds Docker image (`linux/amd64`)
3. Pushes to Artifact Registry
4. Updates Cloud Run service with new image
5. Sets Telegram webhook to the Cloud Run URL

### 3. Teardown — `./scripts/destroy.sh`

Removes all GCP resources:

```bash
./scripts/destroy.sh
```

What it does:
1. Removes Telegram webhook
2. Runs `terraform destroy` to delete all provisioned resources

### 4. Local Development — `./scripts/run.sh`

Runs the server locally with hot-reload:

```bash
./scripts/run.sh
```

## Infrastructure as Code

All infrastructure is defined in `infra/` using Terraform:

| File | Resources |
|---|---|
| `main.tf` | Provider config, GCP API enablement, remote state backend |
| `cloud_run.tf` | Cloud Run service, public access IAM |
| `artifact_registry.tf` | Docker image repository |
| `secrets.tf` | 5 Secret Manager secrets (Gemini, Telegram, Google OAuth) |
| `cloud_storage.tf` | Screenshot bucket with 7-day lifecycle |
| `iam.tf` | Service account with Storage + Secret Manager access |
| `variables.tf` | All configurable inputs |
| `outputs.tf` | Service URL, bucket name, webhook URL |

## Quick Start

```bash
# 1. Configure
cp .env.example .env
# Edit .env with your credentials

# 2. Provision infrastructure (one-time)
./scripts/setup.sh

# 3. Build and deploy
./scripts/deploy.sh

# 4. Open the printed URL on your phone to test
```

## Redeployment

After code changes, redeploy with a single command:

```bash
./scripts/deploy.sh
```

This rebuilds the Docker image, pushes it, and updates Cloud Run — zero downtime.
