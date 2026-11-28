# GeniusTagger stop-aware backfill — 28 November 2026

**Base:** `kron777/Nex_v5.0` main at `55fd635bd535d15ece3e3878bf1e71621f56fa7c`.  
**Scope:** cooperative shutdown during GeniusTagger's immediate first-run backfill and later continuous tagging. No score weights, class threshold, feature flags, lookback windows, backfill horizon, schema or tag semantics changed.

## 1. Source evidence

- `run.py` always constructs and starts GeniusTagger; it is registered with AppState.
- Its first tick fires immediately at boot. The first tick loads weights, pulls fountain events from the preceding 14 days by default, checks existing tags, loads the T6 belief cache, then scores and writes one `genius_tags` row per untagged fire.
- Backfill progress is logged every 200 rows. The existing stop Event previously interrupted only the 60-second interval wait; it was not passed into the active tick/backfill.
- Continuous mode similarly loads a six-hour context window and tags new fires from the last 180 seconds.
- The producer can therefore continue a large sequence of scoring and Writer submissions after shutdown begins. AppState's producer join allowance is at most five seconds.

## 2. Bounded correction

- Pass the existing stop Event into the immediate and periodic worker ticks.
- Preserve direct `tick(context)`, `_backfill(weights, ts_now)` and `_tag_window(weights, ts_now, lookback)` calls through optional keyword-only Event parameters.
- Check stop between weights loading, event retrieval, existing-tag retrieval, T6 cache loading, scoring and per-fire writes.
- Make `_backfill()` return whether the full window completed. `_backfill_done` is set only on completion; an interrupted backfill remains resumable on the next tick/restart.
- Already-written rows remain protected by the existing weights-version uniqueness and `INSERT OR IGNORE`; a resumed backfill skips rows already tagged.
- Add deterministic tests for stop during scoring, stop between backfill fires, already-stopped tick and stop in continuous tagging.

## 3. Boundaries and residuals

- Reader operations, weights-file reads and scoring are synchronous and are not cancelled. The active call must return before the Event is observed.
- A single `_write_tag()` already started before stop may complete; the next fire is not started.
- This does not change the first-run backfill size or make it faster. It only makes the sequence cooperatively stoppable between fires.
- The 14-day default backfill remains potentially large, but interrupted work is not falsely marked complete.

## 4. Validation

Exact-head full-suite CI and baseline verification are required before merge. Tests use mocked Readers/Writers and deterministic Events.

No score calibration, tag class policy, feature flag, lookback, backfill horizon, database schema, frozen S-01–S-25/M1.8 specification, Master Roadmap, Gate 0 or Phase 1 authority changed.
