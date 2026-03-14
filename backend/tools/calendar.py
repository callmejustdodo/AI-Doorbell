"""Google Calendar appointment checking tool."""

import logging
from datetime import datetime, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

TOKEN_FILE = Path(__file__).parent.parent.parent / "token.json"
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def _get_calendar_service():
    """Build an authorized Calendar API service."""
    from googleapiclient.discovery import build

    if not TOKEN_FILE.exists():
        logger.warning("token.json not found — Calendar integration disabled")
        return None

    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_FILE.write_text(creds.to_json())

    return build("calendar", "v3", credentials=creds)


async def check_calendar(visitor_name: str = "") -> dict:
    """Check Google Calendar for today's appointments matching the visitor name."""
    try:
        service = _get_calendar_service()
        if not service:
            return {"found": False, "message": "Calendar not configured"}

        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0)

        events_result = service.events().list(
            calendarId="primary",
            timeMin=start_of_day.isoformat(),
            timeMax=end_of_day.isoformat(),
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

            # Match visitor name against event summary or attendees
            searchable = f"{summary} {' '.join(attendees)}".lower()
            if name_lower and name_lower in searchable:
                return {
                    "found": True,
                    "event": summary,
                    "start_time": start,
                    "attendees": attendees,
                    "message": f"Appointment found: {summary} at {start}",
                }

        # No name match — return all events for context
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

    except Exception as e:
        logger.error("Calendar API error: %s", e)
        return {"found": False, "message": f"Calendar error: {e}"}
