# NEX v5.0 — Phase 0 Current Branch Reconciliation

**Date:** 25 November 2026
**Purpose:** Refresh the Phase 0 evidence against the active host checkout and correct stale handoff claims.
**Status:** Evidence reconciliation only. This is not Gate 0 approval, a runtime certification, or permission to activate any feature.

## Executive finding

The active host checkout is not the same source snapshot as GitHub main. The host checkout is branch claude/nex-continuity-wire at de93134f34adac07a3a41c2a05b33720510a2bfc. GitHub comparison reports this branch 4 commits ahead and 205 commits behind main, with merge base fb87e247a116221cc7d814e2ee5ff2e1300f5a87. Do not merge, rebase, or cherry-pick main wholesale: the branch contains active-host-specific work and main contains later changes, including unrelated behavioural changes.

The original fb87e24 Reality Report and two-path Crosswalk are preserved as NEX_REPOSITORY_REALITY_REPORT_HISTORICAL_fb87e24.md and NEX_ARCHITECTURE_CROSSWALK_v2_HISTORICAL_fb87e24.md. The canonical NEX_REPOSITORY_REALITY_REPORT.md and NEX_ARCHITECTURE_CROSSWALK_v2.md have been refreshed for the active host checkout; the Crosswalk remains partial, with the full producer/consumer DAG outstanding. ADR-001 remains a historical design record. The Phase 0 handoff now points to this reconciliation and corrects its stale Phase 1 claim. In particular, the active branch contains the default-OFF continuity consumer commit f9ac58d, despite the old handoff saying no Phase 1 behavioural modification had started.

## 1. Repository identity and branch scope

- Repository: https://github.com/kron777/Nex_v5.0
- Active host checkout: /mnt/games/storage/Desktop/Desktop/nex5
- Active host branch: claude/nex-continuity-wire
- Active host HEAD: de93134f34adac07a3a41c2a05b33720510a2bfc
- Host collector reported a clean worktree at that SHA.
- GitHub compare main...de93134 reports 4 commits ahead / 205 behind; merge base fb87e247a116221cc7d814e2ee5ff2e1300f5a87.
- The active branch contains 757 tree entries at the audited SHA.
- The active branch has 42 top-level theory_x package directories. This is a filesystem inventory only; it is not interchangeable with the MIND_MAP node count, sentience_dag faculty count, or number of booted worker loops.
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


### M0.3 boot-wiring inventory — first pass

Static inspection of run.py establishes a real boot graph, but not a complete producer/consumer DAG. The following are source-wired at this branch snapshot; they are L2 source evidence only, not proof of live activation or successful operation.

