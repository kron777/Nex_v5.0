# NEX Phase 0 — Verified Defect and Evidence-Gap Backlog (Mainline)

**Snapshot:** `main` at `ae406fa8fcb1abdf25cdf4ae1bd65333e1148ca8`  
**Date:** 27 November 2026  
**Purpose:** Separate confirmed documentation/source discrepancies from unknown host/runtime evidence and incomplete audits. This backlog is not approval to change cognition or policy.

## A. Confirmed documentation discrepancies

### D-01 — Sense adapter count / startup overview (corrected)

- **Evidence:** The factory wires 28 adapters (4 internal, 24 external); the scheduler constructor calls `start_all()`. The scheduler overview and `ARCHITECTURE.md` were corrected in PR #148.
- **Additional drift found:** the `run.py` module overview still said five DBs and paused external feeds; `gui/server.py` still said 23 adapters.
- **Disposition:** all known scheduler overview discrepancies are corrected in PR #148 and PR #153. PR #153 merged as `66a97964f0531c16d60637dc8291b42e0b73f00b`; its exact-head full suite passed.

### D-02 — MIND_MAP node-count convention (resolved; prior audit count corrected)

- **Evidence:** Direct section count of the audited `MIND_MAP.yaml`: `nodes:` contains exactly 30 entries (18 arm nodes, 9 ring nodes, 2 boundary nodes and 1 straddle node); `arms:` contains 5 entries; `findings:` contains 4 entries. The earlier count of 39 came from aggregating all 30 nodes + 5 arms + 4 findings, not from counting the `nodes:` section alone.
- **Impact:** The 30-node convention is correct. The prior Phase 0 report/crosswalk mislabelled the aggregate 39 entries as nodes.
- **Disposition:** CLOSED as an audit counting error. No map entries were removed, merged or changed. Preserve the existing 30 nodes, 5 arms and 4 findings.

### D-03 — MIND_MAP doctrine references absent

- **Evidence:** Current-main CI warns that `VIRTUE_SLATE.md` and `mental_factors_inventory_alobha_spec.txt` are missing. Both paths are absent from the current Git tree; path-specific commit-history searches returned no source-file history. Library searches found references to the filenames in an audit/carry-over text, but did not surface either authoritative source document.
- **Disposition:** unresolved source-authority gap. Do not fabricate substitutes or silently remove the metadata references. Restore/repoint only when the founder supplies or identifies the authoritative source copies and approves a traceable documentation change.

## B. Verified policy / documentation boundary

### P-01 — Coherence Gate exception fallback is fail-open

- **Evidence:** `CoherenceGate.check()` catches evaluation exceptions, records them, and returns ACCEPT with `gate_error_fallback`.
- **Disposition:** current behavior is documented; no change to outcomes or policy in Phase 0. Any fail-closed or other policy change requires the governing specification and the applicable founder approval.

### P-02 — Coherence Gate outcome documentation had drifted

- **Evidence:** code persists HOLD through the Holding Zone and queues RESHAPE; old module docs described them as logged-only.
- **Disposition:** corrected in PR #149 (merged), doc-only.

### P-03 — DAG buildability description had drifted

- **Evidence:** executable `_SATISFIED` set is `built`, `live_unproven`, `terminal`, not `built` only.
- **Disposition:** corrected in PR #150 (merged), text-only; caveats retained.

## C. Evidence gaps / incomplete verification (not code defects)

### E-01 — Current host/runtime baseline absent

No current host collection establishes which checkout is deployed, whether a NEX process is running, whether user services are active, or the current OS/kernel/hardware/process state. The older 25-Nov report belongs to a different host/branch snapshot and must not be relabelled as current.

### E-02 — Live database integrity inventory absent

No current SHA-256/size/WAL inventory was collected for the six substrate databases or runtime snapshots. No private data was copied into Git.

### E-03 — Model/runtime performance baseline absent

Python/SQLite/Ollama exact versions on host, exact Qwen model digest, loaded-model state, idle/load RAM/VRAM and prefill/decode tokens/sec remain UNKNOWN.

