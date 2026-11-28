# Shutdown request-drain versus voice-call timeout — 28 November 2026

**Base:** `kron777/Nex_v5.0` main at `81ec438a7be7fe3cc81112cbb39c715b76ffe026` (after #378 and #381 merges).  
**Scope:** source-level timing analysis only. No timeout, shutdown budget, retry policy, Writer behaviour or runtime setting changed.

## 1. Source evidence

- `gui/server.py` defines `_SHUTDOWN_TOTAL_BUDGET_S = 12.0`. The comment states that the budget covers the run.py in-flight-fire window, producer quiescence and Writer drains, leaving approximately three seconds before `nex_keepalive.sh`'s 15-second forced-kill limit.
- `run.py` begins one monotonic deadline when SIGTERM/SIGINT is received. It first calls `shutdown_gate.begin_shutdown(deadline)`. If request drain is unsuccessful, it logs the active request report and calls `os._exit(1)` before stopping the decoder, calling `AppState.close()` or writing the clean-shutdown marker.
- `gui/shutdown_gate.py` waits for admitted Flask requests until that same deadline. It rejects new requests with HTTP 503 after closing begins. It has no cancellation hook into the work performed by an admitted route.
- `voice/llm.py` implements the default VoiceClient request with `requests.post(..., timeout=120)`.
- The chat route calls `state.voice.speak()` for the initial response and may call it again for one anti-repeat retry and one provenance retry when `NEX5_CHAT_MEMORY=1` / `NEX5_PROVENANCE=1` and an admin session are present. These are sequential calls in the same admitted HTTP request. The tracked `nex_keepalive.sh` launch line explicitly sets both `NEX5_CHAT_MEMORY=1` and `NEX5_PROVENANCE=1`. Each retry remains admin-session and condition gated; actual host frequency is not measured. The inspected path has no SIGTERM-triggered cancellation of an in-flight VoiceClient request.

## 2. Timing consequence

The VoiceClient's per-request timeout (120 seconds) is ten times the total shutdown/request-drain budget (12 seconds). The inspected chat path can make the initial voice call plus one conditional anti-repeat retry and one conditional provenance retry sequentially. If both retries execute and each call stalls to its timeout, the theoretical cumulative voice-call timeout exposure is up to 360 seconds; this is a code-derived upper bound, not an observed latency. If an admitted chat request is still inside any VoiceClient call when shutdown begins and does not return within the remaining 12-second budget:

1. `ShutdownGate.begin_shutdown()` reports an incomplete drain.
2. `run.py` exits non-zero via `os._exit(1)`.
3. `AppState.close()` is not called, so its producer quiescence and Writer-drain protocol is not run.
4. The clean-shutdown marker is not written.
5. The supervisor's approximately 15-second limit can subsequently force-kill the child.

This is intentionally fail-closed with respect to the clean marker, but it is not a successful graceful shutdown. Depending on the exact point at which the request and background Writers are operating, queued work may not be drained before process exit. This source trace does **not** establish that data loss or database corruption actually occurs.

## 3. What remains unknown

- Actual latency distribution of the configured local voice model on the deployed host.
- How often admin-authenticated requests trigger the anti-repeat and provenance retry conditions, and their additional wall-clock cost.
- Whether the normal in-flight request usually completes within the 12-second drain budget.
- Whether a timed-out active request leaves queued Writer operations or partially completed multi-step work.
- Whether the live service manager and process use the exact repository configuration inspected here.

## 4. Next evidence-led experiment

On the authorized host, measure ordinary and worst-case chat latency (including enabled retries), then perform a controlled SIGTERM during an active voice request while observing active request labels, Writer queue depth, process exit code and clean-marker persistence. Use disposable data or a restorable snapshot.

Only after this observation choose between an explicit request-cancellation path, a revised shutdown/supervisor budget, a bounded response abort, or accepting a non-clean exit for long-running requests. Do not silently reduce the 120-second VoiceClient timeout or increase the 12/15-second shutdown budgets without latency and operational evidence.

## 5. Authority boundary

This is an operational lifecycle issue, not a reason to let Mind Aspects control shutdown or action execution. Preserve the separation between interpretive cognition, typed operations, capability validation, approval authority, execution and post-execution verification. No frozen specification, roadmap, Gate 0 or Phase 1 authority changed.
