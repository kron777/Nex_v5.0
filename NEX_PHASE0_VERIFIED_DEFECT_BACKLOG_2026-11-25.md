# NEX Phase 0 — Verified Defect and Evidence-Gap Backlog

**Snapshot:** active host branch claude/nex-continuity-wire at de93134f34adac07a3a41c2a05b33720510a2bfc (25 November 2026).
**Purpose:** founder-reviewable list of verified discrepancies, source-level defects, and evidence gaps. Items are deliberately separated by type; an unknown is not relabelled as a defect.
**Gate status:** this backlog is evidence input for Gate 0, not approval to change behaviour.

## A. Confirmed documentation / source-of-truth discrepancies

### D-01 — Phase 0 handoff is stale about Phase 1
- Type: documentation defect.
- Evidence: PHASE0_HANDOFF.md was written against fb87e24 and says no Phase-1 behavioural modification had started. Active branch commit f9ac58d adds the default-OFF self-state continuity consumer.
- Impact: a reader could incorrectly assume the active branch contains no Phase 1 source changes.
- Disposition: corrected in the Phase 0 reconciliation PR; continuity remains unarmed and unvalidated.

### D-02 — Sense scheduler startup and adapter-count documentation was stale
- Type: documentation defect; operationally significant.
- Evidence: SenseScheduler.__init__ calls start_all() (theory_x/stage1_sense/scheduler.py:149), so external feeds auto-start during construction. The old module docs said external feeds start paused. The actual adapter list has 28 entries, while scheduler.py, gui/server.py and run.py still reported 23. run.py's opening docstring said five DBs, while substrate/paths.py defines six.
- Impact: operators and developers could misunderstand whether external feeds run at boot, how many adapters exist, and how many databases are initialized.
- Disposition: documentation/comments/log label corrected in the Phase 0 reconciliation PR; no scheduler logic changed.

### D-03 — Continuity wiring note misclassified SelfMindView as a leaf
- Type: documentation defect.
- Evidence: run.py:473 constructs SelfMindView; run.py:720 passes it into AppState; gui/server.py:1512 calls current_summary().
- Impact: the documented consumer graph understated the real GUI chat-context path.
- Disposition: correction added to CONTINUITY_WIRE.md and the Phase 0 reconciliation.

### D-04 — Main-branch mind-map node count metadata is inconsistent
- Type: source-document metadata discrepancy.
- Evidence: main's mind_map/MIND_MAP.yaml contains 34 node entries and five arm entries, while its bootstrap comment and the older roadmap/handover refer to 30 nodes.
- Impact: crosswalk counts and audit completeness can be misreported if the old 30-node count is assumed.
- Disposition: reconcile the four additional entries and intended counting convention with the map owner; do not delete or merge entries to force 30.

## B. Confirmed source-level operational defect

### D-05 — Keepalive script retained a host-specific checkout path
- Type: source-level deployment/path defect.
- Evidence: nex_keepalive.sh used /home/rr/Desktop/Desktop/nex5 in its initial cd and again in the keepalive git-revision/journal paths. The verified active checkout is /mnt/games/storage/Desktop/Desktop/nex5.
- Impact: the corrected systemd unit could invoke the script from the right checkout, but the script would cd to the old missing path and exit before launching run.py; the journal would also target the old path.
- Disposition: draft PR #97 replaces all checkout-root references with SCRIPT_DIR derived from BASH_SOURCE[0]. Exact-head CI passed: 1612 passed, 5 skipped, 30 subtests. Not merged or deployed.
- Boundary: do not start/restart services until the source correction is merged/deployed through the approved process and a separate activation decision is made.

## C. Confirmed branch/integration discrepancies

### D-06 — Active host branch diverges substantially from main
- Type: integration risk, not itself a code defect.
- Evidence: active branch de93134 is 4 commits ahead and 205 commits behind main; merge base fb87e24. mind_map/MIND_MAP.yaml and Vitals are present on main but absent from the active branch.
- Impact: wholesale merge/rebase risks importing many unrelated changes, including behavioural work. The active host checkout and main must not be treated as interchangeable.
- Disposition: maintain branch-specific evidence; reconcile file-by-file under the governing authority hierarchy.

