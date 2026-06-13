"""Depletion prediction (design.md Section 6, Section 9 v3).

A vegetarian household with a stable cuisine has low-entropy consumption: milk,
dahi, and atta deplete on near-clockwork cycles, which makes this easier than the
general case. We predict days-remaining from a per-item daily consumption rate and
the current quantity.

Rate sources, in priority order:
1. An explicit override (config).
2. A rate inferred from cook-event history over a trailing window.
3. A built-in default for known staples.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from .pantry.state import Pantry
from .events import EventLog, KIND_COOK

# Built-in daily consumption rates for stable staples, in the item's own unit.
# These are deliberately rough; history refines them once it accumulates.
DEFAULT_DAILY_RATES: dict[str, tuple[float, str]] = {
    "milk": (0.28, "gallon"),   # ~2 gal/week for a family of three + toddler
    "yogurt": (0.15, "tub"),    # ~1 tub/week
    "atta": (0.18, "kg"),       # ~1.25 kg/week of rotis
    "basmati rice": (0.18, "kg"),
    "paneer": (0.12, "kg"),
    "onion": (0.85, "whole"),
    "potato": (0.9, "whole"),
    "tomato": (0.8, "whole"),
}


@dataclass
class Prediction:
    canonical: str
    qty: float | None
    unit: str | None
    daily_rate: float | None
    days_remaining: float | None
    predicted_out: str | None  # ISO date

    def to_dict(self) -> dict:
        return {
            "canonical": self.canonical, "qty": self.qty, "unit": self.unit,
            "daily_rate": self.daily_rate, "days_remaining": self.days_remaining,
            "predicted_out": self.predicted_out,
        }


def _history_rate(canonical: str, log: EventLog | None, today: date,
                  window_days: int = 28) -> float | None:
    """Infer a daily rate from cook events that decremented this item."""
    if log is None:
        return None
    start = today - timedelta(days=window_days)
    total = 0.0
    seen = False
    for ev in log.by_kind(KIND_COOK):
        d = ev.event_date()
        if not d or d < start:
            continue
        for dec in ev.data.get("decremented", []):
            if dec.get("canonical") == canonical:
                total += float(dec.get("before", 0)) - float(dec.get("after", 0))
                seen = True
        for dep in ev.data.get("depleted", []):
            if dep == canonical:
                seen = True  # depleted contributes signal but unknown amount
    if not seen or total <= 0:
        return None
    return total / window_days


def predict(
    pantry: Pantry,
    today: date | None = None,
    overrides: dict[str, float] | None = None,
    log: EventLog | None = None,
) -> list[Prediction]:
    today = today or date.today()
    overrides = overrides or {}
    preds: list[Prediction] = []
    for item in pantry.items():
        rate: float | None = None
        if item.canonical in overrides:
            rate = overrides[item.canonical]
        if rate is None:
            rate = _history_rate(item.canonical, log, today)
        if rate is None and item.canonical in DEFAULT_DAILY_RATES:
            default_rate, default_unit = DEFAULT_DAILY_RATES[item.canonical]
            # Only use the default if the unit matches what we track (or unknown).
            if item.unit is None or item.unit == default_unit:
                rate = default_rate
        days_remaining = None
        predicted_out = None
        if rate and item.qty is not None and rate > 0:
            days_remaining = round(item.qty / rate, 1)
            predicted_out = (today + timedelta(days=int(days_remaining))).isoformat()
        if rate is None:
            continue  # nothing to predict for this item
        preds.append(Prediction(
            canonical=item.canonical, qty=item.qty, unit=item.unit,
            daily_rate=rate, days_remaining=days_remaining, predicted_out=predicted_out,
        ))
    preds.sort(key=lambda p: (p.days_remaining is None, p.days_remaining or 0))
    return preds
