"""Toddler sub-agent: deterministic safety checks + the cook-once/plate-twice fork
(design.md Section 2).

Three concerns, all deterministic:
1. Choking-hazard checks that operate on ingredient *form*, not identity
   (grapes are fine quartered; whole grapes are not).
2. The toddler fork: where a toddler portion is pulled before salt/chili/whole
   spices. Recipes with no clean fork point are flagged adult-only.
3. Age-gating: rules change quarterly, derived from a birthdate, not static.
4. Daycare nut policy: nut-containing items get a daycare-exclusion flag
   (most NJ daycares are nut-free).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from ..models import Recipe, RecipeIngredient, FORMAT_ONE_POT
from ..ontology import normalize

# Forms considered safe (the hazardous shape has been remediated).
_SAFE_FORMS = {"quartered", "halved", "paste", "powder", "ground", "crumbled",
               "mashed", "pureed", "thin strips", "grated", "cooked soft",
               "finely chopped", "shredded"}

# canonical (or raw token) -> (hazard description, safe remediation)
_HAZARD_RULES: dict[str, tuple[str, str]] = {
    "grapes": ("whole grapes are a round choking hazard", "quarter lengthwise"),
    "cherry tomato": ("whole cherry tomatoes are a choking hazard", "quarter them"),
    "cashews": ("whole/chunked nuts are a choking hazard", "use as paste or powder"),
    "almonds": ("whole/chunked nuts are a choking hazard", "use as paste or powder"),
    "peanuts": ("whole peanuts are a choking hazard", "use as smooth paste only"),
    "paneer": ("large paneer cubes can choke", "crumble or cut thin strips"),
    "carrot": ("raw hard carrot is a choking hazard", "cook soft or grate"),
}
# Raw-token hazards not in the ontology.
_RAW_HAZARD_RULES: dict[str, tuple[str, str]] = {
    "popcorn": ("popcorn is a choking hazard for under-4s", "omit for toddler"),
    "whole nuts": ("whole nuts are a choking hazard", "use paste or powder"),
}

_NUT_CANONICALS = {"cashews", "almonds", "peanuts"}


@dataclass
class ToddlerProfile:
    birthdate: str  # ISO date
    daycare_active: bool = False
    nut_free_required: bool = False  # forced on when daycare_active

    def age_months(self, today: date | None = None) -> int:
        today = today or date.today()
        try:
            bd = datetime.strptime(self.birthdate, "%Y-%m-%d").date()
        except ValueError:
            return 0
        return (today.year - bd.year) * 12 + (today.month - bd.month) - (
            1 if today.day < bd.day else 0
        )


@dataclass
class ToddlerHazard:
    ingredient: str
    issue: str
    remediation: str


@dataclass
class ToddlerAssessment:
    safe_with_remediation: bool  # True if every hazard has a remediation applied/possible
    hazards: list[ToddlerHazard] = field(default_factory=list)
    fork_instruction: str = ""
    adult_only: bool = False
    daycare_excluded: bool = False  # contains nuts; not packable for nut-free daycare
    age_notes: list[str] = field(default_factory=list)


def _is_remediated(ing: RecipeIngredient) -> bool:
    if not ing.form:
        return False
    form = ing.form.lower()
    return any(safe in form for safe in _SAFE_FORMS)


def check_hazards(recipe: Recipe) -> list[ToddlerHazard]:
    hazards: list[ToddlerHazard] = []
    for ing in recipe.ingredients:
        canonical = normalize(ing.name)
        rule = None
        if canonical and canonical in _HAZARD_RULES:
            rule = _HAZARD_RULES[canonical]
        else:
            low = ing.name.lower()
            for token, r in _RAW_HAZARD_RULES.items():
                if token in low:
                    rule = r
                    break
        if rule and not _is_remediated(ing):
            issue, remediation = rule
            hazards.append(ToddlerHazard(ing.name, issue, remediation))
    return hazards


def fork_instruction(recipe: Recipe) -> tuple[str, bool]:
    """Return (instruction, adult_only)."""
    if recipe.toddler_fork_step is not None:
        if 0 <= recipe.toddler_fork_step < len(recipe.steps):
            step = recipe.steps[recipe.toddler_fork_step]
            return (
                f"Pull toddler portion before step {recipe.toddler_fork_step + 1} "
                f"(\"{step}\") — i.e. before salt/chili/whole spices.",
                False,
            )
        return ("Pull toddler portion before salt/chili are added.", False)
    if recipe.cooking_format == FORMAT_ONE_POT:
        return (
            "No clean fork point (one-pot, heat/spice integral) — adult-only night, "
            "toddler needs a parallel item.",
            True,
        )
    return (
        "No fork point annotated — verify a low-salt/low-spice portion can be set "
        "aside, else treat as adult-only.",
        False,
    )


def contains_nuts(recipe: Recipe) -> bool:
    for ing in recipe.ingredients:
        if normalize(ing.name) in _NUT_CANONICALS:
            return True
    return False


def _age_notes(profile: ToddlerProfile, today: date | None = None) -> list[str]:
    months = profile.age_months(today)
    notes: list[str] = []
    if months < 12:
        notes.append(f"{months}mo: no added salt or honey; fully pureed/mashed textures.")
    elif months < 18:
        notes.append(f"{months}mo: minimal salt; soft mashed/small-soft-pieces texture.")
    elif months < 24:
        notes.append(f"{months}mo: low salt; soft chopped pieces; still quarter round foods.")
    elif months < 36:
        notes.append(f"{months}mo: limited salt/spice; most textures ok; quarter round foods.")
    else:
        notes.append(f"{months}mo: near-adult textures; popcorn/whole-nut caution to age 4.")
    return notes


def assess(recipe: Recipe, profile: ToddlerProfile | None = None,
           today: date | None = None) -> ToddlerAssessment:
    hazards = check_hazards(recipe)
    instruction, adult_only = fork_instruction(recipe)
    has_nuts = contains_nuts(recipe)
    nut_free = bool(profile and (profile.nut_free_required or profile.daycare_active))
    daycare_excluded = has_nuts and nut_free
    age_notes = _age_notes(profile, today) if profile else []

    # Hazards are remediable (the rules carry remediations), so the recipe is
    # "safe with remediation" as long as none are unfixable. All current rules are.
    return ToddlerAssessment(
        safe_with_remediation=True,
        hazards=hazards,
        fork_instruction=instruction,
        adult_only=adult_only,
        daycare_excluded=daycare_excluded,
        age_notes=age_notes,
    )
