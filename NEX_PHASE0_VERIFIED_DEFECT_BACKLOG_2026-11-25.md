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
- Evidence: main's mind_map/MIND_MAP.yaml contains 34 entries under `nodes:` plus five arm entries. Thirty of those node entries are substantive mind-aspect nodes; four (`scope_void`, `prices_void`, `two_of_thirteen`, `dark_family`) are structural/placeholder entries. The bootstrap comment and older roadmap/handover refer to 30 nodes.
- Impact: crosswalk counts and audit completeness can be misreported if the 30 substantive nodes, 34 YAML node entries and 39 total IDs (including arms) are conflated.
- Disposition: preserve the entries and reconcile the counting convention with the map owner; do not delete or merge nodes to force 30.

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
- Evidence: captured host branch de93134 is 4 commits ahead and 641 behind current main; merge base fb87e24. The remote continuity branch is separately 310 ahead / 641 behind. The main-only MIND_MAP was first added 2026-11-09 and last updated 2026-11-20. Its 51 source references across 41 unique files include 12 files absent from the active-host base. Vitals and other main-only files are also absent. PR #98 merged into the remote continuity branch, not main or the host checkout.
- Impact: wholesale merge/rebase risks importing many unrelated changes, including behavioural work; importing MIND_MAP alone would leave missing source references and fail its own source-existence check. The active host checkout and main must not be treated as interchangeable.
- Disposition: maintain branch-specific evidence; reconcile file-by-file under the governing authority hierarchy. Do not import the map or cherry-pick its supporting code until branch lineage and scope are explicitly decided.

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

### G-01 — Technical trace-overlay contract (previously labelled M0.5) does not yet match the roadmap
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
- Evidence: active branch lacks `mind_map/MIND_MAP.yaml`; main contains it. The map has 34 node entries plus five arms and is explicitly descriptive-only. Its 51 source references across 41 unique files include 12 files absent from the active-host base. Main CI runs `mind_map/mind_map.py --check --verify`, but that script validates map structure, source references, freshness and declared absence claims; it does not inspect runtime callsites to prove represented faculties cannot gate/veto actions. Two `meta.doctrine` references are missing even on main and generate warnings.
- Impact: the map cannot be copied into the active-host branch as a standalone file set; its own source-existence check would fail. Its descriptive-only constraint is declared in metadata but is not mechanically verified against runtime authority paths by that check.
- Disposition: reconcile branch lineage and source dependencies first, then perform a separate source-level authority audit. Do not confuse the MIND_MAP with `sentience_dag.json` or RDO's buildability rules.

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
4. Active host checkout versus current main: 4 ahead / 641 behind; remote continuity branch 310 ahead / 641 behind; MIND_MAP and Vitals absent from the active checkout.
5. Technical trace-overlay roadmap contract versus InfluenceRecord implementation: flag/schema/lineage/sample mismatch (previously tracked under M0.5).

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

### D-21 — Fountain HotObserver candidate query lacks the Tier 8 retirement filter
- Type: source-level candidate-selection/status-filter inconsistency; live incidence UNKNOWN.
- Evidence: the main Fountain own-content query filters `tier < 8`, and residue lookup does too. The dedicated HotObserver query filters only `source='hot_observer'` and a 72-hour creation cutoff; it does not exclude Tier 8 or paused rows. HotObserver writes Tier 3 unlocked beliefs. Harmonizer scans Tier 3–7 unlocked/unpaused beliefs without excluding `hot_observer`, and can retire selected originals by setting tier 8 and prefixing `[RETIRED]`.
- Impact: a retired HotObserver belief can still be randomly selected into Fountain's intermediate candidate list during the remaining 72-hour lookback. The selected row receives activation/use side effects, but source inspection shows it is not rendered into the normal Fountain prompt: hot_observer belongs to neither the own-content nor seed render allowlist. A separately gated substrate-emission/parallel-fire path may consume activated rows; that is distinct from normal prompt inclusion. The writer flag `NEX5_HOT_OBSERVER` is not checked by the candidate query, so old rows remain eligible after new writes are disabled. The tracked `nex_keepalive.sh` sets `NEX5_HOT_OBSERVER=1`, but the current host reconciliation records that the script's hard-coded `cd /home/rr/Desktop/Desktop/nex5` is stale against the repaired checkout `/mnt/games/storage/Desktop/Desktop/nex5` and exits before launching `run.py`. The active user unit is untracked; draft PR #97 contains the path repair but is not merged/deployed. Thus the flag is declared, not proven effective.
- Disposition: retain as a candidate-selection and activation filter gap, not a confirmed direct prompt-injection path. Do not alter the query or runtime flags before Gate 0 / explicit approval.

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

### D-27 — Dormancy reanimation does not revalidate belief status before Fountain candidate retrieval
- Type: source-level retired/paused candidate-selection inconsistency; live incidence UNKNOWN.
- Evidence: DormancyScanner source selection has no tier/paused/locked filter; `wake_one()` selects an un-reanimated dormant row without checking joined belief status; Fountain's `pop_reanimated()` consumer re-reads by ID without a tier/paused/locked predicate. Harmonizer can retire unlocked source-family beliefs to Tier 8 while leaving them unpaused. The reanimation sources are fountain_insight, synergized and behavioural_observation; they fall into Fountain's own-source allowlist but not the always-rendered precipitated_from_sense subset.
- Impact: retired or paused beliefs can be selected into Fountain's intermediate candidate list and receive activation/use side effects. They are not independently rendered by the normal prompt builder; with source-default `NEX5_OWN_CONTENT_RENDER=0`, these non-sense rows are not direct prompt text. If that optional render flag is enabled, the own_render block has no tier/paused/locked recheck and can render them. Activated candidates may also be visible to the separately gated substrate-emission path.
- Disposition: preserve as a candidate-selection/status gap with conditional prompt exposure. Reconcile whether reanimation should apply only to active beliefs. Do not mutate dormant rows or live prompts before Gate 0 / explicit approval.

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

