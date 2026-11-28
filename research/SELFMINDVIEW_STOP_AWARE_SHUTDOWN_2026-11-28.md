# SelfMindView snapshot and self-binding stop-aware lifecycle — 28 November 2026

**Base:** `kron777/Nex_v5.0` main at `55fd635bd535d15ece3e3878bf1e71621f56fa7c`.  
**Scope:** cooperative stop checkpoints through the SelfMindView background snapshot and its nested self-binding operation. No snapshot fields, faculty meanings, self-binding synthesis, cadence, flags or schema changed.

## 1. Source evidence

- `run.py` starts SelfMindView and registers it with AppState. AppState calls `stop()` and joins its worker.
- The worker previously passed no stop Event into `tick()`; the active tick called `_snapshot()` without a stop signal.
- `_snapshot()` performs a multi-aspect `current_state()` read, then calls `self_binding.bind(dynamic_writer=...)`, generates tags and writes `self_mind_snapshots`.
- `self_binding.bind()` ensures its tables, then reads compositional emotion, rāga, dominant drive, attention and substrate signals. Several helpers open independent SQLite connections with a 10-second timeout. It then writes `self_state` and `self_state_history` through the shared dynamic Writer.
- The AppState producer join allowance is at most five seconds. Before this change, a stop signal during the read/bind sequence did not prevent later self-state or snapshot writes from starting.

## 2. Bounded correction

- Pass the existing stop Event from the SelfMindView worker into `tick()`, `_snapshot()` and `current_state()`.
- Preserve direct calls by making the stop Event optional and keyword-only.
- Check stop between the five read-only aspects and before the snapshot bind, tag-generation result and final snapshot Writer operation.
- Pass the Event into `self_binding.bind()`; check between the faculty reads and before starting its state persistence.
- Add a stop checkpoint between the two direct SQLite reads in `_read_attention()`.
- Once the self-binding current-state write begins, finish its paired history append. If stop arrives during binding, SelfMindView skips its subsequent snapshot row.
- Add deterministic tests for stop between aspects, during bind, before bind/schema writes, and during the self_state/history commit pair.

## 3. Boundaries and residuals

- An individual Reader/SQLite call and a faculty detector call are not cancelled. The current call must return before the next checkpoint observes stop.
- `_ensure_table()` is a schema operation and may complete if stop arrives while its `write_many()` is already in progress; later faculty reads and state writes are then skipped.
- Once the `self_state` current-row write starts, the history append is allowed to finish as one logical persistence unit. These are separate Writer submissions, not one database transaction.
- If stop arrives during the final `self_mind_snapshots` Writer submission, that already-started write may complete.
- This is cooperative stage-boundary control, not an atomic stop/write handshake or host-level shutdown proof.

## 4. Validation

Exact-head full-suite CI and baseline verification are required before merge. Tests use deterministic Events and mocked readers/Writers; no live database or external service is required.

No frozen S-01–S-25/M1.8 specification, Master Roadmap, Gate 0, Phase 1 authority, snapshot schema, feature flag or cadence changed.