### E-04 — Full faculty producer/consumer DAG incomplete

The boot graph and key Chat/Fountain paths have been mapped from source. A complete forward (declaration → boot → scheduler → emission → consumer) and backward (output/write → upstream producers) audit for every `theory_x/` faculty is not yet complete.

### E-05 — MIND_MAP freshness warnings

Current-main CI emitted 58 stale-source warnings, 2 missing doctrine-reference warnings and 1 past-due `p13_finitude` unblock warning. These need source review and evidence refresh, not timestamp-only edits.

### E-06 — L4/runtime causal trace not captured

M0.5 currently has L3 synthetic fixtures and paired test evidence. No authorised live run has set `NEX5_TRACE_OVERLAY_CONTEXT=runtime`; L4 remains UNKNOWN.

### E-07 — V2.1 / doctrine authority boundary

Roadmap v3.0 M0.5 (technical causal trace) is distinct from V2.1 M0.5 (six doctrine questions). This backlog does not claim the six doctrine questions are answered, does not recreate a missing Frozen V2.1 source, and does not alter the frozen S-01–S-25 register.

## D. Test / CI evidence

- Exact M0.5 PR head `6d371fe385fc02a2c238247b39aff82681888745`: 2,491 passed, 7 skipped, 40 subtests, baseline OK, CI run #1392.
- Push run #1393 (`45939220368`) is on parent commit `612022e81f749a99de665372704d7acc0645de67`, before PR #153 merged; it is not post-merge evidence for `66a9796`.
- Current main `ae406fa8fcb1abdf25cdf4ae1bd65333e1148ca8`: 2,508 passed, 7 skipped, 40 subtests, baseline OK, CI run `45951932639`.
- Current mind-map verification: 30 nodes, 0 unverified, 14 dark, 2 blocked; 61 verifier warnings (58 stale-source, 2 missing doctrine references, 1 past-due `p13_finitude` marker).

## E. Additional bounded producer/consumer findings verified on current main

These are source-level conditions and test-coverage gaps recovered from older audit notes and re-checked against the current `main` snapshot. They are **not** findings about live rows, active processes or measured incidents.

### G-51 — CounterfactualNode can repeatedly select one unchanged oldest problem

- **Source:** `theory_x/stage_counterfactual/counterfactual_node.py`; `ProblemMemory.touch()` exists in `theory_x/stage7_sustained/problem_memory.py`.
- **Verified:** `_process_one()` selects one `state='open'` row using `ORDER BY last_touched_at ASC LIMIT 1`. It returns on empty TimeFetch, no buildable results, or after Gate processing without updating `last_touched_at` or calling `ProblemMemory.touch()`. The auto-promotion path is disabled.
- **Test gap:** `tests/test_counterfactual_node.py` tests a single open problem and individual packet/Gate behavior; it has no multi-open-problem progression/rotation test.
- **Risk/qualification:** if no other producer touches the selected row, subsequent ticks can select it again and delay newer problems. No live problem rows or tick history were inspected. Whether persistent focus is intended is unresolved.
- **Disposition:** design/evidence question; do not wire `touch()` or change selection until policy is established.

### G-52 — TimeFetch candidate eligibility is broader than its basic test inventory

- **Source:** `theory_x/stage_throw_net/time_fetch.py`.
- **Verified:** `fetch_from_beliefs()` filters confidence and minimum content length but does not constrain `tier`, `paused`, `locked` or `erosion_stage`. Novel-association retrieval joins the paired belief rows without those current-state filters; arc retrieval filters arc type/quality/summary but does not prove current-state eligibility of beliefs represented by an arc.
- **Tests:** `tests/test_throw_net_time_fetch.py` covers confidence/length, similarity and quality ordering, return-transformation exclusion, ProblemMemory routing, deduplication, cap and provenance. It does not test the above belief-status exclusions or post-creation eligibility of novel-association/arc endpoints.
- **Disposition:** policy/coverage gap only. Whether Tier 8, paused, locked or otherwise retired content should be excluded is a governing eligibility decision, not inferred here.

