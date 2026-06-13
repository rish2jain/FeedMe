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

import hashlib
import math
import re
from dataclasses import dataclass, field
from typing import Callable, Iterable, Protocol

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


def recipe_passes(r: Recipe, c: SearchConstraints) -> bool:
    """Hard metadata filter shared by every backend."""
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


def _tokenize(text: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t]


def recipe_doc_text(r: Recipe) -> str:
    """The text that represents a recipe for embedding + lexical search."""
    parts = [r.title, r.cuisine, r.cooking_format, r.protein_class or ""]
    parts += [i.name for i in r.ingredients]
    parts += list(r.tags)
    return " ".join(p for p in parts if p)


def _recipe_tokens(r: Recipe) -> set[str]:
    return set(_tokenize(recipe_doc_text(r)))


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
            if not recipe_passes(r, c):
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


# --- Hybrid search primitives -----------------------------------------------

_EMBED_DIM = 256


def hashing_embed(texts: list[str], dim: int = _EMBED_DIM) -> list[list[float]]:
    """A deterministic, dependency-free, offline embedder (hashed token counts,
    L2-normalized).

    It is a placeholder, not a semantic model: it captures lexical overlap, not
    meaning. Production should inject a real local embedder (e.g. nomic-embed via
    Ollama on the Mac Studio — design.md Section 3) through ``ChromaRecipeStore``'s
    ``embed`` parameter. We default to this so the vector path runs with zero
    network and zero model download, which keeps tests hermetic.
    """
    out: list[list[float]] = []
    for text in texts:
        vec = [0.0] * dim
        for tok in _tokenize(text):
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            vec[h % dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec))
        if norm:
            vec = [v / norm for v in vec]
        out.append(vec)
    return out


def reciprocal_rank_fusion(
    rankings: list[list[str]], k: int = 60
) -> dict[str, float]:
    """RRF over several ranked id lists. Score(id) = sum 1/(k + rank)."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, item_id in enumerate(ranking):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank + 1)
    return scores


# --- Optional ChromaDB backend ----------------------------------------------
try:
    import chromadb  # type: ignore

    _HAS_CHROMA = True
except Exception:  # pragma: no cover
    chromadb = None  # type: ignore
    _HAS_CHROMA = False


def has_chroma() -> bool:
    return _HAS_CHROMA


class ChromaRecipeStore:
    """ChromaDB-backed corpus with hybrid (vector + lexical) retrieval fused by RRF
    (design.md Section 1, Stage 3 — the legal-rag-local pattern).

    Embeddings are computed by an injectable ``embed`` callable and passed to Chroma
    explicitly, so the store needs neither Chroma's embedding-function plumbing nor a
    model download. Defaults to :func:`hashing_embed` for hermetic/offline operation;
    pass a real local embedder for semantic quality.

    A small in-memory mirror of the ``Recipe`` objects is kept for reconstruction and
    lexical scoring (Chroma stores only flat metadata).
    """

    def __init__(
        self,
        embed: Callable[[list[str]], list[list[float]]] | None = None,
        persist_dir: str | None = None,
        collection_name: str = "recipes",
        client=None,
    ) -> None:
        if not _HAS_CHROMA:  # pragma: no cover
            raise RuntimeError("chromadb is not installed; pip install '.[chroma]'")
        self._embed = embed or hashing_embed
        if client is not None:
            self._client = client
        elif persist_dir:
            self._client = chromadb.PersistentClient(path=persist_dir)
        else:
            self._client = chromadb.EphemeralClient()
        self._collection = self._client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )
        self._recipes: dict[str, Recipe] = {}

    def __len__(self) -> int:
        return len(self._recipes)

    def get(self, recipe_id: str) -> Recipe | None:
        return self._recipes.get(recipe_id)

    def all(self) -> list[Recipe]:
        return list(self._recipes.values())

    def add(self, recipe: Recipe, diet: DietConfig | None = None) -> list[DietViolation]:
        violations = check_recipe(recipe, diet)
        if violations:
            return violations
        doc = recipe_doc_text(recipe)
        meta = {
            "cuisine": recipe.cuisine,
            "total_minutes": recipe.total_minutes,
            "protein_class": recipe.protein_class or "",
            "cooking_format": recipe.cooking_format,
            "has_toddler_fork": recipe.toddler_fork_step is not None,
            "tags": ",".join(recipe.tags),
            "canonicals": ",".join(sorted(_recipe_canonicals(recipe))),
        }
        self._collection.upsert(
            ids=[recipe.id],
            documents=[doc],
            embeddings=self._embed([doc]),
            metadatas=[meta],
        )
        self._recipes[recipe.id] = recipe
        return []

    def _vector_ranking(self, query: str, n: int) -> list[str]:
        if n == 0:
            return []
        res = self._collection.query(
            query_embeddings=self._embed([query]), n_results=n
        )
        ids = res.get("ids") or [[]]
        return ids[0] if ids else []

    def _lexical_ranking(self, query_tokens: set[str]) -> list[str]:
        scored = []
        for rid, r in self._recipes.items():
            overlap = len(query_tokens & _recipe_tokens(r))
            if overlap:
                scored.append((overlap, rid))
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return [rid for _, rid in scored]

    def search(
        self,
        constraints: SearchConstraints | None = None,
        pantry: Iterable[str] = (),
        limit: int = 10,
    ) -> list[ScoredRecipe]:
        c = constraints or SearchConstraints()
        pantry_set = {p.lower() for p in pantry}
        query = " ".join(sorted(pantry_set) + list(c.tags_any) + (
            [c.cuisine] if c.cuisine else []))
        query_tokens = set(_tokenize(query))

        n = len(self._recipes)
        vector_ids = self._vector_ranking(query, n) if query_tokens else []
        lexical_ids = self._lexical_ranking(query_tokens) if query_tokens else []

        if query_tokens:
            fused = reciprocal_rank_fusion([vector_ids, lexical_ids])
        else:
            # No query signal (empty pantry/constraints): fall back to a stable order.
            fused = {rid: 0.0 for rid in self._recipes}

        results: list[ScoredRecipe] = []
        for rid, rrf in sorted(fused.items(), key=lambda x: (x[1], x[0]), reverse=True):
            r = self._recipes.get(rid)
            if r is None or not recipe_passes(r, c):
                continue
            cans = _recipe_canonicals(r)
            matches = sorted(cans & pantry_set)
            missing = sorted(cans - pantry_set)
            coverage = len(matches) / len(cans) if cans else 0.0
            # Blend retrieval relevance (RRF) with pantry coverage so the planner
            # still prefers what's on hand.
            score = rrf * 100.0 + coverage * 10.0
            if r.toddler_fork_step is not None:
                score += 0.5
            results.append(ScoredRecipe(r, round(score, 4), matches, missing))
        results.sort(key=lambda s: (s.score, s.recipe.id), reverse=True)
        return results[:limit]


def get_chroma_store(seed: bool = True, **kwargs) -> "ChromaRecipeStore":
    store = ChromaRecipeStore(**kwargs)
    if seed:
        from .seed_recipes import SEED_RECIPES

        for r in SEED_RECIPES:
            store.add(r)
    return store
