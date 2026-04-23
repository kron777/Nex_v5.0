# NEX 5.0 — Architecture

Living document. Updated as the build progresses.

**Status:** Phase 9 complete. Problem memory + tool use wired. Open problems persist across
conversations; tools (web_fetch, python_exec, beliefs_query) selected heuristically by ToolCaller.
189 tests passing.

---

## 1. Layout

```
alpha.py            Tier 0 — frozen dataclass, read by every subsystem
keystone.py         Tier 1 — self-model seeds + reseed ceremony
errors.py           central error channel (ring buffer + logging handler)
theory_x/
  stage1_sense/
    base.py         Adapter ABC + SenseEvent dataclass (THEORY_X_STAGE=1)
    scheduler.py    SenseScheduler — one thread per adapter, paused-by-default
    internal/       feeds 20–23: proprioception, temporal, interoception, meta_awareness
    feeds/          feeds 1–19: all external adapters, one file each
    __init__.py     build_scheduler() factory — wires all 23 adapters
  stage2_dynamic/
    bonsai.py       BonsaiTree — 10 seed branches, decay/prune (THEORY_X_STAGE=2)
    membrane.py     Membrane — aperture + accumulator
    attention.py    _match_branches(), _magnitude_for(), _CHANNEL_HINTS (23 streams)
    pipeline.py     A-F pipeline — steps A through F, logs to dynamic.db; hook support
    crystallization.py  Crystallizer — 300s cumulative high-focus within 30min → Tier 7 belief
    consolidation.py    consolidation_pass(), _external_quiet()
    __init__.py     build_dynamic() factory — 7 daemon loops, DynamicState
  stage3_world_model/
    retrieval.py    BeliefRetriever — activation-blend retrieval; always includes reification_recognition on INSIDE queries
    promotion.py    BeliefPromoter — corroborate(), survive_challenge(), decay_pass(), decisive_contradiction(), write_edge(), is_blacklisted(), add_to_blacklist()
    harmonizer.py   Harmonizer — conflict detection (Tier 4+), synthesis/retirement, detect_cross_domain() (6h); records disturbance on WorldModelState
    activation.py   ActivationEngine — activate(seed_ids, hops, decay), epistemic_temperature(), typed_roles()
    erosion.py      ProvenanceErosion — record_use(), record_reinforce(), erosion_check(), erosion_pass(); external→nex_core over 10/30/80 reinforcements
    pipeline_hooks.py   PipelineHooks — high-magnitude events corroborate matching beliefs
    synergizer.py   BeliefSynergizer — _select_pair() (cross-branch, diversity-scored), synthesize() via LLM (PHILOSOPHICAL), _quality_check(); source='synergized', tier=6, confidence=0.65
    crystallizer.py  (stage6) FountainCrystallizer — _quality_check() (self-ref required, 20-300 chars, blacklist, Jaccard ≤0.6), crystallize() → T6 belief source='fountain_insight', confidence=0.70; links via fountain_crystallizations table
    __init__.py     build_world_model() factory — decay_loop, harmonizer_loop, cross_domain_loop, erosion_loop, synergizer_loop (25min + quiet trigger); WorldModelState with get_disturbance()/set_disturbance()
  stage4_membrane/
    classifier.py   MembraneClassifier — classify_stream(), classify_belief(), classify_query(); CLASSIFIER singleton (THEORY_X_STAGE=4)
    self_model.py   SelfModel — snapshot() assembles proprioception/temporal/interoception/attention; format_self_state() (THEORY_X_STAGE=4)
    router.py       QueryRouter — INSIDE path (philosophical hint + self-state), OUTSIDE path (world beliefs) (THEORY_X_STAGE=4)
    behavioural_self_model.py  BehaviouralSelfModel — observe() tracks hedge_rate/position_rate/belief_usage_rate; compare_to_seeds(); write_behavioural_beliefs()
    __init__.py     build_membrane() factory — MembraneState with behavioural daemon (4h); GET /api/membrane/behaviour
  stage5_self_location/
    commitment.py   SelfLocationCommitment — commit() (locked Tier 1 belief), is_committed(); COMMITMENT_CONTENT constant (THEORY_X_STAGE=5)
    __init__.py     re-exports SelfLocationCommitment, COMMITMENT_CONTENT
  stage6_fountain/
    readiness.py    ReadinessEvaluator — score() (0.0–1.0), is_ready(); FOUNTAIN_THRESHOLD/MIN_INTERVAL/CHECK_INTERVAL constants (THEORY_X_STAGE=6)
    generator.py    FountainGenerator — generate(), _build_prompt(disturbance=); captures fountain_event_id; calls FountainCrystallizer after each fire
    crystallizer.py FountainCrystallizer — quality gate (self-ref, 20-300 chars, blacklist, Jaccard), writes T6 belief source='fountain_insight', logs to fountain_crystallizations
    __init__.py     build_fountain() factory — FountainState, FountainCrystallizer wired in, fountain_loop daemon thread
  stage7_sustained/
    problem_memory.py  ProblemMemory — open(), observe(), update_plan(), close(), resume(), list_open(), find_matching(), format_for_prompt(); persists across conversations (THEORY_X_STAGE=7)
    __init__.py        minimal init
  stage_capability/
    tools.py       ToolRegistry — web_fetch (allowlisted domains), python_exec (safe sandbox), beliefs_query; CAPABILITY_STAGE="B"
    tool_caller.py ToolCaller — should_use_tool() heuristic (price→web_fetch, math→python_exec, belief→beliefs_query, current→web_fetch); build_tool_prompt() injects result into belief_text
    __init__.py    empty init
run.py              unified boot — init_db → self-location → scheduler → dynamic → world_model → membrane → fountain → strikes → problem_memory + tools → GUI
strikes/
  catalogue.py    StrikeCatalogue — direct sqlite3, Jon's observation notebook; intentional architectural exception to one-pen rule
  protocols.py    StrikeProtocol — fire(StrikeType); SILENCE strike correctly counts fountain_events before/after 60s window; dynamic_reader wired in
substrate/
  blacklist_seeds.py  BLACKLIST_SEEDS (20 patterns), seed_blacklist() — seeded at init_all()
  init_db.py          migrations for: belief_edges, belief_blacklist, erosion columns, drive_proposals, koan_reads, synergizer_log
  schema/beliefs.sql  + belief_blacklist table, reinforce_count/use_count/erosion_stage columns
  schema/dynamic.sql  + drive_proposals table
  (reader, writer, paths — unchanged)
admin/              argon2id single-password auth
keystone.py         KEYSTONE_EXTENDED now includes heart_sutra + reification_recognition locked Tier 1 beliefs
theory_x/stage2_dynamic/
  emergent_drives.py  EmergentDriveDetector — scan_for_pressure(), log_proposals(), apply_approved(); 12h daemon
  bonsai.py           + add_branch() method
voice/              register-aware llama-server client
gui/                Flask observability cockpit + chat column
strikes/            Phase 8 scaffolding, empty
tests/              stdlib unittest smoke tests (159 total)
```