### G-53 — Warrant use-day timestamp cursors can skip tied rows at a page boundary

- **Source:** `theory_x/stage_warrant/recorder.py`; `_USE_BATCH = 20000`.
- **Verified:** `belief_lineage` and `arc_members` use strict-greater-than timestamp cursors (`created_at > ?`, `joined_at > ?`) ordered only by those timestamps. The last timestamp in each batch becomes the next cursor.
- **Conditional risk:** if equal-timestamp rows straddle a 20,000-row page boundary, the next query's strict `>` cursor skips remaining rows with that same timestamp. `record_synergy()` and arc-member writes can share a timestamp across related rows. The source establishes the keyset weakness; no live table population or actual skipped row was observed.
- **Test gap:** `tests/test_warrant_recorder.py` covers basic use-day counting, idempotence and ordinary cursor movement; it does not exercise a tied-timestamp group crossing the batch boundary.
- **Disposition / post-snapshot status:** PR #184 is merged. Exact-head full suite run #1514 passed (2,524 passed, 7 skipped, 40 subtests). It implements the composite `(timestamp, rowid)` cursor for both sources, adds an idempotent `tie_id` column migration that preserves existing timestamp progress, and tests tied-page-boundary plus legacy-schema behavior. The change affects pagination only, not the use-day eligibility set or Warrant policy.

### G-54 — Warrant scorer and recorder consume different anchor sources

- **Source:** `theory_x/stage_warrant/warrant.py`, `theory_x/stage_warrant/recorder.py`, `theory_x/stage6_fountain/generator.py`, `nex_keepalive.sh`.
- **Verified:** the Warrant scorer includes `dynamic.substrate_snapshots.walk_anchor_id` as a use signal. The recorder's use-cycle reads Fountain retrievals, `fountain_events.anchor_belief_id`, synergizer parents, `belief_lineage` parents and `arc_members`; it does not read `substrate_snapshots`.
- **Conditional source interaction (corrected 2026-11-27):** there are two Fountain calls. The main-fire call at `generator.py:2779` passes `walk_anchor_id=None`; `snapshots.py:51-95` persists that NULL, and the scorer explicitly filters `walk_anchor_id IS NOT NULL`, so ordinary main-fire snapshots do not contribute to this Warrant use signal. The non-NULL anchor call is the substrate-voice path at `generator.py:1528`, inside the `NEX5_RECONCILE != '1'` branch at `generator.py:1745`. The tracked `nex_keepalive.sh` recipe sets both `NEX5_RECONCILE=1` and `NEX5_WARRANT_RECORD=1`, so that source path is disarmed in the launch configuration. This describes the tracked script only; effective live host environment remains UNKNOWN.
- **Disposition:** scorer/recorder source sets differ, but the only identified non-NULL snapshot producer is disabled by the tracked launcher; the ordinary main-fire snapshot passes NULL and is intentionally not a walk-anchor signal. Preserve this distinction. Before broadening the recorder source set, establish whether a future non-NULL walk anchor is an intended Warrant use signal and test it with isolated fixtures. No claim about actual host use-day undercount is made.

### G-55 — RememberLoop temporal-link lineage is not durable