### D-32 — Harmonizer synthesis resolution reactivates one retired belief at Tier 7
- Type: confirmed source-level control-flow defect; live incidence UNKNOWN.
- Evidence: the successful `Harmonizer.resolve()` synthesis branch first sets both originals to Tier 8, `locked=0`, `paused=0`, and prefixes `[RETIRED]`. It then calls `BeliefPromoter.decisive_contradiction(belief_id_b)`. That method computes `min(7, current + 2)`, so a just-retired Tier 8 row is changed back to Tier 7 while retaining the `[RETIRED]` prefix. Its own docstring also claims a Tier 7 belief is discarded, but the code leaves it at Tier 7. The current escalation test checks only row A and does not create a synthesis bridge.
- Impact: in the synthesis branch, one of the two beliefs is no longer Tier 8 and passes active-tier retrieval filters despite its retired marker. It can re-enter Fountain, VoiceEngine and graph paths that rely on tier<8 or do not filter tier.
- Disposition: add an isolated fixture with a third bridging belief and assert both originals remain Tier 8. Prepare the smallest correction only after Gate 0 / explicit approval; do not change live Harmonizer behaviour now.

### G-19 — Harmonizer scan coverage beyond 200 eligible rows is unspecified
- Type: bounded-scan fairness/evidence gap.
- Evidence: `Harmonizer.scan_for_conflicts()` selects Tier 3–7, unlocked/unpaused rows ordered only by tier ascending, with `LIMIT 200`; no cursor, rotation or time ordering is present. Rows without a detected conflict remain eligible on later two-hour scans.
- Impact: if more than 200 eligible rows exist, the same low-tier/early rows can dominate repeated scans and higher-tier/later rows may be starved. Whether the host population exceeds the cap is UNKNOWN.
- Disposition: measure eligible row counts and define scan fairness before changing the cap or ordering. Do not run scans against live state or modify Harmonizer behaviour without approval.

### G-20 — TaggingBeliefWriter batch-write coverage is not defined
- Type: wrapper coverage / test gap.
- Evidence: `TaggingBeliefWriter.write()` intercepts eligible belief INSERTs, but `write_many()` delegates unchanged to the inner Writer. Direct SQLite, independent Writers, pre-wrapper init_db seeding, positional/no-content SQL and caller-supplied tags also bypass the wrapper. No current normal-runtime belief INSERT through the wrapped `write_many()` path was established in the scanned callsites.
- Impact: the “universal chokepoint” comment overstates the actual interception boundary; a future or unscanned batch INSERT can bypass both tag generation and the wrapper's IntakeResonance probe.
- Disposition: correct the comment and decide whether batch INSERT interception is required. Add isolated tests only after the intended writer contract is defined; do not change the wrapper's runtime behaviour now.

### D-34 — CounterfactualNode can refine retired beliefs from the shared TimeFetch pool
- Type: source-level upstream retrieval policy candidate; live incidence UNKNOWN.
- Evidence: CounterfactualNode calls `TimeFetch.fetch_from_beliefs()` before refinement. TimeFetch filters confidence/length/keyword but not tier/paused/locked. CounterfactualNode then gates the refined ThoughtPacket and inserts only on ACCEPT via the wrapped Writer.
- Impact: a retired/paused/locked belief can become the source material for a new Tier 3 counterfactual belief if the refined candidate passes CoherenceGate. The gate checks the refined packet, not the source belief's status.
- Disposition: define whether retired content may be used as historical source material for counterfactual generation. If not, apply the status policy at TimeFetch or the caller boundary after Gate 0; do not change it now.

### G-21 — IntakeResonance measurement coverage is producer-dependent
- Type: instrumentation coverage/specification gap.
- Evidence: DynamicCrystallizer records twice (explicit compute plus wrapper probe); FountainCrystallizer records once (explicit compute, tags column skips wrapper); CounterfactualNode, HoldingZone promotion, SelfLocationCommitment and Fountain rut mirror record once through wrapper; WorldModel Synergizer is gated but supplies explicit tags and has no explicit resonance call, so records zero; HotObserver/life-loop direct SQL and raw boot seeds also record zero.
- Impact: the log does not represent a uniform one-measurement-per-belief-admission population. Producer comparisons and aggregate CLI distributions are weighted differently; DynamicCrystallizer is double-counted while Synergizer and direct writers are absent.
- Disposition: establish whether IntakeResonance is intended as universal, per-producer, or selective instrumentation. Then define a single measurement boundary and add isolated per-producer tests. Do not alter probes, tags or writer routing before the governing spec is available.

### G-22 — Governing specification version is unresolved
- Type: founder authority / specification conflict; blocks normative remediation.
- Evidence: repository `SPECIFICATION.md` is dated 2026-04-23, marked Phase 0 Locked, calls itself the Constitution of NEX 5.0, says it wins over later engineering until explicitly revised, and says revisions must be logged. Its path history shows one commit and no later amendment. It is not labelled Frozen V2.1. The handover separately identifies a Frozen V2.1 spec as higher authority, but that exact artifact and the founder approval record were not found in the searched archive/Library.
- Impact: the April constitution conflicts with current source on Tier 8 meaning (raw observations vs retired tombstones), Harmonizer resolution (new synthesis/deletion vs existing bridge/retained tombstones), one-pen writes (queue-only vs direct SQLite writers), and database inventory (five vs six). Without knowing whether V2.1 superseded this constitution, source findings cannot all be classified as normative defects.
- Disposition: founder must identify the canonical Frozen V2.1 document and approval record, or explicitly confirm the April `SPECIFICATION.md` remains governing and identify its approved amendments. No behavior remediation, spec edits, or authority changes before that clarification.


### D-35 — Fountain tier-only candidate queries can still select paused beliefs
- Type: source-level status-filter inconsistency; live incidence UNKNOWN.
- Evidence: Fountain's main own-source query, residue re-read and seed-source query omit `paused=0`; the own-source and residue paths do filter `tier < 8`, while the seed-source query has no tier/paused/locked filter. The optional associative-recall candidate pool also omits paused filtering. Stage 3 BeliefRetriever, NovelAssociation and EdgeBuilder candidate queries do filter paused rows.
- Impact: paused rows can enter Fountain's intermediate candidate list. Paused `precipitated_from_sense` rows can be rendered in the always-on own_sense block; other own-source or associative candidates reach prompt text only through the optional own_render block (source default OFF), while seed-source rows are rendered by default. Thus the exposure differs by source slot and must not be described as every paused candidate being directly rendered.
- Disposition: define paused-state semantics and apply them consistently only after Gate 0 / explicit approval. Do not change retrieval filters now.