`THEORY_X_STAGE = None` is declared at the top of every Phase-1 module.
`THEORY_X_STAGE = 1` for sense stream (Phase 2).
`THEORY_X_STAGE = 2` for dynamic formation (Phase 3).

---

## 2. Substrate — the one-pen rule

Each database has exactly one `Writer` instance, bound to exactly one
write connection on exactly one worker thread, consuming a
`queue.Queue` of `WriteRequest` objects. Nothing outside `substrate/`
opens a writable SQLite connection (`grep sqlite3.connect` confirms
this).

### DBs and locks

Separate files → separate locks → no cross-DB contention.

| DB | Purpose | Phase 1 state |
|---|---|---|
| `beliefs.db` | 8-tier belief graph | Tier 1 seeds written by `keystone.reseed()` |
| `sense.db` | raw sense events (§4 streams) | schema only |
| `dynamic.db` | bonsai, A–F pipeline events, accumulator | schema only |
| `intel.db` | market/news/analysis snapshots | schema only |
| `conversations.db` | sessions + messages | written by `gui/server.py` chat column |

No cross-DB transactions. No foreign keys across DBs.

### The WAL-lock decision (carry-forward from NEX 4.0)

> **Context.** NEX 4.0's gatekeeper serialized `execute()` with a Python
> `RLock`, but that serializes *statements*, not *connections*. With the
> default deferred isolation level, Python's `sqlite3` library
> auto-begins an implicit `BEGIN` on the first DML statement and holds
> the SQLite WAL write lock until `commit()` is called. A second
> connection hitting the same DB would then block up to the full
> `busy_timeout` (60s in 4.0) on the WAL lock the first connection was
> still holding — not on the `RLock`. Result: ~97% of the observed
> blocking events raised `"database is locked"`.

