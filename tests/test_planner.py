from datetime import date

from pantry_local.corpus.store import get_default_store
from pantry_local.pantry.state import Pantry, load_pantry
from pantry_local.planning.planner import plan_week, plan_validate, PlanConstraints
from pantry_local.constraints.toddler import ToddlerProfile

TODAY = date(2026, 6, 13)
SEED = "data/pantry_seed.json"


def _pantry():
    return load_pantry(SEED)


def test_plan_has_requested_number_of_dinners():
    plan = plan_week(get_default_store(), _pantry(),
                     PlanConstraints(num_dinners=5), today=TODAY)
    assert len(plan.meals) == 5
    # No repeated recipes.
    assert len({m.recipe_id for m in plan.meals}) == 5


def test_use_first_sequencing_puts_expiring_items_early():
    plan = plan_week(get_default_store(), _pantry(),
                     PlanConstraints(num_dinners=5), today=TODAY)
    # methi/spinach/tomato/paneer expire within the week; at least one early meal
    # should consume an expiring item.
    first_half = plan.meals[: (len(plan.meals) + 1) // 2]
    assert any(m.uses_expiring for m in first_half)


def test_time_limit_respected():
    store = get_default_store()
    constraints = PlanConstraints(num_dinners=3,
                                  days=["Mon", "Tue", "Wed"],
                                  day_time_limits={"Tue": 25})
    plan = plan_week(store, _pantry(), constraints, today=TODAY)
    tue = next(m for m in plan.meals if m.day == "Tue")
    assert tue.total_minutes <= 25


def test_infeasible_time_limit_falls_back_and_flags():
    # No recipe cooks in under 5min, so the day is filled with the fastest dish
    # and a short-night note is added rather than the day being dropped.
    store = get_default_store()
    constraints = PlanConstraints(num_dinners=3,
                                  days=["Mon", "Tue", "Wed"],
                                  day_time_limits={"Tue": 5})
    plan = plan_week(store, _pantry(), constraints, today=TODAY)
    assert len(plan.meals) == 3
    assert any("nothing under 5min" in n for n in plan.notes)


def test_variety_avoids_protein_monotony():
    plan = plan_week(get_default_store(), _pantry(),
                     PlanConstraints(num_dinners=5), today=TODAY)
    proteins = [m.protein_class for m in plan.meals if m.protein_class]
    # No single protein class should dominate all protein meals.
    if proteins:
        most = max(proteins.count(p) for p in set(proteins))
        assert most <= len(proteins) - 1 or len(set(proteins)) >= 3


def test_validate_passes_for_generated_plan():
    store = get_default_store()
    pantry = _pantry()
    profile = ToddlerProfile(birthdate="2025-01-15")
    plan = plan_week(store, pantry, PlanConstraints(num_dinners=5),
                     toddler=profile, today=TODAY)
    report = plan_validate(plan, store, pantry, toddler=profile, today=TODAY)
    assert report["diet_violations"] == []
    assert report["coverage"]["ok"]
    assert "nutrition" in report


def test_toddler_plan_present_on_every_meal():
    plan = plan_week(get_default_store(), _pantry(),
                     PlanConstraints(num_dinners=5),
                     toddler=ToddlerProfile(birthdate="2025-01-15"), today=TODAY)
    assert all(m.toddler_plan for m in plan.meals)
