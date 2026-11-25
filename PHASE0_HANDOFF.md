# Phase 0 — Current Durable Handoff

**Date:** 25 November 2026
**Primary repository:** https://github.com/kron777/Nex_v5.0
**Active host checkout:** /mnt/games/storage/Desktop/Desktop/nex5
**Active host branch:** claude/nex-continuity-wire
**Active host HEAD:** de93134f34adac07a3a41c2a05b33720510a2bfc
**Worktree:** host collector reported clean at this SHA.

The earlier fb87e24 handoff is preserved as PHASE0_HANDOFF_HISTORICAL_fb87e24.md. Use this document together with:
- NEX_REPOSITORY_REALITY_REPORT.md — current M0.1–M0.2 report.
- NEX_ARCHITECTURE_CROSSWALK_v2.md — current partial crosswalk: boot inventory plus Fountain and Chat output paths.
- NEX_PHASE0_CURRENT_RECONCILIATION_2026-11-25.md — branch comparison, M0.1–M0.5 status, boot wiring, Vitals, RDO/Watcher status and remaining gaps.
- NEX_PHASE0_VERIFIED_DEFECT_BACKLOG_2026-11-25.md — founder-reviewable verified defects and evidence gaps.
- ADR-001.md — historical design decision for the default-OFF InfluenceRecord overlay.

## Current Phase 0 position

| Item | Status |
|---|---|
| M0.1 repository identity | Exact active host URL, branch, SHA and clean-worktree report recorded |
| M0.1 host/model/runtime baseline | Partial; DB/snapshot hashes, Python/SQLite exact versions, model digest, RAM/VRAM load and tokens/sec remain UNKNOWN |
| M0.2 test baseline | Founder-provided host run: 1610 passed, 5 skipped, 30 subtests, 0 unexpected failures, 122.87s |
| M0.3–M0.4 architecture crosswalk | Partial; first-pass boot wiring plus two output paths. Full producer/consumer DAG across theory_x, substrate, speech and GUI remains outstanding |
| M0.5 InfluenceRecord | Default-OFF source and fixture tests exist; two coarse seams only |
| M0.5 live L4 capture / zero-delta | UNKNOWN; not performed or authorised |
| Gate 0 | PENDING founder review |

## Important current findings

1. Active host branch de93134 is 4 commits ahead and 205 behind main. Do not merge/rebase main wholesale.
2. The active branch contains Phase 1 continuity code from f9ac58d. The flag defaults OFF; live activation and behavioural effect are UNKNOWN. Do not arm it before Gate 0 and explicit approval.
3. The actual sense scheduler starts external feeds during construction. It has 28 adapters (4 internal, 24 external). Documentation was stale and is corrected in the current reconciliation PR; no scheduler logic was changed.
4. CoherenceGate's module header understates current HOLD/RESHAPE handling; evaluation exceptions return ACCEPT; sense distillation explicitly bypasses the gate. These scope/failure-policy questions are in the defect backlog; do not change them without the governing spec and founder review.
5. The four active user service units were corrected to the actual checkout path and passed systemd syntax verification, but no service was started. nex_keepalive.sh still has the old internal path in the active branch. Draft PR #97 fixes it and passed CI, but is not merged/deployed.
6. Vitals is present on main but absent from the active branch; cherry-picking its merge would import unrelated behaviour. Its exact governing spec and PID-identity safeguards remain unresolved.
7. The exact Frozen V2.1 source document and founder approval record have not been located. Do not recreate them or infer their detailed acceptance criteria.

## M0.5 trace discrepancy

The roadmap extract asks for NEX5_TRACE_OVERLAY=0 and a full trace_id/parent_ids chain across input arrival, candidate generation, salience/workspace selection, gate, SQLite writer delta and output, with NEX_CAUSAL_TRACE_SAMPLE.json. The active branch instead uses NEX5_INFLUENCE_TRACE, NEX5_INFLUENCE_TRACE_CONTEXT and NEX5_INFLUENCE_TRACE_PATH, with two coarse seams and a JSONL fixture. The exact Frozen V2.1 contract must be recovered before extending or renaming the hook.

## Current external PR status

- Watcher service integrity PR #96: draft; exact-head CI passed.
- Keepalive path portability PR #97: draft; exact-head CI passed (1612 passed, 5 skipped, 30 subtests). Not merged/deployed.
- Phase 0 reconciliation PR #98: draft; CI status is tracked on the PR. Documentation/comments/log text only; no execution/control-flow changes.
- RDO Stage 2–7 PRs #66–#71: open/draft, stacked, exact-head CI passed; not merged and not NEX roadmap phases.

## Safety and authority

- Gate 0 is not complete until the founder reviews and approves the current Reality Report, Crosswalk and verified defect backlog.
- A general instruction to continue development is not treated as Gate 0 sign-off.
- Do not start/restart services, activate NEX, change runtime flags, write live DBs, perform live trace capture, or change protected experiments/baselines/tripwires without the relevant explicit approval.
- Protect experiment windows R79–R83.
- Keep RDO and Watcher external to NEX's cognitive runtime.
- Do not claim consciousness, sentience or phenomenal experience.

## Next safe work