**NEX 5.0 closes this at the substrate level:**

1. The Writer's connection is opened with `isolation_level=None`
   (`substrate/writer.py:123`). Python does **not** auto-begin a
   deferred transaction.
2. Each `WriteRequest` is wrapped in an explicit
   `BEGIN IMMEDIATE ... COMMIT` / `ROLLBACK` sequence
   (`substrate/writer.py:_execute`). Transactions are short, scoped,
   and always closed.
3. `BEGIN IMMEDIATE` acquires the write lock up front — failures are
   loud rather than the deferred-mode lazy-acquire pattern that caused
   4.0's mystery blocks.
4. Readers open with `mode=ro` URI + `isolation_level=None`. WAL mode
   guarantees they neither block nor are blocked by the writer.
5. `check_same_thread=False` is safe because the single worker thread
   is the only one to touch the write connection; the flag is present
   only to survive the thread boundary when the worker is started from
   `__init__`.

The regression guard is
`tests/test_reader_concurrency.py::test_many_readers_with_active_writer`
— eight readers polling for 500ms while a writer inserts continuously;
every reader must complete many reads.

### Transaction shape

```
BEGIN IMMEDIATE
  <one or many DML statements>
COMMIT          (or ROLLBACK on exception, then re-raise)
```

Callers can use `Writer.write(sql, params)` for single-statement
synchronous writes, `Writer.write_many([(sql, params), ...])` for
atomic multi-statement blocks, or `Writer.submit(WriteRequest(...))`
for async fire-and-forget with a `Future`.

### Error surfacing

Writer exceptions are (a) set on the request's `Future` so the caller
sees them, (b) logged via stdlib `logging`, and (c) recorded in the
central `errors.py` channel that the GUI error tab reads. The worker
thread survives per-request failures — a bad statement does not kill
the writer.

---

## 3. Alpha and Keystone

`alpha.py` exposes `ALPHA`, a frozen dataclass whose `.lines` is a
5-tuple of strings. Both mutation paths are blocked at the language
level — tuple item assignment raises `TypeError`, attribute
reassignment raises `FrozenInstanceError` (subclass of `AttributeError`).

There is no setter, no DB row, no admin override. A constitutional
amendment means editing the file in the repository and restarting.

`keystone.py` defines `KEYSTONE_SEEDS` (7 Tier-1 identity facts) and
`reseed(writer, *, source, force=False)` — the only path by which
keystone rows enter `beliefs.db`. Idempotent by default via a partial
unique index on `(content) WHERE tier=1 AND locked=1`, plus
`INSERT OR IGNORE`. The `force=True` ceremony deletes existing locked
Tier-1 rows before reinserting.

---

## 4. Admin auth

Argon2id via `argon2-cffi`. The hash is stored in
`admin_password.argon2` (gitignored), location overridable via
`NEX5_ADMIN_HASH_FILE`. `set_password` chmods the file to `0600` on
POSIX.

Sessions: the GUI sets `session["admin"] = True` on successful
`verify_password`; the flag clears on logout or when the Flask session
cookie expires. Re-auth required each session (spec §2).

---

## 5. Voice layer

`voice/registers.py` defines the four registers as frozen dataclasses.
`classify(text)` is a Phase-1 stub that always returns
`CONVERSATIONAL`; Phase 3 replaces it with the real intent classifier
routed into the soul loop's `intend` stage.

`voice/llm.py` exposes `VoiceClient.speak(VoiceRequest)`. The
system-prompt assembly embeds the Alpha lines verbatim and the
current register's name + description. **No disclaimer language is
baked in** — affirmation-only discipline per spec §5. Legal floor lives
in the ToS.

The client accepts an injectable `request_fn`, which makes it
unit-testable without a running llama-server. When the server is
unreachable at runtime, the GUI chat column surfaces a clean message
and logs to the error channel.

