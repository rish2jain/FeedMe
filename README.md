# FeedMe — `pantry-local`

Local-first pantry intelligence for one specific household: a strict no-egg
vegetarian family of three with a ~17-month-old, an Indian (Bengali) cooking base,
and severe time scarcity. This is the **v0** implementation of the architecture in
[`docs/design.md`](docs/design.md) (*IMGIA, Refined*).

> **All phases v0–v4 implemented** (design.md §9). v0 constraint engine + corpus +
> planning + staging; v1 receipt ingestion + recipe-decrement; v2 weekly phone scan +
> calendar-aware planning + urgency sequencing; v3 reconciliation + depletion
> prediction + mid-week alerts + daycare lunch class; v4 the fixed-sensing decision
> trigger. The ChromaDB hybrid-search corpus backend (§1 Stage 3) is built too.
>
> All model inference (VLM image→JSON, embeddings, calendar/Gmail fetch) is an
> **injectable seam** — the orchestrator wires in the Mac Studio's Qwen-VL / Ollama /
> connectors; no model calls live in this package, keeping it local-first and
> hermetically testable.

## What's here

| Layer | Module | What it does |
|---|---|---|
| Ingredient ontology | `pantry_local.ontology` | Normalizes raw names → canonical items with aisle, perishability, store channel, protein class, nutrition tags |
| **Diet gate (deterministic)** | `pantry_local.constraints.diet` | Stage-2 egg/meat/fish/meat-analog blacklist incl. derivatives. Authoritative — no LLM. Configurable rennet. |
| **Toddler gate (deterministic)** | `pantry_local.constraints.toddler` | Form-based choking-hazard checks, cook-once/plate-twice fork annotation, age-gating from birthdate, daycare nut policy |
| Recipe corpus | `pantry_local.corpus` | Curated local recipes (diet-clean by construction). Keyword backend (default) + **ChromaDB hybrid search (vector + lexical, RRF-fused)**. |
| Inventory | `pantry_local.pantry` | Confidence-aware item store, JSON persistence, urgency-scored expiry report |
| **Receipt ingestion (v1)** | `pantry_local.ingestion.receipt` | Receipt text / email body parsed deterministically, or VLM line-items → pantry deltas. VLM call is an injectable seam. |
| **Recipe-decrement (v1)** | `pantry_local.consumption` | Marking a meal cooked subtracts ingredients (unit-aware); bulk staples negligible, unit mismatches flagged not guessed. |
| **Phone scan (v2)** | `pantry_local.ingestion.scan` | VLM fridge-photo diff: high-confidence applied, low-confidence → confirm/deny, absent perishables flagged (occlusion-safe, never auto-removed). |
| **Calendar (v2)** | `pantry_local.integrations.calendar` | Late-meeting days → short-cook/leftover time ceilings for the planner. |
| **Depletion (v3)** | `pantry_local.depletion` | Run-out prediction from per-item rates (override > history > staple defaults). |
| **Reconciliation (v3)** | `pantry_local.reconcile` | Post-shop diff of receipt vs staged list: received / missing / substitutions. |
| **Mid-week alerts (v3)** | `pantry_local.alerts` | Deduped expiry + depletion + plan-gap nudges (no daily nagging). |
| **Daycare lunches (v3)** | `pantry_local.planning.daycare` | Packable, no-reheat, no-choke, nut-free toddler lunches; dormant until daycare starts. |
| **Hardware trigger (v4)** | `pantry_local.hardware` | Decision rule: recommend fixed sensing only if the weekly scan is skipped 8+ weeks. |
| Event log | `pantry_local.events` | Append-only cook/receipt/scan/plan history feeding depletion + the v4 trigger. |
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
- `PANTRY_EVENTS` — path to the event log JSON (default `data/events.json`).
- `TODDLER_BIRTHDATE` — ISO date used for age-gated toddler rules.
- `DAYCARE_ACTIVE` — `true` activates the packable-lunch class and nut-free policy.
- `PANTRY_BACKEND` — `keyword` (default) or `chroma` for the hybrid corpus backend.
- `PANTRY_CHROMA_DIR` — persist directory for ChromaDB (omit for ephemeral/in-memory).

### Corpus backends

- **Keyword** (default): dependency-free, deterministic pantry-overlap scoring.
- **ChromaDB hybrid** (`pip install '.[chroma]'`): vector + lexical retrieval fused
  with Reciprocal Rank Fusion, then blended with pantry coverage — the §1 Stage-3
  design. Embeddings come from an **injectable** callable; the default
  `hashing_embed` is offline/hermetic (lexical, not semantic). For semantic quality,
  inject a real local embedder (e.g. `nomic-embed` via Ollama on the Mac Studio):

  ```python
  from pantry_local.corpus.store import ChromaRecipeStore
  store = ChromaRecipeStore(embed=my_ollama_embed, persist_dir=".chroma")
  ```

### Tool surface (design.md §3)

19 tools: `inventory_get` · `inventory_update` · `inventory_voice_note` ·
`receipt_ingest` · `cook_recipe` · `inventory_scan` · `scan_confirm` · `reconcile` ·
`depletion_report` · `midweek_alerts` · `daycare_lunches` · `hardware_trigger` ·
`expiry_report` · `recipe_search` · `recipe_add` · `plan_week` (calendar-aware) ·
`plan_validate` · `grocery_list` · `instacart_stage`.

## Roadmap (design.md §9)

- **v0 ✅:** constraint engine + corpus + planning + list staging.
- **v1 ✅:** receipt ingestion + recipe-decrement (inventory becomes mostly self-maintaining).
- **v2 ✅:** weekly phone scan (Qwen-VL seam) + calendar-aware planning + urgency sequencing.
- **v3 ✅:** reconciliation + depletion prediction + mid-week alerts + daycare-lunch class.
- **v4 ✅:** fixed-sensing decision trigger (recommends hardware only when the §6 condition is met).

The remaining work is **not infrastructure** — it's wiring the injectable seams to the
household's actual systems (Qwen-VL via Ollama, a real embedder, Gmail/Calendar
connectors) and growing the recipe corpus with the family's repertoire.

## Extending the corpus

The seed corpus (`src/pantry_local/corpus/seed_recipes.py`) ships ~18 recipes; the
v0 target is 50+. The family's own transcribed repertoire is the highest-value data
in the whole system. Every recipe added via `recipe_add` is diet-checked before it
enters the corpus, so the corpus is guaranteed clean.
