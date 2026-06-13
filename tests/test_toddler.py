from pantry_local.models import Recipe, RecipeIngredient as RI, FORMAT_ONE_POT, FORMAT_GRAVY
from pantry_local.constraints.toddler import (
    assess, check_hazards, ToddlerProfile, contains_nuts,
)


def test_whole_grapes_flagged_quartered_safe():
    bad = Recipe(id="g1", title="Fruit", ingredients=[RI("grapes", form="whole")])
    good = Recipe(id="g2", title="Fruit", ingredients=[RI("grapes", form="quartered")])
    assert check_hazards(bad)
    assert not check_hazards(good)


def test_large_paneer_cube_flagged():
    r = Recipe(id="p", title="Paneer", ingredients=[RI("paneer", form="cubed")])
    hz = check_hazards(r)
    assert hz and "paneer" in hz[0].ingredient.lower()
    # thin strips are remediated
    r2 = Recipe(id="p2", title="Paneer", ingredients=[RI("paneer", form="thin strips")])
    assert not check_hazards(r2)


def test_one_pot_is_adult_only():
    r = Recipe(id="k", title="Khichuri", cooking_format=FORMAT_ONE_POT,
               ingredients=[RI("moong dal")])
    a = assess(r)
    assert a.adult_only


def test_fork_step_yields_instruction():
    r = Recipe(id="d", title="Dal", cooking_format=FORMAT_GRAVY,
               steps=["boil dal", "pull toddler portion", "add tadka"],
               toddler_fork_step=1, ingredients=[RI("masoor dal")])
    a = assess(r)
    assert not a.adult_only
    assert "step 2" in a.fork_instruction


def test_daycare_nut_exclusion():
    r = Recipe(id="n", title="Pulao", ingredients=[RI("cashews", form="paste")])
    assert contains_nuts(r)
    a_home = assess(r, ToddlerProfile(birthdate="2025-01-15", daycare_active=False))
    a_daycare = assess(r, ToddlerProfile(birthdate="2025-01-15", daycare_active=True))
    assert not a_home.daycare_excluded
    assert a_daycare.daycare_excluded


def test_age_months_and_notes():
    p = ToddlerProfile(birthdate="2025-01-15")
    from datetime import date
    assert p.age_months(date(2026, 6, 15)) == 17
    a = assess(Recipe(id="x", title="x", ingredients=[RI("rice")]), p,
               today=date(2026, 6, 15))
    assert a.age_notes and "17mo" in a.age_notes[0]