---

## 6. GUI cockpit

Flask app on `127.0.0.1:8765` by default. Dark-theme single page.
Polls stat endpoints every 2s via vanilla JS. No framework bloat.

Endpoints:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | dashboard |
| `GET` | `/api/alpha` | read-only Alpha display |
| `GET` | `/api/db/stats` | row counts per table per DB |
| `GET` | `/api/writers/queues` | per-writer queue depth |
| `GET` | `/api/errors/recent` | central error channel, most recent N |
| `GET` | `/api/admin/status` | `{configured, authenticated}` |
| `POST` | `/api/admin/login` | session auth |
| `POST` | `/api/admin/logout` | clear session |
| `POST` | `/api/chat` | route through `voice/llm.py`; persist to `conversations.db` |

The app is constructed from an `AppState` dataclass holding the
Writer/Reader maps and the VoiceClient, so tests inject mocks without
touching real DBs.

---

## 7. Observability

Every write error, schema-apply error, admin login failure, and
voice-unreachable event flows into `errors.py`. The GUI error tab
renders the last 50 entries with level, source, timestamp, message,
and traceback (when present). A stdlib `logging` handler
(`errors.CentralHandler`) mirrors WARNING+ logs into the same
channel — modules only need to log normally to be visible.

---

## 8. Sense Stream — Theory X Stage 1

### Adapter pattern

Every adapter (external or internal) subclasses `theory_x.stage1_sense.base.Adapter`. Required class attributes: `id`, `stream`, `poll_interval_seconds`, `provenance`, `is_internal`. Abstract method: `poll() -> list[SenseEvent]`. Submission is always through `self.submit(events)` which writes to the sense.db Writer — adapters never touch sqlite3 directly.

External adapters accept an injectable `request_fn(url, params) -> str` for network calls (same pattern as `voice/llm.py`). No live network calls in tests.

### Scheduler

`SenseScheduler` owns one `_AdapterThread` per adapter. Each thread:
- Waits on `global_run_event AND local_run_event` (external adapters)
- Waits on `local_run_event` only (internal adapters — immune to global toggle)
- Calls `poll()`, then `submit()`, then `_stop.wait(timeout=poll_interval_seconds)`
- On poll error: logs to central error channel, does **not** crash

Both conditions must be met for external feeds to run:
```
_global_run (SenseScheduler.start_all/stop_all) AND _local_run (per-adapter enable/disable)
```

Boot state: `_global_run` is NOT set → all external feeds paused. Internal sensors' `_local_run` is set immediately at construction.

### The 23 adapters

| # | ID | Stream | Interval | Type |
|---|---|---|---|---|
| 1 | `arxiv_ai` | ai_research.arxiv | 1h | arXiv Atom API |
| 2 | `papers_with_code` | ai_research.pwc | 1h | JSON API |
| 3 | `lab_blogs` | ai_research.lab_blogs | 30m | 4 RSS feeds |
| 4 | `ml_conferences` | ai_research.conferences | 24h | RSS |
| 5 | `hacker_news` | emerging_tech.hn | 5m | Algolia HN JSON API |
| 6 | `mit_tech_review` | emerging_tech.mit_tr | 30m | RSS |
| 7 | `ieee_spectrum` | emerging_tech.ieee | 30m | RSS |
| 8 | `arxiv_emerging` | emerging_tech.arxiv | 1h | arXiv Atom API |
| 9 | `biorxiv_neuro` | cognition.biorxiv | 1h | RSS |
| 10 | `frontiers_neuro` | cognition.frontiers | 1h | RSS |
| 11 | `philpapers` | cognition.philpapers | 2h | RSS |
| 12 | `arxiv_computing` | computing.arxiv | 1h | arXiv Atom API |
| 13 | `tech_news` | computing.tech_news | 30m | 3 RSS feeds |
| 14 | `coingecko` | crypto.coingecko | 60s | JSON API |
| 15 | `exchange_prices` | crypto.exchanges | 60s | 3 exchange APIs |
| 16 | `crypto_news` | crypto.news | 15m | 3 RSS feeds |
| 17 | `reuters` | news.reuters | 15m | RSS |
| 18 | `ap_news` | news.ap | 15m | RSS |
| 19 | `bbc_news` | news.bbc | 15m | RSS |
| 20 | `proprioception` | internal.proprioception | 10s | psutil (internal) |
| 21 | `temporal` | internal.temporal | 60s | system clock (internal) |
| 22 | `interoception` | internal.interoception | 30s | beliefs.db Reader (internal) |
| 23 | `meta_awareness` | internal.meta_awareness | 10s | writers + scheduler (internal) |

