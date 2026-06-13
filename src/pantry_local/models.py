"""Core data models for pantry-local.

Plain dataclasses with explicit (de)serialization so they round-trip through JSON
(inventory state, recipe corpus, MCP tool payloads) without a heavy ORM.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import Any

# Cooking formats, for the repetition / variety check (design.md Section 5).
FORMAT_GRAVY = "gravy"
FORMAT_DRY = "dry"
FORMAT_GRILLED = "grilled"
FORMAT_ONE_POT = "one_pot"
FORMAT_OTHER = "other"


@dataclass
class RecipeIngredient:
    """A single ingredient line in a recipe.

    ``name`` is the raw text; ``canonical`` (if resolved) keys into the ontology.
    ``form`` matters for toddler safety ("whole", "quartered", "paste", ...).
    ``stage`` lets a recipe mark when an item enters the pot, which the toddler
    fork logic uses (e.g. chili added at the "tadka" stage, after the fork).
    """

    name: str
    qty: float | None = None
    unit: str | None = None
    form: str | None = None
    stage: str | None = None
    optional: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None and v is not False}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RecipeIngredient":
        return cls(
            name=d["name"],
            qty=d.get("qty"),
            unit=d.get("unit"),
            form=d.get("form"),
            stage=d.get("stage"),
            optional=d.get("optional", False),
        )


@dataclass
class Recipe:
    id: str
    title: str
    cuisine: str = "indian"
    ingredients: list[RecipeIngredient] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    prep_minutes: int = 0
    active_minutes: int = 0
    total_minutes: int = 0
    servings: int = 4
    cooking_format: str = FORMAT_OTHER
    # The protein source class (ontology.PROTEIN_*) this dish counts as, for the
    # repetition check. Resolved from ingredients if left None.
    protein_class: str | None = None
    # Toddler: the step index *before which* a toddler portion can be pulled
    # (before salt/chili/whole spices). None => no clean fork point.
    toddler_fork_step: int | None = None
    toddler_adaptable: bool = True
    leftover_yield: float = 1.0  # multiplier on servings for next-day lunches
    tags: list[str] = field(default_factory=list)
    source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "cuisine": self.cuisine,
            "ingredients": [i.to_dict() for i in self.ingredients],
            "steps": self.steps,
            "prep_minutes": self.prep_minutes,
            "active_minutes": self.active_minutes,
            "total_minutes": self.total_minutes,
            "servings": self.servings,
            "cooking_format": self.cooking_format,
            "protein_class": self.protein_class,
            "toddler_fork_step": self.toddler_fork_step,
            "toddler_adaptable": self.toddler_adaptable,
            "leftover_yield": self.leftover_yield,
            "tags": self.tags,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Recipe":
        return cls(
            id=d["id"],
            title=d["title"],
            cuisine=d.get("cuisine", "indian"),
            ingredients=[RecipeIngredient.from_dict(i) for i in d.get("ingredients", [])],
            steps=d.get("steps", []),
            prep_minutes=d.get("prep_minutes", 0),
            active_minutes=d.get("active_minutes", 0),
            total_minutes=d.get("total_minutes", 0),
            servings=d.get("servings", 4),
            cooking_format=d.get("cooking_format", FORMAT_OTHER),
            protein_class=d.get("protein_class"),
            toddler_fork_step=d.get("toddler_fork_step"),
            toddler_adaptable=d.get("toddler_adaptable", True),
            leftover_yield=d.get("leftover_yield", 1.0),
            tags=d.get("tags", []),
            source=d.get("source"),
        )


@dataclass
class PantryItem:
    """An inventory entry. ``confidence`` is explicit per the design's
    'never hallucinate inventory' principle: VLM/receipt-sourced items carry
    their confidence; manually confirmed items are 1.0."""

    canonical: str
    qty: float | None = None
    unit: str | None = None
    expiry: str | None = None  # ISO date
    confidence: float = 1.0
    source: str = "manual"  # manual | receipt | scan | voice

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PantryItem":
        return cls(
            canonical=d["canonical"],
            qty=d.get("qty"),
            unit=d.get("unit"),
            expiry=d.get("expiry"),
            confidence=d.get("confidence", 1.0),
            source=d.get("source", "manual"),
        )

    def days_until_expiry(self, today: date | None = None) -> int | None:
        if not self.expiry:
            return None
        today = today or date.today()
        try:
            exp = datetime.strptime(self.expiry, "%Y-%m-%d").date()
        except ValueError:
            return None
        return (exp - today).days


@dataclass
class PlannedMeal:
    day: str  # e.g. "Mon"
    slot: str  # "dinner" for v0
    recipe_id: str
    title: str
    total_minutes: int
    protein_class: str | None
    cooking_format: str
    toddler_plan: str  # human-readable fork instruction or "adult-only"
    uses_expiring: list[str] = field(default_factory=list)
    leftover_to: str | None = None  # day this meal's leftovers cover

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MealPlan:
    week_of: str  # ISO date of the Sunday
    meals: list[PlannedMeal] = field(default_factory=list)
    standing_rotations: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "week_of": self.week_of,
            "meals": [m.to_dict() for m in self.meals],
            "standing_rotations": self.standing_rotations,
            "notes": self.notes,
        }
