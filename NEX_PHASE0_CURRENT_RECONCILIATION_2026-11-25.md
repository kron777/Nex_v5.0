# NEX v5.0 — Phase 0 Current Branch Reconciliation

**Date:** 25 November 2026
**Purpose:** Refresh the Phase 0 evidence against the active host checkout and correct stale handoff claims.
**Status:** Evidence reconciliation only. This is not Gate 0 approval, a runtime certification, or permission to activate any feature.

## Executive finding

The active host checkout is not the same source snapshot as GitHub main. The host checkout is branch claude/nex-continuity-wire at de93134f34adac07a3a41c2a05b33720510a2bfc. GitHub comparison reports this branch 4 commits ahead and 205 commits behind main, with merge base fb87e247a116221cc7d814e2ee5ff2e1300f5a87. Do not merge, rebase, or cherry-pick main wholesale: the branch contains active-host-specific work and main contains later changes, including unrelated behavioural changes.

The original Reality Report, Crosswalk, ADR and Phase 0 handoff remain useful historical artefacts, but their branch/head metadata and some completion claims are stale. In particular, the active branch now contains the default-OFF continuity consumer commit f9ac58d, despite the old Phase 0 handoff saying no Phase 1 behavioural modification had started.

## 1. Repository identity and branch scope

- Repository: https://github.com/kron777/Nex_v5.0
- Active host checkout: /mnt/games/storage/Desktop/Desktop/nex5
- Active host branch: claude/nex-continuity-wire
- Active host HEAD: de93134f34adac07a3a41c2a05b33720510a2bfc
- Host collector reported a clean worktree at that SHA.
- GitHub compare main...de93134 reports 4 commits ahead / 205 behind; merge base fb87e247a116221cc7d814e2ee5ff2e1300f5a87.
- The active branch contains 757 tree entries at the audited SHA.
- mind_map/MIND_MAP.yaml is absent from the active branch at this SHA, but is present on main. sentience_dag.json is present on the active branch.
- The active branch's .github/workflows/tests.yml has no MIND_MAP validation step. On main, the workflow runs mind_map/mind_map.py --check --verify, but that script checks map structure, evidence/source references, freshness and declared absence claims; it does not inspect NEX runtime callsites or prove that represented faculties cannot gate/veto decisions.
- The main-branch MIND_MAP.yaml declares a descriptive-only constraint in meta.constraint. It contains 34 node entries plus 5 arm entries, while its bootstrap comment and the handover/roadmap references still say 30 nodes. That count discrepancy needs reconciliation; do not silently delete or merge nodes to force the old count.
- The separate sentience_dag.json on the active branch explicitly defines live_unproven as satisfied for buildability, and nex_next_dev.py confirms _SATISFIED = ("built", "live_unproven"). Its own note says this flags rather than blocks dependent work. This is a separate build-order policy from the descriptive MIND_MAP; preserve the distinction.

**Branch discipline:** all findings below describe the active host branch unless explicitly labelled otherwise. Main is a comparison source, not a substitute for the running checkout. No branch merge, rebase or cherry-pick was performed.

## 2. Host and runtime evidence

Host collector evidence and the founder-provided command results establish the following:

- OS: Zorin OS 18.1, Ubuntu Noble base; kernel 7.0.0-43.
- CPU: AMD Ryzen 7 5800X; RAM: 24 GB; GPU: Radeon RX 6600, 8 GB.
- Ollama version reported: 0.40.11.
- qwen2.5:3b is installed, but the captured ollama ps output was empty; no loaded model was verified.
- The host collector found no Python process candidate after its filter. This is not proof that no NEX process exists; it only means the collector did not identify a candidate under that filter.
- Runtime artifact hashing was explicitly skipped by the operator. Database and snapshot hashes, sizes, and active-root identity therefore remain UNKNOWN.
- The collector's cached origin/main comparison was not a fresh remote fetch; the GitHub compare above is the remote branch comparison used here.

### Service path repair and remaining blocker

The four loaded user-unit definitions were corrected by the founder-approved host repair to use /mnt/games/storage/Desktop/Desktop/nex5. The user verified all four with systemctl --user cat, and systemd-analyze --user verify reported no unit syntax errors. No service was started or restarted.

Static source inspection then found that nex_keepalive.sh still executes a hard-coded cd to /home/rr/Desktop/Desktop/nex5 before doing anything else. The corrected systemd unit therefore still points to a script that will attempt to enter the old, missing checkout and exit before launching run.py. Service operation remains untested and should not be attempted until this internal path is corrected.

