# G-84 follow-on — Flask request drain (2026-11-28)

## Observed lifecycle gap

`run.py` uses Flask's threaded development server. The SIGTERM handler executes on the main thread, but already-running Flask request handlers continue on worker threads while the handler drains AppState producers and Writers. Before this change, AppState could report all registered producers stopped even while an unrelated in-flight HTTP route was still using state or writing to a database.

The previous fixed 1.5-second in-flight-fire delay was only a timing guess. It did not identify whether requests were actually active, and it consumed time from the shared 12-second shutdown budget without proving quiescence.

## Bounded request gate

- Add a thread-safe `ShutdownGate` with atomic request admission, an active-request counter and a monotonic-deadline drain.
- Install it as the first Flask `before_request` hook and release admitted requests from `teardown_request`, including error paths.
- Once shutdown begins, reject every new request with HTTP 503; already-admitted requests are allowed to finish.
- Preserve a per-request label, worker-thread name and elapsed duration so a deadline failure identifies which requests remained active.
- The SIGTERM and SIGINT paths close request admission and wait for active requests using the same 12-second deadline already shared with producer and Writer shutdown.
- Only after the request drain succeeds does run.py stop the decoder and call `AppState.close(deadline=...)`. The clean marker remains last.
- If the request drain times out or errors, log the active count, skip AppState/marker success claims and exit non-zero.

This replaces the arbitrary 1.5-second delay with an observed request drain. It does not extend the shutdown deadline.

## Validation

`tests/test_shutdown_gate.py` covers deadline timeout, atomic rejection of new requests, and successful completion of an already-admitted request. `tests/test_appstate_close_runpy_producers.py` asserts the request drain occurs before AppState close and that the fixed delay is gone.

## Remaining boundary

The gate covers requests entering through this Flask application. It does not itself prove lifecycle behavior for an alternate external WSGI server, reverse-proxy workers, or direct non-HTTP callers. Those remain separate deployment/runtime census work. No route behavior changes during normal operation, no database schema or strike policy changes, and no frozen specification, Master Roadmap, Gate 0 or Phase 1 authority change.