### D-36 — April queue-only One-Pen wording conflicts with the merged October connection-factory migration
- Type: governing-document / architecture-contract divergence; NOT a confirmed code defect.
- Evidence: April SPECIFICATION.md §3 describes exactly one Writer thread per database and requires all writes to use its queue. However, owner-authored PR #11 (merged 2026-10-17; merge commit 64933125) explicitly shipped H4/H5 as a canonical substrate.connect() factory plus a full migration of roughly 95 modules, and its body says the one-pen ratchet was retired. The merged tests/test_edges.py::TestNoDirectSqlite checks only that modules outside substrate/ do not import sqlite3 directly; it does not assert that writes use Writer.write(). substrate.connect() centralizes WAL, busy_timeout and foreign_keys pragmas but does not serialize writes through the Writer queue. The Writer class remains available and is used by selected paths.
- Source inventory: the direct-connect paths are enumerated in trace §§61–62. Their presence is consistent with the merged factory migration and must not be reported as an accidental bypass of a still-enforced runtime invariant. The old SPECIFICATION.md and some Writer docstrings still describe a stronger queue-only rule.
- Impact: the intended concurrency contract is ambiguous across governing documents and implementation. The October merged PR is strong evidence that direct connections through substrate.connect() were deliberately accepted, but it does not by itself establish whether the April Constitution was formally amended or whether Writer remains mandatory for selected subsystems.
- Disposition: founder identifies the current authoritative database contract / amendment record and whether the October migration supersedes SPECIFICATION.md §3. Until then, do not migrate direct-connect paths back to Writer, do not claim those paths are defects, and do not infer that substrate.connect() provides single-writer serialization. Keep the inventory for future transaction/concurrency review.
### G-23 — Doctrine / Faculty Model approval and amendment status is unresolved
- Type: founder authority / architecture-specification gap.
- Evidence: `theory_x/DOCTRINE.md` (2026-05-09) says DRAFT awaiting Jon's review and approval, but contains a §7 amendment directing generative node writes through the Faculty Model + Coherence Gate. `theory_x/FACULTY_MODEL.md` (2026-05-10) calls itself foundational and states that every node-generated thought passes through the gate; its implementation order preserves legacy Fountain/Synergizer paths during the initial gate phase. Neither file is labelled Frozen V2.1, and no founder sign-off record was found in the searched archive/Library. The April `SPECIFICATION.md` does not show a later explicit amendment in its path history. DOCTRINE §5 still marks Counterfactual Simulation unblocked/queued and VoiceEngine queued, while both implementations exist in the current branch; §6 requires real-traffic validation and Jon's quality greenlight, neither of which is evidenced by source presence alone.
- Impact: it is unclear which portions of the April Constitution, May Doctrine, May Faculty Model and later Frozen V2.1 are founder-approved and controlling. Direct-writer paths cannot all be classified as gate violations without distinguishing perception, bootstrap, telemetry and generative-thought roles.
- Disposition: founder identifies the canonical governing stack and approved amendments/sign-off. Continue source tracing and isolated tests only; do not edit specifications or implement behavior remediation until authority is clear.

### G-24 — Direct-connection inventory includes Fountain, Moltbook, GUI and optional world-prediction paths
- Type: architecture inventory / transaction-boundary evidence; not a defect solely because these paths do not use Writer.
- Evidence: Fountain generator writes dynamic.db recursion_attrib through substrate.connect(); normal-wired Moltbook listener/responder/poster loops write dynamic.db and sense.db tables through direct connections; GUI action routes directly mutate dynamic.db word_tags, fountain_events, word_contexts, ghost_flags and hypotheses. Ordinary GUI chat persistence and drive-proposal approval use Writer.write() and provide internal contrasts. WorldPredictionLoop writes through direct connections but is explicitly gated by NEX5_WORLD_PRED=1, default OFF.
- Impact: the repository uses a mixed persistence model: selected paths use Writer queues while many modules use independent connections from the canonical substrate.connect() factory. Endpoint invocation, external client readiness and live activity remain UNKNOWN. This is consistent with merged PR #11's factory migration, but the April queue-only constitution text and Writer docstrings have not been reconciled.
- Disposition: preserve this as an inventory. Review transaction boundaries, contention handling and the authoritative database contract before any refactor. Do not migrate paths to Writer or claim that the factory serializes writes without founder direction.
### D-37 — ThoughtPacket arbitrary metadata is lost at persistence boundaries
- Type: source-level provenance implementation gap against Faculty Model §3; normative status awaits founder-approved governing spec.
- Evidence: `ThoughtPacket.metadata` is an arbitrary dict. `beliefs.sql` has no metadata column or packet table; `gate_decisions` does not store metadata. `held_thoughts` has a metadata column, but `HoldingZone.hold()` and `put_reshape_pending()` do not populate it; `promote_to_belief()` does not copy it. Accepted producer INSERTs persist source/confidence/branch/time but not the packet dictionary. Reshape reconstructs only `reshape_hint` and `reshape_depth` from dedicated fields.
- Impact: core provenance survives, but arbitrary packet metadata cannot be queried after acceptance or while held. Metadata-dependent downstream behavior (e.g. counterfactual scenario descriptors) cannot rely on persistence unless separately encoded elsewhere.
- Disposition: identify the canonical Faculty Model/Frozen V2.1 requirement, then define a bounded metadata schema and lifecycle. Do not add columns, migrations or packet logging before Gate 0 / explicit approval.

