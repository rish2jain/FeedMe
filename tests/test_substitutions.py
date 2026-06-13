"""Tests for substitutability knowledge graph."""

from pantry_local.knowledge.substitutions import (
    substitutes_for,
    resolve_missing,
    apply_substitutions,
)


def test_masoor_subs_to_toor():
    assert "toor dal" in substitutes_for("masoor dal")


def test_resolve_missing_with_substitute():
    assert resolve_missing("masoor dal", {"toor dal"}) == "toor dal"


def test_apply_substitutions_reports_swap():
    resolved, swaps = apply_substitutions({"masoor dal"}, {"toor dal"})
    assert "toor dal" in resolved
    assert "masoor dal" not in resolved
    assert swaps[0]["needed"] == "masoor dal"
