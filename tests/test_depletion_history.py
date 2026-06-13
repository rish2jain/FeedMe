"""Tests for history-driven depletion window widening."""

from datetime import date, timedelta

from pantry_local.depletion import predict, DEFAULT_DAILY_RATES
from pantry_local.events import EventLog, KIND_COOK
from pantry_local.pantry.state import Pantry, PantryItem


def test_depletion_prefers_history_over_default():
    pantry = Pantry(items=[PantryItem("milk", 1.0, "gallon")])
    log = EventLog()
    for i in range(10):
        d = date(2026, 5, 1) + timedelta(days=i * 2)
        log.append(KIND_COOK, {
            "decremented": [{"canonical": "milk", "before": 1.0, "after": 0.7}],
        }, ts=f"{d.isoformat()}T12:00:00")
    preds = predict(pantry, today=date(2026, 6, 1), log=log)
    milk = next(p for p in preds if p.canonical == "milk")
    assert milk.daily_rate is not None
    assert milk.daily_rate != DEFAULT_DAILY_RATES["milk"][0]
