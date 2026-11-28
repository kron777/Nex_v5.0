# NEX v5.0 — Phase 0 Mainline Handoff

**Date:** 27 November 2026  
**Repository:** https://github.com/kron777/Nex_v5.0  
**Evidence snapshot:** `main` at `f03a3d2e7b9c71801e44be73cf728c01cb791c9d`  
**Gate 0:** **PENDING — founder review required**

## Read these together

- `NEX_REPOSITORY_REALITY_REPORT.md` — mainline source/CI reality and host/runtime unknowns.
- `NEX_ARCHITECTURE_CROSSWALK_v2.md` — source boot graph, key producer/consumer paths and partial faculty crosswalk.
- `NEX_PHASE0_VERIFIED_DEFECT_BACKLOG_2026-11-27.md` — verified discrepancies and unresolved evidence gaps.
- `ADR-001.md` — M0.5 trace mechanism and rollback.


## Historical continuation record — snapshot c80d9dbb878ac15a39d6707a9c89ab2a51f8518c (27 November 2026)

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
- RDO v1.4 is the current working specification (founder indicated on 24 Nov that they believed it had been approved); v1.3 remains historical implementation lineage. Formal frozen supersession is not recorded in the consolidated NEX register; preserve history rather than retroactively rewriting it.




## Follow-up source audit G-68 to G-72 (27 November 2026)

The following are source-level findings checked against current main `74cff710`; none asserts live host activation or current database contents.

