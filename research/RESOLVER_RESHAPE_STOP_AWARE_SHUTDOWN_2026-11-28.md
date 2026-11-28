# HoldingZoneResolver reshape stop-aware shutdown — 28 November 2026

**Base:** `kron777/Nex_v5.0` main at `93f39f8eb12a24ce703e6cc76c4e4c1d4be71872`.  
**Scope:** prevent an LLM-backed held-thought reshape operation from continuing into later gate/completion stages after the resolver's existing stop Event is observed. No prompt, reshape threshold, retry policy, cadence, request timeout, feature flag or database schema changed.

## 1. Source evidence

- `run.py` starts `HoldingZoneResolver.start_loop()` before the GUI and passes the resolver to `AppState`.
- `AppState._quiesce_producers()` calls `resolver.stop_loop()` and joins its `_thread`.
- The resolver loop waits on its stop Event, but previously called `tick()` without passing the Event into the active tick.
- `tick()` calls `fade_stale()`, then `_process_reshape_pending()`.
- `_process_reshape_pending()` loads up to ten pending rows, calls `ReshapeTransformer.transform()`, submits the transformed packet through `CoherenceGate.check()`, then marks the row reshaped/failed in the holding-zone Writer.
- `ReshapeTransformer.transform()` calls the shared `VoiceClient.speak()`. The default request implementation uses `requests.post(..., timeout=120)`.
- The AppState producer join allowance is at most five seconds. The synchronous VoiceClient call cannot be interrupted by the resolver stop Event.

## 2. Bounded correction

- Pass the resolver's existing stop Event into its worker-owned `tick()`.
- Preserve the public `tick(context)` call shape and standalone `_process_reshape_pending()` / `transform()` use by making the stop Event keyword-only and optional.
- Check stop before starting reshape work, before the model request, after the model returns, before gate submission, and after gate submission before the completion Writer operation.
- If shutdown begins while the model call is blocked, discard its returned text and do not submit it through the gate or mark the row complete/failed.
- If shutdown begins while the gate is executing, do not start the subsequent reshape-completion write.
- Add deterministic tests for stop during the model call, stop during gate checking, and stop during the preceding fade stage.

## 3. Boundaries and residuals

- The in-flight VoiceClient call is not cancelled. It can remain blocked up to its 120-second request timeout, outliving the five-second producer join and causing the existing non-clean shutdown path.
- `CoherenceGate.check()` is synchronous and may perform Writer-backed work through `resolver.on_gate_accept()`. If stop arrives during that call, the call itself is not interrupted; this correction only prevents the subsequent reshape-completion write. An atomic stop/write handshake or cancellable gate transaction is not introduced.
- The checks are cooperative checkpoints, not a proof that all direct SQLite/Writer side effects are quiescent.
- No other producer, shutdown budget, timeout or feature flag was changed.

## 4. Validation

Exact-head full-suite CI and baseline verification are required before merge. The regression tests use deterministic Events to force shutdown during the blocking call and gate stage.

## 5. Follow-on

Continue tracing each enabled producer from its blocking operations to its first subsequent Writer/direct-SQLite side effect. Prioritize operations whose timeouts exceed the five-second join allowance. Do not increase the 12-second application or 15-second supervisor budgets without host measurements.