- Source: theory_x/life/remember_loop.py.
- Verified on current main: remember_tick() selects an old and recent belief, composes a linking sentence and inserts a Tier-6 remember_loop belief through the injected shared beliefs Writer (PR #160). The dedicated tests/test_remember_loop.py covers persistence, daily cap and duplicate handling.
- Remaining gap: the function returns the two source IDs to its caller/log, but does not persist them to belief_lineage or another durable parent table. No direct run.py start call was found; live activation is not established.
- Disposition: lineage provenance gap if/when this producer is authorised and active; define the intended relationship type and parent contract before adding writes. The former raw-connection one-pen bypass is resolved by PR #160.

### G-56 — Diversity EdgeBuilder's cumulative write counter (resolved)

- Source: theory_x/diversity/edge_builder.py.
- Verified: the former connection-cumulative cx.total_changes check was replaced in PR #158 by per-statement rowcounts through Writer.write_many_with_counts(). tests/test_edge_builder.py covers ignored duplicates after successful inserts.
- Disposition: CLOSED as a telemetry defect. This did not change graph admission or edge classification; G-57 remains a separate unresolved design question.

### G-57 — Generic Stage-2 edges can make beliefs ineligible for Stage-3 typed classification

- **Sources:** `theory_x/diversity/edge_builder.py`; `theory_x/stage3_world_model/edge_generator.py`; `theory_x/stage2_dynamic/__init__.py`; `run.py`.
- **Verified:** Stage-2 EdgeBuilder creates generic `cross_domain` edges from a recent comparison pool for under-connected beliefs. Stage-3 EdgeGenerator selects recent `fountain_insight`/`synergized` beliefs only when they have no edge in either direction. A generic edge can therefore remove a belief from the Stage-3 candidate set before typed `supports`, `refines` or `opposes` classification.
- **Qualification:** this may be intended early graph saturation; no live graph coverage or lost classification was measured. The Stage-2 loop is registered through the dynamic factory; Stage-3 EdgeGenerator is separately started in `run.py`.
- **Disposition:** graph-admission ordering/ownership question for the crosswalk. Do not change edge types, queue criteria or loop order without specification/approval.

### G-58 — GoalManager's normal open state does not match CoherenceGate's active-goal query

- **Sources:** `theory_x/stage8_goal_manager/goal_manager.py`; `theory_x/stage_gate/coherence_gate.py`; `gui/server.py`; `tests/test_coherence_gate.py`.
- **Verified:** GoalManager.open() inserts `state='open'`; `list_open()` and `get_active()` select `state='open'`. The GUI goal API creates/lists goals through this manager. CoherenceGate._load_context() queries `goals WHERE state='active'`. Its test helper `_seed_goal()` defaults to `active`, so its fixture does not exercise goals created by GoalManager.
- **Impact:** Goals created through the normal GoalManager path are not returned by the Gate's active-goal context query unless another writer changes their state to `active`. No such state transition was established in this focused source review.
- **Disposition:** reconcile the state contract and add an integration test using GoalManager.open() plus CoherenceGate context assembly. Do not change `open`/ `active` semantics without the governing lifecycle spec.

### G-59 — FocusLoop's stuck state is excluded by open-only consumers

- **Sources:** `theory_x/sustained/focus_loop.py`; `theory_x/stage7_sustained/problem_memory.py`; `theory_x/stage_counterfactual/counterfactual_node.py`; `theory_x/stage_gate/coherence_gate.py`.
- **Verified:** FocusLoop marks a problem `stuck` when it surfaces a chat ping (and can also mark it stuck while a global ping cooldown suppresses the message). ProblemMemory.list_open(), its find_matching(), CounterfactualNode._process_one(), CoherenceGate context and TimeFetch's ProblemMemory-backed problem retrieval consume `state='open'` and therefore skip stuck rows.
- **Important alternate path:** ProblemMemory.select_for_injection() explicitly considers candidates in any state, including stuck and closed, subject to its lookback, anchor and cooldown filters and a minimum surviving pool. This can re-surface a stuck item into a Fountain prompt without changing its state.
- **GUI lifecycle:** resume() returns the stored row without changing its state; GET can inspect it, and observe()/update_plan() can append data without reopening it. The reviewed GUI API has no explicit `stuck -> open` transition.
- **Impact:** stuck items are excluded from normal open-problem paths, but are not universally unreachable. Whether this represents human escalation, a terminal hold or a resumable workflow state remains unresolved.
- **Test gap:** `tests/test_problem_memory.py` covers open/close/decay and matching but not stuck-state behavior/re-entry; `tests/test_counterfactual_node.py` does not cover stuck-problem routing or the Fountain any-state injection path.
- **Disposition:** define the stuck-state contract and test both its normal-path exclusion and intended any-state injection/re-entry. Do not broaden open-state queries or transition states without policy review.


### G-60 — Problem/Goal stale-decay methods are not orchestrated in reviewed normal boot/chat paths

- **Sources:** `theory_x/stage7_sustained/problem_memory.py`; `theory_x/stage8_goal_manager/goal_manager.py`; `theory_x/__init__.py`; `run.py`; `gui/server.py`.
- **Verified:** ProblemMemory exposes `decay(now)` to close `open` problems older than 30 days; GoalManager exposes `decay(now)` to cancel `open` goals older than 60 days. `run.py` constructs and registers both. The Theory X registry only stores/returns registered nodes (`register()` / `all_nodes()`); it contains no scheduler. In the reviewed normal `run.py` and `gui/server.py` paths, neither node's `tick()` nor `decay()` is invoked. Chat uses `find_matching()` / `get_active()`, while GUI uses CRUD/list APIs.
- **Test boundary:** `tests/test_problem_memory.py` and `tests/test_goal_manager.py` test manual decay calls, not an orchestrator invoking them. The repository search API returned incomplete code-search results; therefore this finding is limited to the reviewed boot/chat paths and is not a proof that no operator or auxiliary entry point ever calls these methods.
- **Impact:** The documented 30-day/60-day stale close/cancel rules are callable methods, but automatic execution is not established in the reviewed normal process path.
- **Disposition:** clarify whether stale cleanup is intended to be scheduled, manually invoked, or deliberately dormant. If scheduled, identify the authoritative lifecycle owner and add an integration test before implementation. No scheduler or retention behavior changed.

### G-61 — One-pen Writer migration (partially resolved; further migrations in flight)

- Specification: SPECIFICATION.md §8 states exactly one writer thread per database and that all writes submit through the single Writer queue; substrate/writer.py explicitly says direct writes elsewhere are a bug by definition.
- Resolved on current main with isolated regression coverage:
  - RememberLoop — PR #160.
  - Diversity EdgeBuilder — PR #158 (including per-statement rowcount handling).
  - Sustained FocusLoop — PR #159.
  - Fetch and Wonder — PR #163.
  - Surprise — PR #165.
  - Pattern and Witness — PR #164.
- Further bounded migrations remain open and unmerged:
  - Fountain/momentum persistence — PR #162.
  - Identity loop persistence — PR #166.
  - DailyLife scheduled persistence — PR #168.
  - Affinity loop persistence — PR #169.
- Current evidence: these four PRs have exact-head CI runs in progress at this handoff. PRs #162 and #166 were opened against earlier mainline base SHAs; their integration against the latest mainline must be confirmed before merge. PRs #168 and #169 target current main ae406fa8.
- Impact/qualification: the original three raw-connection paths are no longer present in current main. The one-pen rule is not yet declared globally complete: the full faculty producer/consumer and persistence audit remains open. No live lock contention or runtime failure is claimed.
- Disposition: continue the four bounded migrations through tests and exact-head integration review. Preserve transaction semantics and multi-database ordering; do not mechanically replace calls without reviewing atomicity/side effects.

### G-62 — Internally generated reflective beliefs bypass the declared Coherence Gate boundary

- **Declared contract:** `theory_x/stage_gate/coherence_gate.py` says every thought generated by a faculty node passes through the gate before joining the substrate, and its design commitments call this universal.
- **Verified source paths:** `theory_x/life/remember_loop.py` composes an old/recent temporal-link sentence and inserts it directly as a Tier-6 `remember_loop` belief; Fountain's `_build_prompt()` writes a first-person `self_rut_notice` Tier-6 belief directly to `beliefs` when the striking-rate trough condition and two-hour throttle pass. Neither insert invokes `CoherenceGate.check()` in the inspected code.
- **Declared exception:** Stage-2 `_write_sense_belief()` also writes Tier-7 `precipitated_from_sense` content without the Gate, but its own loop explicitly classifies this as raw external perception rather than a generated thought. Keep this source-perception exception distinct from the two reflective producers above.
- **Disposition:** reconcile the universal wording with explicit non-thought/system-observation exceptions, or decide whether RememberLoop/self-rut observations should be passed through the Gate. No gate calls or persistence behavior changed.

### G-63 — ProblemMemory duplicate-observation rationale (resolved)

- Source: theory_x/stage7_sustained/problem_memory.py and theory_x/sustained/focus_loop.py:_append_observation().
- Verified: the stale ProblemMemory.observe() rationale was corrected in PR #159. _append_observation() retains its same-text early return, and the new tests/test_focus_loop.py provides isolated regression coverage. No ocount >= 10 close gate was found in the inspected current modules.
- Disposition: CLOSED as a documentation/test-coverage defect. The FocusLoop behavior itself was not changed.

### G-64 — Learning Guards retain direct write paths outside the one-pen Writer

- **Sources:** `theory_x/stage_world/learning_guards.py` (`record_tick()`, `cap_blocks()`, `subtract()`, `revert_subtraction()`, `run()`); `theory_x/life/daily_life.py:_activity_expectation_canaries()`.
- **Verified at this report's `ae406fa8` snapshot:** `record_tick()` opens `conversations.db` with write-capable `connect()`, inserts `learning_guard_ticks`, and commits directly. `cap_blocks()` inserts `learning_cap_hits` through its supplied connection. `subtract()` opens write-capable connections to both `conversations.db` and `beliefs.db`, updates `beliefs.confidence`, inserts the corresponding `learning_subtractions` ledger row, and commits the two databases separately. `revert_subtraction()` similarly updates belief confidence and the ledger through direct connections. These paths bypass the per-database Writer contract in `SPECIFICATION.md §8`.
- **Scheduled path:** `_activity_expectation_canaries()` calls `learning_guards.run()`. That function can invoke `subtract()` when the corresponding ratio/attribution condition is met and `NEX5_LEARN_RATIO_SUBTRACT=1` and/or `NEX5_LEARN_ATTRIBUTION_SUBTRACT=1`. The flags are OFF unless explicitly set; this is a conditional source-level bypass, not evidence that either flag is enabled or that a live subtraction occurred.
- **Impact/qualification:** the one-pen persistence audit is not complete while these paths remain. The cross-database update/ledger sequence is not atomic today; a Writer migration must preserve and explicitly test the existing ordering/failure semantics rather than imply a cross-database transaction. No live DB or runtime state was inspected.
- **Disposition / post-snapshot status:** addressed across merged PRs #168, #180 and #183. PR #180 (exact-head run #1493: 2,522 passed, 7 skipped, 40 subtests) routes `record_tick()`, `subtract()` and `revert_subtraction()` through Writers and passes shared beliefs/conversations Writers from DailyLife. PR #183 (exact-head run #1519: 2,525 passed, 7 skipped, 40 subtests) moves `cap_blocks()` into the serialized Expectations conversations-Writer transaction with the learning log. No flags, thresholds, confidence policy, or live state are changed. The two databases remain separate transactions, with belief updates preceding ledger writes; a second-Writer failure can still leave a confidence change without its ledger row.

### G-65 — Dormant Expectations ledger/reconciler uses direct database writes

- **Source:** `theory_x/stage_world/expectations.py` (`ingest()`, `reconcile()`, `_learn()`, `record_canaries()`). The same path calls `learning_guards.record_tick()` after reconciliation; see G-64 for that module's additional direct-write paths.
- **Verified at this report's `ae406fa8` snapshot:** `ingest()` opens `conversations.db` with write-capable `connect()`, inserts expectation-ledger rows, and commits directly. `reconcile()` opens another write-capable conversations connection and directly writes resolution state, `event_valence`, and `affect_nudges`. When `NEX5_EXPECT_LEARN=1`, `_learn()` opens `beliefs.db` with write-capable `connect()`, updates `beliefs.confidence`, and commits separately while the associated learning ledger rows are written through the conversations connection. `record_canaries()` also writes its log directly; PR #168 proposes migrating that one canary-log write to the shared conversations Writer, but does not migrate the ingest/reconcile/learning paths.
- **Activation boundary:** `reconciler_on()` is controlled by `NEX5_RECONCILER`; the audited `run.py` snapshot contains no reference to this module or its reconciler. Treat the reconciler as a dormant source path, not a live worker. `NEX5_EXPECT_LEARN` is a separate OFF-by-default gate for belief-confidence updates. No runtime activation, live database contents, or incident is established.
- **Impact/qualification:** if these functions are invoked, they bypass the one-pen rule in `SPECIFICATION.md §8`. The belief update and conversations-ledger commits are separate database transactions, so their existing cross-database failure boundary must be preserved and explicitly tested; do not imply atomicity across the two files.
- **Disposition / post-snapshot status:** source-level persistence defect addressed by merged PR #183 (exact-head run #1519: 2,525 passed, 7 skipped, 40 subtests). `Writer.transaction(callback)` serializes `ingest()` and `reconcile()` on the conversations Writer; `_learn()` reads beliefs read-only and routes confidence updates through the beliefs Writer; cap-hit and learning-log inserts remain in the same conversations transaction. PR #168's canary Writer migration and PR #180's Learning Guards Writer migration are also merged. **Current-main activation boundary (main `99ae476`):** `nex_keepalive.sh` sets `NEX5_RECONCILER=1` and `NEX5_EXPECT_LEARN=1`, but `run.py` contains no Expectations/reconcile call, and `daily_life.py` imports only `record_canaries` from Expectations. Flags are present in launch configuration but no boot invocation was found in the audited entry path; do not equate flag presence with execution. The two databases remain separate transactions: belief updates commit before the enclosing conversations transaction, so a later conversation commit failure can leave a belief update without its ledger row. PR #183 changes persistence routing only; it does not change flags, thresholds, adjudication, valence or confidence policy and does not activate or wire the reconciler. `reconcile()` itself does not enforce `reconciler_on()`; any future scheduler/boot caller must check that gate before invoking it.

### G-66 — Mind-map source-drift warnings are invalid under the shallow CI checkout

- **Sources:** `mind_map/mind_map.py:last_commit_ts()` and `.github/workflows/tests.yml` at this report's `ae406fa8` snapshot.
- **Verified mechanism:** `last_commit_ts()` asks `git log -1 --format=%ct -- <path>` for each source. The tests workflow uses `actions/checkout@v4` without `fetch-depth`, so the action's default one-commit shallow checkout is used. In a shallow checkout, path history is unavailable; the command returns the checkout commit for tracked paths, making unrelated files appear to have changed on the CI date.
- **Observed evidence:** run `45951932639` reported dozens of source refs as changed on 2026-11-27, including `theory_x/stage_tom/global_workspace.py` and `gui/server.py`, whose relevant source blobs are unchanged between the `ae406fa8` snapshot and current main and whose path history predates that date. The reported 2026-11-27 dates therefore cannot establish which nodes are genuinely stale. Do not bulk-update `last_verified` from this output; the real per-path dates remain to be recomputed with complete history and then reviewed against source changes.
- **Disposition:** PR #175 merged the `fetch-depth: 0` checkout, shallow-history guard and regression tests; exact-head full-history CI passed as run #1476 (`45968094769`). PR #174 merged the P13 correction. PR #185 is the current consolidated source re-verification, rebased onto current main after G-65 and the other merged work; it includes P1/P6/dṛṣṭi, prices, memory, P2/P3, vitarka/vicāra, P7/vedanā, episodic and HRI source reviews, plus all verifier line-range corrections. Exact-head CI for PR #185 is pending. PRs #176, #177, #179 and #181 were closed as superseded; PR #178 remains a passing p8-only backup until #185 passes. Do not claim the remaining path/date warnings cleared until PR #185's verifier output is reviewed. Preserve the two known missing-doctrine warnings and the overdue `p13_finitude` marker; they are separate from this shallow-history defect.

## F. Gate boundary

This backlog is evidence input for Gate 0. It is not permission to enable Phase 1 experiments, change prompts, change confidence/belief revision, modify Coherence Gate policy, alter dark flags, start/restart services or touch live databases.


## G. Post-snapshot current-main follow-up (27 November 2026)

The defect/evidence findings above remain pinned to the stated `ae406fa8` source snapshot. The following later merge/CI facts do not retroactively change that snapshot:

- PR #191 migrated Moltbook responder persistence; PR #196 migrated listener and poster persistence; PR #200 migrated boot-time ResumptionSeeder, IdentityLoop and Fountain momentum/recursion-attribution persistence. #200 exact-head CI run `45990854891` passed (2,539 passed, 7 skipped, 40 subtests). These close the listed bounded migration branches, not the repository-wide one-pen audit.
- PR #185 mind-map source re-verification is merged. Current verifier result on #200: 30 nodes, 0 unverified, 14 dark, 2 blocked. Two missing doctrine references and the overdue `p13_finitude` marker remain warnings and remain unresolved.
- Current main SHA: `5d7f4e28eb6760d206eed455429c90e967a5bf10`.
- No current host/runtime collection or live database inspection was performed. Host process state, runtime flags, database integrity/hashes, model digest/performance and L4 trace remain UNKNOWN.

This follow-up is evidence-status maintenance only. It does not authorise behavioural changes, dark-flag activation, live DB writes, experiment execution, Gate policy changes or Phase 1. Gate 0 remains pending founder review.

### G-67 — Throw-Net trigger thresholds are not enforced by the pending-session consumer

- **Sources:** `theory_x/stage_throw_net/trigger_detector.py` (`record_gate_reject()`, `record_gap_deflection()`, `pending_triggers()`); `theory_x/stage_gate/coherence_gate.py:check()`; `gui/server.py` Chat gap-refusal path; `theory_x/stage_throw_net/throw_net_engine.py:run_pending()`; `run.py` Throw-Net wiring.
- **Verified on current main `5d7f4e28` (post-snapshot source audit):** the detector documents thresholds of 4 same-topic REJECTs in 15 minutes and 3 same-topic gap deflections in 30 minutes. Each `record_*()` returns a boolean indicating threshold crossing, but both call sites discard the return. `pending_triggers()` selects all rows with `fired=0` without testing the stored `threshold_state`; `ThrowNetEngine.run_pending()` processes every returned row as a session. Thus, if the monitor runs, one sub-threshold event can launch a Throw-Net session on the next tick. The detector's boolean threshold is not the session gate.
- **Activation boundary:** `run.py` and the GUI construct the monitor but start its loop only when `NEX5_THROWNET=1`. The flag is registered in `nex_config.py` but is not explicitly set in the tracked `nex_keepalive.sh` command. An inherited systemd/parent environment and current host flag state were not inspected; do not claim the loop is definitely off on the host.
- **Test coverage:** isolated tests cover threshold-return counts, pending-row selection and engine processing independently (`tests/test_throw_net_trigger.py`, `test_throw_net_engine.py`, `test_throw_net_monitor.py`). They do not assert end-to-end threshold gating. The full repository suite passed on exact head #200, but that does not prove the missing integration condition.
- **Related qualification:** `TimeFetch.fetch_from_beliefs()` filters by confidence and content length but not tier/paused/locked/erosion state; this is a separate eligibility-policy question already identified in the crosswalk. `RefinementEngine._r2()` returns true on DB read error, explicitly tested; do not alter either policy by inference.
- **Impact:** if the monitor is enabled, sub-threshold trigger rows can cause candidate retrieval, scoring and Gate resubmission, potentially reintroducing the high-volume churn that motivated the monitor's historical retirement comment. No live session or current runtime impact is established.
- **Disposition:** **OPEN — source-level consumer/threshold defect.** No code, flag, threshold, Gate or live state changed. Corrective design and validation require Gate 0 review because they alter autonomous behaviour.