### G-25 — Post-Phase-22 life-loop belief producers are outside the recorded universal CoherenceGate path
- Type: candidate gate-coverage / doctrine-scope discrepancy; not a confirmed defect while the governing spec and “generative path” boundary remain unresolved.
- Evidence: DOCTRINE.md records Phase 22 universal thought gating on 2026-05-10 and lists five wired paths. Seven belief-producing loops were added on 2026-05-16: Remember, Wonder, Fetch, Identity, Pattern, Witness and Surprise. Each current module contains an INSERT INTO beliefs but no CoherenceGate/coherence_gate/ThoughtPacket/gate.check reference. build_dynamic() appends and starts them in daemon threads. They insert Tier-6 belief rows directly. AffinityLoop only updates existing rows; ScorecardLoop uses Writer.write(); DailyLife, FocusLoop and SignalToProblem mutate non-belief state.
- Impact: if the universal Faculty Model rule covers all background loops that generate new belief content, these seven producers are outside it. If the term generative path is limited to the five named faculty routes or excludes background life loops, their current behavior may be intentional. The draft Doctrine/Faculty Model and missing Frozen V2.1 do not resolve this boundary.
- Disposition: founder clarifies whether life-loop outputs are thoughts subject to CoherenceGate, and whether the May 16 additions were intended exceptions or should have been packet/gate-integrated. Do not alter loop behavior, outputs or activation before Gate 0 / explicit approval.
### G-26 — Recursive self-model loop beliefs are omitted from INSIDE and Fountain own-content allowlists
- Type: source-level producer/consumer classification gap; intent requires founder/design confirmation.
- Evidence: IdentityLoop, PatternLoop and WitnessLoop each insert Tier-6 beliefs under source labels identity_loop, pattern_loop and witness_loop. Their module headers describe own self-description, recursive self-pattern observation and blind-spot observation. Stage4 MembraneClassifier._INSIDE_SOURCES includes identity (seed beliefs) but none of those three loop sources. SelfModel._get_inside_beliefs() filters strictly by that allowlist, and MembraneRouter._inside_route() uses that snapshot plus BeliefRetriever side_filter=INSIDE. FountainGenerator._OWN_CONTENT_SOURCES also omits all three. The classifier was explicitly refreshed on 2026-10-10 (commit 397aa695c8) to add other internally-generated sources and update the membrane source test, but still did not add or test these three loop labels.
- Impact: these explicitly self-reflective beliefs are excluded from the named INSIDE self-inquiry context and Fountain's dedicated own-content retrieval slots. They may still be reachable through other broader retrieval paths; no claim is made that they are globally inaccessible.
- Disposition: founder/design confirms whether IdentityLoop, PatternLoop and WitnessLoop outputs should count as INSIDE self-model content and as Fountain own-content. If yes, define the canonical source classification and tests; do not alter either allowlist before Gate 0 / explicit approval.
### G-27 — Life-loop belief producers bypass content-derived tag generation and normalization
- Type: source-level divergence from TAG_PROTOCOL.md; producer exception policy not found.
- Evidence: TAG_PROTOCOL.md calls itself a foundational spec with decisions locked with Jon (2026-05-11), says tags are auto-generated from entity content, and §6 requires every path into tags to use the helper. The seven post-Phase-22 life-loop producers insert beliefs directly via substrate.connect(), bypassing TaggingBeliefWriter/tag_ops. TAG_PROTOCOL.md and its write-time helper/wrapper were already committed on 2026-05-11; these producers were introduced on 2026-05-16, with no approved exception found in the inspected docs. IdentityLoop, PatternLoop and WitnessLoop hard-code one tag each; RememberLoop, WonderLoop and FetchLoop write literal []; SurpriseLoop serializes ["surprise", "big_surprise" if true else "surprise"], which produces duplicate "surprise" entries when big_surprise is false. Boot-time keystone/koan seeds also bypass the wrapper before construction and retain schema-default empty tags; scripts/seed_identity_beliefs.py uses a raw Writer, while substrate/seed/load_spectrum.py and substrate/spectrumizer_process.py use raw sqlite3 for source=spectrum seed rows. TaggingBeliefWriter explicitly exempts seed scripts/admin tools, so seed scope is a separate policy question. Optional HotObserver omits tags on its direct insert; it is not a seed/admin utility. SelfLocationCommitment and Stage 2 sense distillation are contrasts: they use the wrapped beliefs_writer.write() and receive generated tags.
- Impact: generated belief tags are not consistently content-derived or normalized through the shared helper; the SurpriseLoop non-big branch can persist duplicate tags. The other six cases may reflect intentional manually curated/empty tags, but no approved exception was located.
- Disposition: founder confirms whether generated life-loop beliefs are in scope for the Tag Protocol and whether manual per-producer tags are permitted. After that, add isolated producer tests and correct the duplicate case. Do not change live producer behavior before Gate 0 / explicit approval.
### G-28 — Identity / Pattern / Witness loop docstrings claim a closed feedback edge not present in the inspected source
- Type: source/documentation and producer-consumer discrepancy; intended semantics require founder/design confirmation.
- Evidence: PatternLoop reads identity_log and writes pattern_log plus a Tier-6 belief; WitnessLoop reads pattern_log and writes witness_log plus a Tier-6 belief. IdentityLoop reads previous identity_log and aggregate metrics, but does not read pattern_log, witness_log, or their belief rows; its deterministic _compose_statement() uses only metrics and previous identity statement. FountainGenerator directly injects the latest identity_log statement, but no direct pattern_log/witness_log injection was found. Stage 4 INSIDE and Fountain own-content allowlists exclude pattern_loop/witness_loop (G-26). IdentityLoop's new_beliefs_6h count can change when these beliefs are written, but that is aggregate count feedback, not semantic content feedback.
- Impact: the documented L1→L2→L3→L1 closed recursive self-model is not demonstrated by current source. The observed path is identity_log → PatternLoop → pattern_log → WitnessLoop → witness_log, with identity_log independently injected into Fountain. Pattern/Witness text does not feed IdentityLoop's next composition through an inspected content path.
- Disposition: founder clarifies whether the intended design is a true semantic feedback loop or a feed-forward sequence with aggregate metric feedback. If the latter, correct the docstrings; if the former, specify the intended consumer path and isolated acceptance test. Do not add dependencies or change loop behavior before Gate 0 / explicit approval.
### D-38 — Active development branch lacks the October 26 owner timezone migration from main
- Type: branch-integration / owner-decision propagation gap; runtime effect conditional on loop activation.
- Evidence: main commit c247c240f8 (2026-10-26) records an owner decision for Africa/Johannesburg and migrates identity_loop, pattern_loop, witness_loop, daily_life, decoder, temporal sense, Fountain prompt time, speech quiet hours and related time bucketing to nex_config.local_tz/local_dt. It adds tests/test_local_tz.py. The active branch still hardcodes Europe/Amsterdam in the four life loops and its nex_config.py lacks NEX5_TZ/local_tz. The active branch is materially behind main.
- Impact: if the active checkout is run, the four scheduled life loops use Amsterdam time rather than the owner-selected Johannesburg clock recorded in main. No current service or loop activity is inferred.
- Disposition: do not merge/rebase main wholesale or cherry-pick only a subset of the cross-cutting timezone commit. Confirm that the October 26 owner decision applies to the active branch, then plan a bounded complete backport with the corresponding tests and all dependent modules. No runtime change before explicit approval.
### G-29 — SignalToProblem creates open_problems with source-style tags instead of Tag Protocol content tags
- Type: source-level divergence from TAG_PROTOCOL.md §4/§5; approved exception not found.
- Evidence: tag_ops.TAGGABLE_TABLES includes open_problems; §4 says tags derive from title + description. ProblemMemory complies by calling tag_protocol.generate(title + description) before its Writer INSERT. SignalToProblem instead inserts open_problems directly and writes json.dumps(["auto", f"signal:{signal_type}"]) without generate()/normalize()/write(). The loop is registered and started by build_dynamic().
- Impact: signal-created open problems receive a different tag dialect (source/status-like labels) from ProblemMemory-created problems, contrary to the shared semantic vocabulary/content-derived tagging design. The colon in signal:<type> is not preserved by the protocol normalizer. The module's durable advancements_drift debounce checks tags LIKE '%signal:advancements_drift%', so any future normalization/migration must preserve or deliberately replace that idempotency key. Existing TestTagProtocol tests exercise generate()/write() on synthetic open_problems rows but do not invoke SignalToProblem's producer path.
- Disposition: confirm whether signal-created problems have a deliberate exception or should use the common title+description generation pipeline. Add isolated producer tests after contract confirmation; do not change runtime behavior or existing tags before Gate 0.

