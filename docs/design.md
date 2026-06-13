# IMGIA, Refined: Pantry Intelligence for One Specific Household

A revision of the Integrated Meal and Grocery Intelligence Agent, re-architected around the actual constraints of this household: a strict no-egg vegetarian family of three in a Jersey City single-family house, with a ~17-month-old daughter, an Indian (Bengali) culinary base, a Mac Studio M3 Ultra available as an always-on local compute hub, an existing MCP-server development pattern, and severe time scarcity (full-time consulting + active litigation + job search + toddler).

The original design is generic. Genericity is its main flaw. Below, each refinement states what changes, why, and what it kills from the original.

---

## 1. The Hard Constraint Layer Comes First, Not the Camera

The original design treats dietary preference as one input among many to the Meal Generation Worker. For this household it is the single most architecturally consequential fact, because the constraint profile is unusual in a way that breaks every off-the-shelf recipe system:

- **Strict vegetarian, no eggs.** Most Western recipe databases tag "vegetarian" as lacto-ovo. A naive `diet=vegetarian` filter will happily return frittatas, French toast, fresh egg pasta, mayonnaise-based dressings, and baked goods. This is a hard-fail, not a preference miss.
- **No meat substitutes.** Beyond, Impossible, "plant-based chick'n," and similar products are excluded. This kills a large fraction of the modern "vegetarian" recipe corpus, which leans heavily on substitutes.
- **Indian home cooking as the default register.** Dal, sabzi, rice, roti, paneer, khichuri — the actual weekly baseline. Western APIs (Spoonacular ~365K recipes, Edamam ~2M aggregated) are thin and frequently wrong on Indian home cooking: wrong proportions, anglicized techniques, "curry powder" where a tadka belongs.

### Design consequence: a two-stage deterministic filter + a curated local corpus

**Stage 1 — API-level filtering (coarse).** Where external recipe APIs are used at all, combine filters rather than trusting one: Spoonacular supports `diet=lacto vegetarian` plus `intolerances=egg`; Edamam supports `health=vegetarian` + `health=egg-free`. Use both flags simultaneously. This is necessary but not sufficient.

**Stage 2 — Deterministic ingredient blacklist (authoritative).** A hand-maintained exclusion list checked against the parsed ingredient list of every candidate recipe, exactly like the allergy check in the original Coherence Evaluator, but promoted to the front of the pipeline. The list must include derivatives, because that's where databases fail:

```
eggs, egg whites/yolks, albumin/albumen, lysozyme, meringue,
mayonnaise, aioli, hollandaise, fresh egg pasta, egg noodles,
most store-bought brioche/challah/cakes,
gelatin (animal), rennet-set cheeses (flag, configurable),
fish sauce, oyster sauce, Worcestershire (anchovy), dashi,
Beyond/Impossible/seitan-meat-analog products, "plant-based [meat]"
```

Any recipe failing Stage 2 is discarded before the LLM ever sees it. The LLM's job is matching and sequencing, never adjudicating dietary compliance. (Rennet is included as a flag because "vegetarian" Parmesan mostly isn't; whether to enforce it is a one-line config decision.)

**Stage 3 — The curated local corpus is the real recipe database.** This is the most important change to the original. Build a household recipe corpus (target: 150–400 recipes) in ChromaDB with embeddings — the identical hybrid-search + RRF-fusion architecture already running in legal-rag-local. Sources: the family's own repertoire (transcribed once, the highest-value data in the whole system), curated Indian vegetarian sites/books, and a filtered slice of Western vegetarian recipes that pass Stage 2. Each recipe gets structured metadata: prep time, active time, cuisine, toddler-adaptability flag, leftover-yield, ingredient list normalized to the pantry ontology.

The original document's principle — select from a validated database, don't hallucinate recipes — is correct, but for this household "validated" means *validated against this family's actual constraints and palate*, which no external API provides. The external APIs become a discovery feed for candidate recipes to add to the corpus, not the runtime source of truth.

---

## 2. The Toddler Sub-Agent (Missing Entirely from the Original)

