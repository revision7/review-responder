"""Google Business Profile reviews: live API (optional) or a local mock file.

Live mode needs the `google` extra (`pip install -e ".[google]"`), approved access to
the Business Profile APIs, and these environment variables:

    GOOGLE_CLIENT_SECRETS  path to an OAuth "Desktop app" client JSON
    GOOGLE_ACCOUNT_ID      numeric account id
    GOOGLE_LOCATION_ID     numeric location id

Run `review-responder google-auth` once to sign in; the token is cached in
GOOGLE_TOKEN_FILE (default .google_token.json). Without these, mock mode reads
samples/google_reviews.json and pretends to post replies.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .models import Review
from .sources import parse_rating

SCOPES = ["https://www.googleapis.com/auth/business.manage"]
API_BASE = "https://mybusiness.googleapis.com/v4"


class GoogleError(RuntimeError):
    pass


def _mock_file() -> Path:
    return Path(os.environ.get("GOOGLE_MOCK_FILE", "samples/google_reviews.json"))


def _token_file() -> Path:
    return Path(os.environ.get("GOOGLE_TOKEN_FILE", ".google_token.json"))


def is_live() -> bool:
    required = ("GOOGLE_CLIENT_SECRETS", "GOOGLE_ACCOUNT_ID", "GOOGLE_LOCATION_ID")
    return all(os.environ.get(k) for k in required) and _token_file().exists()


def _location_path() -> str:
    return f"accounts/{os.environ['GOOGLE_ACCOUNT_ID']}/locations/{os.environ['GOOGLE_LOCATION_ID']}"


def to_review(item: dict) -> Review:
    return Review(
        id=item.get("reviewId", ""),
        author=(item.get("reviewer") or {}).get("displayName", ""),
        rating=parse_rating(item.get("starRating")),
        text=item.get("comment", ""),
        date=(item.get("createTime") or "")[:10],
        source="google",
    )


def _session():
    try:
        from google.auth.transport.requests import AuthorizedSession, Request
        from google.oauth2.credentials import Credentials
    except ImportError as e:
        raise GoogleError('Install the Google extra: pip install -e ".[google]"') from e

    creds = Credentials.from_authorized_user_file(str(_token_file()), SCOPES)
    if not creds.valid and creds.refresh_token:
        creds.refresh(Request())
        _token_file().write_text(creds.to_json(), encoding="utf-8")
    return AuthorizedSession(creds)


def authorize() -> None:
    """Interactive one-time OAuth sign-in (opens a browser)."""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as e:
        raise GoogleError('Install the Google extra: pip install -e ".[google]"') from e
    secrets = os.environ.get("GOOGLE_CLIENT_SECRETS")
    if not secrets:
        raise GoogleError("Set GOOGLE_CLIENT_SECRETS to your OAuth client JSON path.")
    creds = InstalledAppFlow.from_client_secrets_file(secrets, SCOPES).run_local_server(port=0)
    _token_file().write_text(creds.to_json(), encoding="utf-8")


def fetch_reviews(limit: int = 50) -> tuple[list[Review], str]:
    """Return (reviews, mode) where mode is 'live' or 'mock'. Skips already-answered reviews."""
    if not is_live():
        mock_file = _mock_file()
        if not mock_file.exists():
            raise GoogleError(f"Mock file not found: {mock_file}")
        items = json.loads(mock_file.read_text(encoding="utf-8")).get("reviews", [])
        return [to_review(i) for i in items if not i.get("reviewReply")][:limit], "mock"

    session = _session()
    reviews: list[Review] = []
    page_token = None
    while len(reviews) < limit:
        params = {"pageSize": 50, "orderBy": "updateTime desc"}
        if page_token:
            params["pageToken"] = page_token
        resp = session.get(f"{API_BASE}/{_location_path()}/reviews", params=params, timeout=30)
        if resp.status_code != 200:
            raise GoogleError(f"Google API error {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        reviews += [to_review(i) for i in data.get("reviews", []) if not i.get("reviewReply")]
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return reviews[:limit], "live"


def post_reply(review_id: str, comment: str) -> str:
    """Publish a reply. Returns 'live' or 'mock'."""
    if not re.fullmatch(r"[\w-]+", review_id):
        raise GoogleError("Invalid review id.")
    if not comment.strip():
        raise GoogleError("Reply is empty.")
    if not is_live():
        return "mock"
    session = _session()
    resp = session.put(
        f"{API_BASE}/{_location_path()}/reviews/{review_id}/reply",
        json={"comment": comment},
        timeout=30,
    )
    if resp.status_code != 200:
        raise GoogleError(f"Google API error {resp.status_code}: {resp.text[:300]}")
    return "live"
