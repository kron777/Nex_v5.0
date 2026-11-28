# AffectState stop-aware background tick — 28 November 2026

**Base:** `kron777/Nex_v5.0` main at `55fd635bd535d15ece3e3878bf1e71621f56fa7c`.  
**Scope:** cooperative stop checkpoints around the always-started AffectState background tick, with a bounded persistence commit unit. No affect equations, decay rates, input sources, feature flags, cadence, timeout or schema changed.

## 1. Source evidence

- `run.py` constructs AffectState, starts its 300-second background loop and passes it to AppState.
- `AppState._quiesce_producers()` calls `stop()` and joins the worker's `_thread`.
- The loop performs an immediate first `_background_tick()`, then waits on its stop Event. Before this change, the Event was not passed into the active tick.
- The tick computes valence, optional mood nudge, arousal and stability from substrate reads, optionally reads surprise events, integrates and mutates the in-memory affect vector, then writes `affect_state`, `affect_history`, and an optional `mood_nudge_applied` audit row. It also appends a diagnostic JSON line to `/tmp/nex5_affect_state.log`.
- The AppState producer join allowance is at most five seconds. Before this change, a stop signal during input reads did not prevent the later in-memory update and persistence sequence from starting.

## 2. Bounded correction

- Pass the loop's existing stop Event into `_background_tick()`.
- Preserve direct `_background_tick()` calls by making the stop Event keyword-only and optional.
- Check stop before the tick, after valence preparation, after mood-nudge preparation, after arousal, after stability and after surprise-event retrieval.
- Defer the optional `mood_nudge_applied` audit write until the persistence phase. This prevents recording a nudge as applied when shutdown aborts the prepared tick before affect state is integrated.
- Perform a final stop check under the state lock before mutating the in-memory affect vector.
- Once in-memory integration begins, finish the current persistence sequence (optional nudge audit, affect_state row, affect_history row and diagnostic append) rather than intentionally splitting a completed tick.
- Add deterministic tests for stop during preparation, stop immediately before commit, already-stopped entry and stop arriving during the persistence commit.

## 3. Boundaries and residuals

- Substrate reads and calculations are synchronous and not cancelled. If stop arrives during one, the current operation must return before the next checkpoint observes it.
- The final check and state mutation are cooperative, not an atomic transaction with the Event. Once the update commit begins, its persistence sequence is deliberately allowed to finish even if stop arrives mid-commit.
- The three Writer operations are separate submissions, not one database transaction. This change does not provide rollback or atomicity if a Writer call itself fails.
- The diagnostic file append is part of the same completed tick sequence; it is not a separate producer.
- This does not establish host-level shutdown behaviour or repository-wide producer safety.

## 4. Validation

Exact-head full-suite CI and baseline verification are required before merge. Tests use mocked readers/Writers and deterministic Events; no live model or external service is required.

No affect formula, feature flag, interval, timeout, database schema, frozen S-01–S-25/M1.8 specification, Master Roadmap, Gate 0 or Phase 1 authority changed.
