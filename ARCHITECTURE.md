# NEX 5.0 — Architecture

Living document. Updated as the build progresses.

**Status:** Phase 1 complete. Bones in place; no Theory X cognition
yet.

---

## 1. Layout

```
alpha.py            Tier 0 — frozen dataclass, read by every subsystem
keystone.py         Tier 1 — self-model seeds + reseed ceremony
errors.py           central error channel (ring buffer + logging handler)
substrate/          one-pen plumbing (writer, reader, paths, init, schemas)
admin/              argon2id single-password auth
voice/              register-aware llama-server client
gui/                Flask observability cockpit + chat column
theory_x/stageN_*/  Phase 2+ scaffolding, empty in Phase 1
strikes/            Phase 8 scaffolding, empty in Phase 1
tests/              stdlib unittest smoke tests
```

`THEORY_X_STAGE = None` is declared at the top of every Phase-1 module.
Stages 1–7 will appear as `theory_x/` is populated in later phases.

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

## 8. What comes next

Phase 2 — Sense Stream (Theory X Stage 1). Populate
`theory_x/stage1_sense/` with the 23 feed adapters writing to
`sense.db` via `substrate.Writer`. No cognition yet; just raw stream
coupling with provenance and timestamps.

See `SPECIFICATION.md §9` for the full phase sequence.
