# FeedMe / `pantry-local` — Backlog

Status: **all phases v0–v4 implemented** (see `README.md` and `docs/design.md`). The
core is local-first and hermetically testable (93 tests, no network). What remains is
**not infrastructure** — it's wiring the injectable seams to the household's real
systems and encoding more domain knowledge, exactly the shape the design predicted
(§10: "the new work is domain knowledge encoding, not infrastructure").

Priority key: **P0** highest value next · **P1** valuable · **P2** opportunistic.
Effort: 🟢 hours · 🟡 a weekend · 🔴 multi-weekend.

---

## 1. Wire the injectable seams (P0 — turns the skeleton into a live system)

Every model/connector boundary is already an injectable seam; these tasks plug in the
real backends on the Mac Studio. No architectural change required.

- [ ] **Qwen-VL receipt parsing** — `ingestion/receipt.ingest_receipt(vlm_client=...)`.
      Wire an Ollama Qwen3-VL (or Qwen2.5-VL 32B/72B) call: receipt image/PDF → line
      items JSON. 🟡 (design §3, §6.1)
- [ ] **Qwen-VL fridge scan** — `ingestion/scan.ingest_scan(vlm_client=...)`. Same
      model, fridge photos (main/crisper/door) → items + confidence. 🟡 (§6.3)
- [ ] **Semantic embedder for Chroma** — `ChromaRecipeStore(embed=...)`. Replace the
      default offline `hashing_embed` (lexical only) with `nomic-embed`/`mxbai` via
      Ollama for real semantic retrieval. 🟢 (§1 Stage 3)
- [ ] **Gmail receipt fetch** — pull Instacart/ShopRite confirmation emails via the
      Gmail connector and feed the body into `receipt_ingest(text=...)`. 🟡 (§6.1)
- [ ] **Google Calendar fetch** — `integrations/calendar.time_limits_from_client(...)`
      against the real connector so `plan_week` is calendar-aware automatically. 🟢 (§7)
- [ ] **Instacart MCP call** — `integrations/instacart.stage_shopping_list(mcp_client=...)`.
      Replace the placeholder URL with the real `create-shopping-list` MCP call to get a
      mapped shopping-list page at ShopRite. 🟢 (§4)
- [ ] **Persist Chroma in production** — run with `PANTRY_BACKEND=chroma` +
      `PANTRY_CHROMA_DIR`; consider making Chroma the default once an embedder is wired. 🟢

## 2. Domain knowledge encoding (P0/P1 — the genuinely new work, §10)

- [ ] **Grow the corpus 18 → 50+** with the family's transcribed repertoire — the
      highest-value data in the whole system. Each goes through `recipe_add`
      (diet-checked on entry). 🔴 ongoing (§1 Stage 3, §9 v0)
- [ ] **Substitutability knowledge graph** (design's re-scored #1 tool, §8): which dal
      subs for which, paneer↔tofu edges given the no-substitute rule, yogurt as
      universal binder. Small curated graph; pays off weekly. 🟡 (§8)
- [ ] **Expand the ontology** — more produce/condiments/regional items; current table is
      Bengali-baseline only. Add as recipes surface `unmatched`/`skipped` items. 🟢 ongoing
- [ ] **Quarterly toddler age-gating review** — texture/salt/portion thresholds in
      `constraints/toddler._age_notes` as the daughter grows. 🟢 recurring (§2)

## 3. Product / UX (P1)

- [ ] **Spouse-parity surface** — shared chat or a minimal LAN web view served from the
      Mac Studio: read the plan, swap a meal, log "cooked / leftovers: ~2 portions" from
      a phone with zero setup. Failure mode is friction, not features. 🔴 (§7)
- [ ] **10-minute proposal-first planning session** — orchestrator opens with a proposal
      (not questions): "here are 5 dinners, methi needs using Wed, swap anything?" 🟡 (§7)
- [ ] **Dynamic expiry calendar** as a UI surface (kept "valuable" in §8). 🟡
- [ ] **Credit-card ROI** — quantify whether annual grocery spend justifies adding a
      US-supermarket multiplier card (portfolio: Platinum/CSR/Venture X/Bilt has none). 🟢 (§4)
- [ ] **Patel rolling list** — accumulate the Indian-store restock list between monthly
      trips from receipt-parse depletion; surface when a trip is happening. 🟢 (§4)

## 4. Quality / infra (P1/P2)

- [ ] **CI** — GitHub Actions running `pytest` on push (chroma tests already skip if
      absent). Consider the `session-start-hook` skill for web sessions. 🟢
- [ ] **Instrumentation / kill criterion** — track planning-session completion; if the
      session is skipped by week 6, fix the 10-min loop's friction before adding
      features (the design's stated kill criterion, §9). 🟡
- [ ] **History-driven depletion** — once the event log accumulates, prefer inferred
      rates over `DEFAULT_DAILY_RATES`; widen/auto-tune the window. 🟢 (§6)
- [ ] **Unit reconciliation for dals/grains** — optional density table so "1 cup dal"
      decrements a "1 kg" bag instead of being flagged manual. Low priority: flagging is
      the safe default and bulk staples are negligible anyway. 🟡

## 5. Deferred by design (P2 — do NOT build until triggered)

- [ ] **Fixed sensing hardware** — only when `hardware_trigger` fires (phone scan skipped
      8+ weeks) OR the next fridge purchase is camera-native (GE Profile / Samsung AI
      Vision / Miele FoodView). The sensing layer is then *bought, not built*. (§6.5, v4)
- [ ] **Produce Quality Prediction** — design says "do not build"; purchase-date
      heuristics + the scan's coarse wilt detection suffice. (§8)
- [ ] **Multi-store price/circular optimizer** — deliberately deleted (§4): the binding
      constraint is hours, not dollars.

---

## Known limitations (current, intentional)

- `hashing_embed` is **lexical, not semantic** — fine for tests/offline; wire a real
  embedder (§1 above) for quality vector search.
- Recipe-decrement **flags unit mismatches** (e.g. cup vs kg) rather than guessing, to
  avoid corrupting inventory. Resolve via §4 density table or the voice/scan channel.
- Scan **never auto-removes** unseen perishables (occlusion-safe); they require a
  confirm/deny answer.
- Corpus is **~18 seed recipes** — representative, not the real repertoire yet (§2).
