"""Tests for integration wiring."""

from __future__ import annotations

import os
from unittest.mock import patch

from pantry_local.integrations.wiring import build_clients_from_env, chroma_backend_requested


def test_build_clients_empty_without_env():
    with patch.dict(os.environ, {}, clear=True):
        clients = build_clients_from_env()
    assert clients.embed is None
    assert clients.receipt_vlm is None
    assert clients.gmail_fetch is None


def test_build_clients_ollama_embed():
    env = {"OLLAMA_EMBED_MODEL": "nomic-embed-text"}
    with patch.dict(os.environ, env, clear=True):
        clients = build_clients_from_env()
    assert clients.embed is not None
    assert clients.receipt_vlm is None


def test_chroma_backend_auto_with_embed():
    env = {"OLLAMA_EMBED_MODEL": "nomic-embed-text"}
    with patch.dict(os.environ, env, clear=True):
        clients = build_clients_from_env()
        assert chroma_backend_requested(clients) is True


def test_chroma_backend_keyword_override():
    env = {"OLLAMA_EMBED_MODEL": "nomic-embed-text", "PANTRY_BACKEND": "keyword"}
    with patch.dict(os.environ, env, clear=True):
        clients = build_clients_from_env()
        assert chroma_backend_requested(clients) is False
