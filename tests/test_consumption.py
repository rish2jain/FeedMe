from pantry_local.models import Recipe, RecipeIngredient as RI
from pantry_local.pantry.state import Pantry, PantryItem
from pantry_local.consumption import decrement_for_recipe


def test_count_decrement_and_depletion():
    pantry = Pantry([PantryItem("tomato", qty=3, unit="whole"),
                     PantryItem("onion", qty=1, unit="whole")])
    recipe = Recipe(id="r", title="Curry", ingredients=[
        RI("tomato", 2, "medium"),  # count<->count
        RI("onion", 1, "medium"),   # depletes fully
    ])
    res = decrement_for_recipe(pantry, recipe)
    assert pantry.get("tomato").qty == 1
    assert "onion" in res.depleted
    assert not pantry.has("onion")


def test_mass_conversion_decrement():
    pantry = Pantry([PantryItem("paneer", qty=0.4, unit="kg")])
    recipe = Recipe(id="r", title="Bhurji",
                    ingredients=[RI("paneer", 250, "g")])
    res = decrement_for_recipe(pantry, recipe)
    item = pantry.get("paneer")
    assert item is not None
    assert abs(item.qty - 0.15) < 1e-6


def test_spices_are_negligible():
    pantry = Pantry([PantryItem("turmeric", qty=1, unit="jar")])
    recipe = Recipe(id="r", title="x", ingredients=[RI("turmeric", 0.5, "tsp")])
    res = decrement_for_recipe(pantry, recipe)
    assert "turmeric" in res.negligible
    assert pantry.get("turmeric").qty == 1  # untouched


def test_unit_mismatch_flagged_not_guessed():
    pantry = Pantry([PantryItem("masoor dal", qty=1, unit="kg")])
    recipe = Recipe(id="r", title="Dal", ingredients=[RI("masoor dal", 1, "cup")])
    res = decrement_for_recipe(pantry, recipe)
    assert any(f["canonical"] == "masoor dal" for f in res.flagged_manual)
    assert pantry.get("masoor dal").qty == 1  # not corrupted


def test_not_in_pantry_reported():
    pantry = Pantry()
    recipe = Recipe(id="r", title="x", ingredients=[RI("tomato", 2, "medium")])
    res = decrement_for_recipe(pantry, recipe)
    assert "tomato" in res.not_in_pantry