### D-07 — Vitals is absent from the active branch but present on main
- Type: branch-content discrepancy and unresolved instrument-provenance issue.
- Evidence: tools/nex_vitals.py, its service/timer, cron note and tests exist on main. They entered via merge 7f873d1, which also changed persona/focus/frame behaviour.
- Impact: cherry-picking the merge to restore Vitals would also import unrelated behaviour. Vitals scheduled --log mode appends persistent measurement history; its live environment reader trusts ~/.nex/nex.pid and reads /proc/<pid>/environ without verifying that the PID belongs to NEX.
- Disposition: do not cherry-pick, restore, enable, start, disable or delete the timer. Recover the exact governing Vitals spec and review process identity, minimisation and measurement provenance first.

## C2. Confirmed coherence-gate documentation and authority-scope discrepancies

### D-08 — CoherenceGate header understates HOLD/RESHAPE handling
- Type: documentation defect.
- Evidence: the module header says HOLD and RESHAPE are only logged and not acted on. Current CoherenceGate.check() calls HoldingZone.hold() for HOLD and put_reshape_pending() for RESHAPE.
- Impact: source documentation understates active persistence and downstream handling.
- Disposition: correct the module documentation only after the intended current scope is reconciled; no gate behaviour changed.

### D-09 — CoherenceGate fails open on evaluation exception
- Type: authority/failure-policy issue requiring founder review.
- Evidence: CoherenceGate.check() catches an _evaluate() exception and returns ACCEPT with reason gate_error_fallback.
- Impact: an internal gate error does not block the candidate. This is an availability-oriented fail-open policy, not a fail-closed gate.
- Disposition: document and assess against the governing Frozen V2.1 / safety authority. Do not change without explicit approval.

### D-10 — Sense distillation bypasses CoherenceGate
- Type: scope/architecture discrepancy, not automatically a defect.
- Evidence: stage2_dynamic._sense_distillation_loop explicitly writes precipitated_from_sense beliefs while stating it bypasses CoherenceGate because external perceptions are substrate content rather than internally generated thoughts. The gate module separately states “Universal: no generative path bypasses the gate.”
- Impact: the boundary between perception-derived belief writes and internally generated thought writes is not formally reconciled in the current source documents.
- Disposition: define the gate's scope from the governing specification; do not label this an intentional exception or a violation without that authority.

## D. Phase 0 evidence and verification gaps

### G-01 — M0.5 trace contract does not yet match the roadmap
- Type: specification/instrumentation gap.
- Evidence: roadmap asks for NEX5_TRACE_OVERLAY=0, trace_id/parent_ids across input, candidate generation, salience/workspace, gate, SQLite writer delta and output, plus NEX_CAUSAL_TRACE_SAMPLE.json. Active branch uses NEX5_INFLUENCE_TRACE / NEX5_INFLUENCE_TRACE_CONTEXT / NEX5_INFLUENCE_TRACE_PATH and has two coarse seams plus a JSONL fixture.
- Impact: current fixture evidence does not establish full causal lineage or the requested contract.
- Disposition: recover Frozen V2.1 and reconcile the exact contract before extending hooks. Do not invent field requirements.

### G-02 — Live causal L4 evidence is absent
- Type: evidence gap.
- Evidence: no authorised live Fountain cycle, Chat turn, trace flag-on/off comparison or live zero-delta test was performed. The host process filter returned no candidates after filtering, which is not proof of no NEX process.
- Impact: live causal influence and runtime consumption remain UNKNOWN.
- Disposition: no live capture until the required authorisation and protected experiment conditions are established.

### G-03 — Full-system producer/consumer crosswalk is incomplete
- Type: evidence gap.
- Evidence: current v2 crosswalk covers Fountain and Chat output paths. A first-pass run.py boot inventory is now documented, but the full forward and backward audit across every theory_x faculty, substrate, speech and GUI consumer is not complete.
- Impact: no claim of complete architecture integration or complete faculty coverage is justified.
- Disposition: continue bounded source tracing, preserving L0–L4 distinctions and uncertainty.

### G-04 — MIND_MAP source and authority verification is incomplete on the active branch
- Type: branch-source and verification gap.
- Evidence: active branch lacks mind_map/MIND_MAP.yaml; main contains it. Main CI runs mind_map/mind_map.py --check --verify, but that script validates map structure, source references, freshness and declared absence claims; it does not inspect runtime callsites to prove represented faculties cannot gate/veto actions.
- Impact: the descriptive-only constraint is declared in map metadata but not mechanically verified against runtime authority paths by that check.
- Disposition: reconcile the active-branch map source and perform a separate source-level authority audit. Do not confuse the MIND_MAP with sentience_dag.json or RDO's buildability rules.