A 17-month-old changes meal planning more than any other single variable, and the original design has no concept of it. Add a fourth generation concern — not a fourth meal slot, but a **modifier that runs against every dinner candidate**:

**Cook once, plate twice.** Every dinner candidate gets a `toddler_fork` annotation: the point in the recipe where a toddler portion is separated *before* salt, chili, or whole spices go in. Indian cooking is unusually well-suited to this — pull dal before the tadka, set aside rice and vegetables before the masala stage. Recipes with no clean fork point (one-pot dishes where heat is integral) get flagged as "adult-only night, toddler needs a parallel item."

**Hard toddler safety checks (deterministic, like the egg blacklist):** choking-hazard forms — whole grapes/cherry tomatoes (quarter them), whole nuts and nut chunks (paste/powder only), raw hard vegetables, popcorn, large paneer cubes (crumble or thin strips). The check operates on ingredient *form*, not ingredient identity — grapes are fine quartered.

**Vegetarian-toddler nutrition is a real gap to engineer for, not a generic "balance check."** No eggs removes the easiest toddler protein + choline + B12 vehicle. The Nutrition Evaluator (Section 5) must track, weekly: iron (legumes + vitamin-C pairing at the same meal for absorption), zinc, B12 (dairy covers partially; the evaluator should surface when weekly dairy is low rather than assume supplementation), protein density per toddler-sized portion (dal water content matters — thick dal vs. thin dal is a nutritional difference at toddler volumes), and vitamin D.

**Daycare horizon.** Given the active daycare search, build the "packable toddler lunch" meal class now: no-reheat, no-choke, nut-policy-compliant (most NJ daycares are nut-free — almond/peanut in any form gets a daycare-exclusion flag). This class is dormant until daycare starts, then becomes a daily slot.

This sub-agent also needs a **time dimension the original lacks**: toddler constraints change quarterly. The profile should carry a birthdate and age-gated rules (texture progression, salt tolerance, portion sizes) rather than a static rule set.

---

## 3. Compute: The Mac Studio Is the Home Hub. Zero Per-Token Cost.

The original hand-waves "on-device or home hub" processing. This household already owns the hub: the Mac Studio M3 Ultra with 96GB RAM, already running Ollama. The entire system runs locally:

| Function | Runs on | Model/Stack |
|---|---|---|
| Fridge/pantry image → structured inventory JSON | Mac Studio | Qwen3-VL (or Qwen2.5-VL 32B/72B-class) via Ollama — these models do bounding boxes and stable JSON output natively, which is exactly the item-identification task |
| Receipt parsing (image/PDF → line items) | Mac Studio | Same VLM; receipt OCR-to-JSON is a demonstrated strength of the Qwen-VL line |
| Recipe embedding + hybrid search | Mac Studio | ChromaDB + the legal-rag-local retrieval stack, reused |
| Weekly planning reasoning (orchestration, sequencing, substitutions) | Claude via existing Max subscription / Claude Code | No marginal API cost under current usage pattern |
| Deterministic checks (diet, toddler safety, coverage, quantity) | Plain Python | No model at all — these must never be probabilistic |

This resolves the original's privacy section by construction: no food images leave the house, no cloud inventory, nothing to disable. It also matches the household's stated economics — existing subscriptions plus local inference, no per-token spend.

**Package it as an MCP server (`pantry-local`).** This is the structurally correct move given the existing development pattern: legal-rag-local already proves the template (local ChromaDB, ~90 tools, hybrid search, MCP exposure to Claude Code/Claude Desktop). The pantry system is a second instance of the same architecture with a different domain. Plausible initial tool surface (~15 tools, not 90):

```
inventory_scan(images[]) → structured items + confidence
inventory_get / inventory_update / inventory_voice_note(text)
receipt_ingest(image|pdf) → pantry deltas
expiry_report() → urgency-scored list
recipe_search(constraints, pantry_filter) → ranked candidates
recipe_add(url|text) → parsed, compliance-checked, embedded
plan_week(constraints) → meal plan draft
plan_validate(plan) → coverage/quantity/diet/toddler checks
grocery_list(plan) → list net of pantry, by category
instacart_stage(list) → shopping-list URL (see Section 4)
reconcile(receipt|edits) → inventory + plan updates
```

