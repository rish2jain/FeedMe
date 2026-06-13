"""Weekly phone scan -> inventory diff (design.md Section 6, item 3; Section 9 v2).

Open fridge, take 3 photos (main, crisper, door), drop into chat. A VLM (Qwen-VL on
the Mac Studio via Ollama) returns structured items with confidence scores; the
low-confidence ones become a few confirm/deny questions. This replaces the entire
fixed-camera subsystem.

The VLM image->JSON call is an injectable seam (``vlm_client``) so no model inference
lives here. High-confidence items are applied immediately; low-confidence items are
held as ``pending_confirmation``. Perishables previously in stock but absent from the
scan are surfaced as ``not_seen`` candidates — NOT auto-removed, because occlusion and
opaque containers make absence unreliable (the design's own accuracy caveat).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ..ontology import normalize, lookup
from ..pantry.state import Pantry, PantryItem

_DEFAULT_THRESHOLD = 0.6


@dataclass
class ScanResult:
    applied: list[dict] = field(default_factory=list)
    pending_confirmation: list[dict] = field(default_factory=list)  # {canonical, qty, unit, confidence, question}
    not_seen: list[str] = field(default_factory=list)  # perishables in stock, absent from scan
    unmatched: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "applied": self.applied,
            "pending_confirmation": self.pending_confirmation,
            "not_seen": self.not_seen,
            "unmatched": self.unmatched,
        }


def ingest_scan(
    pantry: Pantry,
    scan_items: list[dict] | None = None,
    images: list[str] | None = None,
    vlm_client: Callable[[list[str]], list[dict]] | None = None,
    threshold: float = _DEFAULT_THRESHOLD,
    apply: bool = True,
) -> ScanResult:
    """Ingest a fridge scan.

    Provide ``scan_items`` (already-parsed VLM output) or ``images`` + ``vlm_client``
    (runs the injected VLM). Each item is ``{"name", "qty"?, "unit"?, "confidence"?}``.
    """
    if scan_items is None:
        if images is not None and vlm_client is not None:
            scan_items = vlm_client(images)
        else:
            raise ValueError("ingest_scan needs scan_items or images+vlm_client")

    result = ScanResult()
    seen: set[str] = set()
    for it in scan_items:
        canonical = normalize(it.get("name", ""))
        if not canonical:
            result.unmatched.append(it.get("name", ""))
            continue
        conf = float(it.get("confidence", 1.0))
        qty, unit = it.get("qty"), it.get("unit")
        seen.add(canonical)
        if conf >= threshold:
            if apply:
                existing = pantry.get(canonical)
                pantry.upsert(PantryItem(
                    canonical=canonical, qty=qty, unit=unit,
                    expiry=existing.expiry if existing else None,
                    confidence=conf, source="scan",
                ))
            result.applied.append({"canonical": canonical, "qty": qty,
                                   "unit": unit, "confidence": conf})
        else:
            result.pending_confirmation.append({
                "canonical": canonical, "qty": qty, "unit": unit, "confidence": conf,
                "question": f"Is there {canonical} in the fridge?",
            })

    # Perishables we thought we had but the scan didn't surface.
    for item in pantry.items():
        ref = lookup(item.canonical)
        if ref and ref.perishable and item.canonical not in seen \
                and item.canonical not in {p["canonical"] for p in result.pending_confirmation}:
            result.not_seen.append(item.canonical)

    return result


def apply_confirmations(pantry: Pantry, decisions: dict[str, bool],
                        pending: list[dict] | None = None) -> dict:
    """Apply confirm/deny answers. ``decisions`` maps canonical -> present?
    A ``False`` removes the item; a ``True`` keeps/sets it (using ``pending`` qty
    when available)."""
    pend_by_canon = {p["canonical"]: p for p in (pending or [])}
    confirmed, removed = [], []
    for canonical, present in decisions.items():
        if present:
            info = pend_by_canon.get(canonical, {})
            existing = pantry.get(canonical)
            pantry.upsert(PantryItem(
                canonical=canonical, qty=info.get("qty"), unit=info.get("unit"),
                expiry=existing.expiry if existing else None,
                confidence=1.0, source="scan",
            ))
            confirmed.append(canonical)
        else:
            if pantry.remove(canonical):
                removed.append(canonical)
    return {"confirmed": confirmed, "removed": removed}