### G-05 — Host artifact and model-performance baseline is incomplete
- Type: evidence gap.
- Evidence: runtime artifact hashing was skipped. Exact Python/SQLite versions, Qwen2.5 3B digest, idle/load RAM/VRAM and median tokens/sec are not available in the collected evidence.
- Impact: DB/snapshot identity, model reproducibility and resource-performance baseline remain UNKNOWN.
- Disposition: obtain only under the approved read-only host evidence procedure; do not copy private logs/secrets into Git.

### G-06 — Continuity semantics and tests have unverified edge cases
- Type: candidate source defect / test gap.
- Evidence: continuity_for_prompt() selects emotion, raga and drive but the phrase decision uses emotion only; timestamp ordering has no secondary key; connection close is not in a finally block. Tests do not cover dimension disagreement, unchanged/empty emotion sequences, timestamp ties or connection cleanup.
- Impact: the generated continuity clause may overstate steadiness or change, and exceptional reads may leave a connection open.
- Disposition: preserve as a candidate defect for Gate 0 review. Do not change or arm the Phase 1 feature before explicit approval.

## E. Protected / pending boundaries

- Gate 0 remains PENDING until the founder reviews the Reality Report, Crosswalk and this backlog.
- Commit f9ac58d's continuity consumer remains default-OFF; no live effect has been verified.
- R79–R83 remain protected. No experiment, baseline, tripwire or safety/authority change is included here.
- NEX runtime, live DBs, service units and service lifecycle were not changed by this backlog work.
- RDO and Watcher remain external development/evidence instruments, not NEX cognitive faculties.

## F. Top five discrepancies to resolve in Phase 0

1. Phase 0 documents versus current branch: stale handoff and continuity change.
2. Sense scheduler docs versus code: 28 adapters and external auto-start, not 23/paused.
3. CoherenceGate docs versus code: HOLD/RESHAPE are persisted/queued, and evaluation exceptions return ACCEPT.
4. Active branch versus main: 4 ahead / 205 behind; MIND_MAP and Vitals absent from active checkout.
5. M0.5 roadmap contract versus InfluenceRecord implementation: flag/schema/lineage/sample mismatch.

**No item in this backlog authorises a live change.**
### D-11 — Additional direct belief producers and gate-scope reconciliation required
- Type: scope/architecture evidence issue; not adjudicated as a defect.
- Evidence: the expanded active-branch source trace identifies direct belief inserts in `stage6_fountain/generator.py` (`self_rut_notice`) and seven Stage 2 life-loop modules: `life/pattern_loop.py`, `witness_loop.py`, `identity_loop.py`, `surprise_loop.py`, `remember_loop.py`, `wonder_loop.py`, and `fetch_loop.py`. The loops are appended to the `build_dynamic()` list and started by its daemon-thread factory in source. Their inspected insert functions use direct SQLite connections and contain no CoherenceGate call. This is in addition to sense distillation. A further environment-gated direct writer exists in `stage_tom/hot_observer.py`, called only when `NEX5_HOT_OBSERVER=1`; it inserts a Tier 3 `hot_observer` belief every third eligible fire.
- Distinction: the Membrane Behavioural Self-Model is gated under normal `run.py` wiring; EmergentDrive is conditionally gated for the belief insert but adds the Bonsai branch before the gate and marks the proposal applied even after a non-ACCEPT decision. Dynamic crystallization and Behavioural Self-Model both fall through to their belief insert if an exception escapes the gate call, while CounterfactualNode blocks its insert on such an exception. These are materially different control contracts.
- Impact: the current source does not establish one uniform gate boundary for all belief-producing and related state-changing paths. A simple “all beliefs pass through the gate” statement would be unsupported.
- Disposition: trace and classify every producer, its persistence mechanism, gate outcome handling, exception handling and pre/post-gate side effects. Recover Frozen V2.1 and founder approval evidence before deciding which paths are authorised exceptions or violations. No behaviour changed.

### G-07 — Full belief-producer census and gate control contract remain incomplete
- Type: evidence/specification gap.
- Evidence: the current bounded trace verifies at least nine normal/condition-triggered direct runtime producer paths (sense distillation, Fountain rut mirror, and seven life loops), plus one environment-gated direct path (HotObserver), five gated producer families (Dynamic crystallization, World Model synergizer, Fountain crystallization, CounterfactualNode and Behavioural Self-Model), plus EmergentDrive's conditional gate path. It separately identifies the self-location bootstrap anchor and resolver-mediated Holding Zone promotion. This is a verified subset, not an exhaustive repository-wide census; helper-mediated writes, alternate writers and remaining modules remain to be checked.
- Impact: M0.3–M0.4 cannot be marked complete, and gate authority/scope cannot be assessed from the current source alone.
- Disposition: continue bounded forward/backward source tracing. Preserve unknowns; do not change the gate, producers, flags, or live state pending the governing specification and explicit founder review.

