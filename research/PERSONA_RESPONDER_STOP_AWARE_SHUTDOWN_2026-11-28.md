# PersonaResponderLoop stop-aware write boundary — 28 November 2026

**Base:** `kron777/Nex_v5.0` main at `a3fd532e12cbc84fa9505819ce475eef6101a06c` (after #388 and #389).  
**Scope:** prevent the enabled persona-responder producer from starting new Writer-backed work after shutdown is observed. No response policy, prompt, interval, request timeout, feature flag or database schema changed.

## 1. Source evidence

- The tracked `nex_keepalive.sh` launch line sets `NEX5_PERSONA_RESPONDER=1`.
- `run.py` constructs `PersonaResponderLoop` under that flag and registers it with `AppState` for stop/join.
- The loop performs its first tick immediately on startup, then waits for its interval.
- `PersonaResponderLoop.tick()` calls `one_exchange()`. That function reads recent NEX thoughts, calls `_ask_persona()` with a default 30-second HTTP timeout, then may write a rejected reply to the dynamic Writer, a successful reply to the sense Writer, and (when social-depth is enabled) updated interlocutor state to the conversations Writer.
- Before this correction, the stop event interrupted only the interval wait. It was not passed into `tick()`, `one_exchange()` or `_ask_persona()`; a model call returning after stop could proceed into those writes.
- AppState's producer join allowance is at most five seconds, shorter than the model-call timeout.

## 2. Bounded correction

- Resolve the loop's existing stop event inside `tick()`, preserving direct `tick()` calls.
- Pass it through `one_exchange()` and `_ask_persona()` only when present, preserving standalone/CLI calls.
- Check stop before database reads and before starting the model request; check again after the model response and before reply-bouncer/writer work.
- If stop arrives after the reply write but before social-depth state evolution, skip that subsequent state write.
- Add deterministic tests for stop during a blocked model call and for a model call invoked after stop.

## 3. Boundaries and residuals

- The in-flight HTTP call is not cancelled. It can still outlive the five-second producer join and cause the existing non-clean shutdown path.
- The checks prevent the observed model-return path from starting new writes after stop is seen. They are not an atomic stop/write handshake; a Writer operation already started before the stop checkpoint still relies on producer join.
- No persona prompt, response policy, interval, timeout, feature flag, Writer ordering or schema changed.
- This does not establish that every background producer has been audited or that host-level shutdown is proven.

## 4. Validation

The new blocked-call tests and exact-head full-suite CI/baseline verification are required before merge.