| Boot seam | Source wiring | Evidence / qualification |
|---|---|---|
| Substrate initialization | run.py:60–70 calls init_all(), creates six Writer/Reader pairs, wraps the beliefs writer with TaggingBeliefWriter | substrate/paths.py:23–31 defines beliefs, sense, dynamic, intel, conversations and probes DBs. run.py's opening docstring still says “all 5 DBs” (run.py:5) |
| Self-location | run.py:72–76 constructs SelfLocationCommitment and calls commit() | A boot-time beliefs write if run.py starts; not run or tested against live DB in this audit |
| Sense | run.py:108–111 calls build_scheduler() | The factory builds 28 adapters: 4 internal and 24 external. SenseScheduler.__init__ calls start_all() (scheduler.py:149), so external feeds auto-start on construction. The stage1_sense module docs and scheduler module docstring still say external feeds start paused; run.py:109 correctly says auto-start, but run.py:7 incorrectly says PAUSED. The scheduler and GUI docs still say 23 adapters (scheduler.py:1, gui/server.py:15, run.py:111). This is a verified documentation mismatch with operational significance |
| Dynamic formation | run.py:150–153 calls build_dynamic() | Factory starts nine fixed loops and dynamically appends available life loops (witness, pattern, identity, affinity, scorecard, surprise), remember/wonder/fetch, daily-life, sustained focus, signal-to-problem, diversity edge-builder, gate-retention and Moltbook loops. The exact set depends on imports and the Moltbook factory; writes/reads span sense, dynamic and beliefs. Moltbook real posting is separately gated by MOLTBOOK_DRY_RUN. |
| World model | run.py:174–177 calls build_world_model() | Factory creates six worker threads: decay, harmonizer, cross-domain, erosion, synergizer and world consolidation. The world-consolidation worker returns immediately unless NEX5_WORLD_CONSOLIDATE is set; the others have their own wait/cadence loops. Reads/writes beliefs and dynamic. |
| Membrane | run.py:179–187 calls build_membrane() | Factory starts the behavioural self-model loop when conversations reader exists; also receives dynamic, world model and coherence gate references |
| Coherence / holding / reshape | run.py:124–148 constructs CoherenceGate, HoldingZone, HoldingZoneResolver and TriggerDetector; resolver loop starts at run.py:171 | These are operational gate/reshape mechanisms, distinct from the descriptive MIND_MAP taxonomy |
| Fountain | run.py:538–584 calls build_fountain() | Factory starts the fountain thread; generator consumes sense/dynamic/belief context and its crystallizer can write sense, dynamic and beliefs. Existing Phase 0 trace hook is after generation, not full internal lineage |
| Chat | gui/server.py api_chat() | As described in the output-path crosswalk; the route assembles context, invokes voice/tool paths and persists conversations.messages |
| Speech | run.py:611–629 starts SpeechQueueConsumer only when SpeechConfig.enabled | Queue is in beliefs.db (substrate/schema/beliefs.sql), and consumer reads/updates speech_queue through the supplied beliefs reader/writer |
| Ancillary loops | run.py starts SubstrateHarmonic, GeniusTagger, CounterfactualNode, DriveEmergence, CompetingDrives, AffectState, PredictiveSubstrate, SignalLoop, DiversityLoop, EdgeGeneratorLoop and decoder_loop | Several write diagnostic/derived state. Some are log-only; source comments are not proof of downstream consumption |
| Conditional / retired paths | ThrowNet loop requires NEX5_THROWNET=1; WarrantRecorder requires NEX5_WARRANT_RECORD=1; PersonaResponder requires NEX5_PERSONA_RESPONDER=1; WorldPrediction requires NEX5_WORLD_PRED=1; SelfPrediction requires NEX5_SELF_PRED=1; SelfMaintainShadow requires NEX5_SELF_MAINTAIN_SHADOW=1; ArcLoop is explicitly not started | Preserve these flags and states. Do not activate during Phase 0. ProbeRunner is constructed but no start call appears in run.py. SocialPresence is explicitly set to None. |

The adapter count and startup state need correction in the source documentation, but no runtime correction is proposed here. External feeds currently auto-start by constructor behaviour; this is not inferred from a log message alone—the call to start_all() in SenseScheduler.__init__ establishes it. No scheduler or feed was started during this audit. This documentation-only PR updates the stale run.py, stage1_sense, scheduler and GUI descriptions to six databases, 28 adapters and the actual auto-start behaviour. It does not change SenseScheduler or feed startup logic.

The boot inventory is a first forward pass. It does not yet trace each faculty's emitted records through every reader, downstream consumer, terminal output and persistence boundary. The full M0.3–M0.4 producer/consumer DAG remains outstanding.

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

A founder-reviewable standalone version is maintained in [NEX_PHASE0_VERIFIED_DEFECT_BACKLOG_2026-11-25.md](NEX_PHASE0_VERIFIED_DEFECT_BACKLOG_2026-11-25.md). The list below is its concise summary.

