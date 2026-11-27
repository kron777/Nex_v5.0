# NEX v5.0 — Phase 0 Mainline Handoff

**Date:** 27 November 2026  
**Repository:** https://github.com/kron777/Nex_v5.0  
**Evidence snapshot:** `main` at `e78773def4549f646257945e5886ec71a7837374`  
**Gate 0:** **PENDING — founder review required**

## Read these together

- `NEX_REPOSITORY_REALITY_REPORT.md` — mainline source/CI reality and host/runtime unknowns.
- `NEX_ARCHITECTURE_CROSSWALK_v2.md` — source boot graph, key producer/consumer paths and partial faculty crosswalk.
- `NEX_PHASE0_VERIFIED_DEFECT_BACKLOG_2026-11-27.md` — verified discrepancies and unresolved evidence gaps.
- `ADR-001.md` — M0.5 trace mechanism and rollback.


## Latest current-main continuation — 27 November 2026

**Evidence snapshot:** `main` at `c80d9dbb878ac15a39d6707a9c89ab2a51f8518c`. The exact-head full baseline passed: **2,590 passed, 7 skipped, 45 subtests** (run `46014884835`).

### Integrated persistence and cursor corrections

- **PR #243 — shared `daemon_kv` schema/migration:** merged. Fresh databases receive the canonical `key/value/updated_at` table; legacy databases gain `updated_at` additively without losing existing checkpoint rows.
- **PR #248 — WorldPredictionLoop AppState handles:** merged. The gated loop now uses AppState-owned conversations Writer/Reader and beliefs Reader through prediction, calibration, persistence, resolution and scorecard paths. `NEX5_WORLD_PRED` remains OFF; no loop was started.
- **PR #253 — Warrant use-day cursors:** merged. Lineage and arc membership now page by event time plus declared composite-key tie-breakers, avoiding hidden-rowid remapping and late additions to older arc/child keys. The Warrant gate remains OFF. Query-plan/performance on live table sizes is not yet measured.

### Current open work

- **PR #256 — RDO experiment-registry fail-closed tests:** tests-only current-main replay; exact-head full-suite CI pending. No production eligibility or experiment state changes.
- **PR #257 — SurpriseLoop loss-safe event delivery:** current-main replay; exact-head CI pending and **Gate 0 HOLD**. The event-ID cursor/retry correction can allow previously skipped events into the belief corpus. The legacy migration replays rows at/after the cutoff but does not recover rows strictly older than the old timestamp cursor. Founder approval is required before merge/deployment.
- **PR #258 — living manual/backlog/handoff reconciliation:** documentation-only current-main update; exact-head CI pending.

### Defect/evidence status updates

- G-53 (timestamp-only Warrant cursor ties) and G-71 (hidden-rowid cursor stability) are **closed by PR #253**; this does not close Warrant eligibility or use-source questions.
- G-69 (SurpriseLoop event loss) remains **Gate 0 held** pending explicit founder approval.
- G-70 speech trace: PR #261 proposes a bounded process-local correlation bridge and parent-linked consumer events; exact-head full-suite run `46018844996` is in progress after the disposable image build. It is draft/unmerged and does not establish acoustic confirmation or live L4 capture.
- G-73 dormancy coverage/ownership is recorded in the current defect backlog. PR #102/#145 remain older-base work: scanner rotation, eligibility filters, ClockRunner persistence and the duplicate DiversityLoop/ClockRunner ownership question require current-main revalidation and policy review. The PR #102 final Fountain injection query also needs a retired-marker recheck.

The consolidated S-01–S-25 register, roadmap, phase gates and cognitive policy remain untouched. Gate 0 remains pending; Phase 1 is not authorised. No live host activation, database contents, service state, acoustic output or behavioural benefit is claimed.

## Post-snapshot current-main follow-up (27 November 2026)

The source report above remains pinned to `ae406fa8`. Main has since advanced to `99ae476` through merged PRs #168, #174, #175, #180, #183 and #184. A focused current-main read found:

