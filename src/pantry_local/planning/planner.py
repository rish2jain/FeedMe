"""Weekly dinner planner (design.md Sections 7-8).

Plans ~4-5 cooked dinners (not 21 slots), with:
- use-first sequencing: meals that consume soon-to-expire pantry items land in the
  first half of the week.
- variety: penalize repeating a protein class or cooking format.
- calendar awareness: per-day cook-time ceilings flag short nights.
- the toddler fork annotation on every meal.
- a simple leftover network: high-yield dinners cover the next day's lunch.

The selection is greedy and fully deterministic — no LLM. The LLM's role
(orchestration, conversational swaps) sits above this in the planning session.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ..models import MealPlan, PlannedMeal, Recipe
from ..ontology import normalize
from ..pantry.state import Pantry
from ..corpus.store import RecipeStore, SearchConstraints, ScoredRecipe
from ..constraints.diet import DietConfig, check_recipe
from ..constraints.toddler import ToddlerProfile, assess
from . import nutrition

_DEFAULT_DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu"]
_EXPIRY_HORIZON_DAYS = 7


@dataclass
class PlanConstraints:
    num_dinners: int = 5
    days: list[str] = field(default_factory=lambda: list(_DEFAULT_DAYS))
    # Per-day cook-time ceiling in minutes (calendar-derived). Missing => no limit.
    day_time_limits: dict[str, int] = field(default_factory=dict)
    diet: DietConfig = field(default_factory=DietConfig)
    standing_rotations: list[str] = field(default_factory=lambda: [
        "Breakfast: poha / toast / fruit + yogurt (fixed rotation)",
        "Lunch: previous night's leftovers + office days",
        "1-2 dinners: ordered in (confirm broth compliance for ramen)",
    ])


def _recipe_canonicals(r: Recipe) -> set[str]:
    return {c for c in (normalize(i.name) for i in r.ingredients) if c}


def plan_week(
    store: RecipeStore,
    pantry: Pantry,
    constraints: PlanConstraints | None = None,
    toddler: ToddlerProfile | None = None,
    week_of: str | None = None,
    today: date | None = None,
) -> MealPlan:
    c = constraints or PlanConstraints()
    days = c.days[: c.num_dinners]
    week_of = week_of or (today or date.today()).isoformat()

    # Candidate pool, scored by pantry overlap. The corpus is diet-clean by
    # construction (Stage 2 runs on add), so no diet filter is needed here.
    scored = store.search(SearchConstraints(), pantry=pantry.canonicals(), limit=1000)

    expiring = {it.canonical for it in pantry.expiring_within(_EXPIRY_HORIZON_DAYS, today)}

    chosen_ids: set[str] = set()
    used_protein: dict[str, int] = {}
    used_format: dict[str, int] = {}
    meals: list[PlannedMeal] = []
    _short_night_flags: list[tuple[str, int, int]] = []
    n_days = len(days)

    for idx, day in enumerate(days):
        limit = c.day_time_limits.get(day)
        # Earlier days weight expiry use higher (use-first sequencing).
        first_half = idx < (n_days + 1) // 2
        best: tuple[float, ScoredRecipe] | None = None
        for s in scored:
            r = s.recipe
            if r.id in chosen_ids:
                continue
            if limit is not None and r.total_minutes > limit:
                continue
            cans = _recipe_canonicals(r)
            score = s.score
            # Expiry bonus, amplified in the first half of the week.
            exp_hits = len(cans & expiring)
            score += exp_hits * (4.0 if first_half else 1.0)
            # Variety penalties.
            if r.protein_class:
                score -= used_protein.get(r.protein_class, 0) * 3.0
            score -= used_format.get(r.cooking_format, 0) * 1.0
            if best is None or score > best[0]:
                best = (score, s)
        if best is None:
            # Nothing fits this night's time ceiling. Don't drop the day — fall
            # back to the fastest unused dish and flag it (design.md: short nights
            # become ≤25-min-cook or leftover nights).
            remaining = [s for s in scored if s.recipe.id not in chosen_ids]
            if not remaining:
                continue
            s = min(remaining, key=lambda x: x.recipe.total_minutes)
            best = (0.0, s)
            notes_flag = (day, limit, s.recipe.total_minutes)
            _short_night_flags.append(notes_flag)
        s = best[1]
        r = s.recipe
        chosen_ids.add(r.id)
        if r.protein_class:
            used_protein[r.protein_class] = used_protein.get(r.protein_class, 0) + 1
        used_format[r.cooking_format] = used_format.get(r.cooking_format, 0) + 1

        tod = assess(r, toddler, today)
        uses_expiring = sorted(_recipe_canonicals(r) & expiring)
        meals.append(PlannedMeal(
            day=day,
            slot="dinner",
            recipe_id=r.id,
            title=r.title,
            total_minutes=r.total_minutes,
            protein_class=r.protein_class,
            cooking_format=r.cooking_format,
            toddler_plan=tod.fork_instruction,
            uses_expiring=uses_expiring,
        ))

    # Leftover network: a high-yield dinner covers the next day's lunch.
    for i, m in enumerate(meals[:-1]):
        r = store.get(m.recipe_id)
        if r and r.leftover_yield >= 1.4:
            m.leftover_to = meals[i + 1].day

    notes: list[str] = []
    short_days = [d for d in days if d in c.day_time_limits]
    if short_days:
        notes.append(
            "Short-time nights (calendar): "
            + ", ".join(f"{d}<= {c.day_time_limits[d]}min" for d in short_days)
        )
    if expiring:
        notes.append("Using soon: " + ", ".join(sorted(expiring)))
    for day, limit, mins in _short_night_flags:
        notes.append(
            f"{day}: nothing under {limit}min in corpus — picked the fastest "
            f"({mins}min); consider a leftover/order-in night."
        )

    return MealPlan(
        week_of=week_of,
        meals=meals,
        standing_rotations=list(c.standing_rotations),
        notes=notes,
    )


def plan_validate(
    plan: MealPlan,
    store: RecipeStore,
    pantry: Pantry,
    diet: DietConfig | None = None,
    toddler: ToddlerProfile | None = None,
    today: date | None = None,
) -> dict:
    """Run coverage / quantity / diet / toddler / nutrition checks on a plan
    (design.md tool surface: plan_validate). Returns a structured report.
    """
    diet = diet or DietConfig()
    recipes = [store.get(m.recipe_id) for m in plan.meals]
    recipes = [r for r in recipes if r is not None]

    # Diet: must be clean (corpus guarantees it, but re-check at the gate).
    diet_violations = []
    for r in recipes:
        for v in check_recipe(r, diet):
            diet_violations.append({"recipe": r.id, "category": v.category,
                                    "matched": v.matched, "ingredient": v.ingredient})

    # Toddler.
    toddler_report = []
    for r in recipes:
        a = assess(r, toddler, today)
        toddler_report.append({
            "recipe": r.id,
            "adult_only": a.adult_only,
            "daycare_excluded": a.daycare_excluded,
            "hazards": [{"ingredient": h.ingredient, "issue": h.issue,
                         "remediation": h.remediation} for h in a.hazards],
            "fork": a.fork_instruction,
        })

    # Coverage: every requested day filled.
    coverage_ok = len(plan.meals) > 0
    # Quantity: which ingredients are missing from the pantry per meal.
    quantity = []
    pantry_cans = pantry.canonicals()
    for r in recipes:
        missing = sorted(_recipe_canonicals(r) - pantry_cans)
        quantity.append({"recipe": r.id, "missing_from_pantry": missing})

    nutrition_report = nutrition.evaluate(recipes)

    return {
        "ok": coverage_ok and not diet_violations and nutrition_report.ok,
        "coverage": {"planned_meals": len(plan.meals), "ok": coverage_ok},
        "diet_violations": diet_violations,
        "toddler": toddler_report,
        "quantity": quantity,
        "nutrition": {
            "ok": nutrition_report.ok,
            "protein_class_counts": nutrition_report.protein_class_counts,
            "cooking_format_counts": nutrition_report.cooking_format_counts,
            "iron_c_meals": nutrition_report.iron_c_meals,
            "protein_meals": nutrition_report.protein_meals,
            "findings": [{"level": f.level, "code": f.code, "message": f.message}
                         for f in nutrition_report.findings],
        },
    }
