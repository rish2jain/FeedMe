"""Recipe-decrement (design.md Section 6, item 2; Section 9 v1).

Marking a meal cooked decrements its ingredients from the pantry. Combined with
receipt ingestion (additions are observable at purchase time), shelf-stable
inventory becomes *mostly* self-maintaining without a scanning habit.

We are deliberately honest about precision:
- Where recipe and pantry units are convertible (mass<->mass, count<->count,
  volume<->volume), we subtract exactly and remove the item when it hits ~0.
- Bulk staples (spices/condiments) are negligible per meal and never auto-deplete.
- Anything else (unit mismatch, e.g. "1 cup dal" vs "1 kg dal") is left untouched
  and flagged for the voice/scan channel to correct — guessing would corrupt state.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import Recipe
from .ontology import normalize, lookup
from .pantry.state import Pantry
from .units import convert, NEGLIGIBLE_USAGE_AISLES

_EPSILON = 1e-6


@dataclass
class ConsumptionResult:
    decremented: list[dict] = field(default_factory=list)  # {canonical, before, after, unit}
    depleted: list[str] = field(default_factory=list)      # removed (hit ~0)
    negligible: list[str] = field(default_factory=list)    # bulk staples, untouched
    flagged_manual: list[dict] = field(default_factory=list)  # {canonical, reason}
    not_in_pantry: list[str] = field(default_factory=list)  # can't decrement unknown stock

    def to_dict(self) -> dict:
        return {
            "decremented": self.decremented,
            "depleted": self.depleted,
            "negligible": self.negligible,
            "flagged_manual": self.flagged_manual,
            "not_in_pantry": self.not_in_pantry,
        }


def decrement_for_recipe(
    pantry: Pantry, recipe: Recipe, scale: float = 1.0
) -> ConsumptionResult:
    """Decrement a recipe's ingredients from the pantry in place.

    ``scale`` multiplies recipe quantities (e.g. cooked a double batch).
    """
    result = ConsumptionResult()
    for ing in recipe.ingredients:
        if ing.optional:
            continue
        canonical = normalize(ing.name)
        if not canonical:
            continue
        ref = lookup(canonical)
        # Bulk staples: a teaspoon of turmeric off a jar is noise.
        if ref and ref.aisle in NEGLIGIBLE_USAGE_AISLES:
            result.negligible.append(canonical)
            continue
        item = pantry.get(canonical)
        if item is None:
            result.not_in_pantry.append(canonical)
            continue
        # No quantity tracked on the pantry side -> can't subtract numerically.
        if item.qty is None or ing.qty is None:
            result.flagged_manual.append(
                {"canonical": canonical, "reason": "missing quantity on recipe or pantry item"}
            )
            continue
        need = convert(ing.qty * scale, ing.unit, item.unit)
        if need is None:
            result.flagged_manual.append(
                {"canonical": canonical,
                 "reason": f"unit mismatch ({ing.unit or '-'} vs {item.unit or '-'})"}
            )
            continue
        before = item.qty
        after = before - need
        if after <= _EPSILON:
            pantry.remove(canonical)
            result.depleted.append(canonical)
        else:
            item.qty = round(after, 4)
            result.decremented.append(
                {"canonical": canonical, "before": before, "after": item.qty, "unit": item.unit}
            )
    return result