Continue the full forward/backward producer-consumer audit in bounded increments, beginning with the booted paths and their actual persistence/consumer relationships. Recover the exact Frozen V2.1 source/approval and reconcile the M0.5 trace contract. Keep live runtime and protected experiment state untouched. Review PR #97 and PR #98 independently; neither is permission to activate services or Phase 1 behaviour.

## Current handoff addendum — 2026-11-25 source audit

The latest source-trace tranche and verified defect backlog are expanded; see the canonical Crosswalk and `NEX_PHASE0_PRODUCER_CONSUMER_TRACE_TRANCHE_2026-11-25.md`. A confirmed control-flow defect is recorded at D-32: Harmonizer's successful-synthesis branch demotes one just-retired original from Tier 8 back to Tier 7. No fix has been applied because Gate 0 has not been approved.

The current audit also records retired-row filter gaps across Fountain/VoiceEngine/reanimation/graph paths, a DormancyScanner scan-progress issue, VoiceEngine's separate substrate-first reply path, and non-uniform IntakeResonance measurement across producers. Residue retention documentation now matches the reaper's 2-day target, with an isolated temp-DB test added.

**Founder help is now required to proceed from evidence into remediation:** provide the exact Frozen V2.1 specification and the founder approval/sign-off record for Gate 0 (or point to their canonical Library paths). The archive and Library searches returned the handover/roadmap references but not those governing artifacts. Until then, continue read-only source analysis and isolated tests only; do not implement behavior changes, change flags, run live retention, merge, deploy or activate services.


## Founder clarification required — governing specification version

The repo contains `SPECIFICATION.md`, dated 2026-04-23 and marked “Phase 0 Locked”. It calls itself the NEX 5.0 Constitution and says it wins over later engineering until explicitly amended; its Git path history shows no later amendment. It is not labelled Frozen V2.1. It conflicts with current code on Tier 8 meaning, Harmonizer synthesis/deletion behavior, the one-pen rule, and the database inventory.

The exact Frozen V2.1 document and founder Gate 0 approval record were not found in the searched archive/Library. The April constitution may have been superseded, but that cannot be inferred.

**Please provide or point me to the canonical Frozen V2.1 specification and Gate 0 founder sign-off record, and clarify whether the April `SPECIFICATION.md` remains governing or was superseded.** Until then, no behavior remediation, spec edits, live DB writes/retention, flag changes, service activation, merge or deployment.


## Governing stack clarification

The repository contains three relevant layers: April `SPECIFICATION.md` (Phase 0 Locked, self-described Constitution), May `theory_x/DOCTRINE.md` (DRAFT awaiting Jon's review/approval, with a §7 gate amendment), and May `theory_x/FACULTY_MODEL.md` (foundational, universal gate requirement, legacy-path implementation note). None is labelled Frozen V2.1, and the exact Frozen V2.1 artifact / founder sign-off remain missing from the searched archive/Library.

The reshape path is implemented and covered by `tests/test_reshape.py`; it is not an outstanding missing mechanism. The unresolved blocker is which specification layer has founder approval and governs the current source.


## Current source-audit continuation — 2026-11-25

The producer/consumer tranche now extends through §§60–62. It records (a) boot-time keystone/koan seeds created before TaggingBeliefWriter is constructed, (b) the limited scope of the wrapper's single-statement .write() interception, and (c) direct write-capable substrate.connect() paths outside the One-Pen Writer queue.

The direct-connection census includes normal-wired Stage 2 life/focus/daily-life/signal loops, Fountain's recursion_attrib write, and normal-wired Moltbook listener/responder/poster paths; it also identifies request-driven GUI mutation endpoints. The WorldPredictionLoop is separately env-gated by NEX5_WORLD_PRED=1 (default OFF). These are source-wiring findings, not proof of live thread activity, endpoint invocation, external client readiness, contention or data loss. See backlog D-36/G-24.

TaggingBeliefWriter does not provide a universal admission chokepoint: boot seeds use raw Writers before wrapper construction, .write_many() passes through unchanged, and direct SQLite paths bypass it. This is an instrumentation boundary, not automatic authority to route every seed or observation through CoherenceGate.

PR #98 remains draft. The new additions are documentation/evidence only; no runtime code, DB, flags, services, experiments, baselines or tripwires were changed. Exact-head checks must be re-read before claiming CI status for the latest docs commits.

Gate 0 remains pending. Continue bounded read-only source tracing and isolated fixtures only. Normative remediation remains blocked on founder identification of the exact Frozen V2.1 specification and Gate 0 approval record, and clarification of whether April SPECIFICATION.md remains governing.

## Database contract clarification — merged October migration

Source-history review found owner-authored PR #11 merged 2026-10-17. It explicitly shipped the substrate.connect() factory migration across roughly 95 modules and retired the raw-sqlite import ratchet. The current test named TestNoDirectSqlite checks only for raw sqlite3 imports outside substrate; it does not enforce Writer.write() for every write. Direct substrate.connect() paths are therefore intentional under that merged migration and are not automatically defects.

The April SPECIFICATION.md §3 and substrate/writer.py docstring still describe a stronger universal Writer-queue rule. The exact founder-approved transaction/serialization contract is unresolved; do not migrate direct connections back to Writer or assume substrate.connect() serializes callers. See trace §64 and reclassified backlog D-36/G-24.