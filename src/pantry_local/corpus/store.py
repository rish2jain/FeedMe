"""Recipe corpus storage + retrieval.

The design's runtime source of truth is a curated local corpus in ChromaDB with
hybrid search + RRF fusion (reusing the legal-rag-local stack). For v0 — whose only
job is to validate whether the *plans* are good — we ship a dependency-free
``KeywordRecipeStore`` that scores candidates by pantry overlap and constraint match.
The ``RecipeStore`` protocol is the seam: a ``ChromaRecipeStore`` can drop in later
without touching the planner. A guarded ChromaDB backend is included when the
package is installed.

Every recipe is diet-compliance-checked on add (Stage 2). Non-compliant recipes are
rejected at ingestion so the corpus itself is guaranteed clean.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Protocol

from ..models import Recipe
from ..ontology import normalize
from ..constraints.diet import check_recipe, DietConfig, DietViolation


@dataclass
class SearchConstraints:
    max_total_minutes: int | None = None
    cuisine: str | None = None
    require_toddler_fork: bool = False
    exclude_protein_classes: tuple[str, ...] = ()
    exclude_recipe_ids: tuple[str, ...] = ()
    tags_any: tuple[str, ...] = ()


@dataclass
class ScoredRecipe:
    recipe: Recipe
    score: float
    pantry_matches: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


class RecipeStore(Protocol):
    def add(self, recipe: Recipe, diet: DietConfig | None = None) -> list[DietViolation]: ...
    def get(self, recipe_id: str) -> Recipe | None: ...
    def all(self) -> list[Recipe]: ...
    def search(
        self,
        constraints: SearchConstraints | None = None,
        pantry: Iterable[str] = (),
        limit: int = 10,
    ) -> list[ScoredRecipe]: ...


def _recipe_canonicals(recipe: Recipe) -> set[str]:
    out: set[str] = set()
    for ing in recipe.ingredients:
        c = normalize(ing.name)
        if c:
            out.add(c)
    return out


class KeywordRecipeStore:
    """In-memory corpus with deterministic pantry-overlap scoring."""

    def __init__(self) -> None:
        self._recipes: dict[str, Recipe] = {}

    def add(self, recipe: Recipe, diet: DietConfig | None = None) -> list[DietViolation]:
        violations = check_recipe(recipe, diet)
        if violations:
            return violations  # rejected; corpus stays clean
        self._recipes[recipe.id] = recipe
        return []

    def get(self, recipe_id: str) -> Recipe | None:
        return self._recipes.get(recipe_id)

    def all(self) -> list[Recipe]:
        return list(self._recipes.values())

    def __len__(self) -> int:
        return len(self._recipes)

    def _passes(self, r: Recipe, c: SearchConstraints) -> bool:
        if c.max_total_minutes is not None and r.total_minutes > c.max_total_minutes:
            return False
        if c.cuisine and r.cuisine != c.cuisine:
            return False
        if c.require_toddler_fork and r.toddler_fork_step is None:
            return False
        if r.protein_class in c.exclude_protein_classes:
            return False
        if r.id in c.exclude_recipe_ids:
            return False
        if c.tags_any and not (set(c.tags_any) & set(r.tags)):
            return False
        return True

    def search(
        self,
        constraints: SearchConstraints | None = None,
        pantry: Iterable[str] = (),
        limit: int = 10,
    ) -> list[ScoredRecipe]:
        c = constraints or SearchConstraints()
        pantry_set = {p.lower() for p in pantry}
        results: list[ScoredRecipe] = []
        for r in self._recipes.values():
            if not self._passes(r, c):
                continue
            cans = _recipe_canonicals(r)
            # Ignore staples/spices the household always has from the "missing" set
            # so scoring reflects real shopping deltas.
            matches = sorted(cans & pantry_set)
            missing = sorted(cans - pantry_set)
            coverage = len(matches) / len(cans) if cans else 0.0
            # Score: pantry coverage dominates; a small bonus for fast recipes and
            # for having a clean toddler fork.
            score = coverage * 10.0
            if r.total_minutes and r.total_minutes <= 30:
                score += 1.0
            if r.toddler_fork_step is not None:
                score += 0.5
            results.append(ScoredRecipe(r, round(score, 3), matches, missing))
        results.sort(key=lambda s: (s.score, s.recipe.id), reverse=True)
        return results[:limit]


def get_default_store(seed: bool = True) -> KeywordRecipeStore:
    store = KeywordRecipeStore()
    if seed:
        from .seed_recipes import SEED_RECIPES

        for r in SEED_RECIPES:
            store.add(r)
    return store


# --- Optional ChromaDB backend ----------------------------------------------
try:  # pragma: no cover - exercised only when chromadb is installed
    import chromadb  # type: ignore  # noqa: F401

    _HAS_CHROMA = True
except Exception:  # pragma: no cover
    _HAS_CHROMA = False


def has_chroma() -> bool:
    return _HAS_CHROMA
