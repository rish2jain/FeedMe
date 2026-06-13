# FeedMe — Activate All Features

Turn the Mac Studio into a live FeedMe hub in one sitting (~45–60 min first time).
Everything below assumes the repo is at `~/Documents/FeedMe/FeedMe`.

---

## What you get when fully activated

| Feature | Trigger | Needs |
|---------|---------|-------|
| Semantic recipe search | `OLLAMA_EMBED_MODEL` | Ollama + Chroma |
| Receipt photo parsing | `OLLAMA_VLM_MODEL` + `receipt_ingest(image_path=...)` | Ollama Qwen-VL |
| Fridge scan | `OLLAMA_VLM_MODEL` + `inventory_scan(images_json=...)` | Ollama Qwen-VL |
| Gmail receipt auto-ingest | `GMAIL_CREDENTIALS` | Google OAuth |
| Calendar-aware planning | `GOOGLE_CALENDAR_CREDENTIALS` | Google OAuth |
| Live Instacart staging | `INSTACART_MCP_COMMAND` | Instacart MCP wrapper |
| Claude tool surface | `pantry-local` MCP server | MCP config |
| Spouse phone UI | `pantry-local-web` | FastAPI on LAN |
| Planning kill-criterion | `plan_session_complete` | Event log only |

Core logic (diet/toddler gates, planner, depletion) works **without** any of the above.
Integrations layer on when env vars are set.

---

## Step 0 — Verify the base install (5 min)

Use a **dedicated venv** so FeedMe does not fight with other tools (docling,
tensorflow, langchain, etc.) in your global/user site-packages.

```bash
cd ~/Documents/FeedMe/FeedMe
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev,mcp,integrations,chroma,web]"
python -m pytest -q
```

All tests should pass offline. If this fails, fix before continuing.

### If you already installed globally and saw pip conflict warnings

Messages like `docling requires huggingface_hub<1` or `langchain requires langchain-core<1.0`
are **not FeedMe failures** — pip is warning that other packages in the same Python
environment disagree with versions already installed (often pulled in by Chroma's
`huggingface-hub`). FeedMe itself has no runtime deps beyond optional extras.

Your install still worked if you see `Successfully installed pantry-local` and pytest
passes. To avoid future cross-tool breakage, use the venv above and point Claude MCP
at `.venv/bin/pantry-local` instead of the global command.

---

## Step 1 — Ollama models (10 min)

Ollama should already be running on the Mac Studio (`http://127.0.0.1:11434`).

```bash
# Embeddings → semantic Chroma search
ollama pull nomic-embed-text

# Vision → receipt + fridge scan
ollama pull qwen2.5-vl:32b
# or: ollama pull qwen2.5-vl:72b   # if you have headroom on 96GB
```

Smoke-test:

```bash
curl -s http://127.0.0.1:11434/api/tags | python3 -m json.tool
ollama run nomic-embed-text "test" --verbose 2>/dev/null | head -1
```

---

## Step 2 — Google OAuth (Gmail + Calendar) (15 min)

One Google Cloud project covers both connectors.

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services.
2. Enable **Gmail API** and **Google Calendar API**.
3. Create OAuth 2.0 credentials → **Desktop app** → download JSON.
4. Save credentials outside the repo, e.g. `~/.config/feedme/google-credentials.json`.

First run opens a browser to authorize and writes token files next to the credentials path (or paths you set via env).

Required scopes (already coded in the integration modules):

- Gmail: `gmail.readonly`
- Calendar: `calendar.readonly`

---

## Step 3 — Instacart MCP wrapper (10 min)

FeedMe expects a **wrapper script** that reads JSON from stdin and prints JSON with a `url` key:

```json
{"tool": "create-shopping-list", "arguments": {"title": "...", "line_items": [...]}}
```

→ stdout:

```json
{"url": "https://customers.instacart.com/store/shopping_lists/..."}
```

Point `INSTACART_MCP_COMMAND` at that script. If you already have an Instacart Developer Platform MCP server, wrap it in a thin shell script that translates the above contract.

Test manually:

```bash
echo '{"tool":"create-shopping-list","arguments":{"title":"test","line_items":[]}}' \
  | /path/to/your/instacart-mcp-wrapper
```

