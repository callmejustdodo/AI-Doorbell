"""Tool registry: maps tool names to handler functions."""

from backend.tools.known_faces import check_known_faces
from backend.tools.gmail import check_gmail_orders
from backend.tools.calendar import check_calendar
from backend.tools.telegram import send_telegram_alert
from backend.tools.screenshot import capture_screenshot

TOOL_HANDLERS = {
    "check_gmail_orders": check_gmail_orders,
    "check_calendar": check_calendar,
    "check_known_faces": check_known_faces,
    "send_telegram_alert": send_telegram_alert,
    "capture_screenshot": capture_screenshot,
}
