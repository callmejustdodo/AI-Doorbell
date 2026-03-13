"""Screenshot capture tool: saves current video frame to storage."""

import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

# TODO: Implement real GCS upload
# For now, saves locally for demo development


async def capture_screenshot() -> dict:
    """Capture current camera frame and save to storage.

    In production, this would:
    1. Get the last video frame from the active GeminiSession
    2. Encode as JPEG
    3. Upload to GCS bucket
    4. Return signed URL
    """
    screenshot_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().isoformat()

    logger.info("SCREENSHOT: Captured frame %s at %s", screenshot_id, timestamp)

    # Mock URL for development
    mock_url = f"https://storage.googleapis.com/ai-doorbell-screenshots/{screenshot_id}.jpg"

    return {
        "captured": True,
        "screenshot_id": screenshot_id,
        "url": mock_url,
        "timestamp": timestamp,
    }