- PR #168 migrated `expectations.record_canaries()` to the shared conversations Writer; `daily_life.py` passes that Writer.
- `daily_life.py` calls `learning_guards.run()`; the launcher does not set `NEX5_LEARN_RATIO_SUBTRACT` or `NEX5_LEARN_ATTRIBUTION_SUBTRACT`, so the subtraction action is not armed by this launcher. PR #180 is merged and passes exact-head run #1493 (2,522 passed, 7 skipped, 40 subtests): it routes `record_tick()`, `subtract()` and `revert_subtraction()` through Writers and passes the shared beliefs/conversations Writers from DailyLife.
- PR #183 is merged and passes exact-head run #1519 (2,525 passed, 7 skipped, 40 subtests). It adds a serialized conversation-Writer transaction for Expectations ingestion/reconciliation, routes belief updates through the beliefs Writer, and keeps cap-hit/learning-log writes in the same conversations transaction.
- The current launcher sets `NEX5_RECONCILER=1` and `NEX5_EXPECT_LEARN=1`, but the audited `run.py` contains no Expectations/reconcile call; `daily_life.py` imports only `record_canaries` from that module. The flags are present in launch configuration, but no boot invocation was found in the audited entry path. This is not proof about any external scheduler or an already-running process.
- G-64 and G-65 source-level persistence migrations are merged. G-53's tied-timestamp pagination fix is merged in PR #184 (2,524 passed, 7 skipped, 40 subtests); the use-day eligibility set and Warrant policy were not changed. No reconciler activation is authorized. Preserve the existing cross-database failure boundary.

These are post-snapshot observations, not retroactive changes to the `ae406fa8` report or the frozen specifications.

## Post-snapshot current-main follow-up (27 November 2026, after #200)

The evidence snapshot and source-bounded report above remain pinned to their stated commits. Current remote main is now `74cff71045d1f6006b3873138ec658a66acf34a8`.

- #189 manual reconciliation, #191 Moltbook responder persistence, #196 listener/poster persistence, #199 INDEX/handoff reconciliation, and #200 the resumption/identity/Fountain momentum/recursion-attribution migrations are merged.
- #200 exact-head CI run `45990854891` passed: **2,539 passed, 7 skipped, 40 subtests**, baseline OK. Mind-map verification: **30 nodes, 0 unverified, 14 dark, 2 blocked**.
- Current main after the 27 November DAG, scan-coverage and one-pen integrations is `74cff71045d1f6006b3873138ec658a66acf34a8`. Mainline CI run `46009001664` passed: **2,584 passed, 7 skipped, 45 subtests**. The #200 run remains the historical snapshot, not the current-main baseline.
- The two missing doctrine references (`VIRTUE_SLATE.md`, `mental_factors_inventory_alobha_spec.txt`) and overdue `p13_finitude` marker remain unresolved. They are not to be fabricated or date-advanced without source/owner evidence.
- The bounded one-pen migrations listed above are now merged. This does not establish that every write-capable connection in every `theory_x/` faculty has been audited; the full producer/consumer and persistence audit remains open.

### Additional source-to-consumer audit — Throw-Net trigger threshold (27 November)

- `run.py` constructs `TriggerDetector` with the canonical beliefs Reader/Writer and injects it into `CoherenceGate`. Gate REJECTs from non-Throw-Net sources are logged; `gui/server.py` also logs Chat gap deflections.
- `TriggerDetector.record_gate_reject()` returns true at 4 same-topic REJECTs/15 minutes; `record_gap_deflection()` returns true at 3 same-topic deflections/30 minutes. The Gate/Chat callers discard those return values.
- `pending_triggers()` selects every `fired=0` row, and `ThrowNetEngine.run_pending()` processes every returned row without checking the stored threshold count. Therefore, if `NEX5_THROWNET=1` starts the monitor, a single sub-threshold trigger can cause a session on the next monitor tick. This contradicts the documented threshold semantics and is a confirmed source-level consumer gap.
- The monitor is constructed but only started when `NEX5_THROWNET=1` in `run.py` / `gui/server.py`. The flag is registered in `nex_config.py` but absent from the tracked `nex_keepalive.sh` launch command; inherited service/parent environment and live state remain UNKNOWN.
- Existing isolated tests verify the detector's return thresholds, pending-row selection, and engine processing separately; they do not test threshold enforcement end-to-end. `RefinementEngine._r2()` also explicitly defaults to pass on a beliefs-read error (covered by `test_r2_default_pass_on_db_error`); this is documented behavior, not changed here.
- No runtime/DB inspection or activation was performed. Because fixing this would change autonomous behaviour, it remains a Gate 0 defect finding; no code/flag/threshold change is made.

- No live host collection, runtime trace, database hash inventory, model digest or performance measurement was performed in this remote-source session. These remain **UNKNOWN**.
- RDO Stage 2–7 modules, documents and tests are present in current main. The historical Claude Stage 2–7 branches are divergent and approximately 475 commits behind; they are not merge candidates. RDO Stage 7's own handoff/status documentation still requires a real objective-to-delivery demonstration, a verified disposable test-execution boundary, host-only runtime observation and separate human acceptance. The independent Watcher handoff verifier is source/path-only; it does not run tests or establish runtime state.
- RDO v1.3/v1.4 precedence remains unresolved. The recovered v1.4 source metadata and founder recollection do not by themselves establish formal supersession; do not rewrite RDO specifications or stage documents on inference.




