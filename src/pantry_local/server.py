"""`pantry-local` MCP server (design.md Section 3).

Exposes the v0 slice of the tool surface to Claude Code / Claude Desktop. Tools that
depend on the VLM sensing layer (inventory_scan, receipt_ingest) or later phases
(reconcile) are present but return an explicit "deferred to vN" notice rather than
faking results — honesty over a fake-complete surface.

Run with:  python -m pantry_local.server   (requires the `mcp` package)
"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

from .pantry.state import Pantry, load_pantry, save_pantry, PantryItem
from .corpus.store import get_default_store, SearchConstraints, has_chroma
from .models import Recipe, MealPlan
from .constraints.diet import DietConfig
from .constraints.toddler import ToddlerProfile
from .planning.planner import plan_week as _plan_week, plan_validate as _plan_validate, PlanConstraints
from .planning.grocery import grocery_list as _grocery_list
from .integrations.instacart import stage_shopping_list
from .ingestion.receipt import ingest_receipt as _ingest_receipt
from .consumption import decrement_for_recipe

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_STATE = _REPO_ROOT / "data" / "pantry_state.json"
_SEED = _REPO_ROOT / "data" / "pantry_seed.json"

# Toddler birthdate: ~17 months old as of the design's reference date.
_TODDLER = ToddlerProfile(birthdate=os.environ.get("TODDLER_BIRTHDATE", "2025-01-15"))

def _build_store():
    """Pick the corpus backend. PANTRY_BACKEND=chroma uses the ChromaDB hybrid
    store (persisted at PANTRY_CHROMA_DIR if set); default is the keyword store."""
    if os.environ.get("PANTRY_BACKEND", "").lower() == "chroma" and has_chroma():
        from .corpus.store import get_chroma_store
        return get_chroma_store(seed=True, persist_dir=os.environ.get("PANTRY_CHROMA_DIR"))
    return get_default_store(seed=True)


_store = _build_store()


def _state_path() -> Path:
    return Path(os.environ.get("PANTRY_STATE", str(_DEFAULT_STATE)))


def _load_pantry() -> Pantry:
    path = _state_path()
    if path.exists():
        return load_pantry(path)
    if _SEED.exists():
        return load_pantry(_SEED)
    return Pantry()


def _save(pantry: Pantry) -> None:
    save_pantry(pantry, _state_path())


# --- Core tool implementations (importable + testable without MCP) -----------

def inventory_get() -> dict:
    return _load_pantry().to_dict()


def inventory_update(canonical: str, qty: float | None = None, unit: str | None = None,
                     expiry: str | None = None, remove: bool = False) -> dict:
    pantry = _load_pantry()
    if remove:
        ok = pantry.remove(canonical)
        _save(pantry)
        return {"removed": ok, "canonical": canonical}
    pantry.upsert(PantryItem(canonical, qty, unit, expiry, confidence=1.0, source="manual"))
    _save(pantry)
    return {"updated": canonical}


def inventory_voice_note(text: str) -> dict:
    """Parse simple 'finished the milk' / 'threw out the palak' deltas."""
    pantry = _load_pantry()
    from .ontology import normalize
    lowered = text.lower()
    removed, unmatched = [], []
    for verb in ("finished", "threw out", "out of", "used up", "no more"):
        if verb in lowered:
            tail = lowered.split(verb, 1)[1]
            c = normalize(tail)
            if c and pantry.remove(c):
                removed.append(c)
            elif c:
                unmatched.append(c)
    _save(pantry)
    return {"removed": removed, "not_in_pantry": unmatched, "note": text}


def expiry_report() -> dict:
    return {"report": _load_pantry().expiry_report()}


def receipt_ingest(text: str | None = None, items_json: str | None = None) -> dict:
    """Ingest a receipt into the pantry (design.md v1).

    Provide ``text`` (plain receipt / email body, parsed deterministically) or
    ``items_json`` (a JSON list of ``{"name","qty"?,"unit"?}`` from the VLM that
    parsed a receipt image on the Mac Studio). Additions are applied immediately.
    """
    pantry = _load_pantry()
    line_items = json.loads(items_json) if items_json else None
    result = _ingest_receipt(pantry, text=text, line_items=line_items)
    _save(pantry)
    return result.to_dict()


def cook_recipe(recipe_id: str, scale: float = 1.0) -> dict:
    """Mark a recipe cooked and decrement its ingredients from the pantry
    (recipe-decrement, design.md v1)."""
    recipe = _store.get(recipe_id)
    if recipe is None:
        return {"error": f"unknown recipe '{recipe_id}'"}
    pantry = _load_pantry()
    result = decrement_for_recipe(pantry, recipe, scale=scale)
    _save(pantry)
    return {"recipe": recipe_id, **result.to_dict()}


def recipe_search(max_total_minutes: int | None = None, cuisine: str | None = None,
                  limit: int = 10) -> dict:
    pantry = _load_pantry()
    c = SearchConstraints(max_total_minutes=max_total_minutes, cuisine=cuisine)
    scored = _store.search(c, pantry=pantry.canonicals(), limit=limit)
    return {"results": [
        {"id": s.recipe.id, "title": s.recipe.title, "score": s.score,
         "total_minutes": s.recipe.total_minutes, "protein_class": s.recipe.protein_class,
         "pantry_matches": s.pantry_matches, "missing": s.missing}
        for s in scored
    ]}


def recipe_add(recipe_json: str) -> dict:
    """Add a recipe (JSON). Diet-compliance-checked before it enters the corpus."""
    recipe = Recipe.from_dict(json.loads(recipe_json))
    violations = _store.add(recipe)
    if violations:
        return {"added": False, "violations": [
            {"category": v.category, "matched": v.matched, "ingredient": v.ingredient}
            for v in violations]}
    return {"added": True, "id": recipe.id}


def plan_week(num_dinners: int = 5, day_time_limits: dict | None = None) -> dict:
    pantry = _load_pantry()
    constraints = PlanConstraints(num_dinners=num_dinners,
                                  day_time_limits=day_time_limits or {})
    plan = _plan_week(_store, pantry, constraints, toddler=_TODDLER)
    return plan.to_dict()


def plan_validate(plan_json: str) -> dict:
    pantry = _load_pantry()
    from .models import PlannedMeal
    data = json.loads(plan_json)
    plan = MealPlan(week_of=data["week_of"],
                    meals=[PlannedMeal(**m) for m in data["meals"]])
    return _plan_validate(plan, _store, pantry, DietConfig(), _TODDLER)


def grocery_list(plan_json: str) -> dict:
    pantry = _load_pantry()
    data = json.loads(plan_json)
    from .models import PlannedMeal
    plan = MealPlan(week_of=data["week_of"],
                    meals=[PlannedMeal(**m) for m in data["meals"]])
    return _grocery_list(plan, _store, pantry).to_dict()


def instacart_stage(grocery_json: str) -> dict:
    """Stage the delivery channel to Instacart (returns payload + URL)."""
    from .planning.grocery import GroceryList, GroceryChannel, GroceryItem
    data = json.loads(grocery_json)
    channels = []
    for ch in data["channels"]:
        items = [GroceryItem(i["canonical"], i["aisle"], i.get("needed_by", []),
                             i.get("patel_preferred", False)) for i in ch["items"]]
        channels.append(GroceryChannel(ch["channel"], ch["label"], ch["card_hint"], items))
    gl = GroceryList(channels=channels, skipped_unknown=data.get("skipped_unknown", []))
    return stage_shopping_list(gl).to_dict()


def _deferred(phase: str) -> dict:
    return {"status": "deferred", "note": f"Sensing/{phase} lands in {phase} (design.md Section 9)."}


# --- MCP wiring --------------------------------------------------------------

def build_server():  # pragma: no cover - requires mcp installed
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("pantry-local")

    mcp.tool()(inventory_get)
    mcp.tool()(inventory_update)
    mcp.tool()(inventory_voice_note)
    mcp.tool()(receipt_ingest)   # v1
    mcp.tool()(cook_recipe)      # v1: recipe-decrement
    mcp.tool()(expiry_report)
    mcp.tool()(recipe_search)
    mcp.tool()(recipe_add)
    mcp.tool()(plan_week)
    mcp.tool()(plan_validate)
    mcp.tool()(grocery_list)
    mcp.tool()(instacart_stage)

    @mcp.tool()
    def inventory_scan(images: list[str]) -> dict:
        """VLM fridge/pantry scan -> inventory diff. Deferred to v2 (Mac Studio Qwen-VL)."""
        return _deferred("v2")

    @mcp.tool()
    def reconcile(data: str) -> dict:
        """Post-shop reconciliation. Deferred to v3."""
        return _deferred("v3")

    return mcp


def main() -> None:  # pragma: no cover
    build_server().run()


if __name__ == "__main__":  # pragma: no cover
    main()