### D-39 — BehaviouralSelfModel Gate exception handler can fall through to belief insertion
- Type: conditional fail-open control-flow candidate; normative status depends on the founder-approved Gate contract.
- Evidence: `BehaviouralSelfModel.write_behavioural_beliefs()` builds a ThoughtPacket and calls the supplied CoherenceGate. A non-ACCEPT returns without insertion. However, the surrounding `except Exception` logs the error and then continues to the shared beliefs Writer insert. Normal `build_membrane()` wiring supplies Gate and starts the BSM daemon loop on a four-hour cadence. CoherenceGate itself normally catches evaluation failures and returns `gate_error_fallback` ACCEPT; this BSM catch is a separate path if an exception escapes `check()`. The existing BSM test constructs the component without a Gate and does not exercise this branch.
- Impact: an exception escaping the Gate call can result in a Tier 6 `behavioural_observation` belief being inserted without a successful ACCEPT result.
- Disposition: define the required exception policy for all Gate-wired producers. Do not change the BSM catch or writer before Gate 0 / explicit approval.

### G-30 — Manual Decryption ProbeRunner can inject synthetic beliefs into the live graph
- Type: experimental-tool authorization and isolation boundary; not a normal runtime writer.
- Evidence: `decryption/probe_runner.py` is explicitly invoked through `run_condition()` / `run_matrix()`, is not imported by normal startup, and defaults to `dry_run=False`. It uses raw `substrate.connect()` to insert synthetic `fountain_insight` rows with `parent_belief_id=-99`, changes live mode through `POST /api/mode/set`, waits for a genuine Fountain fire, and deletes the injected IDs during normal `finally` teardown. It does not call CoherenceGate or the shared TaggingBeliefWriter. Abrupt termination can bypass cleanup. The script was not run.
- Impact: explicit invocation can temporarily place synthetic beliefs into normal retrieval paths and influence a live Fountain cycle; interrupted teardown can leave them behind.
- Disposition: founder confirms whether this live-system experiment remains authorized and whether it must be isolated/sandboxed. Do not run it or alter it during Phase 0.

### G-31 — ResumptionSeeder promotes recency without rechecking belief status
- Type: boot-time status/recency semantics gap; live incidence UNKNOWN.
- Evidence: normal `run.py` invokes ResumptionSeeder once at startup. It updates `created_at` for IDs in the prior state snapshot. StateSnapshotWriter selects recent IDs by source family (`fountain_insight`, `synergized`, `auto_probe`) without a tier/paused/locked predicate, and ResumptionSeeder updates those IDs without revalidating status. This changes recency, not belief content or tier.
- Impact: a Tier 8 or paused row present in the snapshot can be made recent again. Downstream paths with incomplete status filters may then select it more readily.
- Disposition: define whether boot resumption should exclude retired/paused/locked rows. Do not change snapshot selection or seeder behavior before Gate 0 / explicit approval.

### G-32 — SpeechQueue consumer does not revalidate source-belief status before playback
- Type: downstream output policy question; live incidence UNKNOWN.
- Evidence: FountainCrystallizer enqueues a content snapshot after belief admission. SpeechQueueConsumer selects the pending queue row and speaks its stored content without joining back to `beliefs` or checking current tier/paused/locked state. No live queue row was inspected.
- Impact: a belief that is paused or retired after enqueue can still be spoken later if its queue row remains pending. This may be intentional if admission is considered final authorization for the queued utterance; that contract is not established by the inspected source.
- Disposition: founder/design defines whether post-enqueue status changes should cancel pending speech. Do not add a consumer-side recheck before Gate 0 / explicit approval.

