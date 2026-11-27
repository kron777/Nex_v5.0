# NEX v5.0 — Phase 0 Mainline Handoff

**Date:** 27 November 2026  
**Repository:** https://github.com/kron777/Nex_v5.0  
**Evidence snapshot:** `main` at `ae406fa8fcb1abdf25cdf4ae1bd65333e1148ca8`  
**Gate 0:** **PENDING — founder review required**

## Read these together

- `NEX_REPOSITORY_REALITY_REPORT.md` — mainline source/CI reality and host/runtime unknowns.
- `NEX_ARCHITECTURE_CROSSWALK_v2.md` — source boot graph, key producer/consumer paths and partial faculty crosswalk.
- `NEX_PHASE0_VERIFIED_DEFECT_BACKLOG_2026-11-27.md` — verified discrepancies and unresolved evidence gaps.
- `ADR-001.md` — M0.5 trace mechanism and rollback.


## Post-snapshot current-main follow-up (27 November 2026)

The source report above remains pinned to `ae406fa8`. Main has since advanced to `99ae476` through merged PRs #168, #174, #175, #180, #183 and #184. A focused current-main read found:

- PR #168 migrated `expectations.record_canaries()` to the shared conversations Writer; `daily_life.py` passes that Writer.
- `daily_life.py` calls `learning_guards.run()`; the launcher does not set `NEX5_LEARN_RATIO_SUBTRACT` or `NEX5_LEARN_ATTRIBUTION_SUBTRACT`, so the subtraction action is not armed by this launcher. PR #180 is merged and passes exact-head run #1493 (2,522 passed, 7 skipped, 40 subtests): it routes `record_tick()`, `subtract()` and `revert_subtraction()` through Writers and passes the shared beliefs/conversations Writers from DailyLife.
- PR #183 is merged and passes exact-head run #1519 (2,525 passed, 7 skipped, 40 subtests). It adds a serialized conversation-Writer transaction for Expectations ingestion/reconciliation, routes belief updates through the beliefs Writer, and keeps cap-hit/learning-log writes in the same conversations transaction.
- The current launcher sets `NEX5_RECONCILER=1` and `NEX5_EXPECT_LEARN=1`, but the audited `run.py` contains no Expectations/reconcile call; `daily_life.py` imports only `record_canaries` from that module. The flags are present in launch configuration, but no boot invocation was found in the audited entry path. This is not proof about any external scheduler or an already-running process.
- G-64 and G-65 source-level persistence migrations are merged. G-53's tied-timestamp pagination fix is merged in PR #184 (2,524 passed, 7 skipped, 40 subtests); the use-day eligibility set and Warrant policy were not changed. No reconciler activation is authorized. Preserve the existing cross-database failure boundary.

These are post-snapshot observations, not retroactive changes to the `ae406fa8` report or the frozen specifications.

## Post-snapshot current-main follow-up (27 November 2026, after #200)

The evidence snapshot and source-bounded report above remain pinned to their stated commits. Current remote main is now `5d7f4e28eb6760d206eed455429c90e967a5bf10`.

- #189 manual reconciliation, #191 Moltbook responder persistence, #196 listener/poster persistence, #199 INDEX/handoff reconciliation, and #200 the resumption/identity/Fountain momentum/recursion-attribution migrations are merged.
- #200 exact-head CI run `45990854891` passed: **2,539 passed, 7 skipped, 40 subtests**, baseline OK. Mind-map verification: **30 nodes, 0 unverified, 14 dark, 2 blocked**.
- The two missing doctrine references (`VIRTUE_SLATE.md`, `mental_factors_inventory_alobha_spec.txt`) and overdue `p13_finitude` marker remain unresolved. They are not to be fabricated or date-advanced without source/owner evidence.
- The bounded one-pen migrations listed above are now merged. This does not establish that every write-capable connection in every `theory_x/` faculty has been audited; the full producer/consumer and persistence audit remains open.
- No live host collection, runtime trace, database hash inventory, model digest or performance measurement was performed in this remote-source session. These remain **UNKNOWN**.
- RDO Stage 2–7 modules, documents and tests are present in current main. The historical Claude Stage 2–7 branches are divergent and approximately 475 commits behind; they are not merge candidates. RDO Stage 7's own handoff/status documentation still requires a real objective-to-delivery demonstration, a verified disposable test-execution boundary, host-only runtime observation and separate human acceptance. The independent Watcher handoff verifier is source/path-only; it does not run tests or establish runtime state.
- RDO v1.3/v1.4 precedence remains unresolved. The recovered v1.4 source metadata and founder recollection do not by themselves establish formal supersession; do not rewrite RDO specifications or stage documents on inference.



