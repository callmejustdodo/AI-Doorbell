"""Gmail order matching tool — searches for recent order/delivery emails."""

import base64
import logging
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

TOKEN_FILE = Path(__file__).parent.parent.parent / "token.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def _get_gmail_service():
    """Build an authorized Gmail API service."""
    from googleapiclient.discovery import build

    if not TOKEN_FILE.exists():
        logger.warning("token.json not found — Gmail integration disabled")
        return None

    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_FILE.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


async def check_gmail_orders(keywords: str = "") -> dict:
    """Check Gmail for recent online orders matching the given keywords."""
    try:
        service = _get_gmail_service()
        if not service:
            return {"found": False, "orders": [], "message": "Gmail not configured"}

        query = "subject:(order OR shipping OR delivery OR confirmation) newer_than:7d"
        if keywords:
            query += f" {keywords}"

        results = service.users().messages().list(
            userId="me", q=query, maxResults=5
        ).execute()

        messages = results.get("messages", [])
        if not messages:
            return {
                "found": False,
                "orders": [],
                "message": "No matching orders found in Gmail",
            }

        orders = []
        for msg_ref in messages[:5]:
            msg = service.users().messages().get(
                userId="me", id=msg_ref["id"], format="metadata",
                metadataHeaders=["Subject", "From", "Date"],
            ).execute()

            headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
            orders.append({
                "subject": headers.get("Subject", ""),
                "from": headers.get("From", ""),
                "date": headers.get("Date", ""),
            })

        return {
            "found": True,
            "orders": orders,
            "message": f"Found {len(orders)} recent order email(s)",
        }

    except Exception as e:
        logger.error("Gmail API error: %s", e)
        return {"found": False, "orders": [], "message": f"Gmail error: {e}"}
