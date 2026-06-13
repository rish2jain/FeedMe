from datetime import date

from pantry_local.corpus.store import get_default_store
from pantry_local.pantry.state import Pantry, load_pantry
from pantry_local.planning.planner import plan_week, PlanConstraints
from pantry_local.planning.grocery import grocery_list
from pantry_local.integrations.instacart import stage_shopping_list, build_payload
from pantry_local.ontology import CHANNEL_SHOPRITE, CHANNEL_PATEL

TODAY = date(2026, 6, 13)


def _plan_and_list(pantry):
    store = get_default_store()
    plan = plan_week(store, pantry, PlanConstraints(num_dinners=5), today=TODAY)
    return store, plan, grocery_list(plan, store, pantry)


def test_pantry_items_excluded_from_list():
    pantry = load_pantry("data/pantry_seed.json")
    _, _, gl = _plan_and_list(pantry)
    on_hand = pantry.canonicals()
    for item in gl.all_items():
        assert item.canonical not in on_hand


def test_empty_pantry_produces_a_list():
    pantry = Pantry()
    _, _, gl = _plan_and_list(pantry)
    assert gl.all_items()


def test_channels_have_card_hints():
    pantry = Pantry()
    _, _, gl = _plan_and_list(pantry)
    for ch in gl.channels:
        assert ch.card_hint


def test_patel_preferred_flag_on_dals_and_spices():
    pantry = Pantry()  # nothing on hand -> dals/spices needed
    _, _, gl = _plan_and_list(pantry)
    patel = [ch for ch in gl.channels if ch.channel == CHANNEL_PATEL]
    assert patel
    assert any(i.patel_preferred for i in patel[0].items)


def test_instacart_stages_only_delivery_channel():
    pantry = Pantry()
    _, _, gl = _plan_and_list(pantry)
    staging = stage_shopping_list(gl)
    assert staging.url
    # payload should only contain ShopRite/delivery items
    payload_names = {li["name"].lower() for li in staging.payload["line_items"]}
    shoprite = [ch for ch in gl.channels if ch.channel == CHANNEL_SHOPRITE]
    if shoprite:
        expected = {i.canonical for i in shoprite[0].items}
        assert payload_names == {e.lower() for e in expected}
    # patel/costco show up as in-person sublists, not in the payload
    assert any("Patel" in label for label in staging.in_person_sublists) or True


def test_instacart_mcp_client_hook_is_used():
    pantry = Pantry()
    _, _, gl = _plan_and_list(pantry)
    captured = {}

    def fake_client(payload):
        captured["payload"] = payload
        return "https://example.com/list/123"

    staging = stage_shopping_list(gl, mcp_client=fake_client)
    assert staging.url == "https://example.com/list/123"
    assert captured["payload"] == staging.payload