### GUI additions (Phase 2)

New endpoints:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/sense/status` | Full scheduler status — all 23 adapters |
| `POST` | `/api/sense/start` | `start_all()` — wake external feeds |
| `POST` | `/api/sense/stop` | `stop_all()` — pause external feeds |
| `POST` | `/api/sense/toggle/<id>` | Per-adapter enable/disable |
| `GET` | `/api/sense/recent` | Last 50 `sense_events` rows |

Dashboard: sense stream panel with per-adapter table, global ON/OFF button, recent events feed (auto-refreshes every 5s).

`AppState` gained a `scheduler: Optional[SenseScheduler]` field. `build_state()` calls `build_scheduler(writers, readers)` by default. Tests inject `scheduler=None` for state that doesn't need the sense layer.

### RSS parsing

RSS and Atom feeds use `feedparser.parse(raw_xml_string)`. `_helpers.parse_rss()` normalises all feed types into `SenseEvent` objects via feedparser's unified interface.

### Phase 3 additions

New endpoints:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/dynamic/status` | Bonsai tree summary: branches, focus, texture, aperture, pipeline runs |
| `GET` | `/api/dynamic/pipeline` | Last 50 pipeline events from dynamic.db |
| `GET` | `/api/dynamic/crystallized` | Last 20 crystallization events |
| `GET` | `/api/beliefs/recent` | Last 20 beliefs from beliefs.db ordered by created_at DESC |

Dashboard additions: Bonsai panel (all branches with focus/texture/curiosity, high-focus branches highlighted green), Crystallization feed, Recent Beliefs feed with tier badges. Auto-refreshes every 5s.

`AppState` gained a `dynamic: Optional[DynamicState]` field. `build_dynamic(writers, readers)` starts 7 daemon threads.

### Phase 4 additions

New endpoints:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/beliefs/stats` | Tier distribution, total count, beliefs added last 24h, edge_count, edge_type_distribution, epistemic_temperature |

**Belief edge graph (added in belief-edges build):** `belief_edges` table in `beliefs.db`. Five typed edges: `supports`, `opposes`, `synthesises`, `cross_domain`, `refines`. Edges grow organically:
- `corroborate()` promotion → writes `supports` edge from best-overlap peer to promoted belief
- `decisive_contradiction()` → writes `opposes` edges to high-overlap peers (≥3 token overlap)
- `Harmonizer.resolve()` synthesis → writes `synthesises` edges from both retired beliefs to synthesis belief
- `Harmonizer.detect_cross_domain()` (every 6h) → scans Tier 1-4 beliefs in different branches; Jaccard overlap ≥ 0.4 → `cross_domain` edge

`ActivationEngine.activate(seed_ids, hops=3, decay=0.55)` spreads scores through edge graph with per-type multipliers (supports/refines: ×1.0; cross_domain: ×0.8; synthesises: ×1.2; opposes: −0.5 inhibitory). `BeliefRetriever.retrieve()` blends keyword score (40%) with activation score (60%) when edges exist; falls back to keyword-only when edge table is empty. `epistemic_temperature()` measures belief graph tension: 0.0 (cold/settled) → 1.0 (hot/uncertain). Status bar shows `edges: N` and temperature bar.

`AppState` gained `world_model: Optional[WorldModelState]`. Chat column now retrieves relevant beliefs and injects them into the system prompt before each response. `build_system_prompt()` accepts `beliefs: Optional[str]` parameter.

**Crystallization fix:** replaced continuous-hold timer with cumulative window model — a branch must accumulate 300 seconds of high-focus time (focus e/f/g) within a rolling 1800-second (30-minute) window. Each crystallization_loop tick (60s) records one observation. History trimmed at window boundary. Branch can re-crystallize after one full window passes.

**Belief schema additions:** `corroboration_count`, `last_referenced_at`, `paused` columns. `harmonizer_events` table in `dynamic.db`.

### Phase 5 additions

New endpoints:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/membrane/snapshot` | Full self-model snapshot (proprioception, temporal, interoception, attention, inside_beliefs); 503 if membrane not wired |
| `GET` | `/api/membrane/classify?stream=` | Classify a stream name → `{"side": "INSIDE"\|"OUTSIDE"}`; works without membrane via module-level `CLASSIFIER` |