### D-12 — TaggingBeliefWriter / IntakeResonance universal-chokepoint claim is contradicted by source paths
- Type: documentation/coverage discrepancy; no behaviour change proposed.
- Evidence: `run.py` wraps the shared `writers["beliefs"]` instance, and `writer_wrapper.py` intercepts eligible belief INSERTs routed through that wrapper. However, seven Stage 2 life loops use direct SQLite connections to insert beliefs; `init_db.init_all()` seeds keystone and koan/Tao/don't-know Tier 1 rows through raw Writers before the normal wrapper is constructed; the operator identity/self-belief utilities create independent Writer instances, and the spectrum loader/batch scripts use direct `sqlite3` connections. Those writes do not pass through the boot wrapper. The wrapper comment nevertheless calls its embedded IntakeResonance probe a universal chokepoint through which every belief from every writer passes.
- Impact: neither auto-tagging nor the wrapper's IntakeResonance probe can be assumed to cover every stored belief. Some producers call resonance separately; the full producer-to-tag/resonance coverage is not yet mapped.
- Disposition: document the actual wrapper boundary and complete a producer-by-producer coverage map. Do not refactor writers or force all paths through a shared mechanism without the governing specification and explicit founder approval.

### G-08 — Tagging and intake-resonance coverage census incomplete
- Type: evidence gap.
- Evidence: source confirms direct SQLite and independent Writer paths outside the shared TaggingBeliefWriter. The current audit has not exhaustively identified every belief insert, whether it supplies tags explicitly, relies on schema defaults, invokes tag generation separately, or invokes IntakeResonance separately.
- Impact: global claims about tagging or resonance coverage are not supported by the current trace.
- Disposition: extend the producer inventory with separate columns for persistence path, wrapper interception, tag source and resonance invocation. Preserve UNKNOWN where untraced.

### D-13 — DailyLife module description overstates outreach and sleep behaviour
- Type: source/documentation discrepancy; no behaviour change proposed.
- Evidence: `theory_x/life/daily_life.py` header describes two outreach activities as Moltbook DMs and says 23:00–06:00 sleep mode doubles the Fountain interval. The inspected outreach function only writes an internal message saying it would reach out and explicitly states actual sending is wired separately. `daily_tick()` returns a sleep boolean, but `daily_loop()` ignores it; no ModeState transition or Fountain interval adjustment occurs in this module. ModeState's inspected implementation persists explicit mode changes.
- Impact: the documented activity schedule and sleep effect should not be treated as implemented behaviour without locating another controlling path.
- Disposition: keep the current runtime untouched; reconcile module documentation with the intended design and search for any separate sleep scheduler before changing either code or docs.

### G-09 — Behavioural Self-Model may mix internal DailyLife messages with user-facing replies
- Type: measurement-validity question / evidence gap.
- Evidence: DailyLife writes generated internal entries into `conversations.messages` with `role='nex'` and `session_id='internal_daily_life'`. Its loop calls `daily_tick()` immediately on boot; that function catches up every scheduled activity whose hour has passed, potentially inserting several internal messages in one tick. BehaviouralSelfModel.observe() selects the latest 100 rows where `role='nex'` without filtering by session or register. Metacognition._detect_goal_drift() selects the latest five rows with the same role-only filter and compares their embeddings with the active goal.
- Impact: internal templated morning/reading/outreach/journal entries are eligible to influence response-style metrics, subsequent `behavioural_observation` beliefs, and the recent-response sample used for goal-drift detection. The size of either effect is UNKNOWN because no live boot times, daily_activities rows, message rows or metric contributions were inspected.
- Disposition: determine whether the intended observation population is all NEX-authored messages or only user-facing replies. Validate against isolated fixtures before any runtime change.

### D-14 — Dynamic crystallization can invoke IntakeResonance twice for one belief
- Type: candidate measurement defect; live incidence UNKNOWN.
- Evidence: `build_dynamic()` constructs an IntakeResonance instance and passes it to the Dynamic Crystallizer. `Crystallizer._write_belief()` calls that instance's `compute(content)` before INSERT. The INSERT omits `tags` and uses the shared beliefs writer wrapped by TaggingBeliefWriter; the wrapper's `write()` method therefore runs its own separate lazy IntakeResonance probe before injecting tags. Each successful `compute()` writes a new row to `intake_resonance_log`, whose schema has no content deduplication/uniqueness constraint.
- Condition: this duplicate path is active when the Dynamic crystallizer runs and `NEX5_INTAKE_RESONANCE_OFF` is not `1`. Effective host flag and live duplicate-row incidence were not inspected.
- Impact: one Dynamic crystallization may contribute two measurements for the same content, potentially biasing resonance distributions or later analyses that treat log rows as independent observations.
- Disposition: preserve as a candidate defect; verify with an isolated fixture and establish intended single-owner instrumentation before any runtime change. Do not remove either hook or alter the log without explicit approval.

