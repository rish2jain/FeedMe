# FeedMe — `pantry-local`

Local-first pantry intelligence for one specific household: a strict no-egg
vegetarian family of three with a ~17-month-old, an Indian (Bengali) cooking base,
and severe time scarcity. This is the **v0** implementation of the architecture in
[`docs/design.md`](docs/design.md) (*IMGIA, Refined*).

> v0 scope (design.md §9): **constraint engine + curated corpus + planning + list
> staging.** No camera/VLM sensing yet — pantry state is a seeded JSON file. The
> point of v0 is to validate the only genuinely uncertain hypothesis: *are the meal
> plans good enough that the family follows them?*

## What's here

| Layer | Module | What it does |
|---|---|---|
| Ingredient ontology | `pantry_local.ontology` | Normalizes raw names → canonical items with aisle, perishability, store channel, protein class, nutrition tags |
| **Diet gate (deterministic)** | `pantry_local.constraints.diet` | Stage-2 egg/meat/fish/meat-analog blacklist incl. derivatives. Authoritative — no LLM. Configurable rennet. |
| **Toddler gate (deterministic)** | `pantry_local.constraints.toddler` | Form-based choking-hazard checks, cook-once/plate-twice fork annotation, age-gating from birthdate, daycare nut policy |
| Recipe corpus | `pantry_local.corpus` | Curated local recipes (diet-clean by construction) + pantry-overlap retrieval. ChromaDB backend is the production swap-in. |
| Inventory | `pantry_local.pantry` | Confidence-aware item store, JSON persistence, urgency-scored expiry report |
| Planner | `pantry_local.planning.planner` | ~5 dinners with use-first sequencing, variety, calendar time-ceilings, toddler fork, leftover network |
| Nutrition evaluator | `pantry_local.planning.nutrition` | Dal-rice attractor, iron+C same-meal pairing, protein floor, B12/D watch (advisory) |
| Grocery | `pantry_local.planning.grocery` | List net of pantry, grouped by store channel (Patel/ShopRite/Costco) + aisle, credit-card hints |
| Instacart staging | `pantry_local.integrations.instacart` | Builds the `create-shopping-list` payload; human-review purchase gate |
| MCP server | `pantry_local.server` | Exposes the tool surface to Claude Code / Claude Desktop |

The two safety gates (diet, toddler) are **plain Python and never call an LLM** —
per the design, compliance is adjudicated deterministically; the LLM only matches
and sequences.

## Quickstart

```bash
# Run the tests (no install needed; tests put src/ on the path)
python -m pytest

# Try the pipeline directly
PYTHONPATH=src python -c "
from pantry_local import server as s
import json
plan = s.plan_week(num_dinners=5)
for m in plan['meals']:
    print(m['day'], m['title'], m['toddler_plan'][:60])
gl = s.grocery_list(json.dumps(plan))
print(s.instacart_stage(json.dumps(gl))['url'])
"
```

## Running as an MCP server

```bash
pip install -e ".[mcp]"
pantry-local            # stdio MCP server named "pantry-local"
```

Register with Claude Desktop / Claude Code (`mcp` config):

```json
{
  "mcpServers": {
    "pantry-local": { "command": "pantry-local" }
  }
}
```

Environment:
- `PANTRY_STATE` — path to the runtime inventory JSON (default `data/pantry_state.json`,
  falls back to `data/pantry_seed.json`).
- `TODDLER_BIRTHDATE` — ISO date used for age-gated toddler rules.

### Tool surface (design.md §3)

`inventory_get` · `inventory_update` · `inventory_voice_note` · `expiry_report` ·
`recipe_search` · `recipe_add` · `plan_week` · `plan_validate` · `grocery_list` ·
`instacart_stage`. Sensing tools (`inventory_scan`, `receipt_ingest`, `reconcile`)
are present but return a "deferred to vN" notice — they belong to later phases.

## Roadmap (design.md §9)

- **v0 (this):** constraint engine + corpus + planning + list staging.
- **v1:** receipt ingestion + recipe-decrement (inventory becomes self-maintaining).
- **v2:** weekly phone scan (Qwen-VL on the Mac Studio) + urgency sequencing + calendar.
- **v3:** reconciliation, depletion prediction, daycare-lunch class.
- **v4:** fixed sensing hardware, only on the trigger condition in §6.

## Extending the corpus

The seed corpus (`src/pantry_local/corpus/seed_recipes.py`) ships ~18 recipes; the
v0 target is 50+. The family's own transcribed repertoire is the highest-value data
in the whole system. Every recipe added via `recipe_add` is diet-checked before it
enters the corpus, so the corpus is guaranteed clean.
