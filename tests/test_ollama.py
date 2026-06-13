"""Tests for Ollama integration clients (mocked httpx)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from pantry_local.integrations.ollama import (
    ollama_embed,
    ollama_receipt_vlm,
    ollama_scan_vlm,
    make_embed_fn,
    _parse_json_array,
)


def test_parse_json_array_strips_markdown():
    raw = '```json\n[{"name": "milk", "qty": 1}]\n```'
    assert _parse_json_array(raw)[0]["name"] == "milk"


def test_ollama_embed_mocked():
    client = MagicMock()
    client.post.return_value = MagicMock(
        raise_for_status=MagicMock(),
        json=MagicMock(return_value={"embedding": [0.1, 0.2, 0.3]}),
    )
    out = ollama_embed(["hello"], host="http://test", model="m", client=client)
    assert out == [[0.1, 0.2, 0.3]]
    client.post.assert_called_once()


def test_ollama_receipt_vlm_mocked(tmp_path):
    img = tmp_path / "r.jpg"
    img.write_bytes(b"fake")
    items = [{"name": "Onions", "qty": 2, "unit": "lb"}]
    client = MagicMock()
    client.post.return_value = MagicMock(
        raise_for_status=MagicMock(),
        json=MagicMock(return_value={"message": {"content": json.dumps(items)}}),
    )
    out = ollama_receipt_vlm(str(img), host="http://test", model="vlm", client=client)
    assert out[0]["name"] == "Onions"


def test_ollama_scan_vlm_mocked(tmp_path):
    img = tmp_path / "f.jpg"
    img.write_bytes(b"fake")
    items = [{"name": "milk", "confidence": 0.9}]
    client = MagicMock()
    client.post.return_value = MagicMock(
        raise_for_status=MagicMock(),
        json=MagicMock(return_value={"message": {"content": json.dumps(items)}}),
    )
    out = ollama_scan_vlm([str(img)], host="http://test", model="vlm", client=client)
    assert out[0]["confidence"] == 0.9


def test_make_embed_fn():
    client = MagicMock()
    client.post.return_value = MagicMock(
        raise_for_status=MagicMock(),
        json=MagicMock(return_value={"embedding": [1.0]}),
    )
    fn = make_embed_fn(host="http://test", model="m", client=client)
    assert fn(["x"]) == [[1.0]]