1. **Stale Phase 0 status documents.** The original Reality Report and handoff describe branch/head fb87e24 and pre-continuity status. They need this reconciliation attached and their stale claims explicitly superseded.
2. **Active-branch architecture source gap.** mind_map/MIND_MAP.yaml is absent from the active branch but exists on main. Reconcile branch history and ownership before importing it.
3. **Incomplete crosswalk.** The refreshed v2 crosswalk now includes the first-pass boot wiring and two detailed output paths, but not the full producer/consumer DAG across theory_x, substrate, speech and GUI.
4. **CoherenceGate documentation/authority discrepancy.** Its header says HOLD/RESHAPE are only logged, while current code persists/queues them; evaluation exceptions return ACCEPT; sense distillation explicitly bypasses the gate. Scope and fail-open policy require specification review.
5. **Trace contract mismatch.** Roadmap flag/schema/sample expectations differ from the current InfluenceRecord implementation; Frozen V2.1 and the exact governing roadmap source remain unavailable.
6. **Live trace evidence absent.** No live Fountain/Chat capture, live zero-delta comparison or verified active process identity.
7. **Phase 1 continuity code precedes Gate 0.** The branch contains the default-OFF consumer; the old handoff incorrectly says otherwise. Its semantic edge cases are untested.
8. **Keepalive script path drift.** Systemd unit paths were corrected, but the active branch's script still has the old checkout path in its startup and journal references. Draft PR #97 fixes all references and passed CI; not merged or deployed.
9. **Vitals branch divergence.** Vitals exists on main only, arrived with unrelated behavioural changes, and lacks its governing spec in the available archive.
10. **Branch divergence.** The active branch is 4 ahead / 205 behind main. Integration must be deliberate and file-scoped; no wholesale merge/rebase.

## 7. Safe continuation

- Complete the full-system producer/consumer crosswalk on the active branch, reusing existing source and documenting uncertainty rather than inventing missing nodes.
- Reconcile the missing MIND_MAP source against branch history and the main version before treating either as the active host specification.
- Produce a verified defect backlog with file/line evidence, impact, falsifier, test status and authority boundary.
- Recover the exact Frozen V2.1 specification/approval and the original full roadmap before settling the trace contract or declaring Gate 0 ready.
- Keep the InfluenceRecord overlay default-OFF; do not perform live L4 capture or change its flag without explicit authorisation.
- Keep R79–R83 protected. No experiment, baseline or tripwire changes.
- Keep services untouched until the internal keepalive path correction is reviewed, merged/deployed through the approved process, and a separate activation decision is made.
- Keep Watcher and RDO external to NEX's cognitive runtime.



## 8. External RDO / Watcher progress cross-check

These are development instruments, not NEX cognitive phases or runtime faculties.

- RDO Stage 2–7 PRs #66–#71 all exist as open, draft, stacked pull requests. Their current branch heads match their PR heads, and GitHub Actions completed successfully on each exact head: Stage 2 847af858, Stage 3 c9cb9460, Stage 4 bdeeea60, Stage 5 25e186a8, Stage 6 0693e7f0, Stage 7 a80490ad.
- The current Stage 7 head is a80490ad0336465f0d22172e4cae7b7c273c31ec; this differs from the older Stage 7 hash quoted in the carry-over. The PR body records explicit test-file authorisation, path containment and negative-path tests. It remains draft/unmerged.
- The six RDO PRs form a stacked chain from Stage 2 through Stage 7. CI success verifies the branch test suites; it does not mean the stages are merged, founder-approved, or that their exit criteria requiring reviewed/measurable outcomes are satisfied.
- Watcher PR #96 remains draft and passed CI on exact head 7162e52460c88bedcce75ca04cdb082a2a4b6bd9. It extends the existing host collector with read-only service/timer integrity diagnostics.
- NEX keepalive path portability PR #97 is draft and passed CI on exact head d1b6111c066d1290a6f1725e1ea85d55d665fecf (1612 passed, 5 skipped, 30 subtests). It has not been merged or deployed.
- This Phase 0 reconciliation PR #98 is documentation/comment/log-text only; its latest CI run is still pending at the time of this update.

No RDO or Watcher observations are fed into NEX. No PR above was merged during this cross-check.

**Gate 0 remains PENDING.** This document improves the evidence package; it does not ask the founder to approve Phase 1 and does not treat a general instruction to continue development as Gate 0 sign-off.

## Source audit expansion — 2026-11-25

The current producer/consumer trace has been expanded through §§29–58, with corresponding backlog entries through D-34 and G-21. New highest-priority finding: Harmonizer's successful-synthesis branch reactivates one original conflict belief at Tier 7 after setting it to Tier 8, because it subsequently calls `decisive_contradiction()` which clamps at 7. The existing escalation test checks only row A and does not exercise the synthesis-bridge branch.

