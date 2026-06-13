"""Ollama clients for embeddings and Qwen-VL vision tasks.

All calls go to a local Ollama instance (Mac Studio). Hermetic tests mock httpx;
live Ollama is optional via ``@pytest.mark.integration``.
"""

from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path
from typing import Any, Callable

_DEFAULT_HOST = "http://127.0.0.1:11434"
_DEFAULT_EMBED_MODEL = "nomic-embed-text"
_DEFAULT_VLM_MODEL = "qwen2.5-vl:32b"

_RECEIPT_PROMPT = """Extract grocery line items from this receipt image.
Return ONLY a JSON array of objects with keys: name (string), qty (number or null),
unit (string or null). No markdown, no explanation."""

_SCAN_PROMPT = """You are inventorying a home refrigerator from photos (main shelf,
crisper, door). Return ONLY a JSON array of objects with keys:
name (string), qty (number or null), unit (string or null),
confidence (0.0-1.0 float). No markdown, no explanation."""


def ollama_host() -> str:
    return os.environ.get("OLLAMA_HOST", _DEFAULT_HOST).rstrip("/")


def ollama_embed_model() -> str:
    return os.environ.get("OLLAMA_EMBED_MODEL", _DEFAULT_EMBED_MODEL)


def ollama_vlm_model() -> str:
    return os.environ.get("OLLAMA_VLM_MODEL", _DEFAULT_VLM_MODEL)


def _get_httpx():
    try:
        import httpx
    except ImportError as exc:
        raise RuntimeError(
            "httpx is required for Ollama integrations; pip install pantry-local[integrations]"
        ) from exc
    return httpx


def _parse_json_array(text: str) -> list[dict]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError(f"expected JSON array, got {type(data).__name__}")
    return data


def ollama_embed(texts: list[str], *, host: str | None = None,
                 model: str | None = None, client: Any | None = None) -> list[list[float]]:
    """Embed texts via Ollama ``/api/embeddings``."""
    if not texts:
        return []
    host = host or ollama_host()
    model = model or ollama_embed_model()
    httpx = _get_httpx()
    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=120.0)
    try:
        out: list[list[float]] = []
        for text in texts:
            resp = client.post(
                f"{host}/api/embeddings",
                json={"model": model, "prompt": text},
            )
            resp.raise_for_status()
            embedding = resp.json().get("embedding")
            if not embedding:
                raise ValueError(f"no embedding in Ollama response for model {model}")
            out.append(embedding)
        return out
    finally:
        if own_client:
            client.close()


def _encode_image(path: str) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")


def _vlm_chat(image_paths: list[str], prompt: str, *, host: str | None = None,
              model: str | None = None, client: Any | None = None) -> str:
    host = host or ollama_host()
    model = model or ollama_vlm_model()
    httpx = _get_httpx()
    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=300.0)
    images_b64 = [_encode_image(p) for p in image_paths]
    try:
        resp = client.post(
            f"{host}/api/chat",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt, "images": images_b64}],
                "stream": False,
                "format": "json",
            },
        )
        resp.raise_for_status()
        content = resp.json().get("message", {}).get("content", "")
        if not content:
            raise ValueError("empty VLM response from Ollama")
        return content
    finally:
        if own_client:
            client.close()


def ollama_receipt_vlm(image_path: str, *, host: str | None = None,
                       model: str | None = None, client: Any | None = None) -> list[dict]:
    """Parse a receipt image to line items via Qwen-VL."""
    raw = _vlm_chat([image_path], _RECEIPT_PROMPT, host=host, model=model, client=client)
    return _parse_json_array(raw)


def ollama_scan_vlm(images: list[str], *, host: str | None = None,
                    model: str | None = None, client: Any | None = None) -> list[dict]:
    """Parse fridge photos to inventory items with confidence via Qwen-VL."""
    raw = _vlm_chat(images, _SCAN_PROMPT, host=host, model=model, client=client)
    return _parse_json_array(raw)


def make_embed_fn(host: str | None = None, model: str | None = None,
                  client: Any | None = None) -> Callable[[list[str]], list[list[float]]]:
    """Return an embed callable suitable for ``ChromaRecipeStore(embed=...)``."""

    def _embed(texts: list[str]) -> list[list[float]]:
        return ollama_embed(texts, host=host, model=model, client=client)

    return _embed


def make_receipt_vlm_fn(host: str | None = None, model: str | None = None,
                        client: Any | None = None) -> Callable[[str], list[dict]]:
    def _vlm(image_path: str) -> list[dict]:
        return ollama_receipt_vlm(image_path, host=host, model=model, client=client)

    return _vlm


def make_scan_vlm_fn(host: str | None = None, model: str | None = None,
                     client: Any | None = None) -> Callable[[list[str]], list[dict]]:
    def _vlm(images: list[str]) -> list[dict]:
        return ollama_scan_vlm(images, host=host, model=model, client=client)

    return _vlm
