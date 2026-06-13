"""Nutrition evaluator, respecialized for a no-egg vegetarian household
(design.md Section 5). Advisory only — it never enforces (the blacklists do).

Failure modes checked:
- The dal-rice attractor: too many meals from one protein class / cooking format.
- Iron + vitamin-C co-occurrence at the *same meal* (absorption is a same-meal
  phenomenon), as a weekly target count.
- Protein floor: number of meals with a real protein source.
- B12 and vitamin-D standing watch items (monthly cadence, surfaced gently).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..models import Recipe
from ..ontology import lookup, normalize


@dataclass
class NutritionFinding:
    level: str  # "advisory" | "watch"
    code: str
    message: str


@dataclass
class NutritionReport:
    findings: list[NutritionFinding] = field(default_factory=list)
    protein_class_counts: dict[str, int] = field(default_factory=dict)
    cooking_format_counts: dict[str, int] = field(default_factory=dict)
    iron_c_meals: int = 0
    protein_meals: int = 0

    @property
    def ok(self) -> bool:
        return not any(f.level == "advisory" for f in self.findings)


def _meal_has_iron_and_c(recipe: Recipe) -> bool:
    has_iron = False
    has_c = False
    for ing in recipe.ingredients:
        ref = lookup(normalize(ing.name) or "")
        if not ref:
            continue
        has_iron = has_iron or ref.iron_rich
        has_c = has_c or ref.vitamin_c_rich
    return has_iron and has_c


def evaluate(recipes: list[Recipe]) -> NutritionReport:
    report = NutritionReport()
    if not recipes:
        return report

    for r in recipes:
        if r.protein_class:
            report.protein_class_counts[r.protein_class] = (
                report.protein_class_counts.get(r.protein_class, 0) + 1
            )
            report.protein_meals += 1
        report.cooking_format_counts[r.cooking_format] = (
            report.cooking_format_counts.get(r.cooking_format, 0) + 1
        )
        if _meal_has_iron_and_c(r):
            report.iron_c_meals += 1

    n = len(recipes)

    # Dal-rice attractor: any single protein class dominating > 60% of the week.
    for cls, count in report.protein_class_counts.items():
        if count >= 3 and count / n > 0.6:
            report.findings.append(NutritionFinding(
                "advisory", "protein_monotony",
                f"{count}/{n} dinners are '{cls}'-based — vary the protein source "
                f"(paneer/chana/rajma/tofu/yogurt count separately from dal).",
            ))

    # Cooking-format monotony.
    for fmt, count in report.cooking_format_counts.items():
        if count >= 4 and count / n > 0.6:
            report.findings.append(NutritionFinding(
                "advisory", "format_monotony",
                f"{count}/{n} dinners use the '{fmt}' format — mix in another "
                f"(gravy/dry/grilled/one-pot).",
            ))

    # Protein floor: at least ~half the dinners should carry a real protein source.
    if report.protein_meals / n < 0.5:
        report.findings.append(NutritionFinding(
            "advisory", "protein_floor",
            f"Only {report.protein_meals}/{n} dinners have a real protein source — "
            f"add dal/paneer/chana/rajma/tofu to hit the vegetarian protein floor.",
        ))

    # Iron + C pairing target: aim for >= half the week.
    if report.iron_c_meals < max(2, n // 2):
        report.findings.append(NutritionFinding(
            "advisory", "iron_c_pairing",
            f"Only {report.iron_c_meals}/{n} dinners pair iron + vitamin-C in the "
            f"same meal — pair dal/spinach with tomato/lemon/cilantro for absorption.",
        ))

    # B12 / D standing watch (gentle).
    b12 = any(
        lookup(normalize(i.name) or "") and lookup(normalize(i.name) or "").b12_source
        for r in recipes for i in r.ingredients
    )
    if not b12:
        report.findings.append(NutritionFinding(
            "watch", "b12_watch",
            "No dairy/B12 source in this week's dinners — keep weekly dairy up "
            "(B12 is a standing monthly watch item).",
        ))

    return report