The expanded audit also identifies route-specific retired-belief filters, graph propagation through retired nodes, DormancyScanner's fixed oldest-50 selection, VoiceEngine's separate substrate-first Chat path and LLM miss fallback, Fountain's separate retrieval/rendering flags, and non-uniform IntakeResonance coverage. These remain source-level findings; host-effective flags and live DB incidence are unknown.

Residue retention was rechecked against current source: the reaper includes a 2-day residue target, contrary to the old residue module note. The stale note is corrected and an isolated temp-DB test covers the target override.

**No Gate 0 crossing:** Frozen V2.1 specification and founder approval record remain absent from the searched archive/Library sources. No runtime behavior, live DB, service, active experiment, baseline, tripwire, safety/ethics/authority setting or deployment was changed. Founder review remains required before any behavior remediation.


## Governing specification discovery and authority blocker

The repository contains `SPECIFICATION.md` (2026-04-23, “Phase 0 Locked”), which explicitly calls itself the NEX 5.0 Constitution and says it wins over later engineering until explicitly amended. Its Git path history shows one commit and no later amendment. It is not labelled V2.1, so it cannot safely be equated with the Frozen V2.1 spec referenced by the handover.

This April constitution conflicts with current source on Tier 8 meaning, Harmonizer synthesis/deletion semantics, the one-pen rule, and the number of databases. These may be approved later changes, but the exact Frozen V2.1 spec and founder approval record were not found in the searched archive/Library. The source audit therefore records evidence without treating these conflicts as automatically authorized deviations.

Gate 0 remains blocked. Founder must provide or identify the canonical Frozen V2.1 specification and sign-off record, and clarify whether the April `SPECIFICATION.md` remains governing or has been superseded. No behavior changes, spec amendments, live DB changes, service activation, merge or deployment are authorized by the current approval to continue isolated work.


## Additional authority evidence — Doctrine and Faculty Model

The repo's May 9 `theory_x/DOCTRINE.md` remains marked DRAFT awaiting Jon's review/approval; its §7 amendment directs generative node writes through the Faculty Model + Coherence Gate. The May 10 `theory_x/FACULTY_MODEL.md` calls itself foundational and states the universal gate requirement, with an implementation-order note preserving legacy Fountain/Synergizer paths during the initial gate phase. Neither is labelled Frozen V2.1 and no founder sign-off record was found.

Positive implementation cross-check: the reshape path is implemented and tested; HoldingZoneResolver processes up to 10 pending reshape rows, transforms, re-submits through the gate and records success/failure. The unresolved issue is authority/version reconciliation, not missing reshape machinery.


## Source audit continuation — One-Pen and tag-wrapper boundaries

The current source tranche now covers §§60–62 and the verified defect backlog includes D-36/G-24. New evidence: boot-time keystone/koan seeds use raw Writers before TaggingBeliefWriter construction; its .write_many() method passes batches through unchanged; and numerous normal-wired loops, Fountain persistence, Moltbook workers and GUI mutation endpoints write through direct substrate.connect() connections outside the per-database Writer queue. The WorldPredictionLoop is explicitly env-gated, default OFF.

The repository April constitution's One-Pen rule is therefore in direct tension with multiple current source paths. This remains a source-level conformance finding pending exact Frozen V2.1 authority and approved amendments. No live contention, data loss, or host loop activity is inferred. No code or runtime behavior was changed.

PR #98 remains draft. Latest additions are documentation-only. Exact-head CI must be checked against the current branch head before reporting a pass.

## Database contract disconfirmation — 2026-11-25

Owner-authored PR #11 merged on 2026-10-17 explicitly shipped the substrate.connect() factory migration and retired the raw-sqlite import ratchet. tests/test_edges.py enforces absence of raw sqlite3 imports outside substrate, not universal Writer queue use. The direct-connection paths enumerated in trace §§61–62 are therefore not confirmed defects; they are part of the merged connection-factory model. The April SPECIFICATION.md §3 and Writer docstrings still state queue-only semantics, so the current founder-approved transaction/serialization contract remains unresolved. D-36/G-24 have been reclassified. No migration or runtime changes were made.