---

## Step 4 — Environment file (5 min)

Create `~/.config/feedme/env.sh` (not committed):

```bash
# --- Household ---
export TODDLER_BIRTHDATE="2025-01-15"
export DAYCARE_ACTIVE="false"          # set true when daycare starts

# --- Paths ---
export PANTRY_STATE="$HOME/.config/feedme/pantry_state.json"
export PANTRY_EVENTS="$HOME/.config/feedme/events.json"
export PANTRY_CHROMA_DIR="$HOME/.config/feedme/chroma"
export PANTRY_CURRENT_PLAN="$HOME/.config/feedme/current_plan.json"

# --- Ollama (activates embed + VLM + auto-Chroma) ---
export OLLAMA_HOST="http://127.0.0.1:11434"
export OLLAMA_EMBED_MODEL="nomic-embed-text"
export OLLAMA_VLM_MODEL="qwen2.5-vl:32b"
# PANTRY_BACKEND=chroma   # optional; auto-selected when OLLAMA_EMBED_MODEL is set

# --- Google ---
export GMAIL_CREDENTIALS="$HOME/.config/feedme/google-credentials.json"
export GMAIL_TOKEN="$HOME/.config/feedme/gmail-token.json"
export GOOGLE_CALENDAR_CREDENTIALS="$HOME/.config/feedme/google-credentials.json"
export GOOGLE_CALENDAR_TOKEN="$HOME/.config/feedme/calendar-token.json"
export GOOGLE_CALENDAR_ID="primary"

# --- Instacart ---
export INSTACART_MCP_COMMAND="/path/to/instacart-mcp-wrapper"

# --- Spouse web view ---
export PANTRY_WEB_HOST="0.0.0.0"
export PANTRY_WEB_PORT="8765"
export PANTRY_WEB_PIN="1234"           # optional; omit for LAN-only trust
```

Load before every session:

```bash
source ~/.config/feedme/env.sh
```

Seed pantry from repo defaults (first time only):

```bash
mkdir -p ~/.config/feedme
cp data/pantry_seed.json "$PANTRY_STATE"
```

---

## Step 5 — Register MCP with Claude (5 min)

In Claude Desktop / Claude Code MCP config:

```json
{
  "mcpServers": {
    "pantry-local": {
      "command": "pantry-local",
      "env": {
        "TODDLER_BIRTHDATE": "2025-01-15",
        "PANTRY_STATE": "/Users/YOU/.config/feedme/pantry_state.json",
        "PANTRY_EVENTS": "/Users/YOU/.config/feedme/events.json",
        "PANTRY_CHROMA_DIR": "/Users/YOU/.config/feedme/chroma",
        "OLLAMA_HOST": "http://127.0.0.1:11434",
        "OLLAMA_EMBED_MODEL": "nomic-embed-text",
        "OLLAMA_VLM_MODEL": "qwen2.5-vl:32b",
        "GMAIL_CREDENTIALS": "/Users/YOU/.config/feedme/google-credentials.json",
        "GMAIL_TOKEN": "/Users/YOU/.config/feedme/gmail-token.json",
        "GOOGLE_CALENDAR_CREDENTIALS": "/Users/YOU/.config/feedme/google-credentials.json",
        "GOOGLE_CALENDAR_TOKEN": "/Users/YOU/.config/feedme/calendar-token.json",
        "INSTACART_MCP_COMMAND": "/path/to/instacart-mcp-wrapper"
      }
    }
  }
}
```

Restart Claude after saving. You should see 22 `pantry-local` tools.

---

## Step 6 — Start the spouse web view (2 min)

In a separate terminal on the Mac Studio:

```bash
source ~/.config/feedme/env.sh
pantry-local-web
```

On your phone (same Wi‑Fi): `http://<mac-studio-ip>:8765/?pin=1234`

From there: read the plan, swap a meal by recipe id, log cooked + leftover portions.

---

## Step 7 — First live Sunday session (10 min)

Run in Claude (or via Python) in this order:

### 7a. Pull receipts from Gmail

```
receipt_fetch_gmail()
```

Or with a custom query: `receipt_fetch_gmail(since_query="from:instacart newer_than:7d")`

