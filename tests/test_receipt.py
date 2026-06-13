from pantry_local.pantry.state import Pantry, PantryItem
from pantry_local.ingestion.receipt import parse_receipt_text, ingest_receipt


SAMPLE = """\
ShopRite Order Confirmation
2  Red Lentils 1 kg          $4.99
Onions 3 lb                  $2.49
1 x Paneer 400 g             $5.49
Whole Milk 1 gal             $3.79
Subtotal                     $16.76
Tax                          $0.00
Total                        $16.76
"""


def test_parse_skips_noise_and_maps_canonicals():
    lines = parse_receipt_text(SAMPLE)
    canon = {l.canonical for l in lines if l.canonical}
    assert "masoor dal" in canon
    assert "onion" in canon
    assert "paneer" in canon
    assert "milk" in canon
    # noise lines dropped
    raws = " ".join(l.raw.lower() for l in lines)
    assert "subtotal" not in raws and "total" not in raws


def test_ingest_text_applies_additions():
    pantry = Pantry()
    res = ingest_receipt(pantry, text=SAMPLE)
    assert pantry.has("paneer")
    assert pantry.has("masoor dal")
    applied = {a["canonical"] for a in res.applied}
    assert "milk" in applied
    # receipt-sourced confidence
    assert pantry.get("milk").source == "receipt"


def test_ingest_accumulates_matching_units():
    pantry = Pantry([PantryItem("masoor dal", qty=1, unit="kg")])
    res = ingest_receipt(pantry, line_items=[{"name": "Red Lentils", "qty": 1, "unit": "kg"}])
    assert pantry.get("masoor dal").qty == 2  # 1 + 1


def test_vlm_line_items_higher_confidence():
    pantry = Pantry()
    res = ingest_receipt(pantry, line_items=[{"name": "Paneer", "qty": 400, "unit": "g"}])
    assert res.applied[0]["confidence"] == 0.9


def test_vlm_client_hook():
    pantry = Pantry()
    called = {}

    def fake_vlm(path):
        called["path"] = path
        return [{"name": "Tomatoes", "qty": 5, "unit": "whole"}]

    ingest_receipt(pantry, image_path="/tmp/receipt.jpg", vlm_client=fake_vlm)
    assert called["path"] == "/tmp/receipt.jpg"
    assert pantry.has("tomato")


def test_unmatched_reported():
    pantry = Pantry()
    res = ingest_receipt(pantry, line_items=[{"name": "Quantum Flux Capacitor"}])
    assert res.unmatched
