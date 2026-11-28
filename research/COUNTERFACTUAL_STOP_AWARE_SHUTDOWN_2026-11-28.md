# CounterfactualNode stop-aware candidate processing — 28 November 2026

**Base:** `kron777/Nex_v5.0` main at `55fd635bd535d15ece3e3878bf1e71621f56fa7c`.  
**Scope:** add cooperative shutdown checkpoints to the always-started CounterfactualNode cycle. No candidate scoring, gate outcome, promotion policy, cadence, feature flag, prompt or database schema changed.

## 1. Source evidence

- `run.py` constructs CounterfactualNode, starts its 300-second loop and passes it to AppState.
- `AppState._quiesce_producers()` calls `stop()` and joins the node's `_thread`.
- Before this change, the stop Event interrupted only the interval wait; the active `tick()` / `_process_one()` did not receive it.
- `_process_one()` reads the oldest open problem, fetches up to ten belief candidates via TimeFetch, scores them via RefinementEngine, then loops through buildable candidates and calls `CoherenceGate.check()`. Accepted candidates are inserted into beliefs through the shared Writer.
- TimeFetch and RefinementEngine use synchronous substrate reads. CoherenceGate can synchronously perform Writer-backed work through its resolver. The producer join allowance is at most five seconds.

## 2. Bounded correction

- Pass the existing stop Event from the loop into its worker-owned tick and processing method.
- Preserve direct `tick(context)` and `_process_one()` calls with optional keyword-only stop events.
- Check stop before the initial read, after problem retrieval, after candidate fetch, after scoring, before each gate call, and after gate returns before the accepted-belief insertion.
- If stop arrives during TimeFetch or RefinementEngine, allow that synchronous operation to return but do not start the next stage.
- If stop arrives during Gate.check, allow the synchronous gate call to return but do not start the subsequent belief insertion.
- Add deterministic tests for stop during candidate fetch, stop during gate check, and already-stopped tick.

## 3. Boundaries and residuals

- Database reads and Gate.check are not cancellable by this Event. A call already in progress may continue until it returns.
- Gate.check can perform its own synchronous Writer-backed work; this increment cannot roll back or interrupt that work if stop arrives during the call.
- A Writer insertion already started before stop still relies on producer join and normal Writer draining.
- This is cooperative stage-boundary control, not an atomic stop/write handshake or proof of complete process quiescence.

## 4. Validation

Exact-head full-suite CI and baseline verification are required before merge. Regression tests use Events and mocked services; they do not require a live database or model.

No frozen S-01–S-25/M1.8 specification, Master Roadmap, Gate 0, Phase 1 authority, runtime flag, cadence or database schema changed.