### G-33 — SpeechQueue producer and consumer have inconsistent eligibility and recovery rules
- Type: source-level queue lifecycle inconsistency; runtime impact UNKNOWN.
- Evidence: producer accepts 10–500 characters while consumer suppresses content over 400; producer deduplication blocks any prior row for a belief_id regardless of status; consumer has no startup recovery for rows left in `speaking`; flush and consumer claim are not atomic; API status does not verify worker thread liveness. Details are in `NEX_PHASE0_SPEECH_QUEUE_PRODUCER_CONSUMER_CENSUS_2026-11-25.md`.
- Impact: some queued thoughts can be immediately suppressed, failed/skipped rows cannot be retried for the same belief, interrupted rows can remain stuck, and UI status can report enabled after worker exit.
- Disposition: decide intended once-per-belief, retry, recovery and status semantics before any queue lifecycle change. No code change before Gate 0 / explicit approval.



### D-40 — Paused beliefs remain eligible for tier promotion and decay mutations
- Type: source-level paused-state mutation inconsistency; live incidence UNKNOWN.
- Evidence: `BeliefPromoter.corroborate()` and `survive_challenge()` read target rows by ID without checking `paused`. The regular decay query and the `NEX5_TIER_CLIMB` query select unlocked beliefs by tier/age without `paused=0`. `WorldConsolidator` selects Tier 7 rows with `erosion_stage != 'retired'` and `locked=0`, but no paused predicate, then calls `corroborate()` for up to three promotions per run. The tracked launcher sets `NEX5_TIER_CLIMB=1` and `NEX5_WORLD_CONSOLIDATE=1`; however, the known hard-coded `cd` path blocker means the script currently exits before launching `run.py` on the repaired host checkout. The active user unit is untracked and the path repair remains in draft PR #97, so these flags are declared, not proven effective.
- Impact: paused beliefs can still have their tier and corroboration state changed by background promotion/decay paths. Pause may therefore suppress retrieval without freezing all belief-state mutation.
- Disposition: define whether pause means retrieval suppression only or full mutation freeze. Do not change promotion/decay predicates before Gate 0 / explicit approval.

### G-34 — Shutdown does not quiesce all producers before closing Writers
- Type: source-level shutdown coordination risk; live incident UNKNOWN.
- Evidence: `AppState.close()` calls `scheduler.shutdown()` and then closes Writers; it does not set DynamicState, WorldModelState or Membrane stop events, nor call stop methods on the other started loops. Fountain runs an uninterruptible `while True` daemon. `SenseScheduler.shutdown()` sets adapter stop events but does not join. `Writer.close()` enqueues a sentinel and joins up to 10 seconds; `submit()` has no closed-state guard, so a post-sentinel submission can leave its Future waiting. `run.py` SIGTERM waits 1.5 seconds, calls `state.close()`, then `os._exit(0)`; tracked `nex_keepalive.sh` waits up to 15 seconds before SIGKILL.
- Impact: active background producers can race with Writer shutdown; a late submission can block after the worker exits, and the supervisor deadline may expire before sequential Writer closes finish. No shutdown was executed.
- Disposition: define a coordinated quiesce/stop/join/drain/close order before any lifecycle remediation. Do not modify shutdown code before Gate 0 / explicit approval.

### G-35 — Moltbook dry-run is not read-only, and the tracked launcher enables real outbound actions
- Type: external I/O and dry-run semantics boundary; live activity UNKNOWN.
- Evidence: Stage 2 registers Listener, Responder and Poster loops when the package imports; there is no separate master enable flag in the inspected factory. `MOLTBOOK_DRY_RUN` defaults to exact string `"1"` and only intercepts non-GET requests; GET status/feed/conversation/message reads still reach the remote API. Any value other than exactly `"1"` sets dry_run false. In dry-run, Poster can mark a local row `posted`, Listener can mark local approval, and Responder can mark a reply `sent` after synthetic success responses. Poster candidate selection and Responder related-belief retrieval do not filter paused, locked, retired or Tier 8 belief states. Listener auto-approves agents passing claimed/red-flag/karma filters and creates pending replies with `needs_human=0`. The tracked `nex_keepalive.sh` sets `MOLTBOOK_DRY_RUN=0`, enabling real remote POSTs if the script reaches its launch block and credentials are available. The current host reconciliation records a stale hard-coded `cd` path that exits before `run.py` on the repaired checkout; the actual user service unit is untracked/unknown. See `NEX_PHASE0_MOLTBOOK_EXTERNAL_IO_AND_DRY_RUN_AUDIT_2026-11-25.md`.
- Impact: the integration can ingest external DMs, auto-approve selected requests, send replies and publish NEX thoughts. Dry-run is not offline and can create local false-success state; malformed flag values can unintentionally permit real writes. Unfiltered belief rows can cross the external publication boundary. Actual credentials, effective flag and live activity were not inspected.
- Disposition: confirm whether autonomous inbound ingestion, automatic approval/reply and outbound posting remain intended; define dry-run guarantees and allowed belief states before any activation. Do not run or change the integration before Gate 0 / explicit approval.

### G-36 — Effective runtime flags cannot be confirmed from the tracked repository alone
- Type: deployment evidence gap.
- Evidence: tracked `nex_keepalive.sh` sets multiple optional flags, including `NEX5_HOT_OBSERVER=1`, `NEX5_WORLD_CONSOLIDATE=1`, `NEX5_WARRANT_RECORD=1`, `NEX5_PERSONA_RESPONDER=1`, `NEX5_WORLD_PRED=1`, `NEX5_SELF_PRED=1`, `NEX5_SELF_MAINTAIN_SHADOW=1`, `NEX5_SOCIAL_N=1`, `NEX5_TIER_CLIMB=1`, and `MOLTBOOK_DRY_RUN=0`. The tracked systemd README says active user units live under `~/.config/systemd/user` and are not in the repository. The known `nex_keepalive.sh` hard-coded path blocker currently prevents the tracked script from launching on the repaired host checkout; the narrow path fix remains in draft PR #97. No live environment or unit was inspected.
- Impact: source defaults alone understate the feature set declared by the tracked launcher, but the actual host-effective configuration remains unverified.
- Disposition: verify the active user unit/launcher before any claim about current runtime state or any flag change. No local unit was accessed or changed.