## Latest source-audit continuation — 2026-11-25 (trace §§63–67)

Disconfirming source history corrected the initial One-Pen finding. Owner-authored PR #11 merged 2026-10-17 and explicitly shipped the substrate.connect() factory migration / retired the raw-sqlite import ratchet. tests/test_edges.py checks raw sqlite3 imports, not universal Writer queue use. Direct-connect paths are therefore not confirmed defects; April SPECIFICATION.md §3 and Writer docstrings remain in conflict with the merged factory model. D-36/G-24 now record contract ambiguity and inventory only.

New candidates: G-25 seven post-Phase-22 life-loop belief producers have no ThoughtPacket/CoherenceGate path; G-26 IdentityLoop/PatternLoop/WitnessLoop beliefs are excluded from Stage 4 INSIDE and Fountain own-content allowlists; G-27 life-loop, boot-seed and optional HotObserver belief writes bypass TaggingBeliefWriter/tag_ops, with a concrete conditional duplicate-tag construction in SurpriseLoop. Each remains bounded to source evidence and policy scope; no behavior change.

Current producer/consumer trace extends through §67. Gate 0 remains pending and exact Frozen V2.1 / founder sign-off remain absent from the searched archive/Library. No live runtime, DB, service or experiment state was touched.

## Active-branch timezone divergence — trace §69

Main commit c247c240f8 (2026-10-26) records the owner decision for Africa/Johannesburg and migrates NEX time handling to NEX5_TZ/local_tz. The active branch still hardcodes Europe/Amsterdam in IdentityLoop, PatternLoop, WitnessLoop and DailyLife, and active nex_config.py lacks the helper. The full migration is cross-cutting; no subset backport or main merge was made. See D-38.

## Recursive self-model feedback source check — trace §68

Current code shows IdentityLog → PatternLoop → PatternLog → WitnessLoop → WitnessLog. IdentityLoop does not read Pattern/Witness content when composing its next statement; only aggregate new-belief count may change. Fountain directly injects IdentityLog, but no Pattern/Witness prompt injection was found. The documented closed L1→L2→L3→L1 semantic feedback is therefore unverified in source. See G-28.

## Final source-tranche update — 2026-11-25 (trace §§68–71)

G-28 records that the documented Identity→Pattern→Witness→Identity semantic feedback is not present in the inspected source; the actual path is a forward chain with aggregate-count feedback. G-29 records SignalToProblem's direct open_problems tags ['auto', 'signal:<type>'] and the dependent advancements_drift debounce query. §71 records the intentional 2026-05-16 disable of CounterfactualNode review_queue auto-promotion and explicitly skipped tests; this is not a missing-producer defect. D-38 records the active branch's missing NEX5_TZ migration from main.

Trace extends through §71. PR #98 remains draft. The last observed workflow run targets an earlier commit and is not an exact-head validation for subsequent docs-only commits.

## Dynamic-loop and boot-wiring continuation — 2026-11-25

The next bounded M0.3–M0.4 increment is complete at static-source level. `NEX_PHASE0_DYNAMIC_LOOP_AND_BOOT_WIRING_AUDIT_2026-11-25.md` inventories 26 conditional Stage 2 loop registrations (9 core, 14 additional life/faculty and 3 Moltbook), six World Model thread wrappers, the delayed Membrane behavioural worker, normal and environment-gated startup loops, constructed-but-request-driven faculties, and the SIGTERM/AppState shutdown boundary. The active source starts daemon workers broadly, but no host thread or environment state was inspected.

The audit confirms that construction, thread-start attempt, a loop body that immediately returns, a service-gated worker, and a request-driven faculty are separate activation states. It also confirms that AppState.close() does not stop/join most workers before SIGTERM's os._exit(0); this is a lifecycle design question, not evidence of a live shutdown failure. See the linked audit for the exact inventory and qualifications.
