from pantry_local.pantry.state import Pantry, PantryItem
from pantry_local.ingestion.scan import ingest_scan, apply_confirmations


def test_high_confidence_applied_low_held():
    pantry = Pantry()
    res = ingest_scan(pantry, scan_items=[
        {"name": "Milk", "qty": 1, "unit": "gallon", "confidence": 0.95},
        {"name": "Paneer", "qty": 0.4, "unit": "kg", "confidence": 0.4},
    ])
    assert pantry.has("milk")
    assert not pantry.has("paneer")
    assert any(p["canonical"] == "paneer" for p in res.pending_confirmation)
    assert pantry.get("milk").source == "scan"


def test_not_seen_perishables_flagged_not_removed():
    pantry = Pantry([PantryItem("spinach", 1, "bunch", expiry="2026-06-16")])
    res = ingest_scan(pantry, scan_items=[{"name": "Milk", "confidence": 0.9}])
    # spinach wasn't seen -> flagged, but still present (occlusion-safe)
    assert "spinach" in res.not_seen
    assert pantry.has("spinach")


def test_confirmations_apply_and_remove():
    pantry = Pantry([PantryItem("spinach", 1, "bunch")])
    pending = [{"canonical": "paneer", "qty": 0.4, "unit": "kg"}]
    out = apply_confirmations(pantry, {"paneer": True, "spinach": False}, pending)
    assert "paneer" in out["confirmed"]
    assert pantry.has("paneer")
    assert "spinach" in out["removed"]
    assert not pantry.has("spinach")


def test_vlm_client_hook():
    pantry = Pantry()
    seen = {}

    def fake_vlm(images):
        seen["imgs"] = images
        return [{"name": "Yogurt", "qty": 1, "unit": "tub", "confidence": 0.9}]

    ingest_scan(pantry, images=["main.jpg", "door.jpg"], vlm_client=fake_vlm)
    assert seen["imgs"] == ["main.jpg", "door.jpg"]
    assert pantry.has("yogurt")