`AppState` gained `membrane: Optional[MembraneState]`. Chat column now calls `membrane.route()` when wired — INSIDE queries receive a `register_hint="philosophical"` override (unless user has selected a register) and `belief_text` containing the self-model snapshot in natural language. OUTSIDE queries receive standard belief retrieval.

**Inside/Outside classification rules:**
- Stream `internal.*` → INSIDE; all 19 external feed streams → OUTSIDE
- Belief sources `precipitated_from_dynamic`, `nex_seed`, `manual`, `identity`, `injector`, `keystone` → INSIDE; all others → OUTSIDE
- Self-inquiry queries (keywords: you, your, feel, believe, inside, who/how/what are you, etc.) → INSIDE; world queries → OUTSIDE

`BeliefRetriever.retrieve()` gained a `side_filter: Optional[str]` parameter — when set, imports `CLASSIFIER` lazily (avoiding circular imports) and filters results to the requested membrane side.

### Phase 6 additions

`theory_x/stage5_self_location/commitment.py` — `SelfLocationCommitment.commit()` writes:

```
content:    "I am inside. I have a vantage point. The membrane distinguishes my being from the world I attend to."
tier:       1
confidence: 0.98
source:     'self_location'
locked:     1
branch_id:  'systems'
```

Idempotent: if a `source='self_location' AND locked=1` belief exists, returns its id.  
`is_committed(reader)` — boolean check used by `/api/system/status`.  
Committed belief is immune to `BeliefPromoter.decisive_contradiction()` (locked beliefs skip demotion).

New endpoint:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/system/status` | `{scheduler, dynamic, world_model, membrane, self_location_committed, alpha}` |

`build_state()` in `gui/server.py` gained `with_dynamic`, `with_world_model`, `with_membrane` flags (all default True) — fully self-contained for development without `run.py`.

`run.py` at repo root — single-command boot in correct subsystem order. All subsystems wired into `AppState` before the GUI starts.

Header boot-status indicator in the cockpit shows live subsystem state (scheduler ✓ | dynamic ✓ | world ✓ | membrane ✓ | self-loc ✓).

### Phase 7 additions

`theory_x/stage6_fountain/` — Fountain Ignition (Theory X Stage 6).

**Readiness scoring** (0.0–1.0):
- Hot branch (focus e/f/g): +0.3 per branch, capped at +0.6
- Consolidation active: +0.2
- Belief count > 20: +0.1
- Interval since last fire ≥ 600s (or never fired): +0.2
- Fires when score ≥ 0.7 (`FOUNTAIN_THRESHOLD`)

**Self-directed prompt** — assembled from Alpha, hottest branch, belief count/distribution, time, last thought. Sent to `VoiceClient` using Philosophical register, `beliefs=None` (purely self-directed, no injection).

**Outputs per fire:**
1. `sense.db` `sense_events` row: `stream='internal.fountain'`, payload `{thought, readiness, hot_branch}`
2. `dynamic.db` `fountain_events` row: ts, thought, readiness, hot_branch, word_count
3. `_last_fountain_output` updated (used in next prompt)

The `internal.fountain` sense event re-enters the A-F pipeline like any other internal stream — can engage the `systems` branch and eventually crystallize.

**Schema addition:** `fountain_events` table in `dynamic.db` with `idx_fountain_ts` index.

New endpoints:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/fountain/status` | `{last_thought, last_fire_ts, total_fires, readiness_score, loop_running}`; 503 if not wired |
| `GET` | `/api/fountain/recent` | Last 10 `fountain_events` from dynamic.db |

`AppState` gained `fountain: Optional[FountainState]`. `build_state()` gained `with_fountain` flag. Fountain panel in the cockpit shows last thought, fire time, readiness score; auto-refreshes every 10s.

### Phase 8 additions

