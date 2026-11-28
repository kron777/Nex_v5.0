# Stop-aware predictor loops during shutdown — 28 November 2026

**Base:** `kron777/Nex_v5.0` main at `d7d204c24807eb3e46c37d70f2c1dcaae63830dc`.  
**Scope:** add cooperative stop checkpoints around the two run.py-managed prediction loops that can perform network I/O and then write to shared Writers. No cadence, request timeout, feature flag or shutdown budget changed.

## 1. Source evidence

- The tracked `nex_keepalive.sh` launch line sets both `NEX5_WORLD_PRED=1` and `NEX5_SELF_PRED=1`.
- `run.py` constructs `WorldPredictionLoop` and `SelfPredictionLoop` under those flags and passes both into `AppState`. AppState signals their `stop()` methods and joins their worker threads during producer quiescence.
- The producer join allowance is at most five seconds, within the 12-second total shutdown deadline.
- `WorldPredictionLoop.tick()` previously had no stop checkpoints once a tick began. Its `make_voice_prediction()` path can perform a 10-second price fetch, a 10-second recent-context fetch and a 30-second local voice request, then write paired voice/random predictions and a trust stamp.
- `SelfPredictionLoop.tick()` previously continued through multiple prediction/reconciliation stages after a stop request. Its `make_self_prediction()` reads the fountain status endpoint with a 10-second timeout and then writes prediction rows; subsequent tick stages can also write to shared Writers.
- Both loop `stop()` methods set an event but cannot interrupt an HTTP request already in progress.

## 2. Bounded correction

- Pass each loop's stop event into its active tick.
- Check the event after the WorldPredictionLoop's due-resolution stage and after each blocking network operation in `make_voice_prediction()`, before beginning its paired prediction writes.
- Check the event after the SelfPredictionLoop's status fetch and between its sequential prediction/reconciliation stages, before starting additional writes.
- Preserve direct/standalone function calls by making the stop-event argument optional.
- Add deterministic tests that signal stop while the world voice call and self status read are blocked, then verify no prediction write begins after those calls return; also verify each tick stops before starting its next stage.

## 3. Boundaries and residuals

- These checks do not cancel an in-flight network request. World prediction can still remain blocked for up to its 10/10/30-second request sequence; self prediction's status fetch can remain blocked for up to 10 seconds. Either can outlive the five-second producer join and still cause a non-clean shutdown.
- The correction prevents the observed long-blocking paths from proceeding into new write stages after stop is seen. It is not an atomic stop/write handshake; a write already started before the stop checkpoint still relies on producer join.
- No timeout, interval, prediction policy, feature flag, Writer order or database schema changed.
- This does not establish that every producer in NEX has been audited or that host-level shutdown is proven.

## 4. Validation

The new blocked-call tests and exact-head full-suite CI/baseline verification are required before merge.