### G-10 — IntakeResonance call coverage and cardinality not yet mapped
- Type: evidence gap.
- Evidence: Dynamic crystallization appears to have two independent compute calls; FountainCrystallizer has an explicit call while its tagged INSERT bypasses the wrapper probe; the World Model synergizer supplies tags and no explicit call was observed; seven life-loop inserts bypass the wrapper and have no explicit call in the inspected functions.
- Impact: current data cannot be assumed to contain one IntakeResonance row per belief, nor can every belief be assumed to have been measured.
- Disposition: finish the producer-by-producer resonance coverage/cardinality map and validate on isolated fixtures before changing instrumentation.

### D-15 — Optional Fountain best-of-cluster update returns before CoherenceGate
- Type: conditional gate-scope issue; not adjudicated as a defect.
- Evidence: in `FountainCrystallizer.crystallize()`, the `NEX5_BESTOFCLUSTER=1` branch runs when quality checking returns `semantic_repeat`. If the new thought's genius-v2 score exceeds the matched belief's score, `_maybe_bestofcluster_upgrade()` updates the existing `beliefs.content` and matching `fountain_crystallizations.content`, then returns the existing belief ID. This branch occurs before the normal CoherenceGate call later in `crystallize()`.
- Condition: the path is default-OFF in source; effective host flag is UNKNOWN. It is a content replacement of an existing belief, not a new row insert.
- Impact: if the gate obligation covers every newly generated candidate that changes durable belief content, this path bypasses it. If the gate only governs new belief-row insertion, the current path may be intentional.
- Disposition: resolve gate scope against Frozen V2.1 and founder approval evidence. Do not enable/disable the flag or change this update path before that review.

### D-16 — Fountain persists generated output before the normal CoherenceGate decision
- Type: gate-scope clarification; not adjudicated as a defect.
- Evidence: the normal Fountain path writes the generated thought to `sense_events` (`internal.fountain`) and `dynamic.db:fountain_events`, and records related telemetry, before calling `FountainCrystallizer.crystallize()`. The normal CoherenceGate call occurs inside the crystallizer after quality checks and before the new belief INSERT. A non-ACCEPT decision therefore blocks belief admission and subsequent speech enqueue, but does not retract the already-persisted Fountain event. Quiescent and voice-fallback paths return before crystallization entirely.
- Impact: the phrase “universal gate” is ambiguous unless it specifies whether the gate governs raw generated outputs, durable belief admission, or downstream delivery. The current Fountain path implements the latter two boundaries only for the normal path.
- Disposition: define the intended gate boundary from Frozen V2.1 and founder approval evidence. Do not move the gate or change event persistence before that review.

### D-17 — Chat response generation has no CoherenceGate call
- Type: gate-scope clarification; not adjudicated as a defect.
- Evidence: `gui/server.py` constructs and passes CoherenceGate to several faculties, but the user-facing chat route calls `state.voice.speak()`, performs optional bounded anti-repeat/provenance retries, sanitizes the final text and inserts it into `conversations.messages` without a `coherence_gate.check()` / ThoughtPacket / GateOutcome call.
- Impact: chat reply generation and conversation persistence are outside the current CoherenceGate decision path. Chat messages are not themselves `beliefs` rows, so whether they fall within the intended gate obligation is a specification question.
- Disposition: define whether the gate applies to autonomous belief candidates only, all autonomous outputs, or user-facing chat replies too. Do not add a chat gate or change reply persistence before the governing specification and founder review.

### D-20 — Residue module status documentation contradicts the current reaper target
- Type: documentation discrepancy plus test-coverage gap.
- Evidence: `theory_x/diversity/residue.py` still states residue is absent from `nex_db_reaper.TARGETS` and proposes adding an external retention pass. The current `nex_db_reaper.py` includes `beliefs.db:residue` with a 2-day `created_at` retention override. The nightly timer is configured for 04:00. The local residue `_reap()` deletes consumed rows after 7 days, while the external reaper deletes all rows older than 2 days if it runs.
- Impact: the module docstring's “unbounded” diagnosis and pending recommendation are stale. Actual cleanup depends on the external service/timer executing; the last host evidence showed the reaper service failed with `MainPID=0`, and current execution history is UNKNOWN. Historical row counts in the module docstring are not current host evidence.
- Disposition: correct the docstring and add isolated temp-DB tests for the 2-day target. Do not run the reaper, delete live rows, change retention or activate services without approval.

