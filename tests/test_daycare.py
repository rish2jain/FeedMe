from pantry_local.corpus.store import get_default_store
from pantry_local.constraints.toddler import ToddlerProfile
from pantry_local.planning.daycare import build_daycare_lunches, is_packable


def test_dormant_when_daycare_inactive():
    plan = build_daycare_lunches(get_default_store(),
                                 ToddlerProfile(birthdate="2025-01-15", daycare_active=False))
    assert plan.active is False
    assert plan.lunches == []
    assert plan.notes


def test_active_builds_packable_nutfree_lunches():
    profile = ToddlerProfile(birthdate="2025-01-15", daycare_active=True)
    plan = build_daycare_lunches(get_default_store(), profile, num_days=5)
    assert plan.active is True
    assert plan.lunches
    # nut-containing recipes (veg-pulao w/ cashews, poha w/ peanuts) must be excluded
    ids = {l["recipe_id"] for l in plan.lunches}
    assert "veg-pulao" not in ids
    assert "cabbage-poha" not in ids


def test_is_packable_excludes_adult_only_and_gravy():
    store = get_default_store()
    profile = ToddlerProfile(birthdate="2025-01-15", daycare_active=True)
    # khichuri is one-pot adult-only -> not packable
    assert not is_packable(store.get("khichuri"), profile)
    # rajma is gravy -> not packable
    assert not is_packable(store.get("rajma"), profile)
    # paneer bhurji is dry, forkable, nut-free -> packable
    assert is_packable(store.get("paneer-bhurji"), profile)
