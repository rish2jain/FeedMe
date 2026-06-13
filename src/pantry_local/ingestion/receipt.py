"""Receipt ingestion -> pantry deltas (design.md Section 6, item 1; Section 9 v1).

Two input paths, one output:
- ``line_items``: structured list from the VLM (Qwen-VL on the Mac Studio parses a
  receipt image/PDF to JSON). This is the high-fidelity path.
- ``text``: plain receipt text (e.g. an Instacart/ShopRite email body via the Gmail
  connector). Parsed deterministically with a small set of line patterns.

Both map descriptions to canonical ontology items, attach a confidence and
``source="receipt"``, and apply additions to the pantry. Items that don't map to the
ontology are returned as ``unmatched`` for review rather than silently dropped.

The VLM call itself is NOT made here — it's the orchestrator's job (or a passed-in
``vlm_client``), keeping all model inference at the edges.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

from ..ontology import normalize, lookup
from ..pantry.state import Pantry, PantryItem

# Lines like:  "2  Red Lentils 1 kg            $4.99"
#              "Onions  3 lb   2.49"
#              "1 x Paneer 400g  5.49"
_QTY_PREFIX = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(?:x|@)?\s+(.*)$")
_TRAILING_PRICE = re.compile(r"\s*\$?\d+\.\d{2}\s*$")
_EMBEDDED_QTY = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|g|gram|grams|lb|lbs|oz|ml|l|ct|count|pack)\b",
                           re.IGNORECASE)
# Receipt noise lines to skip.
_SKIP = re.compile(r"\b(subtotal|total|tax|tip|change|cash|visa|mastercard|debit|"
                   r"balance|order|receipt|thank you|delivery|service fee|savings)\b",
                   re.IGNORECASE)


@dataclass
class ReceiptLine:
    raw: str
    canonical: str | None
    qty: float | None = None
    unit: str | None = None


@dataclass
class ReceiptResult:
    applied: list[dict] = field(default_factory=list)   # {canonical, qty, unit, confidence}
    unmatched: list[str] = field(default_factory=list)  # descriptions we couldn't map
    skipped: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"applied": self.applied, "unmatched": self.unmatched, "skipped": self.skipped}


def _parse_line(raw: str) -> ReceiptLine | None:
    line = _TRAILING_PRICE.sub("", raw).strip()
    if not line or _SKIP.search(line):
        return None
    qty: float | None = None
    desc = line
    m = _QTY_PREFIX.match(line)
    if m:
        qty = float(m.group(1))
        desc = m.group(2).strip()
    unit: str | None = None
    em = _EMBEDDED_QTY.search(desc)
    if em:
        # Prefer the embedded pack size as qty/unit when no leading count was found.
        embedded_qty = float(em.group(1))
        unit = em.group(2).lower()
        if qty is None:
            qty = embedded_qty
        desc = _EMBEDDED_QTY.sub("", desc).strip()
    canonical = normalize(desc)
    return ReceiptLine(raw=raw.strip(), canonical=canonical, qty=qty, unit=unit)


def parse_receipt_text(text: str) -> list[ReceiptLine]:
    lines = []
    for raw in text.splitlines():
        parsed = _parse_line(raw)
        if parsed is not None:
            lines.append(parsed)
    return lines


def _apply_lines(pantry: Pantry, lines: list[ReceiptLine], confidence: float) -> ReceiptResult:
    result = ReceiptResult()
    for ln in lines:
        if ln.canonical is None:
            result.unmatched.append(ln.raw)
            continue
        existing = pantry.get(ln.canonical)
        # Additions: if the unit matches an existing tracked qty, accumulate;
        # otherwise (re)set to the receipt's quantity. Receipt purchases reset
        # expiry uncertainty, so we don't carry over a stale expiry here.
        new_qty = ln.qty
        if existing and existing.qty is not None and ln.qty is not None and existing.unit == ln.unit:
            new_qty = existing.qty + ln.qty
        pantry.upsert(PantryItem(
            canonical=ln.canonical, qty=new_qty, unit=ln.unit,
            expiry=existing.expiry if existing else None,
            confidence=confidence, source="receipt",
        ))
        result.applied.append({"canonical": ln.canonical, "qty": new_qty,
                               "unit": ln.unit, "confidence": confidence})
    return result


def ingest_receipt(
    pantry: Pantry,
    text: str | None = None,
    line_items: list[dict] | None = None,
    image_path: str | None = None,
    vlm_client: Callable[[str], list[dict]] | None = None,
) -> ReceiptResult:
    """Ingest a receipt into the pantry from one of three sources.

    Priority: explicit ``line_items`` (VLM output) > ``image_path`` + ``vlm_client``
    (runs the injected VLM) > ``text`` (deterministic parse).

    ``line_items`` / VLM output is a list of dicts: ``{"name", "qty"?, "unit"?}``.
    Structured VLM output is trusted at higher confidence than text parsing.
    """
    if line_items is None and image_path is not None and vlm_client is not None:
        line_items = vlm_client(image_path)

    if line_items is not None:
        lines = []
        for it in line_items:
            lines.append(ReceiptLine(
                raw=it.get("name", ""),
                canonical=normalize(it.get("name", "")),
                qty=it.get("qty"),
                unit=it.get("unit"),
            ))
        return _apply_lines(pantry, lines, confidence=0.9)

    if text is not None:
        return _apply_lines(pantry, parse_receipt_text(text), confidence=0.75)

    raise ValueError("ingest_receipt needs one of: line_items, image_path+vlm_client, or text")
