"""Curated substitutability knowledge for Indian vegetarian cooking.

Small graph of safe swaps used by the planner and grocery list when an ingredient
is missing. Respects the no-meat-analog rule: paneer↔tofu is allowed; Beyond/
Impossible edges are absent by design.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SubstitutionEdge:
    from_canonical: str
    to_canonical: str
    note: str = ""


# Dal family — interchangeable in most weeknight gravies.
_DAL_EDGES = [
    SubstitutionEdge("masoor dal", "toor dal", "red vs yellow — similar cook time"),
    SubstitutionEdge("toor dal", "masoor dal"),
    SubstitutionEdge("moong dal", "masoor dal", "lighter khichuri/dal"),
    SubstitutionEdge("masoor dal", "moong dal"),
    SubstitutionEdge("chana dal", "toor dal", "split chickpea in tadka dal"),
    SubstitutionEdge("toor dal", "chana dal"),
]

# Protein swaps within household rules.
_PROTEIN_EDGES = [
    SubstitutionEdge("paneer", "tofu", "firm tofu for bhurji/gravy"),
    SubstitutionEdge("tofu", "paneer", "paneer when tofu out"),
]

# Universal binder / tang.
_BINDER_EDGES = [
    SubstitutionEdge("yogurt", "milk", "thin to substitute in marinades — not 1:1"),
    SubstitutionEdge("tomato", "tamarind", "extra tang when tomatoes low"),
]

SUBSTITUTION_GRAPH: list[SubstitutionEdge] = _DAL_EDGES + _PROTEIN_EDGES + _BINDER_EDGES

# Index: canonical -> list of substitutes (first = preferred).
_SUBS: dict[str, list[str]] = {}
for edge in SUBSTITUTION_GRAPH:
    _SUBS.setdefault(edge.from_canonical, []).append(edge.to_canonical)


def substitutes_for(canonical: str) -> list[str]:
    """Return ordered substitute canonicals for a missing ingredient."""
    return list(_SUBS.get(canonical, []))


def resolve_missing(canonical: str, pantry_canonicals: set[str]) -> str | None:
    """If ``canonical`` is missing, return a pantry substitute if one exists."""
    if canonical in pantry_canonicals:
        return canonical
    for sub in substitutes_for(canonical):
        if sub in pantry_canonicals:
            return sub
    return None


def apply_substitutions(
    needed: set[str],
    pantry_canonicals: set[str],
) -> tuple[set[str], list[dict]]:
    """Map needed ingredients through the graph; report swaps applied."""
    resolved: set[str] = set()
    swaps: list[dict] = []
    for c in needed:
        sub = resolve_missing(c, pantry_canonicals)
        if sub is None:
            resolved.add(c)
        elif sub != c:
            resolved.add(sub)
            swaps.append({"needed": c, "used": sub})
        else:
            resolved.add(c)
    return resolved, swaps
