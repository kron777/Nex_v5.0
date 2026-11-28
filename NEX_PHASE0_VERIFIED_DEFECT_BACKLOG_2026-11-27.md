# NEX Phase 0 — Verified Defect and Evidence-Gap Backlog (Mainline)

**Snapshot index:** `main` at `60cc178ba1f3c895651c86ad95345c98fd5a2198`  
**Date:** 27 November 2026  
**Purpose:** Separate confirmed documentation/source discrepancies from unknown host/runtime evidence and incomplete audits. This backlog is not approval to change cognition or policy. The header SHA is the latest repository snapshot for navigation only; each finding retains its own source/test evidence date and must be revalidated before being called current.

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

### E-05 — MIND_MAP freshness warnings (stale-source portion resolved)

- **Fresh evidence:** PR #274 exact-head run `46037202834` executed `python mind_map/mind_map.py --check --verify` and reported 30 nodes, 0 unverified, 14 dark, 2 blocked, with **no STALE source-drift warnings**.
- The two missing doctrine references (`VIRTUE_SLATE.md`, `mental_factors_inventory_alobha_spec.txt`) remain tracked under D-03. The past-due `p13_finitude` marker remains a deliberate warning, not permission to rearm.
- **Disposition:** stale-source warning subset RESOLVED on this check. Residual source-authority and P13 warnings remain open under their respective entries; do not change timestamps to suppress warnings.

### E-06 — L4/runtime causal trace not captured

M0.5 currently has L3 synthetic fixtures and paired test evidence. No authorised live run has set `NEX5_TRACE_OVERLAY_CONTEXT=runtime`; L4 remains UNKNOWN.

### E-07 — V2.1 / doctrine authority boundary

Roadmap v3.0 M0.5 (technical causal trace) is distinct from V2.1 M0.5 (six doctrine questions). This backlog does not claim the six doctrine questions are answered, does not recreate a missing Frozen V2.1 source, and does not alter the frozen S-01–S-25 register.

## D. Test / CI evidence

- Exact M0.5 PR head `6d371fe385fc02a2c238247b39aff82681888745`: 2,491 passed, 7 skipped, 40 subtests, baseline OK, CI run #1392.
- Push run #1393 (`45939220368`) is on parent commit `612022e81f749a99de665372704d7acc0645de67`, before PR #153 merged; it is not post-merge evidence for `66a9796`.
- Current main `ae406fa8fcb1abdf25cdf4ae1bd65333e1148ca8`: 2,508 passed, 7 skipped, 40 subtests, baseline OK, CI run `45951932639`.
- Current mind-map verification on PR #274 exact head (run `46037202834`): 30 nodes, 0 unverified, 14 dark, 2 blocked; no stale-source warnings; 2 missing doctrine references and 1 past-due `p13_finitude` marker remain.

## E. Additional bounded producer/consumer findings verified on current main

These are source-level conditions and test-coverage gaps recovered from older audit notes and re-checked against the current `main` snapshot. They are **not** findings about live rows, active processes or measured incidents.

### G-51 — CounterfactualNode can repeatedly select one unchanged oldest problem

- **Source:** `theory_x/stage_counterfactual/counterfactual_node.py`; `ProblemMemory.touch()` exists in `theory_x/stage7_sustained/problem_memory.py`.
- **Verified:** `_process_one()` selects one `state='open'` row using `ORDER BY last_touched_at ASC LIMIT 1`. It returns on empty TimeFetch, no buildable results, or after Gate processing without updating `last_touched_at` or calling `ProblemMemory.touch()`. The auto-promotion path is disabled.
- **Test gap:** `tests/test_counterfactual_node.py` tests a single open problem and individual packet/Gate behavior; it has no multi-open-problem progression/rotation test.
- **Risk/qualification:** if no other producer touches the selected row, subsequent ticks can select it again and delay newer problems. No live problem rows or tick history were inspected. Whether persistent focus is intended is unresolved.
- **Disposition:** design/evidence question; do not wire `touch()` or change selection until policy is established.

### G-52 — TimeFetch and VoiceEngine candidate eligibility are broader than their test inventory

- **Sources:** `theory_x/stage_throw_net/time_fetch.py`, `theory_x/stage_throw_net/voice_engine.py`, `tests/test_throw_net_time_fetch.py`, and `tests/test_voice_engine.py`.
- **Verified:** `TimeFetch.fetch_from_beliefs()` filters confidence and minimum content length but does not constrain `tier`, `paused`, `locked` or `erosion_stage`. Novel-association retrieval joins the paired belief rows without current-state eligibility filters; arc retrieval filters arc type/quality/summary but does not prove current-state eligibility of the beliefs represented by an arc.
- **Consumer path:** `VoiceEngine._retrieve_candidates()` consumes `TimeFetch.run()` results and enriches belief candidates with `tier` and `reinforce_count`; it does not recheck paused/locked/retired state. `_score_candidate()` gives non-T3–T6 tiers a score penalty (0.5), not a hard exclusion. The configured minimum score is 0.6, so a strong semantic/confidence/recency/drive/genius candidate can still clear it. The tier penalty alone does not establish retired-content exclusion.
- **Test inventory (corrected):** `tests/test_throw_net_time_fetch.py` exists and covers confidence/content-length filters, novel-association matching/similarity ordering, arc type/quality filtering, problem routing, deduplication/capping and provenance. It does not test the above belief-status exclusions or current-state eligibility of association/arc endpoints. `tests/test_voice_engine.py` compares T4 and T8 scores but does not assert that T8/paused/locked/retired content is excluded. The prior statement that no TimeFetch test file was found was an incomplete search result.
- **Disposition:** policy/coverage gap only. Whether Tier 8, paused, locked or otherwise retired content should be excluded is a governing eligibility decision, not inferred here. Add path-level tests after the canonical eligibility contract is confirmed; do not change retrieval candidates or scoring without specification/approval.
### G-53 — Warrant use-day timestamp cursors can skip tied rows at a page boundary (RESOLVED)

- **Source:** `theory_x/stage_warrant/recorder.py`; lineage and arc-membership use-day cursors.
- **Original finding:** the strict-greater-than timestamp-only cursors could skip equal-timestamp rows that straddled a 20,000-row page boundary.
- **Resolved by:** PR #253, merged as `c80d9dbb878ac15a39d6707a9c89ab2a51f8518c`. The recorder now orders lineage by `(created_at, child_id, parent_id, relationship)` and arc membership by `(joined_at, arc_id, belief_id)`. Event time is primary; declared composite-key fields break ties. This avoids hidden-rowid dependence and also sees later events attached to older child/arc IDs.
- **Verification:** exact-head full suite run `46014884835` passed (2,590 passed, 7 skipped, 45 subtests). Regression coverage includes tied timestamp pages, rowid remapping, late additions to older arc/child keys, malformed typed cursor fallback and idempotent use-day replay.
- **Disposition:** **CLOSED — cursor pagination correctness only.** Warrant eligibility, use-day source population, survival scoring, sustain policy and feature gates were not changed. Query-plan/performance measurement remains outstanding before enabling the Warrant recorder on a data-bearing host.

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

