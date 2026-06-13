from pantry_local.corpus.seed_recipes import SEED_RECIPES
from pantry_local.planning import nutrition


def _by_id(*ids):
    m = {r.id: r for r in SEED_RECIPES}
    return [m[i] for i in ids]


def test_dal_rice_attractor_flagged():
    # Four dal-class dinners -> protein monotony advisory.
    recipes = _by_id("masoor-dal", "toor-dal-tadka", "lauki-chana-dal", "khichuri")
    report = nutrition.evaluate(recipes)
    assert any(f.code == "protein_monotony" for f in report.findings)


def test_varied_week_passes_protein_floor():
    recipes = _by_id("matar-paneer", "chana-masala", "rajma", "tofu-bhurji", "palak-tofu")
    report = nutrition.evaluate(recipes)
    assert report.protein_meals == 5
    assert not any(f.code == "protein_floor" for f in report.findings)


def test_iron_c_pairing_counted():
    # palak-tofu has spinach (iron) + ... ; chana has chickpeas (iron) + tomato (C)
    recipes = _by_id("chana-masala", "rajma", "palak-tofu")
    report = nutrition.evaluate(recipes)
    assert report.iron_c_meals >= 1
