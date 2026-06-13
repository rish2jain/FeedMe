"""The curated local recipe corpus (design.md Section 1, Stage 3)."""

from .store import (  # noqa: F401
    RecipeStore,
    KeywordRecipeStore,
    get_default_store,
    has_chroma,
    hashing_embed,
    reciprocal_rank_fusion,
)

if has_chroma():  # pragma: no cover
    from .store import ChromaRecipeStore, get_chroma_store  # noqa: F401