The checked-in deploy/systemd/nex5-db-reaper.service reference also contains the old path. That is a stale repository template/reference; it does not mean the founder-corrected loaded user unit reverted.

A narrow source-only portability fix is prepared separately in draft PR #97. It resolves the checkout root from the keepalive script's own location and adds isolated path-resolution tests. It has not been merged or deployed.

### Vitals

tools/nex_vitals.py, tools/nex-vitals.service, tools/nex-vitals.timer, tools/NEX_VITALS_CRON.md and tests/test_nex_vitals.py exist on main but are absent from the active host branch. They entered main through merge 7f873d1, which also brought unrelated changes to persona/focus/frame behaviour. Restoring Vitals by cherry-picking that merge would import those unrelated changes.

Vitals is not merely a read-only query: its scheduled --log mode appends persistent measurement history. Its live-environment reader trusts the PID in ~/.nex/nex.pid and reads /proc/<pid>/environ without verifying process identity against the NEX checkout. The exact governing Vitals spec referenced by its introduction was not recovered. Do not restore, enable, start, disable or delete the timer by assumption.

## 3. Test baseline

The founder-provided host run of PYTHONPATH=. .venv/bin/python scripts/check_test_baseline.py on the active checkout reported:

- 1610 passed
- 5 skipped
- 30 subtests passed
- 0 unexpected failures
- 122.87 seconds

tests/known_failures.txt contains no active test-node allowlist entries. This is the current reported host baseline for the active branch. It is distinct from the older Reality Report's environment-limited snapshot of 1568 collected, 107 failed, 1406 passed, 5 skipped and 62 errors; that older run must not be presented as the current baseline.

Python and SQLite exact versions, Qwen2.5 3B model digest, idle/load RAM and VRAM, and median tokens/sec were not established in the evidence available for this refresh. They remain UNKNOWN, not inferred from the hardware or installed-model listing.

## 4. Phase 0 deliverable status

| Roadmap item | Current evidence | Status |
|---|---|---|
| M0.1 repository identity | Exact active URL, branch, SHA and clean-worktree report | Partial; remote divergence is now known |
| M0.1 runtime DB/snapshot fingerprints | Explicitly skipped by operator | UNKNOWN / outstanding |
| M0.1 host/model performance baseline | Hardware and Ollama version known; model digest, exact Python/SQLite, RAM/VRAM load and tokens/sec absent | Partial |
| M0.2 test baseline | 1610 passed, 5 skipped, 30 subtests; 0 unexpected failures, founder-provided host run | Reported complete for this branch snapshot |
| M0.3–M0.4 architecture crosswalk | Existing v2 crosswalk covers Fountain and Chat output paths only | Seeded; full-system DAG outstanding |
| M0.3–M0.4 MIND_MAP reconciliation | MIND_MAP absent from active branch, present on main | Outstanding; branch-source discrepancy |
| M0.3–M0.4 descriptive-node authority invariant | No matching CI enforcement step in active branch workflow; expected MIND_MAP file absent | UNKNOWN / outstanding |
| M0.5 InfluenceRecord source and fixture tests | Default-OFF overlay, two coarse seams, 16 tests and two fixture records | Implemented/test-verified at fixture level |
| M0.5 requested trace sample | Roadmap asks for NEX_CAUSAL_TRACE_SAMPLE.json; active branch has docs/phase0_influence_capture_fixture.jsonl instead | Naming/schema reconciliation outstanding |
| M0.5 full causal lineage | No demonstrated trace across candidate generation, salience/workspace selection, gate decision, SQLite writer delta and output | Incomplete |
| M0.5 live L4 capture and live zero-delta | No authorised live capture; runtime process identity not verified | UNKNOWN / outstanding |
| Gate 0 | Founder has not yet reviewed and approved the complete Reality Report, Crosswalk and verified defect backlog | PENDING |

### M0.5 trace contract discrepancy

The technical roadmap extract names NEX5_TRACE_OVERLAY=0 and asks for trace_id/parent_ids across Input Arrival → Candidate Generation → Salience/Workspace Selection → Gate → SQLite Writer Delta → Output. The active branch's implementation instead uses NEX5_INFLUENCE_TRACE, NEX5_INFLUENCE_TRACE_CONTEXT and NEX5_INFLUENCE_TRACE_PATH. Its current seams record a Fountain fire after generation and a Chat turn after reply finalisation. The records do not yet establish full parent-child lineage through the intermediate stages or the writer delta.

The existing fixture is useful evidence that the two coarse seams can emit fixture records. It is not the requested full causal sample and does not establish live L4 evidence. The exact Frozen V2.1 document and approval record remain missing, so no unverified field-level requirements are to be invented.

