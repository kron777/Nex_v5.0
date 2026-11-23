# Repository Status Reconciliation — 2026-11-23

**Type:** Observational documentation / discrepancy register  
**Authority:** This report is not a roadmap, specification amendment, runtime audit or founder decision.  
**Repository snapshot inspected:** `main` at `6e6712bd4bde15ad2288f220cd4438b11622c93c`  
**Purpose:** Prevent dated documents and independent phase-numbering systems from being mistaken for one current project status.

## 1. Executive finding

The repository contains several valid but differently scoped descriptions of progress. They cannot safely be collapsed into one phase number.

- The root `ARCHITECTURE.md` describes the original product/infrastructure sequence as Phases 1–9 and separately describes a Sentience Program track.
- `SENTIENCE_PROGRAM.md` describes its own cognitive research sequence (Phase 0, 1, 2, A, M, S, D, E, T, F).
- The latest founder-provided development handover in the 23 November conversation places authorised NEX work in **Master Roadmap Phase 0: Reality Audit and End-to-End Causal Trace**, with Gate 0 required before Phase 1 behavioural work.
- The master handover, Master Roadmap v3.0, exact Frozen V2.1 specification and founder approval record were not found in the inspected repository tree. Their authority and contents must be retrieved from their actual source before any roadmap or specification decision.

These labels refer to different planning systems. “Phase 9 complete” in `ARCHITECTURE.md` does not establish that Master Roadmap Phase 0 is complete or authorise Phase 1.

## 2. Directly observed discrepancies

| Source | Observed statement | Evidence status | Safe interpretation |
|---|---|---|---|
| `ARCHITECTURE.md` lines 5–7 | Phase 9 complete; problem memory/tool use wired; 189 tests passing | Source text verified; status date/context unclear in header | Historical product-phase summary; test count is not a fresh baseline |
| `ARCHITECTURE.md` lines 11–13 and 551–555 | r77 Chat Workspace armed and mid-measurement on 7 Nov | Source text verified; dated claim | Historical experiment status only; reconcile with later closeout before relying on it |
| `ARCHITECTURE.md` lines 19–20 | 1,987 tests passing as of 7–8 Nov | Source text verified; no fresh run performed here | Historical reported test count, not current CI or baseline |
| `SENTIENCE_PROGRAM.md` lines 54–84 | Its own Phase 0–2 marked implemented/partial | Source text verified; no source/runtime verification in this pass | Internal programme claims; each mechanism still needs current evidence classification |
| `SENTIENCE_PROGRAM.md` lines 86–177 | Phase A/M/S/D/E/T/F are proposed or gated work | Source text verified | This programme's sequencing; not a substitute for the Master Roadmap |
| `SENTIENCE_PROGRAM.md` lines 240–247 | Status summary says Phase 0/1/2 implemented; others next/buildable/gated | Source text verified | Dated internal summary; do not treat as live runtime proof |
| `CORPUS.md` line 7 | Generated 2026-05-22 09:38:59 | Source text verified | Generated snapshot is materially stale relative to November repository state |
| `README.md` lines 73–81 | Research programme and evidence discipline | Source text verified | Useful orientation; not an authoritative phase-status register |

## 3. Important runtime contradiction to resolve

The 7 November `ARCHITECTURE.md` text says r77 (`NEX5_CHAT_WORKSPACE`) was armed and mid-measurement. The later founder-provided 23 November handover reports that the R77 Chat Workspace experiment was disarmed after a tripwire breach and its closeout recorded the decision.

The later report is a strong reason not to repeat the 7 November status as current. However, this reconciliation did not inspect the live host, the exact closeout record, current process environment or experiment database. Therefore the current runtime state remains **UNKNOWN** in this report. Do not arm or disarm any flag based on this note.

## 4. Generated corpus: confirmed staleness and regeneration risk

`CORPUS.md` explicitly says it is generated and must not be hand-edited. Its embedded generation timestamp is 22 May 2026.

`scripts/nexsnap.py` documents that it generates both:
1. `CORPUS.md`; and
2. a timestamped runtime state file under `snapshots/`.

The script's documented `--commit` mode performs Git add/commit/push. A regeneration must therefore use the non-commit invocation unless a separate, explicit commit/push action is intended.

This GitHub-only inspection did not execute the generator. No new corpus or runtime snapshot was fabricated. Before running it, inspect `nexsnap_extract.py` and the runtime DB paths to establish whether the extraction is read-only and whether a host/runtime is required. A repository checkout without the approved host cannot truthfully refresh live-state sections.

## 5. Evidence needed to close the discrepancies

1. Retrieve the actual approved Master Roadmap v3.0, master handover, Cognitive Development Research Framework, RDO specification, Watcher specification, exact Frozen V2.1 spec and founder approval record.
2. Reconcile the 7 November r77 status with the later tripwire/closeout record and actual current host state.
3. Run the approved fresh test-baseline procedure in the intended environment; reconcile every failure against `tests/known_failures.txt`.
4. Verify the implementation and consumers behind the `SENTIENCE_PROGRAM.md` Phase 0–2 claims.
5. Inspect `nexsnap_extract.py` and generator side effects; regenerate `CORPUS.md` only from an appropriate, approved evidence environment.
6. Keep product Phases 1–9, Sentience Program phases, and Master Roadmap phases explicitly distinguished in future status reporting.

## 6. Non-decisions

This report does **not**:
- amend or reorder any roadmap;
- declare any cognitive programme phase complete;
- validate any runtime mechanism;
- authorise Phase 1 behavioural work;
- authorise R77 or any other feature flag;
- authorise a live-host probe, restart, migration or database write;
- replace the governing specifications or founder approval.

---
*Prepared from repository source text and the founder-provided 23 November development handover. Claims not directly verified in source/runtime are explicitly marked as such.*