A bonus this framing buys for free: the project itself is portfolio-grade evidence for the solutions-architect lane — a local-first, multi-model, MCP-native consumer agent with deterministic safety rails is a better demonstration artifact than another coding tool.

---

## 4. Grocery Execution: Delivery-First, and the Multi-Store Routing Logic Gets Inverted

The original's Budget and Store Intelligence Worker optimizes a problem this household shouldn't be solving. With the current time load, the binding constraint is hours, not dollars. Driving to a second store to save $23 is a loss at any plausible valuation of a consultant-parent's Saturday. The original even computes this tradeoff — the refinement is to admit the answer is almost always "no" and design around it.

**The store graph for this household is actually three nodes with very different cadences:**

1. **Indian grocery (Patel Brothers / the Journal Square–area stores), ~monthly, in person.** Dals, rice, atta, whole spices, ghee, frozen items, fresh curry leaves/methi/specialty produce. These items are (a) unavailable or 3x the price on mainstream delivery, (b) overwhelmingly shelf-stable, so a monthly bulk cadence works, and (c) the one trip where physical presence has real selection value. The agent's job: maintain a rolling "Indian store list" that accumulates between trips, triggered by receipt-parse depletion, and surface it when a trip happens.
2. **Weekly perishables + mainstream staples: delivery by default.** Instacart now ships a **Developer Platform with an MCP server exposing `create-shopping-list` and `create-recipe` tools** — the agent generates the week's list, stages it as an Instacart shopping-list page mapped to real products at the chosen retailer (ShopRite et al. in Jersey City), and a human taps through store selection and checkout. This is the original's "agent prepares, human executes" purchase gate, except the integration already exists as a first-class MCP tool rather than something to build. The `pantry-local` server calls Instacart's MCP server directly.
3. **Costco, opportunistic.** Bulk dairy, paneer-adjacent staples, produce when a trip is happening anyway. The agent appends a Costco sublist to whatever trip is already planned; it never *generates* a Costco trip.

**What gets deleted from the original:** weekly circular scraping, unit-price normalization across stores, and the time-vs-savings routing optimizer. These are the most engineering-expensive components in the original's grocery layer and the lowest-value for a household where decision fatigue, not grocery spend, is the cost being minimized. Keep one vestige: a "restock at Patel's, not ShopRite" tag on items where the price/quality gap is categorical (spices, dals, ghee) rather than marginal.

**One addition the original misses:** credit-card routing. The household runs a points-optimized card portfolio; the grocery list output should carry a one-line card recommendation per channel (e.g., the best US grocery multiplier card in the wallet for ShopRite/Instacart, the Costco-compatible Visa for Costco). Trivial to implement as a static lookup, nonzero recurring value, and notably the portfolio's known composition (Platinum/CSR/Venture X/Bilt) has no strong grocery-category earner — the system can quantify whether annual grocery spend justifies adding one.

---

## 5. Nutrition Evaluator, Respecialized

The original's evaluator checks generic balance. Replace its rule set with the household-specific failure modes:

- **The dal-rice attractor.** The vegetarian-Indian equivalent of "three chicken dinners in a row" is a week that converges to dal-rice-sabzi variants seven nights running. The repetition check should operate on *protein source* (dal varieties count as one class; paneer, chana, rajma, tofu, yogurt-based mains count separately) and on *cooking format* (gravy/dry/grilled/one-pot), not on recipe name.
- **Iron + C pairing as a hard weekly target**, for both the toddler (Section 2) and a no-egg adult diet. The evaluator should check meal-level co-occurrence, not weekly totals — iron absorption is a same-meal phenomenon.
- **B12 and D as standing watch items.** Advisory flags only, surfaced monthly, never daily nagging.
- **Protein floor per person per day**, computed against the actual planned portions. Vegetarian meal plans fail on protein quietly; this is the one place where rough quantification beats vibes.
- **Allergy/diet compliance** stays deterministic (Sections 1–2) and is not this evaluator's job. The evaluator advises; the blacklists enforce.

