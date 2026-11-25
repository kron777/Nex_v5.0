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
3. Active branch versus main: 4 ahead / 205 behind; MIND_MAP and Vitals absent from active checkout.
4. M0.5 roadmap contract versus InfluenceRecord implementation: flag/schema/lineage/sample mismatch.
5. Continuity Wire note versus actual wiring: SelfMindView is constructed, passed into AppState and consumed by GUI chat.

**No item in this backlog authorises a live change.**