### G-12 — Residue retention operational evidence and test coverage incomplete
- Type: evidence gap.
- Evidence: `tests/test_retention_reaper.py` tests the 30-day and 90-day targets but does not test residue's 2-day target. Host service status was failed at the last evidence collection; no successful reaper run/log or live residue row count was verified.
- Impact: source configuration proves the intended retention policy, not that the host has executed it or that the 2-day cleanup is functioning operationally.
- Disposition: add isolated tests; obtain service/timer and reaper-log evidence through the approved read-only host audit when available. Do not manually run retention against live DBs.

### D-21 — Fountain HotObserver slot lacks the Tier 8 retirement filter
- Type: conditional retrieval defect candidate; live incidence UNKNOWN.
- Evidence: the main Fountain own-content query filters `tier < 8`, and residue lookup does too. The dedicated HotObserver query filters only `source='hot_observer'` and a 72-hour creation cutoff; it does not exclude Tier 8 or paused rows. HotObserver writes Tier 3 unlocked beliefs. Harmonizer scans Tier 3–7 unlocked/unpaused beliefs without excluding `hot_observer`, and can retire selected originals by setting tier 8 and prefixing `[RETIRED]`.
- Impact: a HotObserver belief retired by Harmonizer can still be randomly selected and injected into Fountain context during the remaining 72-hour lookback. The writer flag `NEX5_HOT_OBSERVER` is not checked by the retrieval query, so old rows can remain eligible after new writes are disabled.
- Disposition: preserve as a source-verified filter gap and verify with an isolated fixture. Do not alter the query or runtime flags before Gate 0 / explicit approval.

### D-22 — Optional substrate emission can select activated Tier 8 beliefs
- Type: conditional retrieval defect candidate; live incidence UNKNOWN.
- Evidence: `get_top_activated()` joins `belief_activation` to `beliefs` but does not filter Tier 8, paused or locked rows. Fountain calls it when `NEX5_SUBSTRATE_EMIT=1` (default OFF) and formats the selected beliefs into a substrate-emitted thought. Harmonizer can retire unlocked Tier 3–7 beliefs to Tier 8, while activation rows are not removed by the retirement update.
- Impact: when substrate emission is armed, recently retired beliefs with sufficient remaining activation can be surfaced in the generated thought. The later normal crystallizer/gate path may still block a new belief insert, but it does not prevent this retired content from entering the generated output/event.
- Disposition: preserve as a conditional source finding. Verify with an isolated fixture and resolve the intended retired-belief policy before changing the helper or flag.

### D-23 — NovelAssociation can ingest Tier 8 retired beliefs into the graph
- Type: source-level retrieval/graph contamination candidate; live incidence UNKNOWN.
- Evidence: `NovelAssociation._pull_candidates()` filters by confidence, branch presence and `paused=0`, but not `tier < 8` or `locked=0`. Harmonizer can retire unlocked Tier 3–7 beliefs by setting tier 8, locked 0, paused 0. NovelAssociation's normal 30-minute loop can therefore embed retired rows, write `synthesises` edges and log cross-branch associations; high-similarity pairs can also create a SelfNarrative entry. A Fountain comment claims NovelAssociation already bounds tiers, but current SQL does not.
- Impact: retired belief content can continue influencing graph topology and branch-level prompt annotations. Optional edge-weighted Fountain retrieval may also count edges connected to retired endpoints.
- Disposition: verify with an isolated fixture and reconcile the retired-row policy across all graph/retrieval paths. Do not alter the candidate query or graph state before Gate 0 / explicit approval.

### D-24 — Diversity EdgeBuilder can create graph edges involving Tier 8 retired beliefs
- Type: source-level graph-ingestion candidate; live incidence UNKNOWN.
- Evidence: `edge_builder_tick()` source-candidate query filters `paused=0`, `locked=0` and content length but not tier; its comparison pool filters only `paused=0` and content length. Harmonizer-retired rows are Tier 8, unlocked and unpaused, so they remain eligible as both candidates and targets. Locked Tier 1 rows are excluded as candidates but can appear as targets. The Stage 2 dynamic factory starts `edge_builder_loop` in normal boot wiring.
- Impact: the graph can accumulate `cross_domain` edges involving retired belief IDs. These edges may affect downstream graph-degree consumers even though normal Fountain own-content retrieval excludes Tier 8.
- Disposition: verify with an isolated fixture and define a consistent active-belief policy for graph producers. Do not rewrite or delete live graph edges before Gate 0 / explicit approval.

