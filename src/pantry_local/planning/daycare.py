"""Packable toddler-lunch class (design.md Section 2, Section 9 v3).

Dormant until daycare starts, then a daily slot. A packable lunch is:
- no-reheat-friendly (dry or one-pot formats travel; soupy gravies don't pack well),
- no-choke (no unremediated choking hazards for the toddler),
- nut-policy-compliant (most NJ daycares are nut-free — any nut form is excluded).

Built now so the capability exists the day daycare begins; it simply returns a
"dormant" notice while ``daycare_active`` is False.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ..models import Recipe, FORMAT_DRY, FORMAT_ONE_POT
from ..constraints.toddler import ToddlerProfile, assess, contains_nuts

# Formats that survive a lunchbox without reheating.
_PACKABLE_FORMATS = {FORMAT_DRY, FORMAT_ONE_POT}


@dataclass
class DaycareLunchPlan:
    active: bool
    lunches: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"active": self.active, "lunches": self.lunches, "notes": self.notes}


def is_packable(recipe: Recipe, profile: ToddlerProfile, today: date | None = None) -> bool:
    if recipe.cooking_format not in _PACKABLE_FORMATS:
        return False
    if not recipe.toddler_adaptable:
        return False
    if contains_nuts(recipe):  # nut-free daycare
        return False
    a = assess(recipe, profile, today)
    # Unremediated hazards or adult-only dishes aren't packable for a toddler.
    if a.adult_only or a.hazards or a.daycare_excluded:
        return False
    return True


def build_daycare_lunches(
    store,
    profile: ToddlerProfile,
    num_days: int = 5,
    today: date | None = None,
) -> DaycareLunchPlan:
    if not profile.daycare_active:
        return DaycareLunchPlan(
            active=False,
            notes=["Daycare lunch class is dormant (daycare_active=False). "
                   "It activates automatically when daycare starts."],
        )

    candidates = [r for r in store.all() if is_packable(r, profile, today)]
    # Vary the protein source across the week.
    chosen: list[Recipe] = []
    used_protein: dict[str, int] = {}
    for r in sorted(candidates, key=lambda x: (used_protein.get(x.protein_class or "", 0), x.id)):
        if len(chosen) >= num_days:
            break
        chosen.append(r)
        if r.protein_class:
            used_protein[r.protein_class] = used_protein.get(r.protein_class, 0) + 1

    lunches = []
    for r in chosen[:num_days]:
        a = assess(r, profile, today)
        lunches.append({
            "recipe_id": r.id, "title": r.title,
            "protein_class": r.protein_class,
            "toddler_plan": a.fork_instruction,
            "format": r.cooking_format,
        })

    notes = []
    if len(lunches) < num_days:
        notes.append(f"Only {len(lunches)} packable lunches found in the corpus for "
                     f"{num_days} days — add more dry/no-reheat nut-free recipes.")
    return DaycareLunchPlan(active=True, lunches=lunches, notes=notes)
