"""Shared helpers for recipe corpus modules."""

from __future__ import annotations

from ..models import Recipe


def _r(**kw) -> Recipe:
    kw.setdefault("total_minutes", kw.get("prep_minutes", 0) + kw.get("active_minutes", 0))
    return Recipe(**kw)
