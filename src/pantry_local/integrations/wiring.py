"""Build integration clients from environment variables.

When credentials or Ollama config are absent, clients remain ``None`` so the
core library stays hermetic and testable without network access.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable


@dataclass
class IntegrationClients:
    embed: Callable[[list[str]], list[list[float]]] | None = None
    receipt_vlm: Callable[[str], list[dict]] | None = None
    scan_vlm: Callable[[list[str]], list[dict]] | None = None
    calendar: Callable[[list[str]], list[dict]] | None = None
    gmail_fetch: Callable[[str | None], list[dict]] | None = None
    instacart_mcp: Callable[[dict], str] | None = None

    @property
    def has_embed(self) -> bool:
        return self.embed is not None

    @property
    def has_vlm(self) -> bool:
        return self.receipt_vlm is not None and self.scan_vlm is not None


def _ollama_enabled() -> bool:
    return bool(os.environ.get("OLLAMA_EMBED_MODEL") or os.environ.get("OLLAMA_VLM_MODEL"))


def build_clients_from_env() -> IntegrationClients:
    clients = IntegrationClients()

    if os.environ.get("OLLAMA_EMBED_MODEL"):
        from .ollama import make_embed_fn
        clients.embed = make_embed_fn()

    if os.environ.get("OLLAMA_VLM_MODEL"):
        from .ollama import make_receipt_vlm_fn, make_scan_vlm_fn
        clients.receipt_vlm = make_receipt_vlm_fn()
        clients.scan_vlm = make_scan_vlm_fn()

    if os.environ.get("GOOGLE_CALENDAR_CREDENTIALS") or os.environ.get("GOOGLE_CALENDAR_TOKEN"):
        from .google_calendar import make_calendar_client
        clients.calendar = make_calendar_client()

    if os.environ.get("GMAIL_CREDENTIALS") or os.environ.get("GMAIL_TOKEN"):
        from .gmail import make_gmail_fetcher
        clients.gmail_fetch = make_gmail_fetcher()

    if os.environ.get("INSTACART_MCP_COMMAND"):
        from .instacart_client import make_instacart_mcp_client
        clients.instacart_mcp = make_instacart_mcp_client()

    return clients


def chroma_backend_requested(clients: IntegrationClients | None = None) -> bool:
    """True when Chroma should be used (explicit env or Ollama embedder present)."""
    backend = os.environ.get("PANTRY_BACKEND", "").lower()
    if backend == "chroma":
        return True
    if backend == "keyword":
        return False
    c = clients or build_clients_from_env()
    return c.has_embed or _ollama_enabled() and bool(os.environ.get("OLLAMA_EMBED_MODEL"))
