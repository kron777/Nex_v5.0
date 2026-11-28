# SenseScheduler stop-during-poll submission race — 28 November 2026

**Base:** `kron777/Nex_v5.0` main at `81ec438a7be7fe3cc81112cbb39c715b76ffe026`.  
**Scope:** prevent a scheduler adapter from submitting poll results after its stop event is raised while the poll is in progress. No feed policy, cadence, timeout, shutdown budget or database schema changed.

## 1. Source evidence

- `theory_x/stage1_sense/scheduler.py` runs each adapter as `poll()` followed by `submit(events)`. Before this correction, it did not recheck the worker stop event between those calls.
- `SenseScheduler.shutdown()` sets each adapter worker's stop event. It does not interrupt a poll already blocked in I/O.
- `theory_x/stage1_sense/base.py` uses `requests.get` with a 10-second connect and 20-second read timeout for the default fetch path.
- `AppState.close()` gives producer quiescence at most five seconds (subject to the remaining 12-second total deadline), then attempts Writer closure. A scheduler thread still in poll can therefore outlive the producer-join window.
- If that poll later returned before process exit, the old loop would proceed to `adapter.submit(events)` even though shutdown had already been requested. This creates a late Writer-submission window.

## 2. Bounded correction

After `poll()` returns, the worker now checks `self._stop.is_set()`. If shutdown began during the poll, it discards those just-returned events and exits instead of starting a new Writer submission.

The new regression test blocks inside a fake adapter's poll, signals scheduler shutdown, releases the poll, and asserts that the worker exits without calling submit.

## 3. Boundaries and residuals

- The correction does not cancel or interrupt an in-flight network poll. A slow poll can still outlive the five-second producer join and cause the overall close report to fail; the process remains non-clean and exits through the existing fail-closed path.
- A submission that has already started before the stop event is set is still allowed to finish; producer join remains responsible for waiting for it.
- The test covers stop arriving while poll is blocked. It does not claim that every producer in the process is registered, that every adapter is interruptible, or that host-level shutdown is proven.
- No poll cadence, retry policy, feed enablement or Writer ordering changed.

## 4. Validation

The new isolated regression test and exact-head full-suite CI/baseline verification are required before merge.
