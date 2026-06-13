"""Stage 2 deterministic diet blacklist (design.md Section 1).

Strict no-egg vegetarian, no meat substitutes. This is the authoritative gate:
any recipe with a violation is discarded before the LLM ever sees it. The check
runs against derivatives, because that is exactly where recipe databases fail
("vegetarian" frittata, "egg-free" cake that lists albumin, etc.).

The matching is substring-based on normalized text and deliberately conservative:
a false reject (discarding a safe recipe) is cheap; a false accept (serving the
family eggs) is the failure this whole layer exists to prevent.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from ..models import Recipe

# Each entry: (label, list of substrings that trigger it). Substrings are matched
# against cleaned ingredient text with word boundaries where the token is short
# enough to collide (handled below).
_EGG = [
    "egg", "eggs", "egg white", "egg whites", "egg yolk", "egg yolks",
    "albumin", "albumen", "lysozyme", "meringue", "egg noodle", "egg noodles",
    "fresh egg pasta", "mayonnaise", "mayo", "aioli", "hollandaise",
]
_MEAT = [
    "chicken", "beef", "pork", "lamb", "mutton", "bacon", "ham", "turkey",
    "veal", "goat", "sausage", "pepperoni", "salami", "prosciutto", "gelatin",
    "gelatine", "lard", "tallow", "broth",  # generic broth flagged; veg broth must say so
]
_FISH = [
    "fish", "anchovy", "anchovies", "shrimp", "prawn", "prawns", "crab",
    "lobster", "tuna", "salmon", "cod", "oyster", "oyster sauce", "fish sauce",
    "worcestershire", "dashi", "bonito", "shellfish", "clam", "mussel",
]
_MEAT_ANALOG = [
    "beyond", "impossible", "seitan", "tofurky", "plant-based meat",
    "plant based meat", "vegan chicken", "vegan beef", "chick'n", "chickn",
    "facon", "meat substitute", "soy curls", "tvp", "textured vegetable protein",
]
# Configurable: animal-rennet cheeses. "vegetarian" parmesan mostly isn't.
_RENNET = [
    "parmesan", "parmigiano", "pecorino", "gruyere", "grana padano",
    "manchego", "rennet",
]

# Tokens short enough to cause spurious substring hits => require word boundary.
_WORD_BOUNDED = {"egg", "eggs", "ham", "mayo", "cod", "crab", "tvp", "veal"}

_CLEAN = re.compile(r"[^a-z0-9\s'-]")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", _CLEAN.sub(" ", text.lower())).strip()


def _hit(haystack: str, needle: str) -> bool:
    if needle in _WORD_BOUNDED:
        return re.search(rf"\b{re.escape(needle)}\b", haystack) is not None
    return needle in haystack


@dataclass
class DietViolation:
    category: str  # egg | meat | fish | meat_analog | rennet
    matched: str  # the blacklist term
    ingredient: str  # the offending ingredient/source text


@dataclass
class DietConfig:
    enforce_rennet: bool = False  # one-line policy switch (design.md Section 1)


_CATEGORIES = [
    ("egg", _EGG),
    ("meat", _MEAT),
    ("fish", _FISH),
    ("meat_analog", _MEAT_ANALOG),
]


def check_text(text: str, config: DietConfig | None = None) -> list[DietViolation]:
    """Check an arbitrary ingredient string against the blacklist."""
    config = config or DietConfig()
    cleaned = _clean(text)
    violations: list[DietViolation] = []
    categories = list(_CATEGORIES)
    if config.enforce_rennet:
        categories.append(("rennet", _RENNET))
    for category, terms in categories:
        for term in terms:
            if _hit(cleaned, term):
                violations.append(DietViolation(category, term, text.strip()))
                break  # one hit per category per ingredient is enough
    return violations


def check_recipe(recipe: Recipe, config: DietConfig | None = None) -> list[DietViolation]:
    """Return all diet violations in a recipe. Empty list == compliant."""
    config = config or DietConfig()
    violations: list[DietViolation] = []
    for ing in recipe.ingredients:
        violations.extend(check_text(ing.name, config))
    # Also scan the title (catches e.g. "Egg Curry" with mislabeled ingredients).
    violations.extend(check_text(recipe.title, config))
    return violations


def is_compliant(recipe: Recipe, config: DietConfig | None = None) -> bool:
    return not check_recipe(recipe, config)
