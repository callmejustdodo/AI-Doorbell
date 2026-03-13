"""Google Calendar appointment checking tool."""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# TODO: Implement real Google Calendar API integration with OAuth2
# For now, uses mock data for demo scenarios


async def check_calendar(visitor_name: str = "") -> dict:
    """Check Google Calendar for today's appointments matching the visitor name.

    In production, this would use Google Calendar API v3 with events.list for
    today's date range (timeMin/timeMax) and match visitor_name against event
    summary and attendee names.
    """
    if not visitor_name:
        return {"found": False, "message": "No visitor name provided"}

    name_lower = visitor_name.strip().lower()

    # Mock calendar events for demo
    today = datetime.now().strftime("%Y-%m-%d")
    mock_events = [
        {
            "summary": "Meeting with Minsu",
            "start": f"{today}T15:00:00",
            "end": f"{today}T16:00:00",
            "attendees": ["Minsu"],
        },
        {
            "summary": "Team standup",
            "start": f"{today}T10:00:00",
            "end": f"{today}T10:30:00",
            "attendees": ["David", "Sarah"],
        },
    ]

    for event in mock_events:
        # Check event summary and attendees for name match
        if name_lower in event["summary"].lower() or any(
            name_lower in a.lower() for a in event["attendees"]
        ):
            return {
                "found": True,
                "event": event["summary"],
                "start_time": event["start"],
                "end_time": event["end"],
                "message": f"Appointment found: {event['summary']} at {event['start']}",
            }

    return {
        "found": False,
        "message": f"No appointments found today for '{visitor_name}'",
    }
