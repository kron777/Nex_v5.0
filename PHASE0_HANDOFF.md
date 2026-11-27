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

The evidence snapshot and source-bounded report above remain pinned to their stated commits. Current remote main is now `46c743f9c0009e485e307a574be9cb2c6c2a9b39`.

- #189 manual reconciliation, #191 Moltbook responder persistence, #196 listener/poster persistence, #199 INDEX/handoff reconciliation, and #200 the resumption/identity/Fountain momentum/recursion-attribution migrations are merged.
- #200 exact-head CI run `45990854891` passed: **2,539 passed, 7 skipped, 40 subtests**, baseline OK. Mind-map verification: **30 nodes, 0 unverified, 14 dark, 2 blocked**.
- The two missing doctrine references (`VIRTUE_SLATE.md`, `mental_factors_inventory_alobha_spec.txt`) and overdue `p13_finitude` marker remain unresolved. They are not to be fabricated or date-advanced without source/owner evidence.
- The bounded one-pen migrations listed above are now merged. This does not establish that every write-capable connection in every `theory_x/` faculty has been audited; the full producer/consumer and persistence audit remains open.

### Additional source-to-consumer audit — Throw-Net trigger threshold (27 November)

- `run.py` constructs `TriggerDetector` with the canonical beliefs Reader/Writer and injects it into `CoherenceGate`. Gate REJECTs from non-Throw-Net sources are logged; `gui/server.py` also logs Chat gap deflections.
- `TriggerDetector.record_gate_reject()` returns true at 4 same-topic REJECTs/15 minutes; `record_gap_deflection()` returns true at 3 same-topic deflections/30 minutes. The Gate/Chat callers discard those return values.
- `pending_triggers()` selects every `fired=0` row, and `ThrowNetEngine.run_pending()` processes every returned row without checking the stored threshold count. Therefore, if `NEX5_THROWNET=1` starts the monitor, a single sub-threshold trigger can cause a session on the next monitor tick. This contradicts the documented threshold semantics and is a confirmed source-level consumer gap.
- The monitor is constructed but only started when `NEX5_THROWNET=1` in `run.py` / `gui/server.py`. The flag is registered in `nex_config.py` but absent from the tracked `nex_keepalive.sh` launch command; inherited service/parent environment and live state remain UNKNOWN.
- Existing isolated tests verify the detector's return thresholds, pending-row selection, and engine processing separately; they do not test threshold enforcement end-to-end. `RefinementEngine._r2()` also explicitly defaults to pass on a beliefs-read error (covered by `test_r2_default_pass_on_db_error`); this is documented behavior, not changed here.
- No runtime/DB inspection or activation was performed. Because fixing this would change autonomous behaviour, it remains a Gate 0 defect finding; no code/flag/threshold change is made.

### Further source audit findings (current main `46c743f9`)

#### G-68 — decryption ProbeRunner live-mutation and cleanup risk
- `decryption/probe_runner.py` is distinct from `theory_x.probes.probe_runner.ProbeRunner`, the separate normal-boot/API probe subsystem.
- The decryption runner defaults to `dry_run=False`. In that mode `_setup()` changes NEX mode through `/api/mode/set` and `_seed_prior_context()` writes synthetic `fountain_insight` beliefs through raw SQLite. `_teardown()` deletes injected IDs but does not restore the previous mode.
- `_remove_injected_beliefs()` clears its in-memory ID list in `finally` even if DELETE fails; a retry then loses the IDs. Process termination before `_teardown()` also bypasses cleanup. `dry_run=True` suppresses mode changes and synthetic writes/deletes but still performs read-only DB inspection for the maximum real belief ID.
- This utility is not imported by the normal `run.py` boot path inspected. It was not invoked; no synthetic rows or mode changes were made. Do not run against live NEX without explicit experiment approval and a verified disposable database/runtime.

#### G-69 — SurpriseLoop timestamp cursor can skip tied rows and failed promotions
- `theory_x/life/surprise_loop.py` selects up to 20 events ordered by `triggered_at`, then stores only the maximum timestamp as its cursor. More than 20 rows sharing the boundary timestamp can cause remaining tied rows to be skipped by the next strict-greater-than query.
- The loop advances `max_ts` after the exception handler even when a non-integrity write/conversion failure occurs, so the failed event can be permanently skipped rather than retried. PR #205 now tests only the first-run ten-minute window; it does not fix timestamp ties or failure retry semantics.
- PR #104 contains a stable-ID cursor/retry proposal but is on the stale `claude/nex-continuity-wire` branch. Because this changes which surprise events become beliefs, hold the correction for Gate 0 review and current-main carry-forward.

#### G-70 — M0.5 trace currently stops at speech-queue enqueue
- `theory_x/stage6_fountain/crystallizer.py` records the speech-queue enqueue decision in the current `influence_trace.py` sidecar. `speech/queue_consumer.py` records queue lifecycle state changes but has no `influence_trace` hooks for consumption, synthesis/playback outcome or failure.
- The current per-cycle `TraceContext` has no cross-thread queue-link registry, so the enqueue trace does not follow the item into the worker thread. Old PR #55 uses the superseded `substrate.trace_overlay` API and is not a safe carry-forward.
- This is an observability coverage gap, not a speech behaviour defect. Do not add substrate DB columns or alter speech behaviour by inference. If M0.5 acceptance requires playback lineage, design an in-memory/sidecar-only correlation mechanism with bounded retention and tests.

