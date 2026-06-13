# FeedMe — `pantry-local`

Local-first pantry intelligence for one specific household: a strict no-egg
vegetarian family of three with a ~17-month-old, an Indian (Bengali) cooking base,
and severe time scarcity. This is the **v0** implementation of the architecture in
[`docs/design.md`](docs/design.md) (*IMGIA, Refined*).

> Implemented: **v0** (constraint engine + curated corpus + planning + list staging)
> and **v1** (receipt ingestion + recipe-decrement — inventory becomes mostly
> self-maintaining). The ChromaDB hybrid-search corpus backend (§1 Stage 3) is also
> built. No camera/VLM image scan yet (that's v2); pantry state is a JSON file and
> the VLM receipt-parse step is an injectable seam.

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

`inventory_get` · `inventory_update` · `inventory_voice_note` · `receipt_ingest` ·
`cook_recipe` · `expiry_report` · `recipe_search` · `recipe_add` · `plan_week` ·
`plan_validate` · `grocery_list` · `instacart_stage`. `inventory_scan` (v2 image
scan) and `reconcile` (v3) are present but return a "deferred to vN" notice.

## Roadmap (design.md §9)

- **v0 ✅:** constraint engine + corpus + planning + list staging.
- **v1 ✅:** receipt ingestion + recipe-decrement (inventory becomes mostly self-maintaining).
- **v2:** weekly phone scan (Qwen-VL on the Mac Studio) + urgency sequencing + calendar.
- **v3:** reconciliation, depletion prediction, daycare-lunch class.
- **v4:** fixed sensing hardware, only on the trigger condition in §6.

## Extending the corpus

The seed corpus (`src/pantry_local/corpus/seed_recipes.py`) ships ~18 recipes; the
v0 target is 50+. The family's own transcribed repertoire is the highest-value data
in the whole system. Every recipe added via `recipe_add` is diet-checked before it
enters the corpus, so the corpus is guaranteed clean.
