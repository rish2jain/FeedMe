"""Minimal unit conversion for recipe-decrement (v1).

Recipe-decrement only needs to know whether one quantity can be subtracted from
another, within the same physical dimension. We deliberately do NOT attempt
density-based cross-dimension conversion (cup of dal -> grams) — that is brittle and
out of scope. Where a conversion isn't possible the consumption layer flags the item
for the voice/scan channel rather than guessing.

Three dimensions:
- mass (base: grams)
- volume (base: millilitres)
- count (each ~ 1; produce sizes small/medium/large collapse to a count)
"""

from __future__ import annotations

# unit alias -> (dimension, factor-to-base)
_UNITS: dict[str, tuple[str, float]] = {
    # mass
    "g": ("mass", 1.0), "gram": ("mass", 1.0), "grams": ("mass", 1.0),
    "kg": ("mass", 1000.0), "kilogram": ("mass", 1000.0), "kilograms": ("mass", 1000.0),
    # volume
    "ml": ("volume", 1.0), "milliliter": ("volume", 1.0),
    "l": ("volume", 1000.0), "liter": ("volume", 1000.0), "litre": ("volume", 1000.0),
    "tsp": ("volume", 5.0), "teaspoon": ("volume", 5.0), "teaspoons": ("volume", 5.0),
    "tbsp": ("volume", 15.0), "tablespoon": ("volume", 15.0), "tablespoons": ("volume", 15.0),
    "cup": ("volume", 240.0), "cups": ("volume", 240.0),
    # count (rough but useful for produce)
    "whole": ("count", 1.0), "piece": ("count", 1.0), "pieces": ("count", 1.0),
    "count": ("count", 1.0), "small": ("count", 1.0), "medium": ("count", 1.0),
    "large": ("count", 1.0), "head": ("count", 1.0), "bunch": ("count", 1.0),
    "knob": ("count", 1.0), "bulb": ("count", 1.0),
}

# Bulk staples whose per-recipe usage is negligible against a sack/jar; cooking
# should not auto-deplete these (design.md Section 6: shelf-stable pantry is large
# and slow-moving). Tracked by canonical name.
NEGLIGIBLE_USAGE_AISLES = {"spices", "condiments"}


def unit_dimension(unit: str | None) -> str | None:
    if not unit:
        return None
    return _UNITS.get(unit.lower().strip(), (None, None))[0]


def convert(qty: float, from_unit: str | None, to_unit: str | None) -> float | None:
    """Convert qty from one unit to another within the same dimension.

    Returns None if either unit is unknown or the dimensions differ.
    Unitless on both sides (None/None) is treated as a passthrough count.
    """
    if from_unit is None and to_unit is None:
        return qty
    f = _UNITS.get((from_unit or "").lower().strip())
    t = _UNITS.get((to_unit or "").lower().strip())
    if not f or not t or f[0] != t[0]:
        return None
    return qty * f[1] / t[1]