### G-14 — Intended graph semantics for retired nodes are unspecified
- Type: architecture/specification gap.
- Evidence: Stage 3 retrieval filters its direct candidate rows to tier<=6 and final results only emit IDs in that candidate map. But `ActivationEngine.activate()` traverses `belief_edges` without checking source/target belief tier, paused or locked state, and can propagate through Tier 8 nodes before final result assembly. It stamps all traversed edges. Harmonizer leaves graph edges in place when retiring beliefs; NovelAssociation and EdgeBuilder can also create edges involving retired rows under their current filters.
- Impact: retired beliefs are hidden from direct retrieval results but can remain active as intermediate graph bridges that influence scores of active beliefs. It is unknown whether retirement is intended to remove a node from propagation or preserve its historical graph role.
- Disposition: define active/retired graph semantics before changing edge generation, traversal, retirement or cleanup. Preserve current graph state pending founder/spec review.

### G-15 — IntakeResonance log retention policy is not explicit
- Type: data-lifecycle specification gap.
- Evidence: `intake_resonance_log` is read by `scripts/intake_resonance_cli.py` for lifetime distribution/recent/top/bottom reports, but it is not in `nex_db_reaper.TARGETS` and no retention/compaction policy was found in the inspected source. Its table has no content uniqueness constraint.
- Impact: the log is append-only in the inspected code and may grow with every resonance computation. Duplicate Dynamic crystallization measurements would be counted as independent events by the CLI's aggregate statistics.
- Disposition: determine whether the intended dataset is lifetime-retained or time-bounded; document the choice and add isolated retention/aggregation tests only after the data-governance decision. Do not delete or prune live measurements.

### G-16 — Fountain retrieval-log retention is undefined after FK migration
- Type: data-lifecycle / documentation gap.
- Evidence: `fountain_retrieval_log` records per-fire retrieved belief IDs and is read by associative recall for the last three fires. Its startup migration drops it only if a legacy cross-database FK to `beliefs` exists, then recreates it without that FK. A nearby comment still says the table is destroyed on every restart. The table is not in `nex_db_reaper.TARGETS` and no ongoing pruning was found. By contrast, `fountain_prompt_blocks` is pruned at startup to 30 days.
- Impact: the comment no longer accurately describes persistence after the FK migration; the retrieval log may grow indefinitely even though the observed runtime consumer needs only a short recent window.
- Disposition: establish the intended continuity and retention policy, check for other consumers, then add isolated migration/retention tests. Do not drop or prune live history before that decision.

### D-26 — DormancyScanner does not advance beyond the oldest 50 source rows
- Type: source-level progress defect candidate; live incidence UNKNOWN.
- Evidence: `DormancyScanner.scan_incremental()` selects source families `fountain_insight`, `synergized`, `behavioural_observation` ordered by `created_at ASC LIMIT 50`, with no cursor, no exclusion for existing dormant rows, no `reanimated_at` check and no tier/status filter. It upserts those same rows on every call. DiversityLoop invokes it every 60 seconds, and ClockRunner independently invokes a fresh scanner every 20 Fountain fires.
- Impact: the same oldest 50 rows can be rescanned indefinitely, preventing discovery of newer dormant beliefs and refreshing their `flagged_at` repeatedly. Duplicate scan callsites add redundant work.
- Disposition: reproduce in an isolated fixture with more than 50 eligible rows and define the intended incremental/cursor semantics before any code change.

### D-27 — Dormancy reanimation does not revalidate belief status before Fountain injection
- Type: source-level retired/paused content retrieval candidate; live incidence UNKNOWN.
- Evidence: DormancyScanner source selection has no tier/paused/locked filter; `wake_one()` selects an un-reanimated dormant row without checking joined belief status; Fountain's `pop_reanimated()` consumer re-reads by ID without a tier/paused/locked predicate. Harmonizer can retire unlocked source-family beliefs to Tier 8 while leaving them unpaused.
- Impact: retired or paused beliefs can be surfaced into Fountain context through the periodic reanimation slot even though the main own-content and residue retrieval paths explicitly exclude Tier 8.
- Disposition: validate with isolated fixtures and reconcile whether reanimation should apply only to active beliefs. Do not mutate dormant rows or live prompts before Gate 0 / explicit approval.