#### G-71 — WarrantRecorder rowid tie cursor is not stable across VACUUM
- Current `theory_x/stage_warrant/recorder.py` uses `(timestamp, rowid)` cursors for `belief_lineage` and `arc_members`, fixing the tied-timestamp page-boundary defect in G-53/PR #184.
- Both source tables have declared composite primary keys, but the current cursor tie-breaker is SQLite `rowid`, not the declared key; rowid may change during `VACUUM`. A persisted cursor can then skip or replay rows. PR #106 proposes a composite-key cursor but is based on the stale continuity branch and is not merged.
- This affects use-day measurement and potentially Warrant sustain/retirement accounting. No live table population or VACUUM event was inspected. Keep separate from #184, which fixed tie pagination but not rowid stability.

### Current-main one-pen and PR triage
- The six Stage-2 life loops (`pattern_loop`, `witness_loop`, `surprise_loop`, `remember_loop`, `wonder_loop`, `fetch_loop`) use shared Readers/Writers through `stage2_dynamic` wrappers. Identity (#200), affinity (#169), DailyLife (#168), scorecard and HotObserver (#202), Fountain momentum/recursion (#200), and all three Moltbook loops (#191/#196) are source-wired to canonical handles. The prior 25-Nov writer census is stale for these loop paths; the explicit decryption ProbeRunner remains a separate experimental raw-write exception. This is not a claim that the repository-wide write-path census is complete.
- Open proposals #99–#122 are based on `claude/nex-continuity-wire`, approximately 690 commits behind current main. They include belief eligibility/selection, dormancy, surprise retry/cursor, Warrant use-day cursor, Harmonizer coverage, Tier-6, RememberLoop, affinity, diversity and self-narrative changes. Do not merge the stale branches wholesale; Gate 0 review is required before behavioural/policy changes, followed by individual current-main carry-forward and exact-head tests.
- PR #142–#144 detailed audit documents remain on a stale branch; their G-51–G-58 summaries are already in the main backlog, but the detailed documents are not current-main evidence. PR #146 was superseded by current deterministic empty-window tests; #205 carries only the independent first-run-window test.



- No live host collection, runtime trace, database hash inventory, model digest or performance measurement was performed in this remote-source session. These remain **UNKNOWN**.
- RDO Stage 2–7 modules, documents and tests are present in current main. The historical Claude Stage 2–7 branches are divergent and approximately 475 commits behind; they are not merge candidates. RDO Stage 7's own handoff/status documentation still requires a real objective-to-delivery demonstration, a verified disposable test-execution boundary, host-only runtime observation and separate human acceptance. The independent Watcher handoff verifier is source/path-only; it does not run tests or establish runtime state.
- RDO v1.3/v1.4 precedence remains unresolved. The recovered v1.4 source metadata and founder recollection do not by themselves establish formal supersession; do not rewrite RDO specifications or stage documents on inference.



## Current status

| Roadmap deliverable | Status |
|---|---|
| M0.1 — repository identity | Remote main SHA recorded; current host checkout identity/cleanliness not collected |
| M0.1 — host/runtime/database/model measurements | **PARTIAL / UNKNOWN**; no current host collection or live DB hash inventory |
| M0.2 — test baseline | Current main `46c743f9`: 2,546 passed, 7 skipped, 45 subtests, baseline OK (exact-head run `45995284146`) |
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

1. Current-main CI for `46c743f9` is verified green (2,546 passed, 7 skipped, 45 subtests; baseline OK, run `45995284146`). The earlier `ae406fa8` result remains the historical evidence snapshot; do not conflate it with current main.
2. Scheduler overview documentation is corrected and merged in PR #153; its exact-head full suite is green.
3. Continue the forward/backward source audit across the remaining `theory_x/` faculties; distinguish wired loops from downstream consumers and measured effects.
4. The mind-map count discrepancy is closed (30 nodes, 5 arms, 4 findings). The consolidated source re-verification PR #185 is merged; current verifier result is 30 nodes, 0 unverified, 14 dark, 2 blocked. The 18 path/date warnings were cleared by source-anchor corrections. Keep the two missing doctrine references and overdue `p13_finitude` marker explicit; do not fabricate documents or advance the marker without source review.
5. Preserve the unresolved doctrine-reference and P13 evidence gaps as explicit founder-review items; do not silently remove them.
6. Review the G-53 PR #184 merged cursor migration against any future Warrant source-coverage changes; do not broaden the use-day eligibility set without a specification decision.
7. Obtain a fresh, authorised host-only collection for active checkout identity, service/process state, versions/model digest, performance and DB hashes. Do not copy private runtime data into Git.
8. Present the Reality Report, Crosswalk and verified defect backlog for Gate 0 founder review before any Phase 1 behavioural work.

## Do not cross this boundary

This handoff does not authorise enabling dark flags, running ablations, changing prompts/confidence/belief revision, changing Gate policy, starting/restarting services, writing to live substrate DBs, or claiming L4. Preserve the frozen S-01–S-25 specification/register. The separate V2.1 development proposal is not replaced or rewritten by these Phase 0 documents.