## Current status

| Roadmap deliverable | Status |
|---|---|
| M0.1 — repository identity | Remote main SHA recorded; current host checkout identity/cleanliness not collected |
| M0.1 — host/runtime/database/model measurements | **PARTIAL / UNKNOWN**; no current host collection or live DB hash inventory |
| M0.2 — test baseline | Current main `5d7f4e28`: 2,539 passed, 7 skipped, 40 subtests, baseline OK (exact-head run `45990854891`) |
| M0.3/M0.4 — crosswalk and spec reconciliation | **PARTIAL**; source boot and Chat/Fountain paths are mapped, not every faculty's complete producer/consumer DAG |
| Roadmap v3.0 M0.5 — causal trace | **IMPLEMENTED / MERGED**, default OFF, L3 fixture evidence |
| M0.5 live L4 capture | **UNKNOWN**; no live runtime context enabled |
| V2.1 M0.5 six doctrine questions | Not claimed complete; separate deliverable from roadmap v3.0 M0.5 |
| Scheduler docs | **CORRECTED / MERGED** in PR #153; exact-head full suite passed |
| Gate 0 | **PENDING founder review** |

## Important distinctions

1. The 25-Nov Reality Report/Crosswalk describe a particular host checkout on `claude/nex-continuity-wire`. They are historical host observations and must not be confused with this remote `main` snapshot.
2. A 28-adapter source inventory does not prove all external feeds poll successfully. A daemon loop wired in source does not prove a host worker is alive. Static source, controlled tests and live runtime evidence are distinct.
3. The mind map is a descriptive index, and `mind_map.py` has a static AST guard over configured runtime roots. That guard is not universal proof against every dynamic/external authority path.
4. Coherence Gate's current exception fallback is fail-open (ACCEPT with `gate_error_fallback`). It has been documented, not changed.
5. M0.5 tracing records semantic stages/parents and Writer deltas in a sidecar; it does not write trace rows into SQLite. The overlay is OFF by default and was not enabled in a live NEX process.

## Next Phase 0 actions

1. Current-main CI for `5d7f4e28` is verified green (2,539 passed, 7 skipped, 40 subtests; baseline OK, run `45990854891`). The earlier `ae406fa8` result remains the historical evidence snapshot; do not conflate it with current main.
2. Scheduler overview documentation is corrected and merged in PR #153; its exact-head full suite is green.
3. Continue the forward/backward source audit across the remaining `theory_x/` faculties; distinguish wired loops from downstream consumers and measured effects.
4. The mind-map count discrepancy is closed (30 nodes, 5 arms, 4 findings). The consolidated source re-verification PR #185 is merged; current verifier result is 30 nodes, 0 unverified, 14 dark, 2 blocked. The 18 path/date warnings were cleared by source-anchor corrections. Keep the two missing doctrine references and overdue `p13_finitude` marker explicit; do not fabricate documents or advance the marker without source review.
5. Preserve the unresolved doctrine-reference and P13 evidence gaps as explicit founder-review items; do not silently remove them.
6. Review the G-53 PR #184 merged cursor migration against any future Warrant source-coverage changes; do not broaden the use-day eligibility set without a specification decision.
7. Obtain a fresh, authorised host-only collection for active checkout identity, service/process state, versions/model digest, performance and DB hashes. Do not copy private runtime data into Git.
8. Present the Reality Report, Crosswalk and verified defect backlog for Gate 0 founder review before any Phase 1 behavioural work.

## Do not cross this boundary

This handoff does not authorise enabling dark flags, running ablations, changing prompts/confidence/belief revision, changing Gate policy, starting/restarting services, writing to live substrate DBs, or claiming L4. Preserve the frozen S-01–S-25 specification/register. The separate V2.1 development proposal is not replaced or rewritten by these Phase 0 documents.
