# NovelAssociation scan stop-aware shutdown — 28 November 2026

**Base:** `kron777/Nex_v5.0` main at `60c65fa8452fee891d7fad34dac1585c732c5759`.  
**Scope:** cooperative stop checkpoints inside the always-started NovelAssociation scan loop. No similarity threshold, branch sampling, interval, embedding model, feature flag, Writer schema or graph policy changed.

## 1. Source evidence

- `run.py` always constructs `NovelAssociation`, calls `start_loop()`, and passes it to `AppState`.
- `AppState._quiesce_producers()` calls `stop()` and joins its `_thread`.
- The worker's stop Event interrupts its 1,800-second interval wait. Before this change, the loop called `tick()` without passing the Event into the active scan.
- `tick()` pulls belief candidates and evaluates cross-branch pairs. For each candidate pair, `_scan()` calls local `embed_belief()` twice, calculates cosine similarity, then writes a synthesises edge and a `novel_association_log` row. A sufficiently strong pair can also write a SelfNarrative entry.
- The scan can therefore continue through expensive embedding work and multiple Writer-backed pairs after shutdown begins. AppState allows at most five seconds for producer joining.

## 2. Bounded correction

- Pass the existing stop Event from the worker loop into `tick()` and `_scan()`.
- Preserve existing direct `tick(context)` and `_scan(now)` calls by making the stop Event keyword-only and optional.
- Check stop before candidate retrieval, after candidate retrieval, before each pair, after each embedding call, before similarity-result writes, and before starting the subsequent narrative write.
- Once an edge+log pair has started, let that paired write unit finish; then check stop before any narrative write or next candidate pair. This avoids deliberately splitting the existing two-write logical pair when stop arrives during its submission.
- Add deterministic Event-based tests for stop during embedding, stop before scan start, and stop after one pair before the next pair.

## 3. Boundaries and residuals

- Local embedding work is not cancelled. If stop arrives while `embed_belief()` is running, that call must return before the worker can observe the Event and exit.
- The edge and log are two separate Writer submissions, not one atomic transaction. This increment deliberately completes a pair already started before stop; it does not create an atomic stop/write handshake. A Writer operation already submitted before the checkpoint still relies on the normal producer join and Writer drain.
- The optional SelfNarrative write is skipped when stop is observed after the pair.
- This does not establish repository-wide thread coverage or host-level shutdown safety.

## 4. Validation

Exact-head full-suite CI and baseline verification are required before merge. Regression tests use deterministic Events and mocked embeddings; no live model or database is required.

No runtime feature flag, cadence, similarity threshold, prompt, database schema, frozen specification, Master Roadmap, Gate 0 or Phase 1 authority changed.
