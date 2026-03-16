"""Shared Google OAuth2 credential loader.

Priority: env vars (.env) > token.json > Secret Manager (Cloud Run).
"""

import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from backend.config import settings

logger = logging.getLogger(__name__)

TOKEN_URI = "https://oauth2.googleapis.com/token"


def get_credentials(scopes: list[str]) -> Credentials | None:
    """Get OAuth2 credentials from env vars, local file, or Secret Manager."""

    # 1. Try env vars (from .env or Cloud Run env)
    if settings.GOOGLE_REFRESH_TOKEN and settings.GOOGLE_CLIENT_ID:
        creds = Credentials(
            token=None,
            refresh_token=settings.GOOGLE_REFRESH_TOKEN,
            token_uri=TOKEN_URI,
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=scopes,
        )
        creds.refresh(Request())
        return creds

    # 2. Try local token.json
    try:
        from pathlib import Path
        token_file = Path(__file__).parent.parent.parent / "token.json"
        if token_file.exists():
            creds = Credentials.from_authorized_user_file(str(token_file), scopes)
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                token_file.write_text(creds.to_json())
            return creds
    except Exception as e:
        logger.warning("token.json load failed: %s", e)

    logger.warning("No Google credentials available")
    return None
