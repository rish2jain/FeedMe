"""Google Calendar client for calendar-aware planning.

Fetches events for requested weekdays and returns ``{"day","end_hour"}`` records
for ``time_limits_from_client``.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from typing import Callable

_DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _day_label(dt: datetime) -> str:
    return _DAY_NAMES[dt.weekday()]


def _end_hour(dt: datetime) -> float:
    return dt.hour + dt.minute / 60.0


def _credentials_path() -> str | None:
    return os.environ.get("GOOGLE_CALENDAR_CREDENTIALS") or os.environ.get(
        "GOOGLE_CALENDAR_TOKEN"
    )


def _load_calendar_service():
    cred_path = _credentials_path()
    if not cred_path:
        raise RuntimeError("GOOGLE_CALENDAR_CREDENTIALS or GOOGLE_CALENDAR_TOKEN must be set")
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise RuntimeError(
            "Google API libs required; pip install pantry-local[integrations]"
        ) from exc

    scopes = ["https://www.googleapis.com/auth/calendar.readonly"]
    token_path = os.environ.get("GOOGLE_CALENDAR_TOKEN", cred_path + ".token.json")
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(cred_path, scopes)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as fh:
            fh.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)


def fetch_events_for_days(
    days: list[str],
    *,
    calendar_id: str | None = None,
    today: date | None = None,
    service: object | None = None,
) -> list[dict]:
    """Return latest-ending event per requested weekday label."""
    today = today or date.today()
    calendar_id = calendar_id or os.environ.get("GOOGLE_CALENDAR_ID", "primary")
    svc = service or _load_calendar_service()
    # Map day labels to dates in the current ISO week starting Monday.
    week_start = today - timedelta(days=today.weekday())
    day_to_date = {label: week_start + timedelta(days=i) for i, label in enumerate(_DAY_NAMES)}
    targets = {d: day_to_date[d] for d in days if d in day_to_date}

    latest: dict[str, float] = {}
    for label, d in targets.items():
        start = datetime.combine(d, datetime.min.time()).isoformat() + "Z"
        end = datetime.combine(d + timedelta(days=1), datetime.min.time()).isoformat() + "Z"
        resp = svc.events().list(
            calendarId=calendar_id,
            timeMin=start,
            timeMax=end,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        for ev in resp.get("items") or []:
            end_raw = ev.get("end", {}).get("dateTime")
            if not end_raw:
                continue
            end_dt = datetime.fromisoformat(end_raw.replace("Z", "+00:00"))
            latest[label] = max(latest.get(label, 0.0), _end_hour(end_dt))

    return [{"day": day, "end_hour": hour} for day, hour in sorted(latest.items())]


def make_calendar_client(
    calendar_id: str | None = None,
    service: object | None = None,
) -> Callable[[list[str]], list[dict]]:
    def _client(days: list[str]) -> list[dict]:
        return fetch_events_for_days(days, calendar_id=calendar_id, service=service)

    return _client
