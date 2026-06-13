from pantry_local.models import Recipe, RecipeIngredient as RI
from pantry_local.corpus.store import get_default_store, KeywordRecipeStore, SearchConstraints


def test_seed_store_loads():
    store = get_default_store()
    assert len(store) >= 15


def test_noncompliant_recipe_rejected_on_add():
    store = KeywordRecipeStore()
    bad = Recipe(id="bad", title="Egg Curry", ingredients=[RI("eggs"), RI("onion")])
    violations = store.add(bad)
    assert violations
    assert store.get("bad") is None


def test_pantry_overlap_ranks_higher():
    store = get_default_store()
    # With paneer + peas on hand, matar-paneer should outrank a rajma dish.
    results = store.search(SearchConstraints(), pantry={"paneer", "peas", "onion", "tomato"})
    ids = [r.recipe.id for r in results]
    assert "matar-paneer" in ids
    assert ids.index("matar-paneer") < ids.index("rajma")


def test_time_filter():
    store = get_default_store()
    results = store.search(SearchConstraints(max_total_minutes=25), pantry=set(), limit=50)
    assert all(r.recipe.total_minutes <= 25 for r in results)


def test_exclude_protein_class():
    store = get_default_store()
    results = store.search(SearchConstraints(exclude_protein_classes=("dal",)),
                           pantry=set(), limit=50)
    assert all(r.recipe.protein_class != "dal" for r in results)