---

## 6. Pantry Sensing: Kill the Fixed Camera (for Now). The Phone Is the Camera.

This is the largest departure from the original, which spends its most loving detail on the refrigerator camera system. The 2026 market reality, checked: the integrated path now exists — GE's CES 2026 Profile fridge ships a built-in barcode scanner, interior camera, and direct Instacart integration; Samsung's AI Vision Inside and Miele's FoodView (April 2026) do camera-based interior visibility — but all of them require buying a new high-end refrigerator, and the retrofit options (Smarter FridgeCam class) still lean on manual tagging for anything beyond "show me a photo remotely." Item-level automatic recognition with quantity and freshness state remains unsolved at consumer-retrofit price points. The original's own accuracy caveats (occlusion, opaque containers, quantity estimation) are confirmed, not obsolete.

Meanwhile, this household's inventory structure makes the camera's value proposition weaker than for the median American fridge:

- The shelf-stable Indian pantry (dals, rice, spices, atta) is large, slow-moving, and **camera-useless** — opaque jars and bags. Receipt parsing + recipe-decrement tracks it better.
- The perishable set is narrow and high-turnover: milk, yogurt/dahi, paneer, butter, and produce. A short, predictable perishable list is exactly the case where **a 30-second phone scan** captures nearly everything a fixed camera would.

**Revised sensing stack, in order of value per unit effort:**

1. **Receipt ingestion (build first).** Instacart/ShopRite email receipts via the existing Gmail connector; photographed paper receipts from Patel Brothers and Costco. VLM-parsed locally to line items → pantry deltas. This single component gives ~70% of inventory fidelity for ~10% of the sensing effort, because *additions* to inventory are fully observable at purchase time.
2. **Recipe-decrement.** Marking a meal cooked decrements its ingredients. Combined with receipts, shelf-stable inventory becomes almost fully synthetic — no scanning habit required, which matters because habit-dependent components fail in time-poor households.
3. **Weekly phone scan during the planning session.** Open fridge, take 3 photos (main, crisper, door), drop into the chat. Qwen-VL on the Mac Studio returns the structured inventory diff with confidence scores; low-confidence items become 3 quick confirm/deny questions. This replaces the entire fixed-camera subsystem, costs nothing, and piggybacks on a session that's happening anyway.
4. **Voice/text deltas** ("finished the milk," "threw out the palak") via a shared family channel — necessary for the spouse to be a full participant without touching any UI.
5. **Fixed camera: deferred indefinitely**, with a defined trigger to revisit — if, after 8+ weeks, the phone-scan step is the component being skipped, that's evidence the passive capture is worth hardware investment (or that the next refrigerator purchase should be one of the camera-native models, at which point the sensing layer is bought, not built).

Everything downstream of sensing in the original — the inventory model with confidence scores, urgency scoring, depletion prediction — survives unchanged. Those are good designs. Depletion prediction is actually *easier* here than in the general case: a vegetarian household with a stable cuisine has lower-entropy consumption patterns (milk, dahi, and atta deplete on near-clockwork cycles).

---

## 7. The Planning Session: 10 Minutes, Two Participants, One Channel

The original's weekly orchestrator asks five open-ended questions. For this household the session must be designed against a hard time budget, because the realistic failure mode of this entire system is not technical — it's that week 4's planning session doesn't happen.

- **Sunday, ≤10 minutes, conversational.** The orchestrator opens with a *proposal*, not questions: "Here's the week — Tuesday and Thursday look short on time per your calendar, the methi needs using by Wednesday, here are 5 dinners. Swap anything?" Defaults derived from history; questions only where the system has genuine uncertainty. The original's question-first flow inverts to proposal-first.
- **Calendar-aware by default.** The Google Calendar connector already exists; late-meeting days auto-flag as ≤25-minute-cook or leftover nights. The original lists calendar integration as a future nicety; here it's a launch feature because time variance is the dominant constraint.
- **Spouse parity.** Whoever cooks must be able to read the plan, swap a meal, and log "cooked / leftovers: ~2 portions" from a phone with zero setup. A shared chat surface (or a minimal LAN web view served from the Mac Studio) — not an app the second adult has to adopt.
- **Plan for 4–5 cooked dinners, not 7.** The original plans 21 slots. Reality for this household: breakfasts are quasi-fixed rotations, lunches are substantially leftovers + office days, 1–2 dinners are ordered in or out (the system already knows the local vegetarian-ramen problem well enough to confirm broth compliance). Planning the true ~12–14 decision slots and leaving the rest as standing rotations cuts planning surface in half with no loss.

