# PredictiveSubstrate stop-aware tick — 28 November 2026

**Base:** `kron777/Nex_v5.0` main at `55fd635bd535d15ece3e3878bf1e71621f56fa7c`.  
**Scope:** cooperative stop checkpoints through the always-started PredictiveSubstrate verify/predict cycle. No prediction formula, thresholds, time window, embedding model, flags, interval or schema changed.

## 1. Source evidence

- `run.py` always constructs PredictiveSubstrate, starts its 300-second loop and passes it to AppState.
- `AppState._quiesce_producers()` calls `stop()` and joins its worker thread.
- Before this change, the stop Event interrupted only the interval wait; the active `tick()` did not receive it.
- Each tick verifies pending predictions, then generates an internal-belief prediction and an external-input prediction.
- Prediction generation can embed up to ten recent beliefs, multiple open-problem titles, sense/chat inputs and representative candidates. It then generates tags and writes a prediction row.
- Verification iterates all pending predictions, reads the relevant window, embeds each candidate item, generates tags, writes a `surprise_events` row and updates the original prediction row.
- The embedding calls are synchronous and are not cancelled by the worker's stop Event. The AppState producer join allowance is at most five seconds.

## 2. Bounded correction

- Pass the existing stop Event from the loop into `tick()`, `_verify()`, `_verify_one()`, both prediction generators, representative-content selection and prediction persistence.
- Preserve existing direct calls with optional keyword-only stop events.
- Check stop before and after substrate reads, before and after each embedding, between the verify/internal/external stages, before tag generation and before starting each prediction write.
- If stop arrives during an embedding, allow the current embedding to return but discard the partial centroid/verification result and do not start later embeddings or writes.
- Treat each prediction row write as one already-started operation.
- Treat the surprise-event insert plus corresponding prediction update as one logical verification commit pair; once the first Writer call starts, finish the second so the prediction is not intentionally left half-verified.
- Preserve accurate completed-work counters when stop arrives during an already-started persistence operation.
- Add deterministic tests for stop during internal embedding, stop during verification embedding, stop between tick stages, and stop during the verification commit pair.

## 3. Boundaries and residuals

- Embedding and Reader calls are not cancelled. A call already in progress must return before the Event can be observed.
- The two verification Writer submissions are separate operations, not one database transaction. This change does not add rollback or atomicity.
- If stop arrives after a prediction Writer call has started, that row may complete after the signal.
- Tag generation is not cancelled; the Event is checked after it returns and before the Writer call.
- This does not prove host-level shutdown safety or that every other producer is quiescent.

## 4. Validation

Exact-head full-suite CI and baseline verification are required before merge. Tests use mocked Readers/Writers and deterministic Events; no live embedding model or database is required.

No prediction thresholds, weights, horizon, schema, feature flags, frozen S-01–S-25/M1.8 specification, Master Roadmap, Gate 0 or Phase 1 authority changed.
