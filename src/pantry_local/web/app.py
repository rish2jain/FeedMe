"""Minimal LAN web view for spouse parity (design.md §7).

Read the plan, swap a meal, log cooked / leftovers from a phone on the LAN.
Run: ``pantry-local-web`` or ``python -m pantry_local.web.app``.
"""

from __future__ import annotations

import html
import json
import logging
import os
from pathlib import Path
from urllib.parse import urlencode

from .. import server as srv
from ..models import PlannedMeal, MealPlan

logger = logging.getLogger(__name__)


def _load_plan() -> MealPlan | None:
    path = Path(os.environ.get("PANTRY_CURRENT_PLAN", srv._REPO_ROOT / "data" / "current_plan.json"))
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        meals_raw = data.get("meals")
        if not isinstance(meals_raw, list):
            raise ValueError(f"meals must be a list, got {type(meals_raw).__name__}")
        return MealPlan(
            week_of=data.get("week_of", ""),
            meals=[PlannedMeal(**m) for m in meals_raw],
            standing_rotations=data.get("standing_rotations", []),
            notes=data.get("notes", []),
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        logger.warning("Failed to load plan from %s: %s", path, exc)
        return None


def _save_plan(plan: MealPlan) -> None:
    path = Path(os.environ.get("PANTRY_CURRENT_PLAN", srv._REPO_ROOT / "data" / "current_plan.json"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan.to_dict(), indent=2))


def _pin_denied():
    from fastapi.responses import HTMLResponse
    return HTMLResponse("<h1>Invalid PIN</h1>", status_code=403)


def create_app():
    try:
        from fastapi import FastAPI, Form
        from fastapi.responses import HTMLResponse, RedirectResponse
    except ImportError as exc:
        raise RuntimeError("FastAPI required; pip install pantry-local[web]") from exc

    app = FastAPI(title="FeedMe", docs_url=None, redoc_url=None)
    pin = os.environ.get("PANTRY_WEB_PIN", "")

    def _check_pin(submitted: str | None) -> bool:
        if not pin:
            return True
        return submitted == pin

    def _pin_field() -> str:
        if not pin:
            return ""
        return f"<input type='hidden' name='pin' value='{html.escape(pin, quote=True)}'/>"

    @app.get("/", response_class=HTMLResponse)
    def home(pin: str | None = None):
        if not _check_pin(pin):
            return _pin_denied()
        plan = _load_plan()
        narrative = ""
        if plan is None:
            raw = srv.plan_week()
            narrative = raw.get("proposal", {}).get("narrative", "")
            plan = MealPlan(
                week_of=raw["week_of"],
                meals=[PlannedMeal(**m) for m in raw["meals"]],
                standing_rotations=raw.get("standing_rotations", []),
                notes=raw.get("notes", []),
            )
            _save_plan(plan)
        else:
            narrative = plan.notes[0] if plan.notes else ""
        pin_qs = f"?{urlencode({'pin': pin})}" if pin else ""
        rows = "".join(
            f"<tr><td>{html.escape(m.day)}</td><td>{html.escape(m.title)}</td>"
            f"<td>{m.total_minutes} min</td>"
            f"<td><form method='post' action='/swap'>"
            f"{_pin_field()}"
            f"<input type='hidden' name='day' value='{html.escape(m.day, quote=True)}'/>"
            f"<input name='recipe_id' placeholder='recipe id'/>"
            f"<button>Swap</button></form></td>"
            f"<td><form method='post' action='/cooked'>"
            f"{_pin_field()}"
            f"<input type='hidden' name='recipe_id' value='{html.escape(m.recipe_id, quote=True)}'/>"
            f"<input name='leftovers' placeholder='portions' size='3'/>"
            f"<button>Cooked</button></form></td></tr>"
            for m in plan.meals
        )
        return f"""<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width'/><title>FeedMe</title></head>
<body><h1>FeedMe — week of {html.escape(plan.week_of)}</h1>
<p>{html.escape(narrative)}</p>
<table border='1' cellpadding='6'><tr><th>Day</th><th>Meal</th><th>Time</th><th>Swap</th><th>Log</th></tr>{rows}</table>
<p><a href='/expiry{pin_qs}'>Expiry report</a></p></body></html>"""

    @app.post("/swap")
    def swap(
        day: str = Form(...),
        recipe_id: str = Form(...),
        pin: str | None = Form(None),
    ):
        if not _check_pin(pin):
            return _pin_denied()
        plan = _load_plan()
        if plan is None:
            return RedirectResponse("/", status_code=303)
        recipe = srv.get_recipe(recipe_id)
        if recipe is None:
            return HTMLResponse(
                f"<p>Unknown recipe {html.escape(recipe_id)}</p><a href='/'>Back</a>"
            )
        for m in plan.meals:
            if m.day == day:
                m.recipe_id = recipe.id
                m.title = recipe.title
                m.total_minutes = recipe.total_minutes
                m.protein_class = recipe.protein_class
                m.cooking_format = recipe.cooking_format
        _save_plan(plan)
        return RedirectResponse("/", status_code=303)

    @app.post("/cooked")
    def cooked(
        recipe_id: str = Form(...),
        leftovers: str = Form(""),
        pin: str | None = Form(None),
    ):
        if not _check_pin(pin):
            return _pin_denied()
        srv.cook_recipe(recipe_id)
        trimmed = leftovers.strip()
        if trimmed:
            try:
                portions = int(trimmed)
            except ValueError:
                return HTMLResponse(
                    f"<p>Invalid leftovers value: {html.escape(trimmed)}</p>"
                    f"<a href='/'>Back</a>",
                    status_code=400,
                )
            if portions < 0:
                return HTMLResponse(
                    "<p>Leftovers must be non-negative</p><a href='/'>Back</a>",
                    status_code=400,
                )
            srv._log_event("cook", {"recipe": recipe_id, "leftovers_portions": portions})
        return RedirectResponse("/", status_code=303)

    @app.get("/expiry", response_class=HTMLResponse)
    def expiry(pin: str | None = None):
        if not _check_pin(pin):
            return _pin_denied()
        report = srv.expiry_report()["report"]
        items = "".join(
            f"<li>{html.escape(r['canonical'])}: "
            f"{html.escape(str(r.get('days_left', '?')))} days "
            f"({html.escape(str(r.get('urgency', '')))})</li>"
            for r in report
        )
        return f"<html><body><h1>Expiry</h1><ul>{items}</ul><a href='/'>Back</a></body></html>"

    return app


def main() -> None:
    import uvicorn
    host = os.environ.get("PANTRY_WEB_HOST", "0.0.0.0")
    port_raw = os.environ.get("PANTRY_WEB_PORT", "8765")
    try:
        port = int(port_raw)
    except ValueError:
        logger.error(
            "Invalid PANTRY_WEB_PORT %r; falling back to default 8765", port_raw
        )
        port = 8765
    uvicorn.run(create_app(), host=host, port=port)


if __name__ == "__main__":
    main()
