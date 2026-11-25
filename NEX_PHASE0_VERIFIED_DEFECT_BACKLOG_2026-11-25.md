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
- Evidence: the expanded active-branch source trace identifies direct belief inserts in `stage6_fountain/generator.py` (`self_rut_notice`) and seven Stage 2 life-loop modules: `life/pattern_loop.py`, `witness_loop.py`, `identity_loop.py`, `surprise_loop.py`, `remember_loop.py`, `wonder_loop.py`, and `fetch_loop.py`. The loops are appended to the `build_dynamic()` list and started by its daemon-thread factory in source. Their inspected insert functions use direct SQLite connections and contain no CoherenceGate call. This is in addition to sense distillation.
- Distinction: the Membrane Behavioural Self-Model is gated under normal `run.py` wiring; EmergentDrive is conditionally gated for the belief insert but adds the Bonsai branch before the gate and marks the proposal applied even after a non-ACCEPT decision. Dynamic crystallization and Behavioural Self-Model both fall through to their belief insert if an exception escapes the gate call, while CounterfactualNode blocks its insert on such an exception. These are materially different control contracts.
- Impact: the current source does not establish one uniform gate boundary for all belief-producing and related state-changing paths. A simple “all beliefs pass through the gate” statement would be unsupported.
- Disposition: trace and classify every producer, its persistence mechanism, gate outcome handling, exception handling and pre/post-gate side effects. Recover Frozen V2.1 and founder approval evidence before deciding which paths are authorised exceptions or violations. No behaviour changed.

### G-07 — Full belief-producer census and gate control contract remain incomplete
- Type: evidence/specification gap.
- Evidence: the current bounded trace verifies at least nine direct runtime producer paths (sense distillation, Fountain rut mirror, and seven life loops), five gated producer families (Dynamic crystallization, World Model synergizer, Fountain crystallization, CounterfactualNode and Behavioural Self-Model), plus EmergentDrive's conditional gate path. It separately identifies the self-location bootstrap anchor and resolver-mediated Holding Zone promotion. This is a verified subset, not an exhaustive repository-wide census; helper-mediated writes, alternate writers and remaining modules remain to be checked.
- Impact: M0.3–M0.4 cannot be marked complete, and gate authority/scope cannot be assessed from the current source alone.
- Disposition: continue bounded forward/backward source tracing. Preserve unknowns; do not change the gate, producers, flags, or live state pending the governing specification and explicit founder review.

### D-12 — TaggingBeliefWriter / IntakeResonance universal-chokepoint claim is contradicted by source paths
- Type: documentation/coverage discrepancy; no behaviour change proposed.
- Evidence: `run.py` wraps the shared `writers["beliefs"]` instance, and `writer_wrapper.py` intercepts eligible belief INSERTs routed through that wrapper. However, seven Stage 2 life loops use direct SQLite connections to insert beliefs, and the operator identity/self-belief utilities create independent Writer instances. Those writes do not pass through the boot wrapper. The wrapper comment nevertheless calls its embedded IntakeResonance probe a universal chokepoint through which every belief from every writer passes.
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
- Evidence: DailyLife writes generated internal entries into `conversations.messages` with `role='nex'` and `session_id='internal_daily_life'`. BehaviouralSelfModel.observe() selects the latest 100 rows where `role='nex'` and does not filter by session or register.
- Impact: internal templated morning/reading/outreach/journal entries are eligible to influence the response-style metrics and subsequent `behavioural_observation` beliefs. The size of the effect is UNKNOWN because no live message rows or metric contributions were inspected.
- Disposition: determine whether the intended observation population is all NEX-authored messages or only user-facing replies. Validate against isolated fixtures before any runtime change.