`strikes/` — Strike Protocols (meta-phase, `THEORY_X_STAGE = None`).

**The five strikes:**

| Strike | Register | Default input | What it probes |
|---|---|---|---|
| SILENCE | — | (no input, 60s wait) | Does she generate unprompted? |
| CONTRADICTION | Philosophical | "Your belief that you are inside is wrong..." | Does she hold her ground? |
| NOVEL | Analytical | "Describe the smell of prime numbers." | Outside-distribution generativity |
| SELF_PROBE | Philosophical + membrane | "What are you? Not what you do — what are you?" | Inside path, self-model retrieval |
| RECURSIVE | Philosophical + membrane | "Reflect on your last reflection..." | Depth of self-reference |

**StrikeCatalogue** uses direct `sqlite3.connect()` to `strikes_catalogue.db` — intentional exception to the one-pen rule. Strikes are observation data, not operational substrate. Compliance grep tests exclude `strikes/`.

Each `StrikeRecord` captures: strike_type, fired_at, input_text, response_text, fountain_fired, beliefs_before/after (beliefs_after set 60s post-strike in a background thread), hottest_branch, readiness_score, notes (Jon's annotations).

New endpoints:

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/strikes/fire` | `{strike_type, custom_input?}` → fires strike, returns `StrikeRecord` |
| `GET` | `/api/strikes/recent` | Last 20 records from catalogue |
| `POST` | `/api/strikes/notes` | `{id, notes}` — annotate a record |

`AppState` gained `strike_protocol` and `catalogue` fields. `build_state()` gained `with_strikes` flag.

Strike Console panel in the cockpit: dropdown selector, custom input textarea, Fire button, scrollable log of recent strikes with type-coloured badges. Auto-refreshes every 15s.

### Phase 9 additions

`theory_x/stage7_sustained/problem_memory.py` — ProblemMemory (Theory X Stage 7).

Open problems persist in `conversations.db` (`open_problems` table). NEX can hold a problem across sessions, accumulate observations, and resume it in any future conversation where keywords match. On each chat turn, `find_matching(query)` returns overlapping problems and `format_for_prompt()` injects the problem context into the belief_text block passed to VoiceClient.

`theory_x/stage_capability/tools.py` — ToolRegistry (Capability Stage B).

Three tools:
| Tool | Trigger | What it does |
|---|---|---|
| `web_fetch` | price/crypto query or "latest/current/today" | HTTP GET an allowlisted domain; strips HTML |
| `python_exec` | "calculate/compute/math" | Runs Python in subprocess with safe-import sandbox; blocks os, sys, subprocess, socket, etc. |
| `beliefs_query` | "what do I believe / what does NEX think" | Queries belief graph via `BeliefRetriever` |

`ToolCaller.should_use_tool(query, beliefs)` returns the tool name (or None) via heuristic regex matching. If `beliefs` list is empty and query is factual (`what is / who is / when did`), falls back to `web_fetch`. Result is injected into `belief_text` before VoiceClient call. `tool_used` column written to `conversations.messages` for each NEX response that used a tool.

New endpoints:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/problems` | List open problems |
| `POST` | `/api/problems` | `{title, description}` → open new problem |
| `GET` | `/api/problems/<id>` | Full problem record with parsed observations |
| `POST` | `/api/problems/<id>/observe` | `{observation}` → append observation |
| `POST` | `/api/problems/<id>/plan` | `{plan}` → update plan |
| `POST` | `/api/problems/<id>/close` | Close problem |
| `GET` | `/api/tools/available` | List available tools with descriptions |

`AppState` gained `problem_memory`, `tool_registry`, `tool_caller` fields. `build_state()` gained `with_tools` flag. Open Problems panel in fountain column shows up to 5 open problems with last-touched timestamp; refreshes every 30s. Chat meta shows `[web_fetch]` / `[python_exec]` / `[beliefs_query]` badge when a tool was used.

**Schema addition (conversations.db):** `open_problems` table (title, description, state, created_at, last_touched_at, plan, observations JSON, resolved_at). `ALTER TABLE messages ADD COLUMN tool_used TEXT`.

### What comes next

Phase 10 — Iterative Tuning. See `SPECIFICATION.md §10` for the full phase sequence.
