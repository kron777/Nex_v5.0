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

The source report above remains pinned to `ae406fa8`. Main has since advanced to `847cf4f` through merged PRs #168, #174, #175, #180 and #184. A focused current-main read found:

- PR #168 migrated `expectations.record_canaries()` to the shared conversations Writer; `daily_life.py` passes that Writer.
- `daily_life.py` calls `learning_guards.run()`; the launcher does not set `NEX5_LEARN_RATIO_SUBTRACT` or `NEX5_LEARN_ATTRIBUTION_SUBTRACT`, so the subtraction action is not armed by this launcher. PR #180 is merged and passes exact-head run #1493 (2,522 passed, 7 skipped, 40 subtests): it routes `record_tick()`, `subtract()` and `revert_subtraction()` through Writers and passes the shared beliefs/conversations Writers from DailyLife.
- `learning_guards.cap_blocks()` and Expectations `ingest()`/`reconcile()`/`_learn()` are covered by the pending G-65 migration PR #183, which adds a serialized conversation-Writer transaction and routes belief updates through the beliefs Writer while preserving cap-hit/learning-log transaction coupling.
- The current launcher sets `NEX5_RECONCILER=1` and `NEX5_EXPECT_LEARN=1`, but the audited `run.py` contains no Expectations/reconcile call; `daily_life.py` imports only `record_canaries` from that module. The flags are present in launch configuration, but no boot invocation was found in the audited entry path. This is not proof about any external scheduler or an already-running process.
- G-64's scheduled tick/subtraction/revert migration is merged. G-65 remains a pre-activation source-level persistence blocker pending PR #183 CI. G-53's tied-timestamp pagination fix is merged in PR #184 (2,524 passed, 7 skipped, 40 subtests); the use-day eligibility set and Warrant policy were not changed. Do not enable or wire the reconciler as part of Phase 0. Preserve the existing cross-database failure boundary.

These are post-snapshot observations, not retroactive changes to the `ae406fa8` report or the frozen specifications.

## Current status

| Roadmap deliverable | Status |
|---|---|
| M0.1 — repository identity | Remote main SHA recorded; current host checkout identity/cleanliness not collected |
| M0.1 — host/runtime/database/model measurements | **PARTIAL / UNKNOWN**; no current host collection or live DB hash inventory |
| M0.2 — test baseline | Current main `ae406fa8`: 2,508 passed, 7 skipped, 40 subtests, baseline OK (run `45951932639`) |
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

1. Current-main CI for `ae406fa8` is verified green (2,508 passed, 7 skipped, 40 subtests; baseline OK). The older run `45939220368` was on pre-merge parent `612022`, not on merge commit `66a9796`.
2. Scheduler overview documentation is corrected and merged in PR #153; its exact-head full suite is green.
3. Continue the forward/backward source audit across the remaining `theory_x/` faculties; distinguish wired loops from downstream consumers and measured effects.
4. The mind-map count discrepancy is closed (30 nodes, 5 arms, 4 findings). Both `meta.doctrine` references are confirmed absent from repository history; retain the warnings rather than deleting or inventing replacement documents. `p13_finitude` was source-reverified and merged in PR #174; preserve `dark: true` and the past-due `UNBLOCK 2026-11-21` marker. G-66 established that the 58 STALE dates in run `45951932639` were unreliable because the CI checkout was shallow. PR #175 merged the full-history checkout and guard; exact-head run #1476 (`45968094769`) passed with 2,514 passed, 7 skipped and 40 subtests, but still printed 18 path/date warnings plus the two missing-doctrine warnings and overdue p13 marker. PR #179 consolidates source re-verification for P1/P6/dṛṣṭi, alobha, karuṇā, upekṣā, apramāda, mana, smṛti, vitarka/vicāra, P2/P3/P8, p13, kaukrtya and hṛī/apatrāpya plus the remaining reviewed nodes; its exact-head full suite is pending. Because PR #183 changes `substrate/writer.py` and `theory_x/stage_world/expectations.py`, revalidate the P1/Drsti source line anchors if #183 merges before #179. PR #181 isolates the remaining vedana valence/steering boundary (CI pending). PR #178 is a passing p8-only backup now covered by #179 and will be closed after #179 passes. PRs #176 and #177 were closed as superseded. Review #179's verifier output before claiming the remaining warnings cleared.
5. Verify PR #183's exact-head CI and transaction/failure-order tests; keep G-65 dormant and do not wire the reconciler.
6. Review the G-53 PR #184 merged cursor migration against any future Warrant source-coverage changes; do not broaden the use-day eligibility set without a specification decision.
7. Obtain a fresh, authorised host-only collection for active checkout identity, service/process state, versions/model digest, performance and DB hashes. Do not copy private runtime data into Git.
8. Present the Reality Report, Crosswalk and verified defect backlog for Gate 0 founder review before any Phase 1 behavioural work.

## Do not cross this boundary

This handoff does not authorise enabling dark flags, running ablations, changing prompts/confidence/belief revision, changing Gate policy, starting/restarting services, writing to live substrate DBs, or claiming L4. Preserve the frozen S-01–S-25 specification/register. The separate V2.1 development proposal is not replaced or rewritten by these Phase 0 documents.
