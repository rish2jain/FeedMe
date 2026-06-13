"""Gmail receipt fetch for Instacart/ShopRite confirmation emails.

OAuth credentials are stored outside the repo. When unavailable, fetchers are not
wired and receipt ingestion falls back to manual text/image paths.
"""

from __future__ import annotations

import base64
import os
import re
from typing import Callable

# Common senders for grocery confirmations in this household.
_DEFAULT_SENDERS = (
    "instacart.com",
    "shoprite.com",
    "orders@instacart",
    "noreply@shoprite",
)
_DEFAULT_QUERY = 'subject:(order OR receipt OR delivery) newer_than:14d'


def _credentials_path() -> str | None:
    return os.environ.get("GMAIL_CREDENTIALS") or os.environ.get("GMAIL_TOKEN")


def _load_gmail_service():
    cred_path = _credentials_path()
    if not cred_path:
        raise RuntimeError("GMAIL_CREDENTIALS or GMAIL_TOKEN must be set")
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise RuntimeError(
            "Google API libs required; pip install pantry-local[integrations]"
        ) from exc

    scopes = ["https://www.googleapis.com/auth/gmail.readonly"]
    token_path = os.environ.get("GMAIL_TOKEN", cred_path + ".token.json")
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
    return build("gmail", "v1", credentials=creds)


def _decode_body(payload: dict) -> str:
    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    parts = payload.get("parts") or []
    for part in parts:
        mime = part.get("mimeType", "")
        if mime == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
    for part in parts:
        text = _decode_body(part)
        if text:
            return text
    return ""


def _sender_matches(from_header: str, senders: tuple[str, ...]) -> bool:
    lowered = from_header.lower()
    return any(s in lowered for s in senders)


def fetch_receipt_emails(
    since_query: str | None = None,
    senders: tuple[str, ...] | None = None,
    max_results: int = 10,
    service: object | None = None,
) -> list[dict]:
    """Return receipt email bodies ready for ``ingest_receipt(text=...)``.

    Each dict: ``{"id", "subject", "from", "date", "body"}``.
    """
    senders = senders or _DEFAULT_SENDERS
    query = since_query or os.environ.get("GMAIL_RECEIPT_QUERY", _DEFAULT_QUERY)
    svc = service or _load_gmail_service()
    resp = svc.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    messages = resp.get("messages") or []
    out: list[dict] = []
    for meta in messages:
        msg = svc.users().messages().get(userId="me", id=meta["id"], format="full").execute()
        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
        from_hdr = headers.get("from", "")
        if not _sender_matches(from_hdr, senders):
            continue
        body = _decode_body(msg.get("payload", {}))
        body = re.sub(r"\r\n", "\n", body).strip()
        if not body:
            continue
        out.append({
            "id": meta["id"],
            "subject": headers.get("subject", ""),
            "from": from_hdr,
            "date": headers.get("date", ""),
            "body": body,
        })
    return out


def make_gmail_fetcher(
    senders: tuple[str, ...] | None = None,
    service: object | None = None,
) -> Callable[[str | None], list[dict]]:
    """Return ``fetch(since_query) -> list[email dict]`` for wiring."""

    def _fetch(since_query: str | None = None) -> list[dict]:
        return fetch_receipt_emails(since_query=since_query, senders=senders, service=service)

    return _fetch