### 7b. Fridge scan (3 photos)

Save photos locally, then:

```
inventory_scan(images_json='["/tmp/fridge-main.jpg","/tmp/fridge-crisper.jpg","/tmp/fridge-door.jpg"]')
```

Answer any `pending_confirmation` items via `scan_confirm`.

### 7c. Plan the week (calendar + proposal)

```
plan_week(num_dinners=5)
```

Response includes a `proposal.narrative` — open with that, not questions.
Calendar limits apply automatically when Google Calendar is configured.

### 7d. Validate, list, stage

```
plan_validate(plan_json=<the plan JSON>)
grocery_list(plan_json=<the plan JSON>)
instacart_stage(grocery_json=<the grocery JSON>)
```

The Instacart URL should be a real shopping-list page (not `STAGED_LOCALLY`).

### 7e. Log session complete

```
plan_session_complete(notes="Accepted plan, staged Instacart")
```

Check kill criterion anytime:

```
plan_session_status_report()
```

---

## Feature verification checklist

Run after setup to confirm each integration is live:

```bash
source ~/.config/feedme/env.sh

# Ollama embed + Chroma
PYTHONPATH=src python3 -c "
from pantry_local.integrations.wiring import build_clients_from_env, chroma_backend_requested
c = build_clients_from_env()
assert c.embed, 'embed missing'
assert chroma_backend_requested(c), 'chroma not selected'
print('OK: Ollama embed + Chroma')
"

# VLM (needs a real receipt image path)
# PYTHONPATH=src python3 -c "
# from pantry_local import server as s
# print(s.receipt_ingest(image_path='/path/to/receipt.jpg'))
# "

# Gmail (first call may open browser for OAuth)
# PYTHONPATH=src python3 -c "
# from pantry_local import server as s
# print(s.receipt_fetch_gmail(ingest=False))
# "

# Calendar-aware plan
PYTHONPATH=src python3 -c "
from pantry_local import server as s
p = s.plan_week(num_dinners=3)
assert 'proposal' in p
print('OK: plan_week + proposal:', p['proposal']['narrative'][:80])
"

# Web server
curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:8765/?pin=$PANTRY_WEB_PIN"
# expect 200 when pantry-local-web is running
```

---

## Optional: run as launchd services

Keep MCP-adjacent services alive across reboots.

**Ollama** — already managed separately.

**Web view** — `~/Library/LaunchAgents/com.feedme.web.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.feedme.web</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/local/bin/pantry-local-web</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PANTRY_STATE</key><string>/Users/YOU/.config/feedme/pantry_state.json</string>
    <!-- add other env keys from env.sh -->
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
</dict>
</plist>
```

Load: `launchctl load ~/Library/LaunchAgents/com.feedme.web.plist`

MCP itself is started by Claude on demand — no daemon needed.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `STAGED_LOCALLY` Instacart URL | Set `INSTACART_MCP_COMMAND`; test wrapper manually |
| `Gmail not configured` | Set `GMAIL_CREDENTIALS` or `GMAIL_TOKEN` |
| Receipt image fails | Confirm `OLLAMA_VLM_MODEL` is pulled; check `OLLAMA_HOST` |
| Keyword search only | Set `OLLAMA_EMBED_MODEL`; restart MCP so `_build_store()` re-runs |
| Chroma empty / slow first search | First query builds embeddings for 53 seed recipes — wait ~30s |
| Calendar limits missing | Authorize Calendar scope; check `GOOGLE_CALENDAR_ID` |
| Web view 403 | Wrong `PANTRY_WEB_PIN` query param |
| Kill criterion triggered | Run a planning session; call `plan_session_complete` |

---

## What's intentionally not activated

Per design — do not wire these unless the trigger fires:

- Fixed fridge cameras (skip weekly scan 8+ weeks, or buy camera-native fridge)
- Produce quality prediction API
- Multi-store price optimizer

---

## Next: grow the corpus

The seed corpus has 53 diet-clean recipes. The highest-value upgrade is transcribing
your family's real repertoire via `recipe_add` — not more infrastructure.

See [README.md](README.md) for architecture and [docs/design.md](docs/design.md) for the full product spec.
