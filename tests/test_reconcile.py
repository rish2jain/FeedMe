from pantry_local.pantry.state import Pantry
from pantry_local.reconcile import reconcile, expected_from_grocery_list


def test_reconcile_classifies_received_missing_extra():
    pantry = Pantry()
    expected = ["paneer", "milk", "spinach"]
    res = reconcile(pantry, expected, receipt_items=[
        {"name": "Paneer", "qty": 0.4, "unit": "kg"},
        {"name": "Whole Milk", "qty": 1, "unit": "gallon"},
        {"name": "Tofu", "qty": 0.25, "unit": "kg"},  # substitution
    ])
    assert "paneer" in res.received and "milk" in res.received
    assert "spinach" in res.missing       # didn't arrive
    assert "tofu" in res.substitutions    # arrived, not expected
    # inventory updated as a side effect
    assert pantry.has("paneer") and pantry.has("tofu")


def test_expected_from_grocery_list():
    gl = {"channels": [
        {"items": [{"canonical": "milk"}, {"canonical": "paneer"}]},
        {"items": [{"canonical": "masoor dal"}]},
    ]}
    assert set(expected_from_grocery_list(gl)) == {"milk", "paneer", "masoor dal"}