### D-28 — VoiceEngine TimeFetch can return retired, paused or locked belief content
- Type: source-level user-facing retrieval defect candidate; live incidence UNKNOWN.
- Evidence: the normal Chat path calls VoiceEngine when `voice_mode='use_substrate'` (AppState source default). `TimeFetch.fetch_from_beliefs()` filters confidence and content length but not tier/paused/locked; `fetch_from_novel_associations()` joins belief pairs without status filters or a detected-at lookback and returns old association-log rows. Those non-belief candidates receive default tier/confidence/recency/genius scores and can still exceed the 0.6 threshold. VoiceEngine assigns Tier 8 a lower score, not an exclusion, and returns a qualifying hit verbatim for the non-composition path. The route does not call CoherenceGate.
- Impact: retired/paused/locked belief content can be selected as a direct user-facing reply if it scores above 0.6. Harmonizer prefixes retired content with `[RETIRED]`, and VoiceEngine returns the stored content verbatim, so the marker itself may reach the user. Novel-association pairs can also contain retired content. The main World Model retriever's tier<=6/paused filters do not protect this separate route.
- Disposition: verify with isolated TimeFetch/VoiceEngine fixtures and define whether substrate-as-voice may serve retired/paused/locked content. Do not change the query, mode or reply path before Gate 0 / explicit approval.

### D-29 — VoiceEngine substrate-miss comment contradicts the Chat control flow
- Type: source/comment discrepancy.
- Evidence: `gui/server.py` comment says `use_substrate` suppresses LLM fallback and a miss returns a substrate deflection. On a miss, however, `text` remains None and the route calls `state.voice.speak()`; `VoiceClient.speak()` invokes the configured LLM request function.
- Impact: source comments misdescribe the actual fallback behaviour and may cause incorrect assumptions about whether the LLM is called on substrate misses.
- Disposition: correct the comment after confirming intended Phase 30 behaviour. Do not change routing or fallback semantics without explicit approval.

### D-30 — Fountain Favorites and Surprise blocks can render Tier 8 beliefs
- Type: source-level prompt retrieval defect candidate; live incidence UNKNOWN.
- Evidence: the Favorites block selects `affinity > 0.40` and renders two random rows without tier/paused/locked filters; Harmonizer retirement does not clear affinity. The recent Surprise block selects the latest `source='surprise'` belief within six hours without tier/status filters; the Surprise loop creates unlocked Tier 6 rows that Harmonizer can retire.
- Impact: retired content can re-enter the Fountain prompt through these direct blocks even though the main own-content retrieval query filters `tier < 8`.
- Disposition: validate with isolated fixtures and reconcile a single retired-belief retrieval policy across all prompt blocks. Do not change prompt queries or affinity state before Gate 0 / explicit approval.

### G-18 — Fountain own-belief retrieval/rendering relationship needs an explicit design statement
- Type: architecture/configuration evidence gap.
- Evidence: the main own-source belief pool is retrieved and affects retrieval telemetry/activation/erosion, but its dedicated prompt block is gated by `NEX5_OWN_CONTENT_RENDER=1` (source default OFF). Associative recall and wide-focus are separate default-OFF flags. The always-present `own_sense` block is drawn from sense events, not the own-belief pool.
- Impact: the comment that own lived content dominates retrieval allocation does not establish that own-belief text dominates the actual prompt. At source defaults, the main own-belief pool can be statefully used without being rendered.
- Disposition: determine whether this separation is intentional and record the expected prompt composition. Do not arm own-content, associative-recall or wide-mode flags without explicit approval.

### D-31 — World Model EdgeGenerator can create edges from retired source rows
- Type: source-level graph-status candidate; live incidence UNKNOWN.
- Evidence: `EdgeGeneratorLoop._tick()` selects unedged `fountain_insight`/`synergized` source rows without tier/paused/locked filters and re-reads each source by ID without a status predicate. Only the target-candidate query filters `tier <= 7`; it does not exclude paused or locked targets. The loop runs after a 60-second boot delay and every 30 minutes.
- Impact: an unedged Tier 8 retired source can still create outgoing edges to tier<=7 targets; paused/locked target rows can also be linked. These edges can affect later graph propagation even though the direct retriever filters retired candidates.
- Disposition: reproduce with isolated fixtures and define graph active/retired/paused semantics consistently across all three edge producers and ActivationEngine. Do not mutate live edges or code before Gate 0 / explicit approval.
