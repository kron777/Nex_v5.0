# G-84 shutdown deadline and truthful clean-marker correction — 2026-11-28

**Scope:** AppState producer quiescence → Writer drain → SIGTERM standby outcome.  
**Base snapshot:** main `5ba300779ff3081508e56b509d53a27846bf7c67` (includes merged PR #361 / G-84 step 3).  
**Candidate:** PR #370, branch `fix/g84-shutdown-report-deadline-2026-11-28`.  
**Method:** source trace and isolated regression tests; no live host/service shutdown was run.

## 1. Verified pre-change failure path

The inspected main source had four connected timing/authority defects:

1. `nex_keepalive.sh` sends SIGTERM to the child, waits 15 seconds, then force-kills it if still alive.
2. `run.py`'s SIGTERM handler wrote the clean-shutdown marker before its 1.5-second in-flight-fire delay and before calling `AppState.close()`.
3. `AppState.close()` bounded the registered producer joins to 5 seconds, but called each Writer's `close()` with its own default 10-second timeout. It caught and recorded Writer exceptions/timeouts but returned no aggregate outcome.
4. After `state.close()` returned, the SIGTERM handler logged a successful flush and called `os._exit(0)` regardless of whether a Writer had timed out.

The handler's 1.5-second delay plus the 5-second producer budget left at most 8.5 seconds before the keepalive's 15-second kill. A single Writer could wait 10 seconds; multiple Writer waits were sequential and had no shared remaining-time budget. Because the clean marker was already written and Writer failures were swallowed by AppState, a failed drain could be reported as clean.

The previous producer registry was also deliberately bounded: PR #361 added the four run.py-only EdgeGeneratorLoop, WorldPredictionLoop, SelfPredictionLoop and decoder producers, but no complete process-wide thread census had been established.

## 2. Correction in PR #370

- Define one 12-second monotonic shutdown budget, leaving a 3-second margin before the keepalive's 15-second forced-kill limit.
- Start the deadline at SIGTERM receipt, so the 1.5-second in-flight-fire delay consumes the same budget.
- Pass the absolute deadline into `AppState.close(deadline=...)`.
- Keep the producer phase capped at 5 seconds, but never beyond the remaining global budget.
- Pass the remaining global budget to each Writer close, including the beliefs `TaggingBeliefWriter` wrapper.
- Return a structured close report with success, elapsed/remaining time, deadline exhaustion, surviving producer names, producer stop/join errors, scheduler errors, Writer errors and Writer threads still alive.
- Do not write the clean-shutdown marker until the close report succeeds. Check that the marker itself persists successfully.
- On incomplete shutdown or marker failure, log the failure, leave the clean marker absent and exit non-zero. This prevents a failed drain from masquerading as clean.

## 3. Tests

- Existing producer tests now assert that stop/join failures are represented in the close report.
- New tests verify that sequential Writer closes receive a decreasing remaining budget and that a Writer timeout makes the aggregate report unsuccessful.
- The TaggingBeliefWriter wrapper is tested to forward the timeout to its inner Writer.
- A run.py source-structure regression test checks that the deadline begins at SIGTERM receipt, AppState close is called with that deadline, and the clean marker appears only after the successful report branch.

## 4. Boundaries and remaining risks

This correction makes the existing registered-producer shutdown outcome bounded and truthful. It does **not** prove every process thread is registered; a complete thread-start/stop/join census remains open. No live host shutdown, supervisor timing or actual Writer backlog test has been run.

A non-zero child exit may cause the keepalive to restart the child when the supervisor itself is not stopping. That is intentional fail-visible behaviour: no clean marker is written, so the next boot can classify the prior shutdown as unclean. The exact keepalive/supervisor interaction still needs a controlled host test.

The 12-second budget is an initial engineering margin derived from the current 15-second supervisor kill window, not a frozen specification threshold. Revisit it if the supervisor timeout changes or host measurements show the margin is insufficient.

No NEX processing policy, database schema, frozen S-01–S-25/M1.8 content, Master Roadmap, Gate 0 or Phase 1 authority is changed.