---

## 8. What Survives Unchanged from the Original

To be explicit about what's good and stays: the orchestrator-worker decomposition; the inventory model with explicit confidence and "never hallucinate inventory"; urgency scoring and use-before-expiry meal *sequencing* (urgent items in the first half of the week); the leftover network (Sunday batch → Monday lunch is, if anything, more central in a cuisine where dal and sabzi improve overnight); deterministic compliance checks separated from LLM judgment; the human review gate before any list is staged; post-shop reconciliation; and the recommended principle of building waste-aware sequencing before building any hardware.

The three "missing tools worth building" get re-scored for this household: the **Recipe-to-Pantry Semantic Matching Engine** rises to #1 (substitutability knowledge for Indian vegetarian cooking — which dal substitutes for which, paneer↔tofu boundaries given the no-substitute rule's edges, yogurt as the universal binder — is buildable as a small curated knowledge graph and pays off every single week). The **Dynamic Expiry Calendar** stays valuable as a UI. The **Produce Quality Prediction API** falls to "do not build" — purchase-date heuristics plus the weekly photo scan's coarse wilt detection is sufficient, and the training-data problem the original identifies is real.

---

## 9. Revised Build Sequence (Weekend-Sized Increments)

1. **v0 — Constraint engine + corpus + list staging.** Egg/substitute blacklist, toddler safety rules, ~50 transcribed household recipes in ChromaDB, `plan_week` + `grocery_list` + Instacart MCP staging. No sensing at all; pantry state is a manually seeded JSON. *This validates the only genuinely uncertain hypothesis: whether the meal plans are good enough that the family follows them.*
2. **v1 — Receipt ingestion + recipe-decrement.** Gmail-sourced digital receipts and photographed paper ones, parsed locally. Inventory becomes mostly self-maintaining.
3. **v2 — Weekly phone scan + urgency scoring + use-first sequencing.** The waste-reduction layer turns on. Calendar integration lands here too.
4. **v3 — Reconciliation, depletion prediction, mid-week alerts, daycare lunch class.** Polish, and only if v0–v2 have survived 8 real weeks of family use.
5. **v4 — Fixed sensing hardware, only on the trigger condition in Section 6.**

The kill criterion belongs in the design: if by week 6 the planning session is being skipped, the problem is the session's friction, not the features — fix the 10-minute loop before adding anything else.

---

## 10. Honest Assessment, Recalibrated

The original justifies the system on waste dollars ($1,500–2,000/year). For this household that framing is wrong on both sides: vegetarian grocery baskets skew cheaper, so waste dollars are lower, and the household's marginal dollar matters less than its marginal hour. The real returns, in order: **(1) decision elimination** — removing "what's for dinner" as a daily negotiation between two exhausted adults is worth more than any grocery savings; **(2) toddler nutrition assurance** — a weekly verified iron/protein/B12 floor for a no-egg vegetarian toddler is the highest-stakes output the system produces; **(3) waste reduction**, genuinely third.

And one structural note the original can't see: most components here are recombinations of systems already built in this house — local RAG over a curated corpus, MCP tool surfaces, receipt-class document parsing, multi-model orchestration without API spend. The incremental engineering is smaller than the original's architecture diagram implies. The genuinely new work is the curated recipe corpus and the constraint knowledge (egg derivatives, toddler rules, substitutability graph) — which is to say, the new work is domain knowledge encoding, not infrastructure. That's the correct shape for a side project competing for scarce hours.
