"""Gmail order matching tool — searches for recent order/delivery emails."""

import asyncio
import logging

from backend.tools.google_auth import get_credentials

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

_gmail_service = None


def _get_gmail_service():
    """Build an authorized Gmail API service (cached)."""
    global _gmail_service
    if _gmail_service:
        return _gmail_service

    from googleapiclient.discovery import build

    creds = get_credentials(SCOPES)
    if not creds:
        logger.warning("Gmail credentials not available")
        return None

    _gmail_service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    return _gmail_service


def _sync_check_gmail(keywords: str) -> dict:
    """Synchronous Gmail check — runs in thread pool to avoid blocking event loop."""
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


async def check_gmail_orders(keywords: str = "") -> dict:
    """Check Gmail for recent online orders matching the given keywords."""
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None, _sync_check_gmail, keywords
        )
    except Exception as e:
        logger.error("Gmail API error: %s", e)
        global _gmail_service
        _gmail_service = None
        return {"found": False, "orders": [], "message": f"Gmail error: {e}"}
