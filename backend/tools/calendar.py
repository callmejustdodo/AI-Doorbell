"""Google Calendar appointment checking tool."""

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from backend.tools.google_auth import get_credentials

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

_calendar_service = None


def _get_calendar_service():
    """Build an authorized Calendar API service (cached)."""
    global _calendar_service
    if _calendar_service:
        return _calendar_service

    from googleapiclient.discovery import build

    creds = get_credentials(SCOPES)
    if not creds:
        logger.warning("Calendar credentials not available")
        return None

    _calendar_service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    return _calendar_service


def _sync_check_calendar(visitor_name: str) -> dict:
    """Synchronous Calendar check — runs in thread pool to avoid blocking event loop."""
    service = _get_calendar_service()
    if not service:
        return {"found": False, "message": "Calendar not configured"}

    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0)

    events_result = service.events().list(
        calendarId="primary",
        timeMin=start_of_day.isoformat(),
        timeMax=end_of_day.isoformat(),
        timeZone="Asia/Seoul",
        maxResults=10,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = events_result.get("items", [])

    if not events:
        return {"found": False, "message": "No events on calendar today"}

    name_lower = visitor_name.strip().lower() if visitor_name else ""

    for event in events:
        summary = event.get("summary", "")
        attendees = [a.get("displayName", a.get("email", ""))
                     for a in event.get("attendees", [])]
        start = event["start"].get("dateTime", event["start"].get("date", ""))

        searchable = f"{summary} {' '.join(attendees)}".lower()
        if name_lower and name_lower in searchable:
            return {
                "found": True,
                "event": summary,
                "start_time": start,
                "attendees": attendees,
                "message": f"Appointment found: {summary} at {start}",
            }

    all_events = [
        {"summary": e.get("summary", "Untitled"),
         "start": e["start"].get("dateTime", e["start"].get("date", ""))}
        for e in events
    ]
    if name_lower:
        return {
            "found": False,
            "today_events": all_events,
            "message": f"No appointments found for '{visitor_name}', but {len(all_events)} event(s) today",
        }
    return {
        "found": True,
        "today_events": all_events,
        "message": f"{len(all_events)} event(s) on calendar today",
    }


async def check_calendar(visitor_name: str = "") -> dict:
    """Check Google Calendar for today's appointments matching the visitor name."""
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None, _sync_check_calendar, visitor_name
        )
    except Exception as e:
        logger.error("Calendar API error: %s", e)
        global _calendar_service
        _calendar_service = None
        return {"found": False, "message": f"Calendar error: {e}"}