- **Authority check (27 November 2026):** a recursive path inventory of current `main` found no tracked file identifying the separate user-authored Development Proposal V2.1; earlier Library retrieval did not establish its authoritative original or approval record. This is a retrieval gap, not proof that the document does not exist. The consolidated S-01–S-25 register remains frozen and must not be reconstructed from secondary descriptions.
- **Disposition refinement:** G-58 remains OPEN. The source/test mismatch is verified, but intended `open` versus `active` semantics are not. Do not change GoalManager writes, CoherenceGate queries, add state transitions, migrate rows or alter lifecycle policy until the exact governing clause and approval are recovered. Next step: map the approved clause to the producer/consumer state machine and add a GoalManager.open() → CoherenceGate integration test. If authority cannot be recovered, retain the mismatch as an explicit unresolved blocker rather than guess.

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

### G-61 — One-pen Writer migration (partially resolved; full census remains open)

- Specification: SPECIFICATION.md §8 states exactly one writer thread per database and that all writes submit through the single Writer queue; substrate/writer.py explicitly says direct writes elsewhere are a bug by definition.
- Resolved on current main with isolated regression coverage:
  - RememberLoop — PR #160.
  - Diversity EdgeBuilder — PR #158 (including per-statement rowcount handling).
  - Sustained FocusLoop — PR #159.
  - Fetch and Wonder — PR #163.
  - Surprise — PR #165.
  - Pattern and Witness — PR #164.
