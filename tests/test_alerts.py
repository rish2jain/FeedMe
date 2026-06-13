from datetime import date

from pantry_local.pantry.state import Pantry, PantryItem
from pantry_local.corpus.store import get_default_store
from pantry_local.models import MealPlan, PlannedMeal
from pantry_local.alerts import midweek_alerts

TODAY = date(2026, 6, 13)


def test_expiry_alert_when_not_in_plan():
    pantry = Pantry([PantryItem("methi", 1, "bunch", expiry="2026-06-14")])
    alerts = midweek_alerts(pantry, plan=None, store=get_default_store(), today=TODAY)
    assert any(a.kind == "expiry" and a.canonical == "methi" for a in alerts)


def test_no_expiry_alert_when_used_by_plan():
    store = get_default_store()
    pantry = Pantry([PantryItem("paneer", 0.4, "kg", expiry="2026-06-14")])
    plan = MealPlan(week_of="2026-06-13", meals=[
        PlannedMeal(day="Sat", slot="dinner", recipe_id="paneer-bhurji",
                    title="Paneer Bhurji", total_minutes=25, protein_class="paneer",
                    cooking_format="dry", toddler_plan="x"),
    ])
    alerts = midweek_alerts(pantry, plan=plan, store=store, today=TODAY)
    assert not any(a.kind == "expiry" and a.canonical == "paneer" for a in alerts)


def test_depletion_alert_before_next_shop():
    pantry = Pantry([PantryItem("milk", 0.5, "gallon")])  # ~0.28/day -> ~1.8 days
    alerts = midweek_alerts(pantry, store=get_default_store(), today=TODAY,
                            days_to_next_shop=4)
    assert any(a.kind == "depletion" and a.canonical == "milk" for a in alerts)


def test_optional_ingredients_do_not_trigger_plan_gap():
    store = get_default_store()
    pantry = Pantry()
    # Vegetable Poha lists peanuts as optional -> must not be a plan gap.
    plan = MealPlan(week_of="2026-06-13", meals=[
        PlannedMeal(day="Sat", slot="dinner", recipe_id="cabbage-poha",
                    title="Vegetable Poha", total_minutes=22, protein_class=None,
                    cooking_format="one_pot", toddler_plan="x"),
    ])
    alerts = midweek_alerts(pantry, plan=plan, store=store, today=TODAY)
    assert not any(a.canonical == "peanuts" for a in alerts)


def test_plan_gap_alert():
    store = get_default_store()
    pantry = Pantry()  # nothing in stock
    plan = MealPlan(week_of="2026-06-13", meals=[
        PlannedMeal(day="Sat", slot="dinner", recipe_id="rajma", title="Rajma",
                    total_minutes=40, protein_class="rajma", cooking_format="gravy",
                    toddler_plan="x"),
    ])
    alerts = midweek_alerts(pantry, plan=plan, store=store, today=TODAY)
    assert any(a.kind == "plan_gap" for a in alerts)
