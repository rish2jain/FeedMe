"""Instacart MCP client wrapper for ``create-shopping-list``.

The real Instacart Developer Platform MCP server is invoked as a subprocess or
HTTP bridge configured via environment variables.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
from typing import Callable


def instacart_mcp_create_list(payload: dict, *, command: str | None = None,
                              timeout: float = 60.0) -> str:
    """Call Instacart MCP ``create-shopping-list`` and return the list URL."""
    cmd = command or os.environ.get("INSTACART_MCP_COMMAND")
    if not cmd:
        raise RuntimeError("INSTACART_MCP_COMMAND must be set for live Instacart staging")
    # Expect a wrapper script that reads JSON stdin and prints JSON with a "url" key.
    proc = subprocess.run(
        shlex.split(cmd),
        input=json.dumps({"tool": "create-shopping-list", "arguments": payload}),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Instacart MCP failed: {proc.stderr.strip() or proc.stdout}")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Instacart MCP returned non-JSON: {proc.stdout[:200]}") from exc
    url = data.get("url") or data.get("shopping_list_url")
    if not url:
        raise RuntimeError(f"Instacart MCP response missing url: {data}")
    return url


def make_instacart_mcp_client(command: str | None = None) -> Callable[[dict], str]:
    def _client(payload: dict) -> str:
        return instacart_mcp_create_list(payload, command=command)

    return _client
