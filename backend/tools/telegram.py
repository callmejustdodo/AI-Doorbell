"""Telegram Bot: send alerts with inline formatting, photos, and inline buttons."""

import logging

logger = logging.getLogger(__name__)

# TODO: Implement real Telegram Bot API integration
# For now, logs alerts for demo development


URGENCY_EMOJI = {
    "low": "\U0001f4e6",      # 📦
    "medium": "\U0001f464",    # 👤
    "high": "\u26a0\ufe0f",   # ⚠️
}

URGENCY_PREFIX = {
    "low": "Delivery arrived",
    "medium": "Visitor",
    "high": "CAUTION",
}


async def send_telegram_alert(
    urgency: str = "low",
    visitor_type: str = "unknown",
    summary: str = "",
    capture_photo: bool = False,
) -> dict:
    """Send formatted alert to homeowner via Telegram.

    Formatting is done inline — no NotifierAgent needed.
    For known_person visitors, includes inline keyboard buttons.
    """
    emoji = URGENCY_EMOJI.get(urgency, "")
    prefix = URGENCY_PREFIX.get(urgency, "Alert")
    message = f"{emoji} {prefix} -- {summary}"

    # Log for development (replace with real Telegram API call)
    logger.info("TELEGRAM ALERT [%s]: %s", urgency, message)

    result = {
        "sent": True,
        "message": message,
        "urgency": urgency,
        "visitor_type": visitor_type,
        "photo_attached": capture_photo,
    }

    if visitor_type == "known_person":
        result["inline_buttons"] = [
            "Tell them to come in",
            "Tell them to wait",
            "Decline",
        ]
        logger.info("TELEGRAM: Inline buttons added for known person")

    if capture_photo:
        logger.info("TELEGRAM: Photo capture requested")

    return result
