from datetime import date

from pantry_local.ontology import normalize, lookup, CHANNEL_PATEL
from pantry_local.pantry.state import Pantry, load_pantry, save_pantry, PantryItem


def test_normalize_aliases_and_phrases():
    assert normalize("Red Lentils") == "masoor dal"
    assert normalize("2 cups chopped red onion") == "onion"
    assert normalize("fresh coriander leaves") == "cilantro"
    assert normalize("unobtanium") is None


def test_lookup_metadata():
    dal = lookup("masoor dal")
    assert dal.channel == CHANNEL_PATEL
    assert dal.iron_rich
    assert dal.protein_class == "dal"


def test_pantry_roundtrip(tmp_path):
    p = Pantry([PantryItem("milk", 1, "gallon", expiry="2026-06-20")])
    path = tmp_path / "state.json"
    save_pantry(p, path)
    loaded = load_pantry(path)
    assert loaded.has("milk")
    assert loaded.get("milk").expiry == "2026-06-20"


def test_expiry_report_urgency_ordering():
    p = load_pantry("data/pantry_seed.json")
    report = p.expiry_report(today=date(2026, 6, 13))
    assert report
    # methi expires 2026-06-15 -> should be high/critical and near the top
    top = report[0]
    assert top["urgency"] in {"expired", "critical", "high"}


def test_add_raw_normalizes():
    p = Pantry()
    assert p.add_raw("Red Lentils", 1, "kg")
    assert p.has("masoor dal")
    assert not p.add_raw("unobtanium")
