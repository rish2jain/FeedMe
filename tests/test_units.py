from pantry_local.units import convert, unit_dimension


def test_mass_conversion():
    assert convert(1, "kg", "g") == 1000
    assert convert(500, "g", "kg") == 0.5


def test_volume_conversion():
    assert convert(1, "cup", "ml") == 240
    assert convert(3, "tsp", "tbsp") == 1


def test_count_passthrough():
    assert convert(2, "whole", "medium") == 2
    assert convert(3, None, None) == 3


def test_cross_dimension_is_none():
    assert convert(1, "cup", "g") is None
    assert convert(1, "kg", "tbsp") is None


def test_unknown_unit_is_none():
    assert convert(1, "smidgen", "g") is None


def test_unit_dimension():
    assert unit_dimension("tbsp") == "volume"
    assert unit_dimension("kg") == "mass"
    assert unit_dimension("whole") == "count"
    assert unit_dimension("nonsense") is None
