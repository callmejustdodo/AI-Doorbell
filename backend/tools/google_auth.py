"""Shared Google OAuth2 credential loader.

Loads token.json locally, or from Secret Manager on Cloud Run.
"""

import json
import logging
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

TOKEN_FILE = Path(__file__).parent.parent.parent / "token.json"
SECRET_NAME = "google-oauth-token"
GCP_PROJECT = os.environ.get("GCP_PROJECT", "molthome")


def get_credentials(scopes: list[str]) -> Credentials | None:
    """Get OAuth2 credentials from local file or Secret Manager."""
    # Try local token.json first
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), scopes)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json())
        return creds

    # Try Secret Manager (Cloud Run)
    try:
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{GCP_PROJECT}/secrets/{SECRET_NAME}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        token_data = json.loads(response.payload.data.decode("utf-8"))

        creds = Credentials.from_authorized_user_info(token_data, scopes)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        return creds
    except Exception as e:
        logger.warning("Could not load credentials: %s", e)
        return None