### G-37 — SenseScheduler documentation says paused while boot code auto-starts external feeds
- Type: source documentation/activation-state discrepancy; live feed activity UNKNOWN.
- Evidence: SenseScheduler class docstring and a `run.py` comment say external feeds start paused; constructor calls `start_all()` during normal boot, and `run.py` logs auto-start. A nearby code comment records the auto-start change as deliberate (“per Jon's request”, 2026-05-09). The active service unit and adapter credentials were not inspected.
- Impact: a reader relying on the docstring/comment may incorrectly believe external feeds remain paused; source code starts the adapter threads.
- Disposition: preserve the recorded historical intent, but reconcile the stale comments/docs with the approved startup contract. Do not alter feed startup behavior before Gate 0 / explicit approval.



### G-38 — External-input prediction generation and verification use different populations
- Type: source-level prediction measurement-population mismatch; score impact UNKNOWN.
- Evidence: `PredictiveSubstrate._predict_external()` selects sense rows with `stream NOT LIKE 'internal.%'`, separately selects user messages, concatenates sense rows before messages and truncates to ten; it does not globally sort the combined inputs by recency. `_verify_one()` for `external_input` then selects all sense events in the target window without the `internal.%` exclusion, plus user messages. Thus internal sense events can be used as verification “actuals” despite being excluded from the forecast input population, and recent user messages can be displaced by ten qualifying sense rows. See `NEX_PHASE0_PREDICTION_SURPRISE_CROSS_FACULTY_AUDIT_2026-11-25.md`.
- Impact: external surprise scores may reflect a different event population from the one used to form the prediction, and the forecast may not represent the globally most recent ten inputs. No live data distribution or score effect was measured.
- Disposition: define the intended external-input population and sampling order, then add isolated generation/verification tests. Do not change prediction queries or historical scores before Gate 0 / explicit approval.

### G-39 — SurpriseLoop timestamp cursor can skip equal-time overflow and failed writes
- Type: conditional derived-belief promotion loss/retry gap; live incidence UNKNOWN.
- Evidence: `surprise_loop.surprise_tick()` selects flagged rows with `triggered_at > since ORDER BY triggered_at ASC LIMIT 20`, then advances a timestamp-only cursor to the maximum timestamp seen. PredictiveSubstrate resolves all due predictions in one tick using one `now` value for each generated `surprise_events.triggered_at`; if more than 20 eligible rows share that timestamp, rows beyond the first batch no longer satisfy the strict-greater-than cursor query. The loop also advances `max_ts` after a row's belief INSERT raises, so a transient failed insert is not retried by the cursor.
- Impact: in a backlog/recovery case, some surprise events may never be promoted to beliefs. Normal steady-state cadence usually creates far fewer than 20 due events, but no runtime backlog was inspected.
- Disposition: decide the required lossless/retry/dedup contract and use a stable row identity or composite cursor if warranted. Add isolated equal-timestamp overflow and failed-write tests after the contract is confirmed. Do not change the cursor or reprocess live events before Gate 0 / explicit approval.

### G-40 — GoalManager-created open goals are not selected by CoherenceGate
- Type: source-level producer/consumer state-vocabulary mismatch; live incidence UNKNOWN.
- Evidence: `GoalManager.open()` and the goals schema create rows with `state='open'`; GoalManager list/get_active also selects `open`. `CoherenceGate._load_context()` selects only `state='active'`. No normal GoalManager method writes `active`. The Gate test helper seeds `active` directly, so it does not exercise the normal GoalManager/API producer path. The detailed trace is in `NEX_PHASE0_OPEN_PROBLEM_AND_GOAL_LIFECYCLE_AUDIT_2026-11-25.md`.
- Impact: normal API-created goals are not included in the Gate's up-to-five goal context rows. No live goal population or Gate decision effect was measured.
- Disposition: founder/design confirms whether `open` is the intended active goal state or whether `active` is a distinct state with an omitted transition. Align producer, consumer and integration tests only after the lifecycle contract is confirmed; no query or state change before Gate 0.

### G-41 — ProblemMemory and GoalManager decay methods are not scheduled in normal boot
- Type: lifecycle wiring/documentation gap; practical impact UNKNOWN.
- Evidence: ProblemMemory.decay() closes open problems stale over 30 days; GoalManager.decay() cancels open goals stale over 60 days. Both classes are constructed in normal startup, but the inspected run.py/gui/server.py path does not call their tick()/decay() methods. `theory_x.register()` stores nodes in a process list and `all_nodes()` returns a copy; there is no tick/decay scheduler in the registry. The unit tests call decay() directly, not through a boot lifecycle.
- Impact: the documented stale auto-close/auto-cancel behavior does not occur autonomously through the inspected normal startup path. Existing stale records can remain open absent manual/API state changes.
- Disposition: founder/design confirms whether decay is intended to be manually invoked, called by another orchestrator, or scheduled. Do not introduce a lifecycle scheduler or alter stale thresholds before Gate 0.

### G-42 — Stuck problems disappear from open-only views but remain eligible for Fountain injection
- Type: state-semantics / visibility contract question; live incidence UNKNOWN.
- Evidence: FocusLoop marks a problem `stuck` after surfacing a help message. GUI `GET /api/problems`, Chat matching, FocusLoop, CounterfactualNode, DailyLife, CoherenceGate, PredictiveSubstrate, CompetingDrives and SelfMindView all select only `state='open'`. The GUI has no dedicated stuck-list route in the inspected source, though a known ID can be fetched directly. Fountain ProblemMemory.select_for_injection() intentionally selects any state, including stuck/closed, subject to its age, real-question, pool-size and cooldown filters.
- Impact: a stuck item is removed from most visible/active problem flows but may later be re-surfaced by Fountain's separate all-state injection mechanism. This may be intentional to pause automatic work while retaining reflective re-surfacing; no live stuck rows were inspected.
- Disposition: founder/design defines whether stuck is a parked, user-visible, terminal or re-surfacing state. Do not change filters, routes or state transitions before Gate 0.

### G-43 — Signal retention allowlist has drifted from SignalToProblem eligibility
- Type: source-level retention-policy mismatch; live impact UNKNOWN.
- Evidence: SignalToProblem currently promotes `2_branch`, `3_branch`, `4_branch` and `advancements_drift`. The signal reaper preserves un-actioned rows only for `2_branch`, `3_branch`, `t6_promotion_burst`, `pattern_recognition_burst`, `cross_branch_convergence`, `novel_arc` and `concept_emergence`. It therefore preserves obsolete burst types no longer promotable and omits two current types. Its seven-day age condition means omitted types are already outside SignalToProblem's six-hour lookback when deleted, but the stated “preserve unconsumed promotable rows” contract is not aligned. See `NEX_PHASE0_SIGNAL_PIPELINE_RETENTION_AND_PATTERN_AUDIT_2026-11-25.md`.
- Impact: un-actioned obsolete types can remain indefinitely; current types can be deleted after seven days. Actual row counts and disk effect are UNKNOWN.
- Disposition: decide whether retention should mirror the current promotion contract or preserve a separate historical set, then reconcile allowlists and test it. Do not change retention before Gate 0 / explicit approval.

### G-44 — SignalToProblem cross-database writes are not atomic
- Type: conditional cross-database consistency gap; live incidence UNKNOWN.
- Evidence: `signal_to_problem_tick()` inserts an `open_problems` row using a conversations.db connection and updates `signals.actioned_at` using a beliefs.db connection. It commits beliefs first and conversations second. These are independent SQLite transactions; a successful first commit followed by a failed second commit can leave a signal marked actioned without the corresponding problem row.
- Impact: under a commit failure in the second DB, a promotable signal may be consumed without a durable open problem. No such failure or missing problem was observed.
- Disposition: founder/design confirms the required atomicity/recovery contract (idempotent replay, outbox, or reconciliation). Do not redesign the persistence boundary before Gate 0 / explicit approval.

### G-45 — Self-continuity wording can claim stability/movement without evaluating the full selected state
- Type: Phase 1 semantic-evidence mismatch; live activation UNKNOWN.
- Evidence: `continuity_for_prompt()` selects emotion, raga and drive, but all phrase branches inspect emotion only. The held-steady branch filters out empty emotion rows, so it can claim continuity across recent bindings despite missing samples. The generic “moving rather than settling” fallback is emitted when emotion cannot establish a result, without checking whether raga or drive changed. See `NEX_PHASE0_SELF_CONTINUITY_SEMANTICS_AUDIT_2026-11-25.md`.
- Impact: if the default-OFF flag is armed, the self-view may express a continuity/change claim not supported by all three selected dimensions or by complete samples. No live activation or phrase output was inspected.
- Disposition: founder/design defines the continuity dimensions and missing-data language. Do not arm or alter this Phase 1 consumer before Gate 0 / explicit approval.

### G-46 — Self-continuity history ordering is not deterministic for timestamp ties
- Type: Phase 1 deterministic-ordering gap; live incidence UNKNOWN.
- Evidence: the query orders only by `bound_at DESC` and uses the first two rows as current/previous. No secondary key is specified.
- Impact: equal-bound_at rows can yield different current/previous pairings across query plans or DB states. No tie case was observed.
- Disposition: confirm whether the writer guarantees unique timestamps; if not, define an approved stable tie-breaker before changing the query.

### G-47 — Self-continuity connection close is not protected on exception paths
- Type: resource-cleanup robustness gap; live impact UNKNOWN.
- Evidence: `continuity_for_prompt()` creates a SQLite connection, fetches rows and calls `c.close()` only on the success path. The broad exception handler returns an empty string but there is no `finally` cleanup.
- Impact: an exception after connection creation can leave cleanup to Python object destruction/GC. The helper is read-only and fail-safe for prompt composition; no resource leak was observed.
- Disposition: decide whether explicit deterministic cleanup is required for this short helper. Do not change the Phase 1 seam before Gate 0 / explicit approval.

### G-48 — InfluenceRecord is an output-seam capture, not end-to-end causal lineage
- Type: technical trace-overlay coverage gap (previously labelled M0.5) against the roadmap extract recorded in the reconciliation; exact governing scope UNKNOWN.
- Evidence: actual runtime seams call `record_fountain_fire()` after generator return and `record_chat_turn()` after Chat reply persistence. Records include a limited set of scalar inputs and output digest/preview; the module marks retrieved-belief and faculty-block attribution unresolved. There are no `trace_id` or `parent_ids`, no candidate-generation/workspace/Gate/writer-delta capture, and Chat cycle_id is `chat:<session_id>` rather than a unique turn ID. See `NEX_PHASE0_INFLUENCE_TRACE_COVERAGE_AUDIT_2026-11-25.md`.
- Impact: records cannot reconstruct the requested stage-by-stage causal path or uniquely correlate individual Chat turns within a session. The fixture is not live evidence.
- Disposition: recover Frozen V2.1 and founder approval to determine whether the two seams are a deliberate Phase 0 precursor or an incomplete technical trace-overlay implementation. Do not add hooks, IDs or reads before that decision.

### G-49 — InfluenceRecord L4 evidence label is caller-declared, not independently authenticated
- Type: evidence-integrity / provenance-label gap; no live L4 record observed.
- Evidence: `_env_context()` treats `NEX5_INFLUENCE_TRACE_CONTEXT=runtime` as runtime; constructor accepts `context='runtime'`. `test_runtime_context_is_L4_fixture_is_L3` deliberately produces L4 from an ordinary unit-test tracer. No host/process identity check or external runtime attestation is present.
- Impact: a fixture or non-live process can emit records labelled L4 if the caller declares runtime context. The label alone cannot prove live-host observation.
- Disposition: define the approved L4 evidence contract and authorisation mechanism. Do not add host checks or relabel existing evidence before Gate 0.

### G-50 — Enabled InfluenceRecord sink stores raw text previews without an in-module retention/redaction policy
- Type: privacy / evidence-retention contract gap; live activation UNKNOWN.
- Evidence: `record_chat_turn()` stores up to 160 characters of prompt and reply preview; `record_fountain_fire()` stores up to 160 characters of thought preview. The default sink is `logs/influence_trace.jsonl`; the module appends and creates the directory but defines no redaction, rotation, retention cap, encryption or access policy.
- Impact: if enabled, user-provided and generated text snippets persist outside the substrate DBs. No live trace file or file permissions were inspected.
- Disposition: define what content may be persisted, access controls and retention before any activation. Keep the overlay default-OFF until approved.
