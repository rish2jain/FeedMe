from datetime import date

from pantry_local.pantry.state import Pantry, PantryItem
from pantry_local.events import EventLog
from pantry_local import depletion

TODAY = date(2026, 6, 13)


def test_default_rate_prediction():
    pantry = Pantry([PantryItem("milk", qty=1.0, unit="gallon")])
    preds = depletion.predict(pantry, today=TODAY)
    milk = next(p for p in preds if p.canonical == "milk")
    assert milk.days_remaining is not None
    assert milk.predicted_out is not None


def test_unit_mismatch_skips_default():
    # milk default is in gallons; a "liter" entry shouldn't use the gallon rate.
    pantry = Pantry([PantryItem("milk", qty=1.0, unit="liter")])
    preds = depletion.predict(pantry, today=TODAY)
    assert all(p.canonical != "milk" for p in preds)


def test_override_rate():
    pantry = Pantry([PantryItem("paneer", qty=1.0, unit="kg")])
    preds = depletion.predict(pantry, today=TODAY, overrides={"paneer": 0.5})
    paneer = next(p for p in preds if p.canonical == "paneer")
    assert paneer.daily_rate == 0.5
    assert paneer.days_remaining == 2.0


def test_history_rate_used():
    pantry = Pantry([PantryItem("onion", qty=14.0, unit="whole")])
    log = EventLog()
    log.append("cook", {"decremented": [{"canonical": "onion", "before": 10, "after": 8}]},
               ts="2026-06-01T19:00:00")
    preds = depletion.predict(pantry, today=TODAY, log=log)
    onion = next(p for p in preds if p.canonical == "onion")
    # 2 onions over a 28-day window -> ~0.071/day
    assert onion.daily_rate and onion.daily_rate > 0


def test_items_with_no_rate_skipped():
    pantry = Pantry([PantryItem("bay leaf", qty=1.0, unit="pack")])
    preds = depletion.predict(pantry, today=TODAY)
    assert all(p.canonical != "bay leaf" for p in preds)
