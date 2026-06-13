"""Tests for Instacart MCP client wrapper."""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

from pantry_local.integrations.instacart_client import instacart_mcp_create_list


def test_instacart_mcp_create_list():
    payload = {"title": "test", "line_items": []}
    proc = MagicMock(returncode=0, stdout=json.dumps({"url": "https://instacart.test/list/1"}))
    with patch("pantry_local.integrations.instacart_client.subprocess.run", return_value=proc):
        url = instacart_mcp_create_list(payload, command="fake-mcp")
    assert url == "https://instacart.test/list/1"
