"""`pantry-local` MCP server (design.md Section 3).

Exposes the full tool surface to Claude Code / Claude Desktop. Integration clients
(Ollama VLM/embedder, Gmail, Google Calendar, Instacart MCP) activate via env vars
through ``integrations.wiring``; without them the server stays hermetic.

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
from .planning.planner import (
    plan_week as _plan_week,
    plan_validate as _plan_validate,
    plan_proposal_summary,
    PlanConstraints,
)
from .planning.grocery import grocery_list as _grocery_list
from .integrations.instacart import stage_shopping_list
from .ingestion.receipt import ingest_receipt as _ingest_receipt
from .ingestion.scan import ingest_scan as _ingest_scan, apply_confirmations as _apply_confirmations
from .consumption import decrement_for_recipe
from .integrations.calendar import derive_time_limits, CalEvent, time_limits_from_client
from .integrations.wiring import build_clients_from_env, chroma_backend_requested, IntegrationClients
from .reconcile import reconcile as _reconcile
from .alerts import midweek_alerts as _midweek_alerts
from .planning.daycare import build_daycare_lunches
from . import depletion as _depletion
from . import hardware as _hardware
from .events import (
    EventLog, load_events, save_events,
    KIND_COOK, KIND_RECEIPT, KIND_SCAN, KIND_PLAN, KIND_PLAN_SESSION,
    plan_session_status,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_STATE = _REPO_ROOT / "data" / "pantry_state.json"
_SEED = _REPO_ROOT / "data" / "pantry_seed.json"

_DEFAULT_EVENTS = _REPO_ROOT / "data" / "events.json"

# Toddler birthdate: ~17 months old as of the design's reference date.
_TODDLER = ToddlerProfile(
    birthdate=os.environ.get("TODDLER_BIRTHDATE", "2025-01-15"),
    daycare_active=os.environ.get("DAYCARE_ACTIVE", "").lower() in {"1", "true", "yes"},
)

def _build_store(clients: IntegrationClients | None = None):
    """Pick the corpus backend. Uses Chroma when PANTRY_BACKEND=chroma or when an
    Ollama embedder is configured; injects the embed fn when available."""
    clients = clients or _CLIENTS
    use_chroma = chroma_backend_requested(clients) and has_chroma()
    if use_chroma:
        from .corpus.store import get_chroma_store
        persist = os.environ.get("PANTRY_CHROMA_DIR") or str(_REPO_ROOT / "data" / "chroma")
        kwargs: dict = {"seed": True, "persist_dir": persist}
        if clients.embed is not None:
            kwargs["embed"] = clients.embed
        return get_chroma_store(**kwargs)
    return get_default_store(seed=True)


_CLIENTS = build_clients_from_env()
_store = _build_store(_CLIENTS)


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


def _events_path() -> Path:
    return Path(os.environ.get("PANTRY_EVENTS", str(_DEFAULT_EVENTS)))


def _log_event(kind: str, data: dict) -> None:
    path = _events_path()
    log = load_events(path)
    log.append(kind, data)
    save_events(log, path)


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


def receipt_ingest(text: str | None = None, items_json: str | None = None,
                   image_path: str | None = None) -> dict:
    """Ingest a receipt into the pantry (design.md v1).

    Provide ``text`` (plain receipt / email body, parsed deterministically),
    ``items_json`` (VLM-parsed line items), or ``image_path`` (requires Ollama VLM
    via ``OLLAMA_VLM_MODEL``). Additions are applied immediately.
    """
    pantry = _load_pantry()
    line_items = json.loads(items_json) if items_json else None
    if image_path and line_items is None and not _CLIENTS.receipt_vlm:
        return {
            "error": (
                "VLM client not configured for image receipt ingest "
                "(set OLLAMA_VLM_MODEL)"
            ),
        }
    vlm = _CLIENTS.receipt_vlm if image_path and line_items is None else None
    result = _ingest_receipt(
        pantry, text=text, line_items=line_items,
        image_path=image_path, vlm_client=vlm,
    )
    _save(pantry)
    _log_event(KIND_RECEIPT, result.to_dict())
    return result.to_dict()


def receipt_fetch_gmail(since_query: str | None = None, ingest: bool = True) -> dict:
    """Fetch Instacart/ShopRite receipt emails via Gmail and optionally ingest them."""
    if _CLIENTS.gmail_fetch is None:
        return {"error": "Gmail not configured (set GMAIL_CREDENTIALS or GMAIL_TOKEN)"}
    emails = _CLIENTS.gmail_fetch(since_query)
    results = []
    if ingest:
        pantry = _load_pantry()
        for em in emails:
            result = _ingest_receipt(pantry, text=em["body"])
            results.append({"email_id": em["id"], "subject": em["subject"], **result.to_dict()})
        _save(pantry)
        _log_event(KIND_RECEIPT, {"gmail_batch": len(results)})
    return {"emails": len(emails), "ingested": results if ingest else emails}


def get_recipe(recipe_id: str) -> Recipe | None:
    """Look up a recipe by id from the corpus store."""
    return _store.get(recipe_id)


def cook_recipe(recipe_id: str, scale: float = 1.0) -> dict:
    """Mark a recipe cooked and decrement its ingredients from the pantry
    (recipe-decrement, design.md v1)."""
    recipe = get_recipe(recipe_id)
    if recipe is None:
        return {"error": f"unknown recipe '{recipe_id}'"}
    pantry = _load_pantry()
    result = decrement_for_recipe(pantry, recipe, scale=scale)
    _save(pantry)
    payload = {"recipe": recipe_id, **result.to_dict()}
    _log_event(KIND_COOK, payload)
    return payload


def inventory_scan(items_json: str | None = None, images_json: str | None = None) -> dict:
    """Weekly phone scan -> inventory diff (design.md v2).

    Pass ``items_json`` (pre-parsed VLM output) or ``images_json`` (JSON list of
    image paths; requires ``OLLAMA_VLM_MODEL``).
    """
    pantry = _load_pantry()
    images = json.loads(images_json) if images_json else None
    scan_items = json.loads(items_json) if items_json else ([] if not images else None)
    vlm = _CLIENTS.scan_vlm if images and scan_items is None else None
    result = _ingest_scan(
        pantry, scan_items=scan_items, images=images, vlm_client=vlm,
    )
    _save(pantry)
    _log_event(KIND_SCAN, {"applied": result.applied,
                           "pending": len(result.pending_confirmation)})
    return result.to_dict()


def scan_confirm(decisions_json: str, pending_json: str | None = None) -> dict:
    """Apply confirm/deny answers from a scan (design.md v2).

    ``decisions_json``: JSON object mapping canonical -> bool (present?).
    """
    pantry = _load_pantry()
    decisions = json.loads(decisions_json)
    pending = json.loads(pending_json) if pending_json else None
    out = _apply_confirmations(pantry, decisions, pending)
    _save(pantry)
    return out


def reconcile(expected_canonicals: list[str], receipt_text: str | None = None,
              receipt_items_json: str | None = None) -> dict:
    """Post-shop reconciliation vs the staged list (design.md v3)."""
    pantry = _load_pantry()
    items = json.loads(receipt_items_json) if receipt_items_json else None
    result = _reconcile(pantry, expected_canonicals, receipt_text=receipt_text,
                        receipt_items=items)
    _save(pantry)
    return result.to_dict()


def depletion_report() -> dict:
    """Predicted run-out dates for tracked staples (design.md v3)."""
    pantry = _load_pantry()
    log = load_events(_events_path())
    preds = _depletion.predict(pantry, log=log)
    return {"predictions": [p.to_dict() for p in preds]}


def midweek_alerts(plan_json: str | None = None, days_to_next_shop: int = 4) -> dict:
    """Mid-week actionable alerts (design.md v3)."""
    pantry = _load_pantry()
    log = load_events(_events_path())
    plan = None
    if plan_json:
        from .models import PlannedMeal
        data = json.loads(plan_json)
        plan = MealPlan(week_of=data["week_of"],
                        meals=[PlannedMeal(**m) for m in data["meals"]])
    alerts = _midweek_alerts(pantry, plan=plan, store=_store,
                             days_to_next_shop=days_to_next_shop, log=log)
    return {"alerts": [a.to_dict() for a in alerts]}


def daycare_lunches(num_days: int = 5) -> dict:
    """Packable nut-free toddler lunches (design.md v3). Dormant until daycare."""
    return build_daycare_lunches(_store, _TODDLER, num_days=num_days).to_dict()


def hardware_trigger() -> dict:
    """Evaluate the fixed-sensing revisit trigger from scan history (design.md v4)."""
    log = load_events(_events_path())
    return _hardware.evaluate(log).to_dict()


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


def plan_week(num_dinners: int = 5, day_time_limits: dict | None = None,
              calendar_json: str | None = None, use_calendar: bool = True) -> dict:
    """Plan the week's dinners (design.md v0/v2).

    ``calendar_json``: explicit events; when omitted and ``use_calendar`` is true,
    fetches from Google Calendar if configured. Explicit ``day_time_limits`` win.
    """
    pantry = _load_pantry()
    limits = dict(day_time_limits or {})
    days = ["Sun", "Mon", "Tue", "Wed", "Thu"][:num_dinners]
    if calendar_json:
        try:
            raw_events = json.loads(calendar_json)
        except json.JSONDecodeError as exc:
            return {"error": f"Invalid calendar_json: {exc}"}
        if not isinstance(raw_events, list):
            return {"error": f"calendar_json must be a list, got {type(raw_events).__name__}"}
        events: list[CalEvent] = []
        for i, e in enumerate(raw_events):
            if not isinstance(e, dict):
                return {"error": f"calendar event {i} must be an object, got {e!r}"}
            if "day" not in e or "end_hour" not in e:
                return {
                    "error": (
                        f"calendar event {i} missing required keys "
                        f"'day' and 'end_hour': {e!r} in {calendar_json!r}"
                    ),
                }
            try:
                events.append(CalEvent(day=e["day"], end_hour=float(e["end_hour"])))
            except (TypeError, ValueError) as exc:
                return {
                    "error": (
                        f"calendar event {i} has invalid end_hour: {e!r} "
                        f"({exc}) in {calendar_json!r}"
                    ),
                }
        derived = derive_time_limits(events)
        derived.update(limits)
        limits = derived
    elif use_calendar and _CLIENTS.calendar is not None:
        derived = time_limits_from_client(days, _CLIENTS.calendar)
        derived.update(limits)
        limits = derived
    constraints = PlanConstraints(num_dinners=num_dinners, day_time_limits=limits)
    plan = _plan_week(_store, pantry, constraints, toddler=_TODDLER)
    _log_event(KIND_PLAN, {"week_of": plan.week_of,
                           "meals": [m.recipe_id for m in plan.meals]})
    out = plan.to_dict()
    out["proposal"] = plan_proposal_summary(plan, pantry)
    return out


def plan_session_complete(notes: str | None = None) -> dict:
    """Record that the weekly planning session finished (kill-criterion tracking)."""
    _log_event(KIND_PLAN_SESSION, {"completed": True, "notes": notes or ""})
    return {"logged": True}


def plan_session_status_report() -> dict:
    """Weeks since last planning session; surfaces design §9 kill criterion."""
    log = load_events(_events_path())
    return plan_session_status(log)


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
    return stage_shopping_list(gl, mcp_client=_CLIENTS.instacart_mcp).to_dict()


# --- MCP wiring --------------------------------------------------------------

def build_server():  # pragma: no cover - requires mcp installed
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("pantry-local")

    for tool in (
        inventory_get, inventory_update, inventory_voice_note,
        receipt_ingest, receipt_fetch_gmail, cook_recipe,                 # v1
        inventory_scan, scan_confirm,                # v2
        reconcile, depletion_report, midweek_alerts, daycare_lunches,  # v3
        hardware_trigger,                            # v4
        expiry_report, recipe_search, recipe_add,
        plan_week, plan_validate, plan_session_complete, plan_session_status_report,
        grocery_list, instacart_stage,
    ):
        mcp.tool()(tool)

    return mcp


def main() -> None:  # pragma: no cover
    build_server().run()


if __name__ == "__main__":  # pragma: no cover
    main()
