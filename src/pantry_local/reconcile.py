"""Post-shop reconciliation (design.md Section 8, Section 9 v3).

After a shop, compare what actually arrived (parsed from the receipt) against what
the grocery list expected, then update inventory accordingly. Surfaces:
- ``substitutions``/extras: arrived but not on the list (Instacart loves these),
- ``missing``: on the list but not in the receipt (out of stock / dropped),
- ``received``: matched as expected.

The receipt is ingested through the same v1 path, so inventory is updated as a side
effect; this layer adds the diff against the plan.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .pantry.state import Pantry
from .ingestion.receipt import ingest_receipt, ReceiptResult


@dataclass
class ReconcileResult:
    received: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    substitutions: list[str] = field(default_factory=list)
    receipt: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "received": self.received,
            "missing": self.missing,
            "substitutions": self.substitutions,
            "receipt": self.receipt,
        }


def reconcile(
    pantry: Pantry,
    expected_canonicals: list[str],
    receipt_text: str | None = None,
    receipt_items: list[dict] | None = None,
) -> ReconcileResult:
    res = ingest_receipt(pantry, text=receipt_text, line_items=receipt_items)
    received = {a["canonical"] for a in res.applied}
    expected = set(expected_canonicals)
    return ReconcileResult(
        received=sorted(received & expected),
        missing=sorted(expected - received),
        substitutions=sorted(received - expected),
        receipt=res.to_dict(),
    )


def expected_from_grocery_list(grocery: dict) -> list[str]:
    """Pull the canonical names out of a grocery_list() dict."""
    out = []
    for ch in grocery.get("channels", []):
        for item in ch.get("items", []):
            out.append(item["canonical"])
    return out