## Follow-up source audit G-68 to G-72 (27 November 2026)

The following are source-level findings checked against current main `74cff710`; none asserts live host activation or current database contents.

- **G-68 — decryption ProbeRunner safety (OPEN):** `decryption/probe_runner.py` defaults to `dry_run=False`, can change NEX mode and insert synthetic beliefs, does not restore the previous mode, and clears its injected-ID cleanup list even if deletion fails. It is not imported by the normal `run.py` boot path inspected and was not invoked. No experiment was run.
- **G-69 — SurpriseLoop event loss (OPEN / Gate 0 review required):** timestamp-only paging can skip timestamp ties and the old loop can checkpoint beyond failed writes. PR #239 prepares a monotonic event-ID cursor, legacy timestamp migration, retry-safe checkpointing, duplicate-content handling and a canonical `daemon_kv` schema/migration. Exact-head CI is pending. Because this can change which events reach the belief corpus, do not merge or deploy before founder Gate 0 approval.
- **G-70 — speech trace continuity (OPEN / PR #261 proposed):** the current-main gap is cross-thread causal trace continuity. PR #261 adds bounded in-memory correlation and parent-linked consumer events; exact-head run `46018844996` is in progress. The PR is draft/unmerged and no live acoustic/L4 evidence is claimed.
- **G-71 — Warrant hidden-rowid cursor stability (CLOSED by PR #253):** the versioned cursor uses event time and declared composite primary-key tie-breakers; exact-head run `46014884835` passed (2,590 passed, 7 skipped, 45 subtests). Warrant eligibility and policy remain separate open questions G-74/G-75. No Warrant eligibility or lifecycle policy changes.
- **G-72 — gated SelfPredictionLoop handle injection (CLOSED):** PR #236 routes commitments writes through canonical handles; PR #238 injects AppState Readers/Writers through self-prediction, owned-belief, commitments and Expectations paths. Exact-head runs #236 `46006462779` and #238 `46008022480` passed (2,573/2,584 passed respectively, 7 skipped and 45 subtests each). The `NEX5_SELF_PRED=1` start gate remains unchanged; no loop was started.

The consolidated S-01–S-25 register, roadmap, phase gates and cognitive policy remain untouched. G-69 remains explicitly held for Gate 0 review; G-68 remains an experimental safety question; G-70 has a bounded implementation proposed in draft PR #261 pending exact-head CI/review; G-71 cursor stability is closed by #253, with Warrant eligibility/lifecycle still open as G-74/G-75.

## Current status

| Roadmap deliverable | Status |
|---|---|
| M0.1 — repository identity | Remote main SHA recorded; current host checkout identity/cleanliness not collected |
| M0.1 — host/runtime/database/model measurements | **PARTIAL / UNKNOWN**; no current host collection or live DB hash inventory |
| M0.2 — test baseline | Current main `e78773de`: 2,599 passed, 7 skipped, 45 subtests, baseline OK (exact-head run `46015838864`) |
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

1. Current-main CI for `74cff710` is verified green (2,584 passed, 7 skipped, 45 subtests; baseline OK, run `46009001664`). The earlier #200/`5d7f4e28` result remains historical evidence; do not conflate it with current main.
2. Scheduler overview documentation is corrected and merged in PR #153; its exact-head full suite is green.
3. Continue the forward/backward source audit across the remaining `theory_x/` faculties; distinguish wired loops from downstream consumers and measured effects.
4. The mind-map count discrepancy is closed (30 nodes, 5 arms, 4 findings). The consolidated source re-verification PR #185 is merged; current verifier result is 30 nodes, 0 unverified, 14 dark, 2 blocked. The 18 path/date warnings were cleared by source-anchor corrections. Keep the two missing doctrine references and overdue `p13_finitude` marker explicit; do not fabricate documents or advance the marker without source review.
5. Preserve the unresolved doctrine-reference and P13 evidence gaps as explicit founder-review items; do not silently remove them.
6. Review the G-53 PR #184 merged cursor migration against any future Warrant source-coverage changes; do not broaden the use-day eligibility set without a specification decision.
7. Obtain a fresh, authorised host-only collection for active checkout identity, service/process state, versions/model digest, performance and DB hashes. Do not copy private runtime data into Git.
8. Present the Reality Report, Crosswalk and verified defect backlog for Gate 0 founder review before any Phase 1 behavioural work.

## Do not cross this boundary

This handoff does not authorise enabling dark flags, running ablations, changing prompts/confidence/belief revision, changing Gate policy, starting/restarting services, writing to live substrate DBs, or claiming L4. Preserve the frozen S-01–S-25 specification/register. The separate V2.1 development proposal is not replaced or rewritten by these Phase 0 documents.


## Additional current-main Warrant lifecycle questions — 27 November 2026

The refreshed backlog adds two source-level Warrant questions:

- **G-74 — retired-marker eligibility:** WarrantPass's scoring query and WarrantRecorder's survival query do not filter the independent `erosion_stage='retired'` marker. Normal Harmonizer retirement writes Tier 8, and no normal writer for a lower-tier retired marker or live such row was established. Confirm whether the marker must override tier for these Warrant operations before adding filters.
- **G-75 — recorder versus scorer boot:** normal `run.py` starts WarrantRecorder only behind `NEX5_WARRANT_RECORD=1`. No normal WarrantPass loop construction/start was found in `run.py` or `gui/server.py`; `tools/warrant_validate.py` runs one-shot read-only `compute_all()`. The tracked keepalive sets the recorder flag but not `NEX5_WARRANT`; host-effective state remains UNKNOWN due the known launcher path blocker and uninspected user systemd unit. Record-only operation may be intentional while evidence accrues.

Neither question authorises changing Warrant scoring, eligibility, flags, or lifecycle. The Warrant cursor fix in PR #253 is pagination-only; the Warrant gate remains OFF.


## Post-#256 mainline update — 27 November 2026

**Evidence snapshot:** `main` at `e78773def4549f646257945e5886ec71a7837374`. PR #256 merged the RDO registry regression tests; exact-head full suite passed **2,599 passed, 7 skipped, 45 subtests** (run `46015838864`).

- PR #259 is the current-main SurpriseLoop event-ID/retry correction. Its exact-head full suite run `46017043819` passed **2,610 passed, 7 skipped, 45 subtests**. **Gate 0 hold remains** because event delivery changes which records can enter the belief corpus. The migration does not recover events strictly older than the legacy timestamp cutoff.
- PR #260 is the current-main manual/backlog/handoff replay on this post-#256 mainline.
- G-53/G-71 Warrant cursor defects remain closed by PR #253. G-69 remains Gate 0 held. G-73 dormancy ownership/eligibility remains open; PR #102/#145 are older-base proposals and not approved for merge.
- G-74/G-75 remain Warrant eligibility and boot-lifecycle questions; no Warrant score loop or flag was enabled.

The frozen S-01–S-25 register, roadmap, phase gates and cognitive policy remain untouched. No host activation, live database state, acoustic output or behavioural benefit is claimed.


## TimeFetch/VoiceEngine eligibility crosscheck — 27 November 2026

The current G-52 backlog entry now records that `tests/test_throw_net_time_fetch.py` exists and what it covers. The remaining gap extends beyond TimeFetch: `VoiceEngine._retrieve_candidates()` enriches belief candidates with tier/reinforce_count but does not recheck paused, locked or retired state, and `_score_candidate()` applies a tier penalty rather than a hard exclusion. Its minimum score can still be cleared by a strong candidate. `tests/test_voice_engine.py` compares T4 and T8 scores but does not assert exclusion. Treat this as an eligibility-contract question; do not change retrieval/scoring until the governing policy is confirmed.


## G-70 implementation continuation — 27 November 2026

PR #261 proposes bounded, default-OFF speech trace continuity across Fountain enqueue and the asynchronous consumer. It registers the correlation before the queue row becomes visible, expires links after one hour, bounds the registry to 512 entries, and emits parent-linked dequeue, synthesis, playback, suppression and failure/status events. Tests cover registry lifecycle and principal success/failure branches. The process-local bridge does not recover across restart; `spoken` is not acoustic confirmation. Exact-head full-suite run `46018844996` passed: **2,606 passed, 7 skipped, 45 subtests**, baseline OK. The mind-map check reported 30 nodes, 0 unverified, 14 dark and 2 blocked, while retaining the two missing doctrine references and overdue P13 warning. It also exposed a P9 schema line-reference shift caused solely by the eight-line `daemon_kv` insertion; P9's unchanged `held_tensions` definition and relevant source/tests were rechecked and its source anchor updated in this documentation branch. The documentation branch's own exact-head verifier remains pending. PR #261 remains draft/unmerged; no runtime or feature flag was changed.

