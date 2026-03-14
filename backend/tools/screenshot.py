"""Screenshot capture tool: captures current video frame and sends to Telegram."""

import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

# Module-level frame store — updated by the WebSocket handler
_last_frame: bytes | None = None


def set_last_frame(frame: bytes):
    """Called from the WebSocket handler to store the latest video frame."""
    global _last_frame
    _last_frame = frame


def get_last_frame() -> bytes | None:
    """Get the most recent video frame."""
    return _last_frame


async def capture_screenshot() -> dict:
    """Capture current camera frame. Returns frame bytes info for Telegram sending."""
    screenshot_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().isoformat()

    frame = _last_frame
    if frame:
        logger.info("SCREENSHOT: Captured frame %s (%d bytes) at %s",
                     screenshot_id, len(frame), timestamp)
        return {
            "captured": True,
            "screenshot_id": screenshot_id,
            "timestamp": timestamp,
            "has_frame": True,
        }

    logger.warning("SCREENSHOT: No video frame available")
    return {
        "captured": False,
        "screenshot_id": screenshot_id,
        "timestamp": timestamp,
        "has_frame": False,
    }
