from pantry_local.models import Recipe, RecipeIngredient as RI
from pantry_local.constraints.diet import (
    check_recipe, check_text, is_compliant, DietConfig,
)
from pantry_local.corpus.seed_recipes import SEED_RECIPES


def _recipe(*names):
    return Recipe(id="t", title="Test", ingredients=[RI(n) for n in names])


def test_all_seed_recipes_are_compliant():
    for r in SEED_RECIPES:
        assert is_compliant(r), f"{r.id} should be diet-compliant"


def test_plain_egg_is_caught():
    v = check_recipe(_recipe("2 eggs", "flour"))
    assert any(x.category == "egg" for x in v)


def test_egg_derivatives_are_caught():
    for term in ["albumin", "meringue", "mayonnaise", "egg whites", "egg noodles"]:
        v = check_text(term)
        assert v and v[0].category == "egg", term


def test_meat_and_fish_caught():
    assert any(x.category == "meat" for x in check_text("chicken thighs"))
    assert any(x.category == "fish" for x in check_text("fish sauce"))
    assert any(x.category == "fish" for x in check_text("worcestershire sauce"))


def test_meat_analogs_caught():
    assert any(x.category == "meat_analog" for x in check_text("Beyond burger"))
    assert any(x.category == "meat_analog" for x in check_text("seitan strips"))


def test_word_boundary_avoids_false_positives():
    # "eggplant" must not trigger the egg rule.
    assert is_compliant(_recipe("eggplant", "onion", "tomato"))
    # "hammour"-style substrings shouldn't trip "ham".
    assert not any(x.matched == "ham" for x in check_text("hamburger bun is excluded by meat? no"))


def test_rennet_is_configurable():
    r = _recipe("parmesan", "pasta")
    assert is_compliant(r)  # default: rennet not enforced
    assert not is_compliant(r, DietConfig(enforce_rennet=True))


def test_false_accept_never_happens_for_known_bad_terms():
    bad = ["egg", "chicken broth", "anchovy paste", "gelatin", "impossible meat"]
    for term in bad:
        assert not is_compliant(_recipe(term, "rice")), term
