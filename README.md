# AI Doorbell

An AI doorbell agent that sees visitors through a phone camera, has real-time conversations via Gemini Live API, cross-checks Gmail and Google Calendar, and reports to the homeowner via Telegram.

## Architecture

```
Phone (Camera+Mic) ──WebSocket──▶ FastAPI Backend ──▶ Gemini Live API
                    ◀──Audio────  (Cloud Run)       ◀── Audio + Tool Calls
                                       │
                                       ├── Gmail API (order matching)
                                       ├── Google Calendar API (appointments)
                                       ├── Known Faces DB (JSON)
                                       ├── Telegram Bot API (alerts)
                                       └── Cloud Storage (screenshots)
```

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Vanilla HTML/JS, WebRTC MediaStream API, AudioWorkletNode |
| Backend | FastAPI (Python), WebSocket binary framing |
| AI Core | Gemini Live API (`gemini-2.5-flash-native-audio-preview-12-2025`) |
| AI SDK | `google-genai` |
| APIs | Gmail API, Google Calendar API, Telegram Bot API |
| Storage | Google Cloud Storage |
| Infra | Cloud Run, Terraform, Docker |

## Prerequisites

- Python 3.12+
- [Google Cloud project](https://console.cloud.google.com/) with billing enabled
- Gemini API key (from [AI Studio](https://aistudio.google.com/))
- Google OAuth credentials (`credentials.json`) with Gmail + Calendar scopes
- Telegram Bot token (from [@BotFather](https://t.me/BotFather))
- Docker (for cloud deployment)
- Terraform (for infrastructure provisioning)

## Reproducible Testing

### 1. Clone and install

```bash
git clone https://github.com/<your-org>/AI-Doorbell.git
cd AI-Doorbell
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### 2. Set up Google OAuth

Create OAuth credentials in the [Google Cloud Console](https://console.cloud.google.com/apis/credentials) with `gmail.readonly` and `calendar.readonly` scopes, download as `credentials.json` to the project root, then run:

```bash
python scripts/auth_google.py
```

This opens a browser for consent and saves `token.json`. From `token.json`, extract the refresh token.

### 3. Configure environment

Create a `.env` file in the project root:

```env
# Gemini
GEMINI_API_KEY=your-gemini-api-key

# Telegram
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id

# Google OAuth (from credentials.json + token.json)
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REFRESH_TOKEN=your-refresh-token

# Google Cloud Storage (optional for local testing)
GCS_BUCKET_NAME=your-bucket-name

# Owner config
OWNER_NAME=YourName
LANGUAGE=en
DELIVERY_INSTRUCTIONS=Please leave it at the door
```

### 4. Run locally

```bash
./scripts/run.sh
# or
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload
```

Open `http://localhost:8080` on your phone browser (same network). Grant camera and microphone permissions.

### 5. Test the three scenarios

**Scene 1 — Delivery verification:**
1. Ensure you have a recent order confirmation email in Gmail (e.g., Amazon)
2. Stand in front of the camera and say: *"Hi, I have a delivery for you"*
3. Verify: AI calls `check_gmail_orders`, matches the order, and says the product name
4. Verify: Telegram receives a low-urgency delivery alert with screenshot

**Scene 2 — Acquaintance with appointment:**
1. Add a calendar event for today with an attendee name (e.g., "Meeting with Minsu at 3pm")
2. Add the same name to `data/known_faces.json`
3. Say: *"Hi, is Kyuhee here? I'm Minsu"*
4. Verify: AI calls `check_calendar` + `check_known_faces`, confirms the appointment
5. Verify: Telegram receives alert with inline buttons (Let in / Wait / Decline)
6. Tap a button in Telegram and verify AI relays the command to the visitor

**Scene 3 — Suspicious visitor:**
1. Say: *"I have a delivery for you"* (with no matching order in Gmail)
2. When AI asks for details, give vague answers
3. Verify: AI calls `check_gmail_orders` (no match), asks follow-up questions
4. Verify: AI captures a screenshot and sends a high-urgency alert to Telegram

### 6. Deploy to Cloud Run

```bash
./scripts/deploy.sh
```

This builds the Docker image, pushes to Artifact Registry, updates secrets in Secret Manager, and deploys to Cloud Run. The Telegram webhook is automatically configured with the service URL.

### 7. Verify cloud deployment

```bash
# Check service is running
gcloud run services describe ai-doorbell --region=asia-northeast3 --format="value(status.url)"

# Check Telegram webhook is set
curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo" | python3 -m json.tool
```

Open the Cloud Run URL on your phone and repeat the test scenarios above.

## Project Structure

```
AI-Doorbell/
├── backend/
│   ├── main.py              # FastAPI app, WebSocket handler, REST endpoints
│   ├── gemini_session.py    # Gemini Live API session manager
│   ├── config.py            # Environment configuration (pydantic-settings)
│   ├── models.py            # Data models
│   ├── tools/
│   │   ├── __init__.py      # Tool registry
│   │   ├── gmail.py         # Gmail order search
│   │   ├── calendar.py      # Google Calendar query
│   │   ├── known_faces.py   # Known faces DB lookup
│   │   ├── telegram.py      # Telegram Bot alerts
│   │   └── screenshot.py    # Camera frame capture
│   ├── static/
│   │   └── index.html       # Frontend (camera + subtitles + controls)
│   └── requirements.txt
├── data/
│   └── known_faces.json     # Registered acquaintances
├── infra/                   # Terraform IaC
│   ├── cloud_run.tf
│   ├── secrets.tf
│   ├── variables.tf
│   └── ...
├── scripts/
│   ├── run.sh               # Local dev server
│   ├── deploy.sh            # Full GCP deployment
│   └── auth_google.py       # One-time OAuth consent flow
└── Dockerfile
```

## License

MIT