## 5. Phase 1 continuity change already present on the active branch

Commit f9ac58d adds a default-OFF continuity consumer: self_binding.continuity_for_prompt() reads recent self_state_history rows and SelfMindView.current_summary() appends a descriptive clause when NEX5_SELF_CONTINUITY=1.

Static wiring is present: run.py constructs SelfMindView and passes it into AppState; gui/server.py calls current_summary() and appends the result to belief_text for the chat composition path. This establishes a source-level route, not proof that every reply path consumes it or that it has been active in the live process. The relevant call sites are run.py:473 and :720, gui/server.py:1512, SelfMindView.current_summary at theory_x/stage_tom/self_mind_view.py:434, and continuity_for_prompt at theory_x/stage_tom/self_binding.py:345. The CONTINUITY_WIRE.md description of SelfMindView as a zero-importer/leaf consumer is therefore incomplete: it is constructed by run.py and its summary is consumed by the GUI chat path.

The old PHASE0_HANDOFF.md statement that no Phase 1 behavioural modification had started is therefore stale. The continuity feature is a Phase 1 context modification in source, even though its flag defaults OFF. No live flag activation or live behavioural effect has been verified. Do not arm it or expand it before the Gate 0 review and explicit authorisation.

### Continuity semantics — candidate issues, not yet changed

- The query selects emotion, raga and drive, but the wording decision uses emotion only. It can say the self-state held steady while raga/drive changed.
- The fallback phrase “moving rather than settling” can be emitted without demonstrating which selected dimension changed.
- The query orders only by bound_at DESC; equal timestamps have no deterministic secondary ordering.
- The connection close is not protected by a finally block if an exception occurs after connection creation.
- Existing tests establish default-OFF behaviour, a same-emotion phrase, read-only SELECT behaviour and fail-safe handling. They do not test dimension disagreement, unchanged/empty emotion sequences, timestamp ties or connection cleanup.

These are semantic/robustness review items. No continuity behaviour was changed during this reconciliation.

## 6. Verified defect and discrepancy backlog

1. **Stale Phase 0 status documents.** The original Reality Report and handoff describe branch/head fb87e24 and pre-continuity status. They need this reconciliation attached and their stale claims explicitly superseded.
2. **Active-branch architecture source gap.** mind_map/MIND_MAP.yaml is absent from the active branch but exists on main. Reconcile branch history and ownership before importing it.
3. **Incomplete crosswalk.** The existing v2 crosswalk is a two-output-path seed, not the full producer/consumer DAG across theory_x, substrate, speech and GUI.
4. **Trace contract mismatch.** Roadmap flag/schema/sample expectations differ from the current InfluenceRecord implementation; Frozen V2.1 and the exact governing roadmap source remain unavailable.
5. **Live trace evidence absent.** No live Fountain/Chat capture, live zero-delta comparison or verified active process identity.
6. **Phase 1 continuity code precedes Gate 0.** The branch contains the default-OFF consumer; the old handoff incorrectly says otherwise. Its semantic edge cases are untested.
7. **Keepalive script path drift.** Systemd unit paths were corrected, but the script's own hard-coded cd still targets the missing old checkout. Draft PR #97 prepares a source-only fix; not merged or deployed.
8. **Vitals branch divergence.** Vitals exists on main only, arrived with unrelated behavioural changes, and lacks its governing spec in the available archive.
9. **Branch divergence.** The active branch is 4 ahead / 205 behind main. Integration must be deliberate and file-scoped; no wholesale merge/rebase.

## 7. Safe continuation

- Complete the full-system producer/consumer crosswalk on the active branch, reusing existing source and documenting uncertainty rather than inventing missing nodes.
- Reconcile the missing MIND_MAP source against branch history and the main version before treating either as the active host specification.
- Produce a verified defect backlog with file/line evidence, impact, falsifier, test status and authority boundary.
- Recover the exact Frozen V2.1 specification/approval and the original full roadmap before settling the trace contract or declaring Gate 0 ready.
- Keep the InfluenceRecord overlay default-OFF; do not perform live L4 capture or change its flag without explicit authorisation.
- Keep R79–R83 protected. No experiment, baseline or tripwire changes.
- Keep services untouched until the internal keepalive path correction is reviewed, merged/deployed through the approved process, and a separate activation decision is made.
- Keep Watcher and RDO external to NEX's cognitive runtime.

**Gate 0 remains PENDING.** This document improves the evidence package; it does not ask the founder to approve Phase 1 and does not treat a general instruction to continue development as Gate 0 sign-off.