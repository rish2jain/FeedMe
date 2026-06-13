"""Pantry inventory: a confidence-aware item store with JSON persistence.

In v0 the pantry is a manually seeded JSON file (design.md Section 9 v0). The model
already supports confidence and source so that receipt/scan/voice ingestion (v1-v2)
can write into it without schema changes. Items are keyed by canonical ontology name.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from ..models import PantryItem
from ..ontology import normalize, lookup


class Pantry:
    def __init__(self, items: list[PantryItem] | None = None) -> None:
        self._items: dict[str, PantryItem] = {}
        for it in items or []:
            self._items[it.canonical] = it

    # --- mutation ---
    def upsert(self, item: PantryItem) -> None:
        self._items[item.canonical] = item

    def add_raw(self, raw_name: str, qty: float | None = None, unit: str | None = None,
                expiry: str | None = None, confidence: float = 1.0,
                source: str = "manual") -> bool:
        """Normalize a raw name and store it. Returns False if it can't be mapped."""
        canonical = normalize(raw_name)
        if not canonical:
            return False
        self.upsert(PantryItem(canonical, qty, unit, expiry, confidence, source))
        return True

    def remove(self, canonical: str) -> bool:
        return self._items.pop(canonical, None) is not None

    # --- queries ---
    def has(self, canonical: str) -> bool:
        return canonical in self._items

    def get(self, canonical: str) -> PantryItem | None:
        return self._items.get(canonical)

    def canonicals(self) -> set[str]:
        return set(self._items.keys())

    def items(self) -> list[PantryItem]:
        return list(self._items.values())

    def expiring_within(self, days: int, today: date | None = None) -> list[PantryItem]:
        out = []
        for it in self._items.values():
            d = it.days_until_expiry(today)
            if d is not None and d <= days:
                out.append(it)
        out.sort(key=lambda i: (i.days_until_expiry(today) if i.expiry else 9999))
        return out

    def expiry_report(self, today: date | None = None) -> list[dict]:
        """Urgency-scored list (design.md tool surface: expiry_report)."""
        report = []
        for it in self._items.values():
            d = it.days_until_expiry(today)
            if d is None:
                continue
            if d < 0:
                urgency = "expired"
            elif d <= 1:
                urgency = "critical"
            elif d <= 3:
                urgency = "high"
            elif d <= 6:
                urgency = "medium"
            else:
                urgency = "low"
            report.append({
                "canonical": it.canonical,
                "days_until_expiry": d,
                "urgency": urgency,
                "perishable": bool(lookup(it.canonical) and lookup(it.canonical).perishable),
            })
        order = {"expired": 0, "critical": 1, "high": 2, "medium": 3, "low": 4}
        report.sort(key=lambda r: (order[r["urgency"]], r["days_until_expiry"]))
        return report

    # --- serialization ---
    def to_dict(self) -> dict:
        return {"items": [it.to_dict() for it in self._items.values()]}

    @classmethod
    def from_dict(cls, d: dict) -> "Pantry":
        return cls([PantryItem.from_dict(i) for i in d.get("items", [])])


def load_pantry(path: str | Path) -> Pantry:
    p = Path(path)
    if not p.exists():
        return Pantry()
    return Pantry.from_dict(json.loads(p.read_text()))


def save_pantry(pantry: Pantry, path: str | Path) -> None:
    Path(path).write_text(json.dumps(pantry.to_dict(), indent=2))
