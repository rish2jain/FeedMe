"""Mid-week alerts (design.md Section 9 v3).

Surfaces a small, actionable list between planning sessions by combining three
signals, deduped:
- expiry: perishables about to expire that the rest of the week's plan won't use,
- depletion: staples predicted to run out before the next shop,
- plan gaps: ingredients a remaining planned meal needs that aren't in stock.

The goal is a handful of "buy milk before Thursday" nudges, not daily nagging.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .pantry.state import Pantry
from .models import MealPlan
from .ontology import normalize
from .events import EventLog
from . import depletion


@dataclass
class Alert:
    kind: str       # expiry | depletion | plan_gap
    canonical: str
    message: str
    urgency: str    # critical | high | medium

    def to_dict(self) -> dict:
        return {"kind": self.kind, "canonical": self.canonical,
                "message": self.message, "urgency": self.urgency}


def _plan_uses(plan: MealPlan | None, store) -> set[str]:
    used: set[str] = set()
    if not plan or store is None:
        return used
    for meal in plan.meals:
        recipe = store.get(meal.recipe_id)
        if not recipe:
            continue
        for ing in recipe.ingredients:
            if ing.optional:
                continue
            c = normalize(ing.name)
            if c:
                used.add(c)
    return used


def midweek_alerts(
    pantry: Pantry,
    plan: MealPlan | None = None,
    store=None,
    today: date | None = None,
    days_to_next_shop: int = 4,
    log: EventLog | None = None,
) -> list[Alert]:
    today = today or date.today()
    alerts: list[Alert] = []
    seen: set[tuple[str, str]] = set()

    def add(kind: str, canonical: str, message: str, urgency: str) -> None:
        key = (kind, canonical)
        if key not in seen:
            seen.add(key)
            alerts.append(Alert(kind, canonical, message, urgency))

    plan_uses = _plan_uses(plan, store)

    # 1. Expiry: expiring soon and NOT used by the remaining plan -> use it or lose it.
    for entry in pantry.expiry_report(today):
        if entry["urgency"] in {"expired", "critical", "high"}:
            c = entry["canonical"]
            if c not in plan_uses:
                add("expiry", c,
                    f"{c} expires in {entry['days_until_expiry']}d and isn't in the "
                    f"plan — use it or it's waste.",
                    "critical" if entry["urgency"] != "high" else "high")

    # 2. Depletion: predicted to run out before the next shop.
    for p in depletion.predict(pantry, today, log=log):
        if p.days_remaining is not None and p.days_remaining <= days_to_next_shop:
            add("depletion", p.canonical,
                f"{p.canonical} runs out in ~{p.days_remaining}d (before next shop) "
                f"— add to the list.",
                "high" if p.days_remaining <= days_to_next_shop / 2 else "medium")

    # 3. Plan gaps: a planned meal needs something not in stock.
    pantry_cans = pantry.canonicals()
    for c in sorted(plan_uses - pantry_cans):
        add("plan_gap", c, f"{c} is needed by the plan but not in stock.", "medium")

    order = {"critical": 0, "high": 1, "medium": 2}
    alerts.sort(key=lambda a: order[a.urgency])
    return alerts
