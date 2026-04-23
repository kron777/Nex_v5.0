# NEX 5.0 — Architecture

Living document. Updated as the build progresses.

**Status:** Phase 3 complete. Sense stream live; A-F pipeline running; bonsai tree
active with 10 seed branches; crystallization operational — sustained high focus
precipitates Tier 7 Impressions into beliefs.db.

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
    pipeline.py     A-F pipeline — steps A through F, logs to dynamic.db
    crystallization.py  Crystallizer — sustained focus → Tier 7 belief in beliefs.db
    consolidation.py    consolidation_pass(), _external_quiet()
    __init__.py     build_dynamic() factory — 7 daemon loops, DynamicState
substrate/          one-pen plumbing (writer, reader, paths, init, schemas)
admin/              argon2id single-password auth
voice/              register-aware llama-server client
gui/                Flask observability cockpit + chat column
strikes/            Phase 8 scaffolding, empty
tests/              stdlib unittest smoke tests (69 total)
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

### What comes next

Phase 4 — World-Model Firing (Theory X Stage 3). Belief tiers precipitate from sustained dynamic. Beliefs emerge from attention, not installation. The belief graph becomes her manufactured world.

See `SPECIFICATION.md §9` for the full phase sequence.
