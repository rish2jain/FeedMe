import pytest

from pantry_local.corpus.store import (
    has_chroma, reciprocal_rank_fusion, hashing_embed, SearchConstraints,
)

chroma = pytest.importorskip("chromadb") if not has_chroma() else None
pytestmark = pytest.mark.skipif(not has_chroma(), reason="chromadb not installed")


def test_rrf_fuses_rankings():
    a = ["x", "y", "z"]
    b = ["y", "x", "w"]
    scores = reciprocal_rank_fusion([a, b])
    # y is rank0 in b and rank1 in a -> should beat z (only in a)
    assert scores["y"] > scores["z"]
    assert scores["x"] > scores["w"]


def test_hashing_embed_is_deterministic_and_normalized():
    v1 = hashing_embed(["masoor dal onion"])[0]
    v2 = hashing_embed(["masoor dal onion"])[0]
    assert v1 == v2
    norm = sum(x * x for x in v1) ** 0.5
    assert abs(norm - 1.0) < 1e-6


def test_chroma_store_seeds_and_searches():
    from pantry_local.corpus.store import get_chroma_store
    store = get_chroma_store(seed=True)  # ephemeral
    assert len(store) >= 15
    results = store.search(SearchConstraints(),
                           pantry={"paneer", "peas", "onion", "tomato"}, limit=10)
    ids = [r.recipe.id for r in results]
    assert "matar-paneer" in ids


def test_chroma_rejects_noncompliant():
    from pantry_local.corpus.store import get_chroma_store
    from pantry_local.models import Recipe, RecipeIngredient as RI
    store = get_chroma_store(seed=False)
    violations = store.add(Recipe(id="bad", title="Egg Curry",
                                  ingredients=[RI("eggs")]))
    assert violations
    assert store.get("bad") is None


def test_chroma_respects_metadata_filters():
    from pantry_local.corpus.store import get_chroma_store
    store = get_chroma_store(seed=True)
    res = store.search(SearchConstraints(max_total_minutes=25, exclude_protein_classes=("dal",)),
                       pantry={"onion", "tomato"}, limit=50)
    assert all(r.recipe.total_minutes <= 25 for r in res)
    assert all(r.recipe.protein_class != "dal" for r in res)


def test_chroma_hybrid_matches_keyword_top_results():
    # The hybrid store and the keyword store should broadly agree on relevance
    # for a strong pantry signal (sanity check, not exact ordering).
    from pantry_local.corpus.store import get_chroma_store, get_default_store
    pantry = {"chickpeas", "onion", "tomato", "ginger", "garlic"}
    chroma_ids = {r.recipe.id for r in
                  get_chroma_store().search(SearchConstraints(), pantry=pantry, limit=5)}
    kw_ids = {r.recipe.id for r in
              get_default_store().search(SearchConstraints(), pantry=pantry, limit=5)}
    assert "chana-masala" in chroma_ids
    assert chroma_ids & kw_ids  # overlap, not disjoint