- **G-68 — decryption ProbeRunner safety (OPEN):** `decryption/probe_runner.py` defaults to `dry_run=False`, can change NEX mode and insert synthetic beliefs, does not restore the previous mode, and clears its injected-ID cleanup list even if deletion fails. It is not imported by the normal `run.py` boot path inspected and was not invoked. No experiment was run.
- **G-69 — SurpriseLoop event loss (OPEN / Gate 0 review required):** timestamp-only paging can skip timestamp ties and the old loop can checkpoint beyond failed writes. PR #239 prepares a monotonic event-ID cursor, legacy timestamp migration, retry-safe checkpointing, duplicate-content handling and a canonical `daemon_kv` schema/migration. Exact-head CI is pending. Because this can change which events reach the belief corpus, do not merge or deploy before founder Gate 0 approval.
- **G-70 — speech trace continuity (source/test gap CLOSED by PR #261):** merged commit `cc8ae43652bdba919198ee4bb90fabbd8f05632f` adds bounded in-memory correlation and parent-linked consumer events. Exact-head run `46020502376` passed **2,611 passed, 7 skipped, 45 subtests**. No live acoustic/L4 evidence is claimed; complete M0.5 acceptance remains open.
- **G-71 — Warrant hidden-rowid cursor stability (CLOSED by PR #253):** the versioned cursor uses event time and declared composite primary-key tie-breakers; exact-head run `46014884835` passed (2,590 passed, 7 skipped, 45 subtests). Warrant eligibility and policy remain separate open questions G-74/G-75. No Warrant eligibility or lifecycle policy changes.
- **G-72 — gated SelfPredictionLoop handle injection (CLOSED):** PR #236 routes commitments writes through canonical handles; PR #238 injects AppState Readers/Writers through self-prediction, owned-belief, commitments and Expectations paths. Exact-head runs #236 `46006462779` and #238 `46008022480` passed (2,573/2,584 passed respectively, 7 skipped and 45 subtests each). The `NEX5_SELF_PRED=1` start gate remains unchanged; no loop was started.

The consolidated S-01–S-25 register, roadmap, phase gates and cognitive policy remain untouched. G-69 remains explicitly held for Gate 0 review; G-68 remains an experimental safety question; G-70 source/test continuity is implemented, but M0.5 acceptance remains open for live/paired evidence; G-71 cursor stability is closed by #253, with Warrant eligibility/lifecycle still open as G-74/G-75.

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

PR #262 merged as `c9e25d7cf85659e80053f5fe75928ee71486a141` and corrects the WarrantPass class docstring's false attribution to `run.py`; it does not construct or start the pass. Neither question authorises changing Warrant scoring, eligibility, flags, or lifecycle. The Warrant cursor fix in PR #253 is pagination-only; the Warrant gate remains OFF.


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

PR #261 proposes bounded, default-OFF speech trace continuity across Fountain enqueue and the asynchronous consumer. It registers the correlation before the queue row becomes visible, expires links after one hour, bounds the registry to 512 entries, and emits parent-linked dequeue, synthesis, playback, suppression and failure/status events. Tests cover registry lifecycle and principal success/failure branches. The process-local bridge does not recover across restart; `spoken` is not acoustic confirmation. Previous PR #261 head `15a1f7589bec0a308ddae2eb6a662513bb6b1207` passed exact-head run `46018844996`: **2,606 passed, 7 skipped, 45 subtests**, baseline OK. Latest head `bed052c9d63422f52a9514325f74f113959db2a3` adds concurrent one-shot claims, trace-free speech fallback, speaking/suppressed status-write coverage and stronger terminal assertions; exact-head run `46020502376` is pending. The prior pass is not being represented as verification of the latest changes. The mind-map check on the previous head reported 30 nodes, 0 unverified, 14 dark and 2 blocked, retaining the two missing doctrine references and overdue P13 warning. It exposed a P9 schema line-reference shift caused solely by the eight-line `daemon_kv` insertion; P9's unchanged `held_tensions` definition and relevant source/tests were rechecked and its source anchor updated in this documentation branch. The documentation branch's own exact-head verifier remains pending. PR #261 remains draft/unmerged; no runtime or feature flag was changed.



## Post-#262 mainline update — 27 November 2026

**Evidence snapshot:** `main` at `c9e25d7cf85659e80053f5fe75928ee71486a141`. PR #262 corrected the WarrantPass class docstring's false attribution to `run.py`; normal boot still wires WarrantRecorder only behind `NEX5_WARRANT_RECORD=1`, and WarrantPass remains unconstructed by the reviewed boot path. Exact-head full-suite run `46020220371` passed **2,599 passed, 7 skipped, 45 subtests**. G-75 remains an intent/lifecycle question; no Warrant flag or scorer was activated.



## Post-#261 mainline update — 27 November 2026

**Evidence snapshot:** `main` at `cc8ae43652bdba919198ee4bb90fabbd8f05632f`. PR #261 merged the G-70 cross-thread speech trace bridge. Exact-head full-suite run `46020502376` passed **2,611 passed, 7 skipped, 45 subtests**. G-70's source/test gap is closed; M0.5 remains open because no authorised live L4 trace or complete paired semantic-equivalence evidence was produced. Trace overlay remains default OFF; no runtime or speech device was touched.



## Post-PR #263 manual reconciliation and Claude handoff — 27 November 2026

**Current evidence snapshot:** `main` at `80c30b6cc649bb9ce46fd6fdc06bf4afbc9f57c5`. PR #263 merged the synchronized manual, backlog, handoff, ADR-001 and mind-map documentation after PR #261. This is a documentation-only integration. Gate 0 remains pending founder review; Phase 1 remains unauthorized.

### First-read order for Claude

1. `INDEX.md` — first-read architecture and development manual; read §37 for authority boundaries and the unresolved G-58 issue.
2. This file — Phase 0 handoff and evidence snapshot.
3. `NEX_PHASE0_VERIFIED_DEFECT_BACKLOG_2026-11-27.md` — current verified discrepancies, policy questions and evidence gaps.
4. `NEX_REPOSITORY_REALITY_REPORT.md` and `NEX_ARCHITECTURE_CROSSWALK_v2.md` — source/boot and producer/consumer evidence.
5. `ADR-001.md`, the frozen S-01–S-25 register and the authoritative roadmap.

### Explicit unresolved authority: Development Proposal V2.1 / G-58

The separate user-authored NEX v5.0 Development Proposal V2.1 and its approval record have not been located in the current-main repository tree or established by the Library retrieval performed so far. Do not recreate or infer their contents. Claude should independently search its available project context for the exact original and approval evidence, quote the relevant goal-lifecycle clauses precisely, and identify whether they are approved and controlling.

G-58 is a real implementation mismatch: GoalManager creates/selects `open` goals while CoherenceGate reads `active` goals; existing Gate fixtures seed `active` directly and miss the normal creation path. The intended lifecycle rule is not yet established. No writer/query change, automatic transition, row migration, or semantic reinterpretation is authorized until the original governing clause and approval are verified. If Claude cannot recover them, report the retrieval gap and leave G-58 open.

### Current-main open work

- PR #264 is a draft current-main pagination correction for provenance erosion. Exact-head full-suite run `46023260805` was still in progress at the latest status check; do not call the change validated or merged. Review its behaviour-impact note before any merge.
- G-69 remains Gate 0 held. G-73/G-74/G-75 remain open. The two missing doctrine references and overdue P13 unblock remain explicit warnings.
- The frozen S-01–S-25 register, roadmap, Gate 0 and Phase 1 boundaries remain unchanged.

Claude's review should follow the same research → bounded implementation → rescan → consequence/evidence → manual-update loop. Separate facts, hypotheses, policy decisions and approvals. Do not treat a green CI run as host activation or behavioural validation.


## Historical PR #265 correction record — superseded by the current status block below (27 November 2026)

The first manual update described PR #264 as based on the post-#263 mainline. A later commit-graph check found its merge base was still `cc8ae43652bdba919198ee4bb90fabbd8f05632f`. Its exact-head suite run `46023260805` passed, but that run did not validate the later mainline. PR #264 is closed as superseded. **PR #266** replayed the same change on `edb869af154a33cd77df5ad9bdf010d3e6ab06a2`; it was itself superseded after main advanced. **PR #268** is the latest-main replay; see the current status block. Do not treat the old pass as current-main validation. The change may advance previously starved beliefs at a future scheduled erosion pass and remains subject to review.


## Current Claude handoff status — verified at main 9f5a9f0b476716b6a6fd0a39aa3cf3041a3a4465 (27 November 2026)

This block supersedes older "latest/current" labels elsewhere in this handoff. Read it before acting.

- Current main: `9f5a9f0b476716b6a6fd0a39aa3cf3041a3a4465`.
- PR #268: current-main provenance-erosion replay; draft; base exactly current main; head `8b8ffaff27e298ff96dd4a09452ac14067dc4916`; exact-head CI run `46024945847` had built its disposable image and was still executing the full baseline at last check. Do not claim pass/fail until queried again. Behaviour may advance previously starved beliefs; undo log is audit metadata, not rollback.
- PR #266: older-base replay, superseded by #268; do not cite its CI as proof for #268.
- PR #259: SurpriseLoop loss-safe proposal remains Gate 0 HOLD and is not a current-main replay. GitHub metadata says base `e78773def4549f646257945e5886ec71a7837374`, head `9686fa6da7e835a149f31b516a5ff7a731c3a8b0`; its branch diverges from current main. It must not be merged/deployed; founder approval is required for the behaviour impact.
- PR #255: closed unmerged older attempt.
- G-58 unresolved; exact V2.1 and approval evidence not located. Do not change goal-state semantics.
- G-70 source/test gap closed by merged PR #261; M0.5 acceptance remains open.
- G-73/G-74/G-75 remain open; verify each against the backlog before changing anything.
- Gate 0 pending founder review; Phase 1 unauthorized.
- Reality Report and Architecture Crosswalk are historical at `ae406fa8fcb1abdf25cdf4ae1bd65333e1148ca8`, 44 commits behind current main. Use as orientation only and revalidate claims against source.

Claude must independently query the repository and CI before acting. Do not treat this handoff as proof that another model has read it or that the founder has approved any action.


---

## 27 November 2026 — G-65 and G-76–G-79 current-main update

**Current main:** `90ffd57c75b33eff161ea33e29388e0732f0290e`.

- PR #270 merged (`d2a5c107019d79276879f3ade6ebefd348686e36`); exact validation run `46032636987`: 2,624 passed, 7 skipped, 45 subtests.
- PR #271 merged (`77d4cd89015ebf605c9e5ec6af994a28126f6ed5`); exact-head run `46032708456`: 2,629 passed, 7 skipped, 45 subtests.
- PR #269 documentation reconciliation merged as `3e7f0f35ccc58519f57ae4fd2e13b1f688f688a3`; exact-head run `46034624423`: 2,629 passed, 7 skipped, 45 subtests.
- PR #272 merged as `90ffd57c75b33eff161ea33e29388e0732f0290e`; exact head `67fcf46a84bcfae5b5a309502680fffe8bb347b8`, run `46035516300`: 2,632 passed, 7 skipped and 45 subtests.
- G-65's former “no boot invocation” statement is superseded: the tracked launcher sets `NEX5_SELF_PRED=1`, `NEX5_RECONCILER=1`, and `NEX5_EXPECT_LEARN=1`; SelfPredictionLoop calls Expectations reconciliation behind the corresponding gate. Host-effective activation remains UNKNOWN.
- G-76 remains open for founder clarification: ordinary use increments `use_count`, while erosion stage checks use `reinforce_count`; the reviewed runtime reinforcement caller is the corroboration-promotion path.
- G-77 is closed by #270; G-78 is closed by #271. G-79's compare-and-set fix is merged by #272 and closed on current main.
- PR #259 remains open and Gate 0 HOLD. Gate 0 is pending founder review; Phase 1 remains unauthorized. The frozen S-01–S-25 register and Master Roadmap are unchanged.

The canonical manual is `INDEX.md`; its plain-text mirror is `NEX_5.0_DEVELOPMENT_MANUAL_CLAUDE_HANDOFF_2026-11-27.txt`. Keep both byte-for-byte synchronized after the four-file content update. No host collection, runtime activation, flag change or live database access was performed.


## Post-PR #274 merge — mind-map freshness evidence (27 November 2026)

**Current main:** `e4f439e6aef4383795ccc7e3e29b1d242ed0f98c`. PR #274 merged after exact-head run `46037202834` passed 2,632 tests, 7 skipped and 45 subtests with baseline OK. The CI mind-map verifier reported 30 nodes, 0 unverified, 14 dark, 2 blocked and no stale-source warnings. Two missing doctrine references and the overdue P13 marker remain; see D-03/E-05 in the backlog. The P13 marker is not permission to rearm. The manual mirror was re-fetched and verified byte-identical to INDEX after merge. No runtime, host, database or feature-flag activity occurred.


## Current-main system research continuation — 27 November 2026

**Evidence snapshot:** `main` at `14873c10673760b8adbbf6fb0076226d1c97ffa4`. See `NEX_PHASE0_SYSTEM_RESEARCH_2026-11-27.md` and the updated verified defect backlog.

- PR #275 merged as `49837fd`; exact-head run passed 2,632 tests, 7 skipped, 45 subtests.
- PR #276 merged as `baac692`; exact-head and post-merge main CI passed 2,634 tests, 7 skipped, 45 subtests. RDO source searches now exclude generated `.cycles`.
- PR #277 merged as `14873c1`; exact-head CI passed 2,636 tests, 7 skipped, 45 subtests. Keepalive checkout path is portable; `MOLTBOOK_DRY_RUN=1` remains unchanged.
- Current mind-map check: 30 nodes, 0 unverified, 14 dark, 2 blocked; no stale-source warnings. Two doctrine references and the past-due P13 marker remain.
- New open findings: G-80 reanimation handoff durability; G-81 divergent fire counters; G-83 groove-alert replay; G-84 shutdown quiescence; G-85 SignalToProblem primary one-pen/cross-database boundary (the auxiliary prose-stats bypass is closed by #279); G-86 SignalReaper allowlist drift; G-87 Moltbook dry-run/external-consent semantics; G-90 contextual social-silence capability gap; G-91 RDO objective context is stored but not enforced. Scanner coverage remains under G-73.
- The global one-pen audit remains open. SignalToProblem is a boot-registered direct-writer path and its cross-database recovery contract needs explicit design before migration.
- The RDO remains external/advisory; raw objective seeding, contextual-constraint enforcement and the v1.4 OFT/interface-profile gaps remain open implementation work. v1.4 is the current working basis; v1.3 remains historical.

No live host, runtime, database, credential or external service was accessed. No cognitive policy, feature flag, MIND_MAP node, frozen S-01–S-25 register, Master Roadmap or Gate 0 decision changed. Gate 0 remains pending founder review; Phase 1 remains unauthorized.


### Post-research-snapshot PR #279 update — 27 November 2026

PR #279 merged as `8d2121d121931d37afcb1c3d23d27e7ccc9145d1`; exact-head CI run `46044361663` passed 2,638 tests, 7 skipped, 45 subtests, baseline OK. It moves the scheduled prose-statistics rebuild to the shared beliefs Writer/Reader path. This closes the auxiliary write bypass, not SignalToProblem's primary split-database transaction. G-85/G-61 remain open pending a defined idempotency/recovery contract. Post-merge main run `46045384807` also passed 2,638 tests, 7 skipped, 45 subtests, baseline OK.


### Post-snapshot PR #280 update — 27 November 2026

PR #280 merged as `f03a3d2e7b9c71801e44be73cf728c01cb791c9d`; exact-head CI run `46045754339` passed 2,640 tests, 7 skipped, 45 subtests, baseline OK. It fixes Writer-level shutdown/submission races by serializing admission, draining accepted work before one sentinel, rejecting late writes, and retaining a timed-out worker reference. This closes only the Writer subproblem in G-84. The application still lacks a global producer stop/join coordinator and G-84 remains open. Post-merge main CI is in progress.


### RDO v1.4 implementation gap audit

See `rdo/RDO_V1_4_IMPLEMENTATION_GAP_AUDIT_2026-11-27.md` for the current source-to-requirement matrix and next vertical-slice increment.


## 28 November 2026 — one-pen census and open persistence PRs

At pre-merge main `a6d084051e1d523812ef51c2d93784cba226499d`, the read-only census tool (`tools/one_pen_census.py`) found 112 write-capable call sites and one boot-reachable direct writer to the substrate databases: SignalToProblem (G-85). PR #347 has since merged as `8d6bc95d387687ed470713467d8779d09479e11d`, correcting that primary path. PR #348 merged as `321a156e162a6554e27ae329522f253e8f6fe676`, adding G-84 shutdown step 1. These are merged changes, not open proposals. The 112-site census remains a pre-merge snapshot and must be rerun on current main before treating its count or classifications as current; see INDEX §44 for the exact-head CI run IDs.

The census also records `strikes/catalogue.py` as a documented direct-write exception for its own separate database.

Every `warrant_validate` verdict from before PR #271 was computed on history-free survival (G-78). Founder decisions are pending on G-80, G-78, G-76 and the census scope (G-61). Gate 0 remains pending.


## Post-census persistence update — 28 November 2026

- PR #347 merged as `8d6bc95d387687ed470713467d8779d09479e11d`; exact-head CI run `46089697232`: 2,841 passed, 7 skipped, 45 subtests. The primary SignalToProblem one-pen bypass is corrected with idempotent recovery ordering; no cross-database atomicity is claimed. G-85's identified source defect is closed; G-61 remains open for census scope/governance and remaining exceptions.
- PR #348 merged as `321a156e162a6554e27ae329522f253e8f6fe676`; exact-head CI run `46091039346`: 2,838 passed, 7 skipped, 45 subtests; baseline OK, no STALE warnings. AppState now quiesces dynamic loops before Writer close. G-84 remains open for the remaining producers and global shutdown deadline.
- The 112-site census is pre-merge evidence at `a6d08405`; rerun it on current main before using the count as current.
- Founder decisions G-80, G-78, G-76 and the non-substrate scope question under G-61 remain pending. Gate 0 remains pending; Phase 1 remains unauthorized.


## 28 November 2026 — G-83 Row 9 source-to-effect refinement

The current source trace refines existing G-83; no duplicate finding ID is created. Main snapshot `18c8f06171e1de35c3210831a49b63d0e2487af0`. Manual §114 records the complete distinction.

- Metacognition counts all derived `groove` event rows globally over 30 minutes; it does not count distinct alert IDs/episodes or group by topic. The 600-second source query returns at most three rows per tick.
- The Row 9 `conversations.db` `stillness_log` has no topic/source field. The crystallizer blocks all belief crystallization while any row is active; it does not apply same-topic matching.
- Fountain generation and dynamic fire recording occur before crystallization. Generator still returns/logs the thought after the crystallizer returns `None`; belief/link creation and the normal speech-queue enqueue path are skipped.
- A second `dynamic.db` `stillness_log` is an unrelated duplicate-retrieval instrumentation table. Do not conflate it with Row 9.
- `theory_x/SYNTHESIS_PLAN_V2.md` §3 describes same-topic triggering/suppression. This is historical design provenance, not authority to revise frozen S-01–S-25/M1.8 or Founder Sign-Off. The controlling Row 9 approval remains UNKNOWN unless located.

The existing test suite's source assertions cover the mocked threshold and crystallizer hold, not distinct-source/topic identity or the full Generator-to-speech consequence. No tests were run; no live host/database/process/service was accessed; no runtime code, schema, flag, or behavior was changed. Gate 0 remains pending founder review; Phase 1 remains unauthorized.


### 28 November 2026 — G-83 implementation-history refinement

The initial Row 9 history is now checked against both design and implementation commits. `SYNTHESIS_PLAN_V2.md` §3 was added at `36e7ed40661db58d83214b40aebde7a33fdb2519` (11:29:57 UTC, 11 May 2026) and describes a same-topic threshold/suppression. The Row 9 implementation landed at `c4b005f32e931047711ef6cdbe03e84a00183885` (13:21:14 UTC) with a global count of derived groove events and global crystallizer hold; its tests mock aggregate counts and do not carry topic/source identity. The current `DOCTRINE.md` summary is more general. No rationale for the difference was located in the inspected commit message or patch. This confirms a historical design-artifact divergence, not its authority or founder approval. G-83 stays OPEN; do not restore same-topic behaviour without locating controlling sign-off. See INDEX §§114–115. Gate 0 remains pending; Phase 1 remains unauthorized.

 
### 28 November 2026 — G-83 caller/cadence refinement

The 60-second DiversityLoop invokes GrooveSpotter, DormancyScanner and ClockRunner, not Metacognition. Production Metacognition is constructed in run.py and ticked by the chat handler in gui/server.py; the SentienceNode protocol describes tick as once per chat turn, while its registry only registers/lists nodes and does not dispatch periodic ticks. Thus alerts can accumulate between chat turns; the next tick selects at most three newest eligible rows. This is source/caller evidence, not evidence of actual chat cadence. See INDEX §116. No code/tests/runtime changes; Gate 0 pending and Phase 1 unauthorized.


### 28 November 2026 — G-83 renewal and starvation implications

The source ordering permits a further conditional failure mode: same eligible alert rows can be re-read on later chat turns, and new derived groove events are written before the active-stillness check. Once a 60-second stillness row expires, a tick can count those refreshed derived events (within the 1,800-second count window) and renew the global hold without a new detector episode. With four or more eligible unacknowledged rows, ORDER BY detected_at DESC LIMIT 3 can keep returning the same newest three and allow older rows to age out. These are source-derived possibilities, not live observations. Add controlled-clock tests before considering any fix. See INDEX §117; G-83 remains OPEN.


### 28 November 2026 — G-83 prior-art comparison

The Sentience 5.5 Stillness_Node.py cited as Row 9 prior art is now inspected. It has a single global non-reentrant stillness state and a trigger/time/duration log, with no topic or alert identity. NEX SYNTHESIS_PLAN_V2 §3 then described a topic-specific NEX extension; the NEX implementation uses a global count/global crystallizer hold. The implementation resembles prior art in scope, but the reason the plan's topic-specific delta was not carried is undocumented in the inspected commit. Authority remains UNKNOWN. See INDEX §118; G-83 stays OPEN.


### 28 November 2026 — G-83 speech-consumer boundary

Row 9 prevents the current fire from reaching the crystallizer's later speech enqueue, but SpeechQueueConsumer is a separate beliefs.db-only daemon and does not read conversations.stillness_log. Already-pending speech entries can continue to drain while Row 9 is active, subject to the consumer's independent pause and quiet-hours controls. tests/test_speech.py has no pending-entry-during-Row-9 case. This is evidence that Row 9 is not a speech-consumer pause. See INDEX §119; G-83 remains OPEN.


### 28 November 2026 — G-83 reader census and influence classification

The tracked-source reader map is extended in INDEX §120. Two additional live influence routes were found: CompetingDrives reads 24-hour max groove severity into its coherence drive (0.30 factor), and Fountain's recent-STRIKING prompt block uses the most recent qualifying alert pattern to filter candidate context. The former can influence a changed drive-tension prompt; the latter can alter prompt material when NEX5_GENIUS_PROMPT_OFF is not 1. The documented keepalive profile explicitly sets NEX5_RECONCILE=1, disabling substrate-voice's own groove-triggered path. Stakes readiness and topic shadow are separately gated. SubstrateHarmonic, snapshot, GUI and probe routes are observational/request-triggered, not acknowledgement writers. No direct tracked-code write to acknowledged_at was found; external/untracked/dynamic SQL and live host state remain UNKNOWN. G-83 remains OPEN. No code/tests/runtime changes; Gate 0 pending; Phase 1 unauthorized.


### 28 November 2026 — G-83 detector identity and restart boundary

GrooveSpotter has four per-instance fingerprints (exact content, top trigram, template belief-ID set, centroid current-window ID tuple). They suppress unchanged scans while the same instance lives, clear when the detector condition falls away, and reset on process restart. A restart can therefore emit another alert row for an unchanged condition. Persisted sample_belief_ids do not preserve every detector fingerprint; scripts/trajectory.py's (alert_type, sample_belief_ids) episode grouping is a separate analytical equivalence relation. tests/test_diversity.py does not characterize repeated detect_all(), reset/recur or restart replay for the four detectors. See INDEX §121; G-83 remains OPEN.


### 28 November 2026 — G-83 test characterization candidate

Draft PR #448 adds one test file only for the four GrooveSpotter process-local fingerprints: same-instance unchanged suppression, clear/recur, and new-instance replay. Exact head f4447ad5b243b97c91c28fc00abbef88fe7c51f9, base main 18c8f06171e1de35c3210831a49b63d0e2487af0. Full CI run 46173749707 was queued; commit status pending at handoff. No local tests were run and no test pass is claimed. Keep draft until exact-head CI and review. No runtime source/behaviour change. See INDEX §122; G-83 stays OPEN.


### 28 November 2026 — G-83 historical runtime evidence anchor

The 14 November investigation journal records 1,198 groove_alerts rows (then 1,199 ~20 minutes later) and 0/1,198 acknowledged at that historical time. 94.8% were template_repetition; 5.2% ngram_repetition. Its 30-minute gap-clustering grouped 1,199 rows into 55 groups (median 14 rows, p90 54, max 102; median span ~106.7m, max ~837.3m). Nov 10 alert IDs 751/752 were severity-1 template alerts; the journal records a real cooldown write and later crystallization rejection. This is historical database evidence only, not current runtime observation. The 30-minute gap clusters are not the current producer fingerprints or Row 9 derived-event identity. See INDEX §123; G-83 remains OPEN.


### 28 November 2026 — G-83 producer/consumer test candidates

Two separate draft test-only PRs now characterize the two replay boundaries:
- #448 producer fingerprints, exact head f4447ad5b243b97c91c28fc00abbef88fe7c51f9, full suite run 46173749707 IN_PROGRESS.
- #449 consumer replay/Row 9 renewal with one source alert and five controlled chat ticks, exact head 50c2e083de1dab3e40301b37dc14b614a0d08f23, full suite run 46174148899 IN_PROGRESS.

Neither workflow has a result yet. No local tests were run. Both remain drafts; no runtime behaviour or specification is changed. See INDEX §124; G-83 remains OPEN.


### 28 November 2026 — G-83 producer tests exact-head validation

PR #448 producer fingerprint characterization passed exact-head GitHub Actions run 46173749707: 3,081 passed, 7 skipped, 86 subtests, 0 deselections; baseline OK. Mind-map check: 30 nodes, 0 unverified, 12 dark, 2 blocked; existing doctrine-reference and overdue P13 warnings remain. This verifies only the current per-instance fingerprint behavior in tests, not production restart cadence or semantic episode identity. PR #448 remains draft pending review. PR #449 consumer replay/Row 9 renewal run 46174148899 remains in progress. See INDEX §125; G-83 remains OPEN.

### 28 November 2026 — G-83 consumer characterization result and chat-prompt boundary

Draft PR #449 exact head `8132db2a338727e580e3269ad148277db727b0d4` passed full-suite workflow `46174972385`: 3,079 passed, 7 skipped, 86 subtests; baseline OK; disposable sandbox probe OK. Its controlled-clock tests verify five derived groove events and two Row 9 stillness activations from one unchanged unacknowledged source alert, plus separate generic Metacognition and topic-filtered Stage-SelfNarrative formatting. This is test-only evidence, not live runtime observation or approval to change behaviour.

The source-to-sink follow-up confirms that run.py passes Stage-SelfNarrative into Metacognition; gui/server.py ticks Metacognition on the chat path and appends its generic groove self-observation line; the same tick writes pattern-specific narrative_log rows, which the later Stage-SelfNarrative prompt formatter only returns when the user's prompt prefix matches the narrative content by substring. The combined formatter/caller exposure remains a test candidate. G-83 remains OPEN: no acknowledgement/episode semantics, topic scope, Row 9 threshold/duration, or output policy is changed. See INDEX §126 and verified defect backlog G-83. Gate 0 remains unestablished; Phase 1 remains unauthorized.

### 28 November 2026 — G-83 prompt assembly / thin-belief gate boundary

Static source trace of `gui/server.py` shows Metacognition and topic-filtered Stage-SelfNarrative output appended to `belief_text` before the chat thin-belief gate. That gate counts only `- [Tier` markers, so reflective text does not increase `belief_count`. For ordinary non-probe/non-social requests outside `_ALLOW_THIN_REGISTERS`, an insufficient count persists a gap refusal and returns before voice prompt assembly or `state.voice.speak()`. Surviving paths later embed `belief_text` under “Your interior right now” in `voice_prompt` and pass it to the voice layer. Prompt formatting alone therefore does not prove LLM exposure. See INDEX §127. Route-level fixture test remains a candidate; no gate/prompt policy change, live runtime observation, or Phase 1 authorization.
Voice transport refinement: `voice/llm.py` builds a two-message payload and passes `VoiceRequest.prompt` unchanged as the user-message content to `_request_fn`. This closes the static source path only; provider acceptance and semantic use remain unobserved. See INDEX §127.

### 28 November 2026 — G-83 route-to-transport test candidate

Draft PR #450 (`b33022cfaf47cc34dc8eec316cd583c15e6d880e`) adds a GUI route fixture using real Metacognition and Stage-SelfNarrative objects with mocked voice transport. It asserts Technical's insufficient-belief return occurs before transport and Philosophical carries both reflective strings into the transport user message. Workflow `46175227754` passed 3,078 tests, 7 skipped, 86 subtests; baseline and sandbox checks passed. Test-only; no live model/provider or cognitive behaviour change. See INDEX §127.

### 28 November 2026 — G-83 upstream producer provenance

GrooveSpotter's source query reads the latest `fountain_insight` and `synergized` beliefs, not chat messages. DiversityLoop invokes it every 60 seconds. Unchanged n-gram patterns are suppressed by an in-memory fingerprint (restart resets it). N-gram alerts at severity >=0.5 write a two-hour pattern-specific `signal_cooldown`, which FountainCrystallizer checks against future thought content. This targeted cooldown is distinct from Metacognition's consumer replay and Row 9 global hold. See INDEX §128. No behaviour changed.
Exact-repeat producer audit note: `EXACT_REPEAT_MIN=2` is the implemented threshold, but `_detect_exact_repetition()`'s docstring says at least three. PR #448's fingerprint fixture uses three repeats and does not distinguish the thresholds; `tests/test_diversity.py` has no explicit threshold assertion. Intended threshold remains UNKNOWN; no code/test policy change and no new defect ID pending history/authority review. See INDEX §128.
Cadence refinement: Fountain's own worker waits for the active mode interval before each readiness check/generation (default 120s, chat mode 300s, silent disables Fountain); DiversityLoop scans every 60s; Metacognition is chat-turn-triggered. Active host mode is UNKNOWN. See INDEX §128.

### 28 November 2026 — G-83 source-identity preservation boundary

Metacognition temporarily carries `groove_id`, but `_write_event()` persists no source-row/episode ID in `meta_cognition_events`. The parallel narrative branch does persist it as `narrative_log.source_id`. Row 9 counts every groove event row without grouping by identity. PR #449's controlled fixture verifies five same-source rows can count separately. This confirms the identity gap, not the intended semantic unit; no schema change is authorised. See INDEX §129.

### 28 November 2026 — G-83 optional second-order readers

Stage-9's built-in event digest is dark behind `NEX5_METACOG_DIGEST=1`; if armed, three groove rows can trigger a digest regardless of whether they came from distinct source alerts. It excludes its own digest rows and has a one-hour per-type cooldown. The separate `tools/metacog_digest.py` is manually invoked only, requires `NEX5_METACOG_REFLECT=1` and `--live`, and reads all meta events without source deduplication before making a reflection call. Static checks found no import/invocation from the live GUI, `run.py` or keepalive. Runtime flag states remain UNKNOWN. See INDEX §129.

### 28 November 2026 — Metacognition decay dispatch audit

`Metacognition.decay(now)` implements 14-day resolution and is directly unit-tested, but no production caller was located in the inspected `run.py`, `gui/server.py` or SentienceNode registry. The registry only registers/lists nodes; it does not dispatch lifecycle methods. Automatic stale-event resolution remains unverified pending a repository-wide call-site census. No scheduler or retention behaviour changed. See INDEX §130.
Targeted call-site sweep checked 24 Theory X life-loop, scheduler, world/signal/diversity-loop, registry/protocol and monitor files. No Metacognition decay caller, generic decay dispatcher, all_nodes dispatcher or other meta_cognition_events resolved_at writer was found in those paths. Not a whole-repository proof. See INDEX §130.

### 28 November 2026 — G-83 optional Fountain prompt rail

The same Metacognition object is passed to both AppState and FountainGenerator. The generator appends its cached `format_for_prompt()` line to `focus_block` and `_wide_fac` only when `NEX5_METACOG_VOICE=1`; it does not tick Metacognition itself. Source says default-off; runtime flag state UNKNOWN. No dedicated Fountain flag-boundary test was located. See INDEX §131.

### 28 November 2026 — G-83 acknowledgement ownership

`groove_alerts.acknowledged_at` exists in schema but GrooveSpotter leaves it NULL; Metacognition reads unacknowledged rows within 600 seconds and does not acknowledge them. No writer was found in the inspected active paths. The 10-minute query window is the only observed expiry mechanism. Intended acknowledgement owner/semantics and repository-wide absence of writers remain UNKNOWN. See INDEX §132.
**Schema-history note:** `groove_alerts.acknowledged_at` was present when the table first appeared in commit `a396dda08e8861e22029ceef813c69211671a37e` (26 Apr 2026). The commit describes diversity/rut detection but does not document acknowledgement ownership or semantics. See INDEX §132.
Producer/consumer distinction: commit `543e4ce957f2e3ad8e3ebf9fb25cd1bf977fed1a` fixed repeated GrooveSpotter alert INSERTs via per-detector fingerprints; it did not add an acknowledgement writer. The current G-83 replay is a separate consumer re-read of one existing row during the 600-second Metacognition window. See INDEX §132.

### 28 November 2026 — Metacognition cache age on Fountain rail

`format_for_prompt()` reads `_cached_recent` only; it does not check cache age or refresh. Fountain's optional reader does not call `tick()`, so with `NEX5_METACOG_VOICE=1` it may reuse the last chat-refreshed observation across fires until another chat tick or explicit invalidation. The 14-day decay caller is not located in production. This is a source-level stale-context possibility, not a live occurrence. See INDEX §131.
Session-scope refinement: `meta_cognition_events` schema has nullable `session_id`, but `Metacognition.tick(context)` ignores context and `_write_event()` does not populate the field; GUI calls `tick()` without context and Row 9 has no session predicate. Current source is database-global, not session-scoped. Intended scope UNKNOWN. See INDEX §129.
Authority classification: the optional Fountain Metacognition line is textual prompt context only; it is not a typed operation, capability grant, approval signal, execution command or verification result. It does not make the Tibetan mind map or any Mind Aspect an action gate/veto. See INDEX §131.
Cache timing: `_CACHE_TTL=60s`; every chat tick can write events/narratives and count Row 9, but refreshes `_cached_recent` only when empty or older than 60s. `format_for_prompt()` reads the cached snapshot; Fountain reads the same snapshot without refreshing. Actual chat cadence UNKNOWN. See INDEX §131.

### 28 November 2026 — G-83 Fountain rail exact-head CI

Draft PR #451 exact head `91739d131f21f3dd2c55d35ef2b23a07aa73c424`, workflow `46176528182`, passed 3,078 tests, 7 skipped, 86 subtests; baseline and sandbox checks passed. The fixture verifies the optional flag and that Fountain reads the cache without ticking Metacognition. Stale-cache age and host flag state remain UNKNOWN. See INDEX §131.

### 28 November 2026 — G-83 consolidated causal model

INDEX §133 now provides the consolidated Fountain → belief → GrooveSpotter → Metacognition → Row 9 → chat/Fountain prompt feedback map, separating confirmed source/test evidence from host flag, runtime and semantic unknowns. Next bounded work: stale-cache characterization, acknowledgement/resolved_at writer census, decay caller verification, then sample-belief/retrieval-manifest lineage. No behaviour changed; Gate 0 pending and Phase 1 unauthorized.

### 28 November 2026 — G-83 prompt and retrieval lineage boundary

Fountain's optional Metacognition rail injects only the generic cached formatter line, not the GUI Stage-SelfNarrative pattern-specific `narrative_log` text. `groove_alerts.sample_belief_ids` is not selected by Metacognition; the disabled/de-wired GrooveBreaker selects but does not use it; Fountain context retrieval does not query the alert table. No direct alert-to-source-belief retrieval priority path was found. See INDEX §§131, 133.

### 28 November 2026 — G-83 generation versus persistence controls

The Fountain model call returns a thought before the crystallizer checks Row 9 stillness and `signal_cooldown`. Those controls reject belief persistence after generation; the generator still logs/returns the thought. They are not generation brakes. The optional `NEX5_METACOG_VOICE` text rail is the only direct Metacognition-to-Fountain prompt influence found, default-off by source. See INDEX §134.
Sample-ID provenance: exact repetition stores exact matching rows; template repetition stores templated IDs; n-gram and centroid store only the first five rows of their active window. Those latter IDs are samples, not exact causal parents. No active downstream consumer uses them for retrieval priority. See INDEX §133.
Internal Fountain feedback is generic only; it does not receive GrooveSpotter pattern text, alert/source IDs, sample IDs or GUI Stage-SelfNarrative content. The pattern-specific path is GUI topic-filtered narrative; Fountain's pattern-specific effect is only post-generation cooldown. See INDEX §133.

### 28 November 2026 — live Metacognition tick versus decay

Correction of scope: Metacognition is connected to the live GUI chat path. `run.py` constructs/registers the shared object; `gui/server.py` calls `tick()` and `format_for_prompt()` during chat. The unlocated production path is specifically `decay(now)` for 14-day stale-event resolution. A targeted 24-file lifecycle sweep found no dispatcher but is not a whole-repository proof. See INDEX §135.
Persistence-loop effect: GrooveSpotter reads only stored Fountain/Synergized beliefs, so crystallization rejection prevents the generated thought from becoming future detector input. Row 9/cooldown regulate durable memory accumulation, not current LLM generation. See INDEX §134.

### 28 November 2026 — lifecycle ownership split

Theory X `register()/all_nodes()` is not a lifecycle dispatcher. `AppState._quiesce_producers()` is a separate bounded shutdown list for named worker services; `AppState.close()` shuts down the scheduler, quiesces workers and drains Writers, but does not iterate cognitive nodes or call `decay(now)`. Metacognition remains chat-tick-driven and has no autonomous worker in the inspected path. See INDEX §136.

### 28 November 2026 — registered-node decay inventory

Four persistent cleanup methods are present: Metacognition 14d, GoalManager 60d, ProblemMemory 30d and NovelAssociation 14d. Unit tests directly call each method; no production dispatcher/call was located in inspected boot/chat/background paths. Their consequences differ: Metacognition old unresolved rows remain eligible for the newest-three prompt slots; old open ProblemMemory rows remain eligible for chat matching; old GoalManager rows remain open; NovelAssociation's independent 2-hour prompt cutoff already hides old entries, so its 14-day decay is housekeeping. ProblemMemory is instantiated by main `run.py` but not registered there; only the optional test `create_app(with_tools=True)` path registers it. Do not infer one uniform defect or add a generic scheduler. See INDEX §137.

### 28 November 2026 — Metacognition external retention backstop

`nex_db_reaper.py` includes `conversations.db:meta_cognition_events:created_at` under a 30-day default retention and physically deletes old rows in batches. A versioned user-systemd timer schedules it nightly around 04:00, but the README says repository unit files are reference copies; active units live in `~/.config/systemd/user/`. Installation is documented; actual timer/service activation and last-run state remain UNKNOWN. This deletion is not the 14-day `decay()` resolution transition and the reaper does not target `goals`, `open_problems` or `novel_association_log`. See INDEX §138.

### 28 November 2026 — external cleanup census

The DB reaper covers `meta_cognition_events` only, not `goals`, `open_problems` or `novel_association_log`. `scripts/problem_persistence.py` is read-only; Stage Gate retention covers only `gate_decisions` and empty `throw_net_sessions`; signal reaper covers only `signals`. No other cleanup timer was found among inspected versioned units. This is a bounded repository census, not proof about arbitrary host cron or user units. See INDEX §139.

### 28 November 2026 — protocol versus lifecycle orchestration

Doctrine §4 defines `tick()` and `decay(now)` but does not specify a universal decay dispatcher, cadence or owner. Node tests prove local method effects, not runtime invocation. Keep four evidence claims separate: protocol implementation, unit-tested effect, production caller/trigger, active-host observation. The current source trace has evidence for the first two and selected tick/worker paths, but no located owner for the four persistent decay methods (with Metacognition's separate 30-day DB reaper backstop). Do not add a scheduler without policy ownership. See INDEX §140.

### 28 November 2026 — registered-node lifecycle census

The normal `run.py` boot registers nine Theory X nodes. Optional `gui/server.py::build_state(with_tools=True)` separately registers ProblemMemory, GoalManager and Metacognition. The registry stores/lists nodes but does not dispatch tick/decay. GoalManager and Metacognition have substantive unowned decay methods; NovelAssociation's 14-day log annotation is uncalled housekeeping but its prompt reader only looks back two hours. ProblemMemory's 30-day decay is covered by G-60; it is constructed but not registered in normal `run.py` (it can be registered in optional GUI build_state). See INDEX §137 and corrected G-60 backlog wording.

### 28 November 2026 — DB-reaper test coverage boundary

`tests/test_retention_reaper.py` proves the generic `reap_table()` batch-delete helper, but its target-list assertion checks only `drive_emergence_log` and `substrate_coherence`. It does not assert the `meta_cognition_events` target or exercise `reap()` against that table. The 30-day target is source-observed; systemd scheduling is configuration-observed; active timer/host execution remains UNKNOWN. See INDEX §142.

### 28 November 2026 — DB-reaper host deployment history

Historical 25 Nov host diagnostics first found `nex5-db-reaper.service` failing `203/EXEC` against the old `/home/rr/Desktop/Desktop/nex5` path. A later check verified the loaded unit was corrected to `/mnt/games/storage/Desktop/Desktop/nex5` and `nex_db_reaper.py` existed there. No service was deliberately started/restarted and no successful run or nightly retention pass was observed. The versioned repository service file still contains the old path, so reinstalling that reference copy could regress the correction. Current timer activation, service health and last successful run remain UNKNOWN. See INDEX §145.

### 28 November 2026 — G-83 narrative retention boundary

Pattern-specific `narrative_log` entries are inserted on every source-alert re-read and can duplicate the same `source_id`. PR #449's exact-head fixture verifies five same-source rows and that all five occupy the topic-matched formatter output; an unrelated topic returns empty. The GUI formatter has no age cutoff or source deduplication; it selects only `content`/`created_at`, not stored `trigger`/`source_id`, and the GUI supplies `prompt[:100]` as the topic. `tests/test_self_narrative.py` verifies the five-row cap and no-op `decay()`, not an expiry policy. The 30-day DB reaper targets `meta_cognition_events` but not `narrative_log` or `groove_alerts`. Other known narrative writers include ProblemMemory, GoalManager, NovelAssociation and CoherenceGate. **Design qualification:** `SELF_NARRATIVE_SPEC.md` explicitly makes v1 unbounded; a 90-day/size cap was only a possible Phase 26b follow-on after observing production write frequency. Runtime contains later trigger paths, but the spec was not updated; whether Phase 26b observation/approval occurred elsewhere remains UNKNOWN. See INDEX §§144–147.

### 28 November 2026 — shared narrative writer/provenance boundary

`narrative_log` has multiple writers: Metacognition, ProblemMemory, GoalManager, NovelAssociation and CoherenceGate. Its prompt formatter selects only `content` and `created_at`, omitting `trigger` and `source_id`; the model receives the narrative text and age label without typed source provenance. This is broader than the GrooveSpotter replay path. See INDEX §144.

### 28 November 2026 — chat-gap side-effect boundary

The real GUI route calls Metacognition.tick()/formatters before the thin-belief early return. A Technical request can be refused before VoiceClient transport while still re-consuming the alert and writing event/narrative state. Repeated blocked requests may contribute to Row 9 without any model call. PR #450 verifies route ordering/transport, not the three-event threshold from blocked requests. See INDEX §127.


### 28 November 2026 — SelfNarrative rut-mirror tick ownership

The `SelfNarrative.tick()` method contains a conditional rut-notice writer, but its normal-path dispatch is not established. `run.py` constructs/registers the node without a dedicated loop; the Theory X registry stores/returns nodes but does not dispatch; the inspected GUI chat path calls only `format_for_prompt()`; Metacognition writes groove narratives directly without calling `SelfNarrative.tick()`. The existing empty-fixture tick test does not exercise the rut threshold or prove a caller. Live flag/cadence/execution remain UNKNOWN. No scheduler or runtime change is authorised. See INDEX §148.


### 28 November 2026 — Rut-mirror prompt retrieval boundary

The fixed rut notice is not injected as a generic reflective cue by the inspected GUI path. The GUI passes `prompt[:100]` as `current_topic`; SelfNarrative uses the entire string in a case-insensitive SQL substring match against narrative content. An unrelated prompt prefix returns no rut notice even if the row exists. Draft PR #452 adds isolated exact-versus-unrelated topic tests; exact-head CI remains pending. No prompt/retrieval policy change. See INDEX §149.

GeniusTagger is separately wired to its own 60-second loop and writes the `genius_tags` input table; that does not own or dispatch `SelfNarrative.tick()`. Host worker execution and live tag freshness remain UNKNOWN. See INDEX §148.


### 28 November 2026 — Corrected rut lifecycle and dual-path finding

Correction: SelfNarrative.tick() itself has no demonstrated dispatcher, but Metacognition.tick() directly calls the injected SelfNarrative._maybe_notice_rut() helper on the GUI chat path. This bypasses the NEX5_RUT_MIRROR_OFF check located only in SelfNarrative.tick(). Separately, FountainGenerator writes the same rut text into beliefs under its NEX5_GOVERNOR_OFF-gated governor path, with an instance-local two-hour throttle; the narrative path uses persisted narrative_log history. The two writers, stores and throttles are source-observed; deployed flags, live execution, co-occurrence and intended flag scope remain UNKNOWN. Draft PR #452 adds a test-only characterization of the direct-caller bypass; exact-head CI pending. See INDEX §§148–150.


### 28 November 2026 — Fountain rut belief consumption boundary

The Fountain governor writes `source='self_rut_notice'` only after the current `_retrieve_context_beliefs()` call has fetched own/seed candidate rows. Its explicit own/seed allowlists and dedicated `hot_observer` slot omit this source, so same-fire Fountain retrieval is impossible and the next explicit Fountain source query does not select it. The generic GUI BeliefRetriever loads eligible tier<=6/confidence>=0.15 beliefs, making the row a query-dependent candidate there; actual delivery remains UNKNOWN. See INDEX §151.


### 28 November 2026 — GeniusTagger rut-window timestamp semantics

GeniusTagger backfill can process 14-day-old Fountain events but writes tagged_at=ts_now; the rut observers filter on tagged_at within 90 minutes, so historical fires can appear recent during backfill. The schema allows multiple rows per (fountain_event_id, weights_version) and rut queries do not deduplicate IDs or filter versions. Draft PR #453 adds test-only characterization; exact-head CI pending. Actual host history and impact remain UNKNOWN. See INDEX §152.


PR #452 exact-head workflow 46181820624 passed at e3e1e037f0769e66e62b84fe982abf37f49e1485. The isolated test confirms the direct Metacognition caller bypasses the wrapper OFF check; live host state remains UNKNOWN.


### 28 November 2026 — Rut decision provenance

Both rut observers query only genius_tags.class and do not carry contributing event IDs or weights_version into the output. The narrative row uses source_id=None; the belief row carries only the self_rut_notice source label and ordinary belief fields. Source rows remain independently queryable, but neither output has a frozen input manifest. This compounds §152's time/version ambiguity. See INDEX §153.


### 28 November 2026 — Rut sample readiness

GeniusTagger is started asynchronously; _own_and_start() does not wait for its first backfill to finish. Neither Metacognition nor the Fountain governor checks _backfill_done before reading genius_tags. A partial historical backfill can therefore be sampled while still being written; combined with §152 timestamp semantics, this may produce a premature decision. Host overlap remains UNKNOWN. See INDEX §154.


### 28 November 2026 — Rut belief membrane classification

self_rut_notice is not in MembraneClassifier._INSIDE_SOURCES, so the generic BeliefRetriever classifies it OUTSIDE. QueryRouter's INSIDE self-inquiry path filters it out; OUTSIDE retrieval remains query-dependent. Draft PR #454 adds test-only characterization; exact-head CI pending. Whether the source was intended to be INSIDE is UNKNOWN. See INDEX §155.


PR #453 exact-head workflow 46182191953 passed at 2d15c4d4c87881138c937c5600f1a281677d8391. Fixture tests validate the backfill timestamp and same-fire multi-version row behaviours; host occurrence and detector impact remain UNKNOWN.


### 28 November 2026 — GeniusTagger consumer inventory

The tagger producer is write-only, but its integrated signal is consumed by ReadinessEvaluator (up to .15 readiness penalty), recent-STRIKING Fountain prompt injection, the governor (reanimation cadence 20->5 plus self_rut_notice), Metacognition rut narrative, and optional NEX5_CONTINUITY_N prompt context. GENIUS_SCORE_v2.md §7's statement that consumers do not yet exist is stale against the inspected source. Actual host flags/activity remain UNKNOWN. PR #455 covers readiness/prompt consumers; #454 governor; #452 Metacognition. See INDEX §156.


TRACK_THEORY.md's 2026-05-27 afterword anticipates the retrieval, prompt and readiness consumers; GENIUS_SCORE_v2.md §7's final paragraph was not reconciled. Treat the mismatch as stale documentation, not proof of unauthorized runtime behaviour.


### 28 November 2026 — GeniusTagger fan-out contract

The GeniusTagger signal fans out to independent consumers with different windows, thresholds and flags: readiness 1h/5 rows/40%; prompt block 24h; governor 90m/4 rows/5%; Metacognition rut 90m/4 rows/5%; optional continuity all-time top scores. There is no common sample manifest or shared decision contract. Do not harmonize these during Phase 0. PRs #452/#453 passed; #454/#455 pending. See INDEX §157.


### 28 November 2026 — Genius reporting denominator

Genius HUD/panel stats and provenance reports aggregate tag rows across weights versions, not unique Fountain events/current version. The HUD's current_version is from the latest row while its rate is all-row aggregate. /api/fountain/recent instead keeps the latest row per event. Actual host duplicates and live metric impact remain UNKNOWN. See INDEX §158.
