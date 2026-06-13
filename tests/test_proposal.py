"""Tests for proposal-first planning summary."""

from datetime import date

from pantry_local.corpus.store import get_default_store
from pantry_local.pantry.state import Pantry, PantryItem
from pantry_local.planning.planner import plan_week, plan_proposal_summary, PlanConstraints


def test_plan_proposal_summary_includes_narrative():
    store = get_default_store(seed=True)
    pantry = Pantry(items=[
        PantryItem("fenugreek leaves", 1, "bunch", "2026-06-14", confidence=1.0),
    ])
    plan = plan_week(store, pantry, PlanConstraints(num_dinners=3), today=date(2026, 6, 12))
    summary = plan_proposal_summary(plan, pantry, today=date(2026, 6, 12))
    assert "dinners" in summary
    assert "Swap anything?" in summary["narrative"]
    assert summary["orchestrator_prompt"]