- **Historical PR status rechecked 27 November:** PRs #162 and #166 are closed unmerged; their bounded work was superseded by later merged persistence integration, including PR #200. PRs #168 and #169 are merged. PRs #180/#183 and #191/#196/#200 also merged their respective one-pen migrations. The older “four migrations in flight” status is superseded.
- **Additional current-main active path:** `signal_to_problem_loop` is registered in the Stage 2 dynamic factory. It opens raw write-capable connections to beliefs and conversations, adds `signals.actioned_at` at runtime, commits the two databases separately, and invokes `prose_stats.build_direct()` every 30 ticks. See G-85 and the 27 November system research report.
- The Writer/Reader-based `prose_stats.build()` exists but is not used by the scheduled loop. No dedicated SignalToProblem or prose-stats integration test was found.
- **Impact/qualification:** the global one-pen audit remains open. The cross-database ordering/recovery contract is unresolved; do not mechanically replace the two-DB transaction or imply atomicity. No live lock contention or runtime incident is claimed.
- **Disposition:** continue the remaining census and define idempotent recovery before migrating SignalToProblem. A separate prose-statistics Writer migration may be evaluated after equivalence/performance tests.
- **Repository census, 28 November 2026 (pre-merge baseline `a6d08405`):** `tools/one_pen_census.py` (read-only static scan; `tests/test_one_pen_census.py`) lists 112 write-capable `connect()` call sites outside `substrate/` and the tests. Classified by enclosing-function write SQL/commit and by caller tracing:
  - **Boot-reachable direct writers to the six substrate databases:** only `signal_to_problem_tick()` (G-85; fix proposed in PR #347).
  - **Documented exception:** `strikes/catalogue.py` writes its own `strikes_catalogue.db` directly by design (module docstring: observation data, not operational substrate); it is constructed at boot (`run.py:634`) and written from the strike protocol and the GUI notes endpoint. Whether SPECIFICATION.md §8 should cover non-substrate databases is a governance question, not a defect fixed here.
  - **Present but not boot-reachable:** `groove_breaker` (`ENABLED=False`, never constructed), `value_drift_monitor` (no importers), `genius_provenance_tag.backfill/undo` and `source_identity.backfill` (no callers), `prose_stats.build_direct` (no callers since PR #279), the `hot_observer` `__main__` demo, and 10 standalone script/tool sites.
  - **Read-only use of a write-capable connection:** 68 runtime sites read through a non-`mode=ro` connection; 7 hand their connection to a helper or caller and were traced by hand (all readers, apart from the strikes catalogue). These are hygiene, not one-pen writes.
  - **Limits:** a source-text heuristic, not proof; SQL assembled elsewhere, connections stored on attributes and dynamic imports can evade it, and reachability was traced by hand. Host/runtime state was not inspected.

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
- **Disposition / post-snapshot status:** source-level persistence defect addressed by merged PR #183 (exact-head run #1519: 2,525 passed, 7 skipped, 40 subtests). `Writer.transaction(callback)` serializes `ingest()` and `reconcile()` on the conversations Writer; `_learn()` reads beliefs read-only and routes confidence updates through the beliefs Writer; cap-hit and learning-log inserts remain in the same conversations transaction. PR #168's canary Writer migration and PR #180's Learning Guards Writer migration are also merged. **Historical activation boundary (main `99ae476`; superseded by the 27 November current-main re-audit below):** at that earlier snapshot, the audited entry path did not show an Expectations/reconcile invocation. That “no boot invocation” conclusion is no longer current. The later SelfPredictionLoop integration provides a boot-reachable caller under the tracked launcher. The two databases remain separate transactions: belief updates commit before the enclosing conversations transaction, so a later conversation commit failure can leave a belief update without its ledger row. PR #183 changed persistence routing only; it did not change flags, thresholds, adjudication, valence or confidence policy.

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


---

## Follow-up source audit — G-68 to G-72 (27 November 2026)

These findings were rechecked against current main after the bounded persistence integrations. They are source-level findings, not claims about current host activation or live data.

### G-68 — decryption ProbeRunner live-mutation and cleanup risk

- **Source:** `decryption/probe_runner.py`, distinct from `theory_x.probes.probe_runner.ProbeRunner`.
- **Verified:** `dry_run` defaults to `False`. Live setup calls `/api/mode/set` and inserts synthetic `fountain_insight` beliefs using a raw SQLite connection. Teardown deletes the recorded IDs but does not restore the previous NEX mode. The ID list is cleared in `finally` even if deletion fails, removing the in-memory retry list. Process termination before teardown bypasses cleanup. Dry-run suppresses mode changes and synthetic writes/deletes but still performs read-only DB inspection.
- **Activation boundary:** not imported by the normal `run.py` boot path inspected. It was not invoked; no synthetic rows or mode changes were made.
- **Disposition:** **OPEN — experimental safety/cleanup risk.** Do not run against live NEX without explicit experiment approval and a verified disposable database/runtime. No code or runtime change.

### G-69 — SurpriseLoop timestamp cursor and failed-promotion loss (OPEN / Gate 0 review required)

- **Source:** `theory_x/life/surprise_loop.py`; producer `theory_x/stage_prediction/predictive_substrate.py::_verify()`.
- **Original finding:** timestamp-only pagination with `triggered_at > since` and `LIMIT 20` can skip tied rows at a page boundary; the old loop also advanced its checkpoint past non-integrity conversion/write failures. Ordinary surprises could receive a duplicate `surprise` tag.
- **Current-main proposal:** PR #259 replays the event-ID cursor correction on the post-#256 mainline. It uses monotonic `surprise_events.id`, persists timestamp and ID together, migrates by replaying rows exactly at the legacy cutoff, stops at the first non-duplicate failure so the failed and later events retry, and treats only duplicate belief-content collisions as already represented. It also fixes duplicate tags. Source review confirms the producer writes `actual_content`, `surprise_flag` and `big_surprise` at event insertion.
- **Migration limitation:** events strictly older than the legacy timestamp cutoff are treated as historical and are not replayed. Recovering that history requires a separate, explicit corpus-backfill decision.
- **Verification:** predecessor PR #257 passed its exact-head suite on the pre-#256 base (2,601 passed, 7 skipped, 45 subtests). PR #259 is the authoritative post-#256 current-main replay; exact-head full suite run `46017043819` passed (2,610 passed, 7 skipped, 45 subtests).
- **Governance:** **GATE 0 HOLD — NOT FOR MERGE OR DEPLOYMENT.** Previously skipped events may now reach the belief corpus and change downstream retrieval inputs. Founder review and explicit approval are required. No prediction scoring, surprise thresholds, event generation, cadence or feature gates are changed.

### G-70 — M0.5 trace continuity across the speech queue (IMPLEMENTED / source-test gap CLOSED; M0.5 acceptance OPEN)

- **Sources:** `theory_x/stage6_fountain/crystallizer.py`, `influence_trace.py`, `speech/queue_consumer.py`, and `speech/player.py`.
- **Verified baseline:** the crystallizer records speech-queue enqueue in the trace sidecar. Persisted `spoken` means the blocking playback call returned without raising, not independent acoustic confirmation that sound reached a listener.
- **Merged correction:** PR #261 merged as `cc8ae43652bdba919198ee4bb90fabbd8f05632f`. A process-local correlation registry keyed by belief ID (512-entry bound, one-hour TTL, one-shot consumption) is registered before queue insertion becomes visible. The originating TraceContext continues through parent-linked dequeue, synthesis, playback, suppression and terminal status/failure events. Failed insertion discards the correlation and records a categorical failure event.
- **Regression coverage:** registry capacity/expiry/one-shot/discard semantics, concurrent one-shot claims, successful playback, synthesis/playback failures, suppression, speaking/spoken/suppressed status-write failures, and speech without a trace link. Trace metadata excludes speech text/audio and records categorical exception types.
- **Limitations:** correlation is process-local and is not reconstructed after restart. `spoken` remains an operational return status, not proof of acoustic delivery. No schema, speech selection, queue ordering, cadence, synthesis/playback behaviour, feature flags or cognitive decisions were changed. The trace overlay remains default OFF.
- **Exact-head evidence:** PR #261 head `bed052c9d63422f52a9514325f74f113959db2a3`; run `46020502376` **PASSED** (**2,611 passed, 7 skipped, 45 subtests; baseline OK**). The code-only branch mind-map check still reported P9 stale; its corrected source anchor was reverified in documentation run `46020611137` (**2,599 passed, 7 skipped, 45 subtests**, no P9 stale warning).
- **Disposition:** **G-70 source/test gap CLOSED. M0.5 acceptance remains OPEN** pending complete roadmap evidence, including authorised live L4 capture and paired semantic-equivalence evidence. No live runtime, speech device, database or feature flag was touched.

### G-71 — WarrantRecorder hidden-rowid cursor stability across VACUUM (RESOLVED)

- **Sources:** `theory_x/stage_warrant/recorder.py` and `substrate/schema/beliefs.sql`.
- **Original finding:** PR #184's timestamp-plus-hidden-rowid cursor could be invalidated when SQLite VACUUM remapped rowids; the tables instead declare composite primary keys `belief_lineage(child_id, parent_id, relationship)` and `arc_members(arc_id, belief_id)`.
- **Resolved by:** PR #253, merged as `c80d9dbb878ac15a39d6707a9c89ab2a51f8518c`. The versioned JSON cursor uses event time plus the declared primary-key columns as tie-breakers; hidden rowids are not used.
- **Verification:** exact-head full suite run `46014884835` passed (2,590 passed, 7 skipped, 45 subtests). Tests force rowid remapping and exercise later additions to older arc/child keys.
- **Disposition:** **CLOSED — cursor identity and ordering.** The feature gate and Warrant eligibility/policy are unchanged. The timestamp/key access path has not yet been benchmarked on live row counts; see the current INDEX manual's Warrant query-plan note.

### G-72 — gated SelfPredictionLoop canonical database-handle injection

- **Source:** `run.py`, `theory_x/stage_world/self_prediction.py`, `theory_x/stage_world/owned_belief.py`, `theory_x/stage_world/commitments.py`, and `theory_x/stage_world/expectations.py`.
- **Resolved:** PR #236 routes commitments schema, scans, cursors and standalone releases through the canonical conversations Writer and dynamic Reader. PR #238 injects AppState conversations/beliefs Writers and conversations/dynamic/beliefs Readers into the gated `SelfPredictionLoop`, self-prediction functions, owned-belief producer, commitments scan and Expectations reconciler. It adds actual Writer-injection and nested handle-propagation tests.
- **Verification:** PR #236 exact-head run `46006462779` passed (2,573 passed, 7 skipped, 45 subtests). PR #238 exact-head run `46008022480` passed (2,584 passed, 7 skipped, 45 subtests). PR #238 merged as `74cff71045d1f6006b3873138ec658a66acf34a8`.
- **Activation boundary:** `NEX5_SELF_PRED=1` remains the loop start gate. No loop was started, no feature flag was changed, and no host environment/process state was collected. This closes the source-level handle-injection defect only; it is not evidence of runtime activation or completion of the global write-path census.
- **Disposition:** **CLOSED — persistence ownership/integration fix merged.** Cadence, prediction rules, selection, thresholds and feature gates were preserved.


### G-73 — Dormancy scan coverage, duplicate ownership and eligibility boundary (OPEN / policy review)

- **Sources:** `theory_x/diversity/dormancy.py`, `theory_x/diversity/loop.py`, `theory_x/diversity/consolidation.py`, `theory_x/diversity/reanimate.py`, and `theory_x/stage6_fountain/generator.py`.
- **Verified on current main:** `DormancyScanner.scan_incremental()` selects the oldest 50 rows from three source categories by `created_at ASC`, without a cursor or exclusion for already-scanned rows. It therefore reselects the same oldest cohort on every call; rows after the first 50 are starved. The scan includes `behavioural_observation`, but `_average_gap()` computes its baseline from only `fountain_insight` and `synergized`. `DiversityLoop` owns one scanner and calls it on its loop cadence. `ClockRunner._run_fast()` constructs a second scanner on each fast tick (20-fire boundary), so that path does not preserve scanner cursor state. The two paths target the same beliefs population/table but are separate owners; actual combined work rate was not measured. `wake_one()` filters only `reanimated_at IS NULL`; it does not recheck tier, paused, locked or retired eligibility.
- **Pending proposal:** PR #102 adds an in-memory ID-keyset cursor with wraparound, makes ClockRunner's scanner persistent, and adds tier/paused/retired filters to scan, dormant selection and reanimation. PR #145 adds tests for partial-tail wraparound and persistent-instance reuse. Both exact-head runs passed on their own older base, but neither branch has been revalidated on current main. The proposal still leaves DiversityLoop and ClockRunner with separate scanner instances/cursors.
- **Defence-in-depth gap in the proposal:** its final Fountain reanimation fetch rechecks `tier <= 7` and `paused = 0` but does not recheck `erosion_stage != 'retired'`, unlike the preceding dormant/reanimation queries. Add a regression for a belief retired between selection and final injection before treating the path as fully guarded.
- **Disposition:** **OPEN — scan coverage/ownership and eligibility contract.** Confirm whether two scan cadences are intentional and whether the retired marker must be enforced at every injection boundary. Do not merge/replay the behavioural filters or alter maintenance cadence before the governing policy/Gate 0 review. No live dormancy rows or runtime scan frequency were inspected.


### G-74 — Warrant scoring and survival scans do not filter the retired-stage marker (OPEN / eligibility contract)

- **Sources:** `theory_x/stage_warrant/warrant.py::compute_all()`; `theory_x/stage_warrant/recorder.py::survival_cycle()`.
- **Verified on current main:** WarrantPass selects unpaused beliefs with `tier <= max_tier` (default 7) but does not read/filter `erosion_stage`. WarrantRecorder survival selects unlocked, unpaused Tier 3 / 5–6 / 7 rows and likewise does not filter `erosion_stage`.
- **Qualification:** `erosion_stage='retired'` is an independent marker in the broader eligibility system. Harmonizer's normal retirement path writes Tier 8; no normal runtime writer for a lower-tier retired marker was established, and no live rows were inspected.
- **Conditional impact:** if a lower-tier, unpaused row carries the retired marker, WarrantPass may include it in scoring and WarrantRecorder may include it in shadow survival checks.
- **Disposition:** confirm whether the retired marker overrides tier for Warrant scoring and survival. If yes, add isolated lower-tier-retired fixtures and filters to both paths. No scoring, recorder, schema or runtime behavior changed.

### G-75 — WarrantRecorder and WarrantPass have distinct normal-boot boundaries (OPEN / lifecycle question)

- **Sources:** `run.py`, `theory_x/stage_warrant/recorder.py`, `theory_x/stage_warrant/warrant.py`, `gui/server.py`, `tools/warrant_validate.py`, and tracked `nex_keepalive.sh`.
- **Verified on current main:** `run.py` constructs and starts WarrantRecorder only behind `NEX5_WARRANT_RECORD == '1'`. No normal construction/start of the periodic WarrantPass loop was found in the inspected `run.py` or `gui/server.py` paths, although WarrantPass has its own `NEX5_WARRANT` start guard and its module docstring describes background operation. `tools/warrant_validate.py` calls `compute_all()` once for read-only validation; it does not start the periodic loop.
- **Configuration qualification:** the tracked keepalive declares `NEX5_WARRANT_RECORD=1` but not `NEX5_WARRANT`. The known launcher path blocker and uninspected user systemd unit mean host-effective activation remains UNKNOWN.
- **Documentation correction:** PR #262 merged as `c9e25d7cf85659e80053f5fe75928ee71486a141` and corrects the WarrantPass class docstring, which incorrectly attributed its construction/start to `run.py`. The normal boot source actually starts WarrantRecorder behind `NEX5_WARRANT_RECORD` and does not construct WarrantPass. The merge is documentation-only; it does not add a caller or change flags.
- **Disposition:** record-only operation may be intentional while Warrant evidence accrues after its failed validation gate. Clarify the intended lifecycle; do not wire WarrantPass, alter flags or change its gate without founder approval. No live process or `belief_warrant` state was inspected.


## Provenance erosion replay status correction — 27 November 2026

PR #264's exact-head full-suite run `46023260805` completed successfully, but PR metadata/commit comparison established that its merge base was the pre-PR #263 commit `cc8ae43652bdba919198ee4bb90fabbd8f05632f`. The run therefore does not validate a current-main replay. PR #264 was closed as superseded. PR #266 carries the same bounded keyset-pagination implementation and regression tests on current main `edb869af154a33cd77df5ad9bdf010d3e6ab06a2`; it is draft and requires its own exact-head full-suite result. Behavioural impact and review boundary are documented in #266. Do not merge or deploy until that run is green and the changed belief-evolution consequences are reviewed.


## Current-main PR status correction — 27 November 2026

At main `9f5a9f0b476716b6a6fd0a39aa3cf3041a3a4465`:

- PR #268 is the latest-main replay of provenance erosion keyset pagination. Base equals current main; head `8b8ffaff27e298ff96dd4a09452ac14067dc4916`; run `46024945847` was still executing the exact-head full baseline at last check. Do not claim validated/merged until it finishes and the behavioural impact is reviewed.
- PR #266 is an older-base replay and is superseded by #268. PR #264 is also superseded; its green run is not evidence for the latest replay.
- PR #259 remains an open but stale-base SurpriseLoop proposal. Its base is `e78773def4549f646257945e5886ec71a7837374`; head is `9686fa6da7e835a149f31b516a5ff7a731c3a8b0`; its branch diverges from current main. G-69 remains Gate 0 HOLD; do not merge/deploy or replay into current main without explicit founder approval of the behaviour impact.
- The Repository Reality Report and Architecture Crosswalk are source snapshots at `ae406fa8fcb1abdf25cdf4ae1bd65333e1148ca8`, 44 commits behind current main. Their findings are historical until rechecked. The backlog header SHA does not automatically refresh the evidence for each finding.


---

## Current-main source revalidation — G-65 and G-76 to G-79 (27 November 2026)

**Snapshot:** `main` at `3e7f0f35ccc58519f57ae4fd2e13b1f688f688a3`. This follow-up supersedes the earlier G-65 activation statement and records the new G-76–G-79 evidence. Host-effective state remains UNKNOWN unless explicitly stated otherwise.

### G-65 — Expectations reconcile/learning path is launcher-armed and boot-reachable

The former “no boot invocation” conclusion from main `99ae476` is superseded. Current source shows `run.py:511–514` starts `SelfPredictionLoop` behind `NEX5_SELF_PRED=1`; `theory_x/stage_world/self_prediction.py:1149–1154` calls `expectations.reconcile()` when `reconciler_on()` holds; and `reconcile()` reaches `_learn()` when `learning_on()` holds. The tracked `nex_keepalive.sh:218–219` sets `NEX5_SELF_PRED=1`, `NEX5_RECONCILER=1` and `NEX5_EXPECT_LEARN=1`. The path is therefore launcher-armed, but actual host launcher use, process state and effective environment remain UNKNOWN. This does not establish that a live host currently runs the loop.

### G-76 — Provenance erosion's use/reinforcement description does not match its counter (OPEN)

- **Sources:** `theory_x/stage3_world_model/erosion.py` and `theory_x/stage3_world_model/promotion.py:118–182`.
- `record_use()` increments `use_count`; `_erosion_check()` reads `reinforce_count`. `record_reinforce()` increments `reinforce_count` and invokes the check. The reviewed caller inventory found the runtime call in `BeliefPromoter.corroborate()` after a corroboration promotion (`promotion.py:182`). Thus ordinary use does not itself advance erosion; progression is currently reinforcement-count driven.
- Thresholds are 10 (`external`), 30 (`nex_absorbed`) and 80 (`nex_integrated`); `nex_core` has no next threshold. The module docstring's “through use and reinforcement” wording is inaccurate for the current mechanism.
- **Disposition:** OPEN for founder clarification of intended erosion semantics. No counter, threshold, stage transition or confidence bump changed. No live population/max figure is asserted.

### G-77 — BeliefPromoter stale-transition race (CLOSED by PR #270)

- **Sources:** `theory_x/stage3_world_model/promotion.py`; `tests/test_promotion_atomicity.py`.
- Corroboration's read/decision/write is serialized in the canonical beliefs Writer transaction. Decay writes are conditional on the snapshot tier, unlocked state and unchanged idle cutoff; decisive contradiction performs its read/decision/write transactionally.
- PR #270 merged as `d2a5c107019d79276879f3ade6ebefd348686e36`; run `46032636987` passed 2,624 tests, 7 skipped and 45 subtests with baseline OK. Thresholds and promotion/demotion policy are unchanged.

### G-78 — Warrant survival parser did not decode stored promotion-log strings (CLOSED by PR #271)

- **Sources:** `theory_x/stage_warrant/warrant.py::_promotion_events()`, `_survival()`; `tests/test_warrant_promotion_log_format.py`.
- The producer stores each JSON event as a JSON-encoded string element. The consumer now decodes both string and object forms and skips malformed elements without losing valid history; tests include a row written by the real BeliefPromoter.
- PR #271 merged as `77d4cd89015ebf605c9e5ec6af994a28126f6ed5`; exact-head run `46032708456` passed 2,629 tests, 7 skipped and 45 subtests with baseline OK.
- **Consequence for earlier validation results (verified from source at `a6d08405`):** `tools/warrant_validate.py` judges its gate on the composite `warrant` (`WEIGHTS`: survival 0.35, sustain 0.35, indep 0.20, xsynth 0.10) through group AUCs and Spearman correlations, including decayed-tier groups. Before PR #271, survival ignored all promotion history for every belief that had any, so any `warrant_validate` verdict produced before `77d4cd8` -- including the failed validation gate G-75 refers to, whose source run was not located in the repository -- was computed with history-free survival and is not evidence about the current scorer. A read-only host re-run needs founder authorisation; none was performed.

### G-79 — Expectations _learn compare-and-set (CLOSED by PR #272)

- **Source:** `theory_x/stage_world/expectations.py::_learn()`; tests: `tests/test_expectations.py::TestLearningDoesNotOverwriteConcurrentChanges`.
- Before PR #272 (main `3e7f0f3`), the read-then-unconditional absolute confidence write could overwrite an intervening confidence change, modify a belief locked after the read, and record a stale before-value.
- PR #272 implemented compare-and-set on ID + previously read confidence + unlocked state, with at most three read/re-decide retries. Only applied transitions are logged; unchanged factor/clamps/cap policy and beliefs-before-conversations ordering are preserved. No cross-database atomicity is claimed.
- The three race tests fail on unmodified main and pass with the fix; mutation checks detect removal of the confidence guard, lock guard and retry. Focused local suites: 154 passed after the fix; original implementation left the three new tests failing.
- Exact head `67fcf46a84bcfae5b5a309502680fffe8bb347b8`, run `46035516300`: 2,632 passed, 7 skipped, 45 subtests; baseline OK. PR #272 was squash-merged to main as `90ffd57c75b33eff161ea33e29388e0732f0290e`.
- The path is boot-reachable under the tracked launcher (G-65). The competing learning-guard subtraction flags are not set in that launcher, `revert_subtraction()` has no runtime caller, and erosion's confidence bump only occurs on stage advance. This is preventive integrity hardening, not evidence of an observed live race. Host-effective state remains UNKNOWN.

### Governance boundary

G-76 remains a founder decision. G-79 is closed by PR #272, merged as `90ffd57c75b33eff161ea33e29388e0732f0290e`. Gate 0 remains pending founder review; Phase 1 is unauthorized; G-69 / PR #259 remains Gate 0 HOLD. No runtime flags, live database state, frozen specification, roadmap or cognitive policy were changed by this evidence update.


## Post-PR #274 mind-map freshness recheck — 27 November 2026

**Current main:** `14873c10673760b8adbbf6fb0076226d1c97ffa4`. PR #274 merged as this commit after its exact-head run `46037202834` passed **2,632 tests, 7 skipped, 45 subtests; baseline OK**. Its CI mind-map check reported 30 nodes, 0 unverified, 14 dark and 2 blocked, with no stale-source warnings. The two missing doctrine references remain unresolved under D-03; the past-due P13 marker remains intentionally retained and is not permission to rearm. No MIND_MAP node or runtime state changed.


## Current-main system research continuation — 27 November 2026

**Evidence snapshot:** `main` at `14873c10673760b8adbbf6fb0076226d1c97ffa4`. Detailed source anchors and limits are in `NEX_PHASE0_SYSTEM_RESEARCH_2026-11-27.md`.

### G-80 — Reanimation mark-before-delivery loss window (OPEN)

`wake_one()` persists `reanimated_at` before placing the selected row in process-local `_pending_reanimation`; `pop_reanimated()` clears that global. There is no durable pending-delivery record or restart recovery for a row already marked reanimated. A process loss between marking and Fountain consumption can strand the handoff. No incident is established. Define at-most-once versus recoverable delivery and add crash/restart tests before choosing an outbox or retry design.

### G-81 — Fountain and ClockRunner fire counters diverge (OPEN)

Fountain increments `_total_fires` at four output paths, while `notify_fire()` appears only in the normal LLM path. ClockRunner thresholds and Fountain reanimation cadence therefore count different populations. Define the intended meaning of “fire”; do not change cadence until that contract is explicit.

### G-82 — Folded into G-73: dormancy scan coverage and ownership

The current scanner selects the first 50 beliefs by creation time without a cursor. ClockRunner constructs a new scanner in its fast path, while DiversityLoop has a separate scanner. G-82 is not a separate defect: it is additional current-main evidence for G-73's existing scan-coverage/ownership/eligibility question. PR #102/#145 remain old-branch drafts and do not resolve final retired-state revalidation.

### G-83 — Metacognition re-emits unacknowledged groove alerts (OPEN)

The Chat route calls `Metacognition.tick()`; its groove detector reads recent unacknowledged alerts and writes meta-cognition event rows without acknowledging the source alert. The stillness threshold counts event rows, so repeated Chat turns can count one alert multiple times. Define idempotency/acknowledgement and distinct-source evidence before changing reflective behaviour.

**28 November 2026 source refinement (same finding; not a new defect ID):** the bounded source trace confirms the 600-second / LIMIT 3 source query, per-returned-row derived event writes, global 1,800-second count of all derived `groove` rows, and 3-row threshold. One tick returning three source rows can meet the threshold; repeated ticks against one unchanged source ID can also meet it. The stillness activation row contains no topic/source identity. `FountainCrystallizer` treats any active conversations stillness row as a global crystallization hold, while `FountainGenerator` has already generated/recorded the fire and still returns/logs the thought; the crystallizer's later speech-queue path is not reached. Older `theory_x/SYNTHESIS_PLAN_V2.md` §3 describes a same-topic threshold and same-topic Fountain suppression, so current source behaviour is broader/different. The older plan is provenance only, not authority to amend frozen specifications or Founder Sign-Off. Two separately named `stillness_log` tables exist in conversations.db (Row 9) and dynamic.db (Fountain duplicate-retrieval instrumentation); they are unrelated. Before any fix, resolve intended evidence identity, per-topic/global scope, output-versus-crystallization semantics, and controlling authority. Existing tests verify a mocked count threshold and the crystallizer hold, but not distinct source IDs, topic matching, or the full Generator/output consequence. Snapshot: main `18c8f06171e1de35c3210831a49b63d0e2487af0`; see manual §114. No runtime change or tests run in this pass.

**Implementation-history refinement:** the design-plan commit `36e7ed40661db58d83214b40aebde7a33fdb2519` (11:29:57 UTC, 11 May 2026) added §3's same-topic threshold/suppression description; the Row 9 implementation commit `c4b005f32e931047711ef6cdbe03e84a00183885` followed at 13:21:14 UTC. Its patch/commit message implements a global count of derived groove rows and a global crystallizer hold, with scalar-count tests and no topic/source-ID matching. No rationale for dropping or deferring the same-topic detail was located in the inspected commit text. `theory_x/DOCTRINE.md` has a more general Row 9 summary without the same-topic wording. This proves an artifact-level scope divergence, not which source had authority or whether the change was founder-approved. Keep that authority question UNKNOWN; do not restore the older plan's behavior without approval. See manual §§114–115.
 
**Caller/cadence refinement:** current run.py starts the 60-second DiversityLoop separately from the production Metacognition instance. GrooveSpotter runs in that loop; Metacognition.tick() is called by the chat handler in gui/server.py. The SentienceNode protocol says tick is called once per chat turn, and the registry only registers/lists nodes; it has no periodic tick dispatcher. Therefore background alerts can accumulate between chats, and the next chat tick selects at most the three newest eligible rows. No background Row 9 evaluation occurs from DiversityLoop itself. Exact live chat cadence remains UNKNOWN. See manual §116.

**Stillness-renewal consequence:** because the active-stillness check occurs after this tick's per-row groove event inserts, later chat ticks can continue replenishing the 1,800-second derived-event count from the same still-unacknowledged source rows while a 60-second hold is active. At a chat tick after the hold expires, the same eligible alert(s) can be read again and can re-trigger another hold without a new detector episode. This is a source-derived possibility only; no live renewal cycle is claimed. The query's ORDER BY detected_at DESC LIMIT 3 also means a static set of 4+ eligible rows repeatedly selects the newest three, potentially starving older rows until they age out of the 600-second lookback. Add controlled-clock tests for single/three/four source IDs, repeated ticks across expiry, and no-new-alert renewal. See manual §117.

**Prior-art comparison:** the cited Sentience 5.5 Stillness_Node.py (main snapshot 1767acf1fdb321d046261eb3c3059084c85fc0c8) uses a global non-reentrant is_still/stillness_until state and logs only trigger/time/duration; it has no topic or source-alert identity. NEX SYNTHESIS_PLAN_V2 §3 describes a topic-specific extension, but the May 11 NEX implementation retained a global event count/global crystallizer hold. This may reflect reuse of the prior-art shape, but no decision to defer the topic-specific delta was located. Do not treat the old prior-art file or plan as approval to change current semantics. See manual §118.

**Speech-consumer boundary:** the active SpeechQueueConsumer is constructed with beliefs Writer/Reader only and polls pending beliefs.db speech_queue rows. Its current polling/playback path has no conversations stillness read. Row 9 prevents a new queue entry from a fire whose crystallization is held, but it does not pause already-pending queue entries; those can continue to be spoken under the consumer's independent pause/quiet-hours controls. tests/test_speech.py does not test a pending item during Row 9 activation. See manual §119; no runtime behaviour change is proposed or authorized.

**28 November 2026 reader-census refinement:** the bounded tracked-source scan found no direct acknowledgement writer. It also identified two additional live influence paths: (1) active CompetingDrives reads max groove severity over 24h, gives it 0.30 weight in raw coherence, and can surface a changed opposing-drive tension block in the Fountain prompt; (2) Fountain's recent-STRIKING prompt block, enabled unless NEX5_GENIUS_PROMPT_OFF=1, uses the latest alert pattern (severity ≥0.5, 1h) to remove matching candidate fires from the prompt. Both read without acknowledging the source. Other located consumers are conditional/dormant (substrate voice under NEX5_RECONCILE, stakes readiness under NEX5_STAKES, topic shadow, GrooveBreaker) or observational (SubstrateHarmonic log-only, StateSnapshotWriter, on-request ProbeRunner context, GUI overview, offline trajectory). See manual §120. No live host/database was inspected, and the code-search index is unavailable; source-bounded census only.

**Producer-identity refinement:** GrooveSpotter uses four process-local fingerprints: exact sentence content, top trigram text, templated-belief-ID frozenset, and ordered current-window IDs for centroid tightening. Fingerprints clear when their detector condition falls away, but reset on process restart; the module explicitly permits one fresh emission after restart. The persisted sample_belief_ids fields do not preserve all four fingerprints uniformly (especially n-gram and centroid). The offline trajectory tool groups by (alert_type, sample_belief_ids), which is not equivalent to all producer fingerprints. Existing tests do not characterize repeated detect_all() calls, reset/recur, or restart replay for all four detectors. See manual §121. This is producer-side identity/replay evidence, separate from Metacognition consumer replay and Row 9 renewal.

**Test characterization candidate:** draft PR #448 adds only tests/test_groove_spotter_fingerprints.py, covering same-instance unchanged-scan suppression, clearing/re-emission, and fresh-instance replay for all four current producer fingerprints (ngram, exact, template, centroid). Head f4447ad5b243b97c91c28fc00abbef88fe7c51f9 against main 18c8f06171e1de35c3210831a49b63d0e2487af0. Exact-head workflow run 46173749707 was queued and commit status pending at this snapshot; no tests were executed locally and no passing result is claimed. Test-only, no runtime changes; keep draft pending CI/review. See manual §122.

**Historical runtime anchor (2026-11-14 investigation):** journal/INVESTIGATION_2026-11-14_groove_facts.txt records a read-only live DB count of 1,198 rows, then 1,199 about 20 minutes later; 0/1,198 had acknowledged_at set. The sample was 1,136 template_repetition (94.8%), 62 ngram_repetition (5.2%), zero exact and zero centroid alerts. The same journal's 30-minute gap clustering of 1,199 rows produced 55 groups (median 14 alerts/group, p90 54, max 102; median span ~106.7m, max ~837.3m). The Nov 10 incident's alerts 751/752 were template_repetition severity 1.0 and its group had 8 alerts over 56.4m; signal_cooldown was written and later matched a crystallization reject. These are historical observations, not current-host facts. Gap groups are an offline time-cluster metric, not the four producer fingerprints or Row 9 derived-event identity. See manual §123.

**Controlled-clock consumer test candidate:** draft PR #449 adds one isolated test for one still-unacknowledged source alert read across five Metacognition ticks. It asserts the source stays singular/unacknowledged, five derived groove events accumulate, a 60-second stillness row is created on event 3, the active hold does not stack on event 4, and a second hold is created on event 5 after expiry without a new source alert. Exact head 50c2e083de1dab3e40301b37dc14b614a0d08f23; workflow run 46174148899 IN_PROGRESS at snapshot, no pass claimed. Together with producer test PR #448 this characterizes both replay boundaries, but does not select the intended G-83 semantic identity. See manual §124.

**Producer test result:** PR #448 exact head f4447ad5b243b97c91c28fc00abbef88fe7c51f9 passed GitHub Actions run 46173749707 on 2026-11-28: 3,081 passed, 7 skipped, 86 subtests, 0 deselections, baseline OK; mind-map check 30 nodes / 0 unverified / 12 dark / 2 blocked. This validates the four per-instance detector fingerprint tests only; it does not establish canonical semantic episode identity or live restart replay. PR #448 remains draft pending review. Consumer replay/Row 9 renewal PR #449 run 46174148899 was still in progress at snapshot. See manual §125.

**Exact-head characterization update (28 November 2026):** draft PR #449 at `50c2e083de1dab3e40301b37dc14b614a0d08f23` passed workflow `46174148899` (3,078 passed, 7 skipped, 86 subtests; baseline OK; disposable sandbox probe OK). Its controlled-clock test verifies that one unchanged unacknowledged source alert can produce five derived groove rows and two Row 9 stillness activations across five chat ticks, without a new detector emission. Source tracing further confirms the generic Metacognition prompt line is appended on the chat path, while pattern-specific Stage-SelfNarrative entries are topic-substring filtered. Combined prompt/narrative exposure remains untested; no live runtime observation or behaviour change. PR #449 remains a test-only characterization candidate; G-83 remains OPEN pending source-identity/episode semantics and controlling-authority review. See INDEX §126.\n\n**Prompt-boundary source trace (28 November 2026):** `gui/server.py` appends generic Metacognition and topic-filtered Stage-SelfNarrative text to `belief_text` before the thin-belief gate. The gate counts only `- [Tier` markers; those reflective strings do not increase the count. For non-probe, non-social requests outside `_ALLOW_THIN_REGISTERS`, an insufficient count returns a persisted gap refusal before voice prompt assembly and before `state.voice.speak()`. On surviving paths, `belief_text` is included under “Your interior right now” in `voice_prompt`. Thus formatter output is not proof of LLM exposure. Route-level characterization remains pending; no policy change. See INDEX §127.\n\n**Voice transport boundary:** on a route that reaches `VoiceClient.speak()`, `voice/llm.py` places `VoiceRequest.prompt` unchanged in the transport payload's user message. This closes the static source path but does not prove provider acceptance or semantic use. See INDEX §127.

### G-84 — Shutdown does not quiesce all producers before Writer close (OPEN; legacy G-34)

`AppState.close()` calls scheduler shutdown and closes Writers but does not call `stop_dynamic()` or coordinate all other workers. `run.py` starts SpeechQueueConsumer, SignalLoop, DiversityLoop and EdgeGeneratorLoop; AppState ignores the first three during close and does not retain the EdgeGeneratorLoop. The decoder is signaled but not joined. Scheduler stop signals are not joined because adapter thread handles are not retained. Writer close enqueues a sentinel and joins; submit has no closed-state guard on the pre-PR-280 snapshot. The keepalive supervisor has a 15-second SIGKILL deadline. This is a conditional data-loss/hang risk, not an observed incident. A central lifecycle coordinator and global deadline are required.

**Step 1 proposed (PR #348, 28 November 2026):** `AppState.close()` stops and joins the dynamic layer through `stop_dynamic()` between the scheduler shutdown and the Writer close, bounded by 5 s inside the keepalive's 15 s SIGTERM window. The other worker families listed above remain unjoined; the coordinated global deadline is still open.

### G-85 — SignalToProblem direct Writer bypass and split commit (OPEN; legacy G-44, under G-61)

The boot-registered SignalToProblem worker's primary `signal_to_problem_tick()` still uses direct connections to beliefs and conversations, dynamically adds `actioned_at`, and commits the beliefs database before the conversations database. This bypasses the one-pen contract and has a cross-database failure window. The separate hourly prose-statistics rebuild was migrated to the shared beliefs Writer/Reader by PR #279; that does not alter the primary tick. Define recovery/idempotency before migrating the primary transaction; do not claim cross-database atomicity.

**Fix proposed (PR #347, 28 November 2026):** conversations-Writer transaction for the cap/debounce/dupe/insert decisions, then `actioned_at` marks through the beliefs Writer after that commit; re-deciding a signal is idempotent on the `Auto-opened from signal #<id> (type: ...)` stamp. A scratch check of main showed the old order loses the problem when the conversations commit fails, and a signal whose problem exists can open a second one. No cross-database atomicity is claimed; gates, thresholds and cap are unchanged.

### G-86 — SignalReaper preservation allowlist drift (OPEN; legacy G-43)

SignalReaper preserves obsolete signal types while omitting current `4_branch` and `advancements_drift` types from its allowlist. Because reaping only targets rows older than seven days and promotion looks back six hours, this does not establish loss of a currently eligible promotion. It does create a retention-contract mismatch and can retain obsolete unconsumed types indefinitely.

### G-87 — Moltbook dry-run is not offline (OPEN; legacy G-35 updated)

Current main sets `MOLTBOOK_DRY_RUN=1`, which suppresses non-GET requests only. GET ingestion remains live; local records can still be marked `posted`/`sent` after synthetic success, and eligible inbound DMs are processed with `needs_human=0`. Related-belief retrieval does not filter tier/paused/locked/retired state. No external calls or host credentials were inspected. Review external consent, human approval, belief eligibility and simulated-state labels before live mode.


### G-88 — Keepalive checkout path portability (CLOSED by PR #277)

PR #277 derives `SCRIPT_DIR` from the script location, updates Git/journal paths and adds a portability regression test. Exact-head run `46042032164`: 2,636 passed, 7 skipped, 45 subtests; baseline OK. The merged main tree matches the tested head. Current main's `MOLTBOOK_DRY_RUN=1` was preserved. Host systemd unit identity remains unknown.

### G-89 — RDO generated-cycle source-evidence contamination (CLOSED by PR #276)

PR #276 excludes ignored `rdo/.cycles` from both RDO source-search paths and adds regression tests. Exact-head run `46040900959`: 2,634 passed, 7 skipped, 45 subtests; baseline OK. Post-merge main run `46041833321` also passed 2,634. RDO-generated plans can no longer become their own source anchors through these grep paths.

### G-90 — Social silence is not yet represented as a contextual social act (capability gap)

**Sources:** `theory_x/SOCIAL_PRESENCE_PROTOCOL.md`; `theory_x/stage_social/social_presence.py`; `theory_x/conversation_memory.py`; `theory_x/stage9_metacognition/metacognition.py`; `theory_x/stage6_fountain/generator.py`.

The Social Presence Protocol and isolated module define response-count and average-response-latency metrics, but the module is disabled in current boot (see G-91). ConversationMemory retains a bounded turn history. The two implemented “stillness” mechanisms are different: Fountain detects repeated retrieval overlap and eventually force-fires after a stillness streak; Metacognition writes a time-limited `stillness_log` entry after a groove-event threshold. These are internal generation/pacing signals, not a model of social silence. Fountain also contains natural-language self-reflection about silence, but the reviewed paths do not turn that into a structured social-silence state or classifier.

No reviewed current-main path distinguishes deliberate social silence from technical failure, or interprets silence in relation to duration, relationship, conversational dynamics, emotional circumstances and likely human interpretation. The system has adjacent context signals, but response latency alone is not an interpretation of silence.

This is a capability gap against the founder's stated social-silence design principle, not a claim that a frozen S-01–S-25 requirement is violated. Do not equate retrieval stillness or groove suppression with social silence. A future design should distinguish listening, companionship, respect, familiarity, reflection, restraint, rejection, avoidance and abandonment, while also detecting technical failure and expected-response context.

### G-91 — SocialPresence protocol claims autonomous boot, but current boot disables it (OPEN)

**Sources:** `run.py`; `theory_x/SOCIAL_PRESENCE_PROTOCOL.md`; `theory_x/stage_social/social_presence.py`; `gui/server.py`; `theory_x/stage9_metacognition/metacognition.py`; `tests/test_social_presence.py`.

The protocol says SocialPresence is registered in `run.py`, starts a daemon loop and snapshots every 300 seconds. Current `run.py` explicitly records its removal, sets `_social_presence = None`, and assigns `metacognition._sp = None`. The GUI's `current_summary()` injection and Metacognition's `_sp` consumers are conditional, so they are inactive under this boot path.

The removal comment says the module had no GUI/chat consumers, but current main now contains guarded consumer call sites in `gui/server.py` and Metacognition. The comment's consumer rationale is therefore stale even though the module remains disabled. The isolated SocialPresence unit tests do not establish boot integration or live operation.

**Disposition:** treat SocialPresence metrics and its autonomous loop as disabled on current main. Decide whether to restore it with meaningful consumers, or explicitly mark the protocol deferred/archived. Do not re-enable it merely to make the protocol text true; if restored, add boot-wiring, consumer and shutdown tests.

### RDO capability boundary (not a defect ID)

Current objective intake requires externally supplied seed obligations and reconciliation signatures. The deterministic extrapolator expands a bounded rule catalogue (default depth 4); it does not independently compile arbitrary raw intent into those initial seeds. RDO remains an external advisory tool, not NEX runtime. The founder-supplied v1.4 text was provided in a prior conversation, but its raw bytes are not available in the current repository/Library for direct comparison; v1.3 §16 remains the verified staged sequence, while v1.4 precedence is unresolved. See the system research report.


### Post-snapshot persistence update — PR #279 (27 November 2026)

PR #279 merged as `8d2121d121931d37afcb1c3d23d27e7ccc9145d1` after exact-head CI run `46044361663` passed 2,638 tests, 7 skipped, 45 subtests, baseline OK. The scheduled SignalToProblem loop now invokes `prose_stats.build()` with the shared beliefs Writer/Reader; the builder performs its upserts in one Writer transaction. The new tests compare its output with the direct builder and verify that the scheduled loop does not call `build_direct()`.

This resolves only the auxiliary prose-statistics direct-write path. The primary `signal_to_problem_tick()` direct writes to beliefs and conversations, runtime `actioned_at` schema alteration, and split commit boundary remain open under G-85/G-61. No cross-database atomicity is claimed. Post-merge main run `46045384807` also passed 2,638 tests, 7 skipped, 45 subtests, baseline OK. The mind-map check reported 30 nodes, 0 unverified, 14 dark, 2 blocked, two missing doctrine references and the overdue P13 marker.


### G-91 — Objective intake context is preserved but not enforced by planning (OPEN / RDO capability gap)

The v1 intake validates and stores `intent`, `owner`, `scope`, `constraints`, `exclusions`, and `acceptance_criteria` in its append-only revision ledger. However, `submit_objective()` passes only `original_text`, top-level `assumptions`, supplied seed obligations, relationships, reconciliation signatures and max depth into `run_cycle()`. The cycle's `objective_input` metadata contains identity/revision/digest/repository SHA, not the contextual fields. The planner does not translate constraints/exclusions into obligations or check proposed work packages against them; acceptance criteria are not used as a completion-verification contract. Existing tests validate input/revision integrity but do not prove contextual constraint enforcement.

This is an advisory capability/contract gap, not an execution incident: RDO does not apply work. The full input remains auditable, but the plan may not be constrained by all fields the caller supplied. Next design a typed translation into traceable obligations/anti-requirements and a separate acceptance-verification record. Until then, describe these fields as preserved context, not enforced constraints. Use v1.4 as the current working specification and preserve v1.3 as historical; change schema v1 only through a specific, traceable design increment.


### G-84 post-snapshot partial resolution — PR #280 (27 November 2026)

PR #280 merged as `f03a3d2e7b9c71801e44be73cf728c01cb791c9d`; exact-head run `46045754339` passed 2,640 tests, 7 skipped, 45 subtests, baseline OK. Writer now serializes submit/start/close admission, queues one shutdown sentinel after accepted requests, rejects late submissions synchronously, retains the worker reference and raises on timeout, and permits explicit restart after clean shutdown.

This closes the Writer-level late-submit/forgotten-worker race. G-84 remains OPEN for the application-level shutdown sequence: AppState still does not stop/join all producer loops, the EdgeGeneratorLoop is not retained in AppState, scheduler adapter threads are not joined, and the global shutdown deadline is not coordinated with the supervisor's 15-second SIGKILL window. Post-merge main CI is in progress.


### RDO v1.4 implementation audit reference

The current OFT module is partial. The Interface Tension Profile, explicit q/tau performance margins, headroom/operating envelopes, Pareto/net-value assessment, hysteresis/marginal-value stopping and several v1.4 adversarial cases remain open. See `rdo/RDO_V1_4_IMPLEMENTATION_GAP_AUDIT_2026-11-27.md`.


### Post-census persistence implementation update — 28 November 2026

PR #347 merged as `8d6bc95d387687ed470713467d8779d09479e11d` after exact-head run `46089697232` passed 2,841 tests, 7 skipped and 45 subtests. The primary `signal_to_problem_tick()` path now uses the AppState conversations Writer for the problem transaction, a read-only beliefs Reader for lookup, and the beliefs Writer to mark signals only after the problem commit. Signal-derived problem descriptions provide an idempotency key, so a retry after the first commit does not create duplicates. No cross-database atomicity is claimed. G-85's identified primary direct-writer defect is closed; G-61 remains open for the scope question about non-substrate databases and the limits of the static census.

PR #348 merged as `321a156e162a6554e27ae329522f253e8f6fe676` after exact-head run `46091039346` passed 2,838 tests, 7 skipped and 45 subtests, baseline OK with no STALE mind-map warnings. `AppState.close()` now stops Stage-2 dynamic loops before closing Writers, with a five-second bounded wait. This is only G-84 step 1: Fountain, SelfPrediction/WorldPrediction, speech/other consumers, decoder and scheduler adapter threads are not all joined under a global deadline. G-84 remains OPEN.

The one-pen census of 112 sites is a pre-merge snapshot at `a6d08405`; rerun `python tools/one_pen_census.py` on current main before treating its count or classifications as current. The scan remains heuristic and does not prove reachability.
**Route-level test candidate (28 November 2026):** draft PR #450 exact head `b33022cfaf47cc34dc8eec316cd583c15e6d880e`, workflow `46175227754` pending. It exercises the real `/api/chat` route: Technical is forced through the insufficient-belief early return before voice transport; Philosophical is checked for generic Metacognition and topic-matched Stage-SelfNarrative strings in the exact VoiceClient transport user message. Test-only; no provider acceptance or semantic model use claimed. See INDEX §127.
