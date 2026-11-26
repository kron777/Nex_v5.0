# Phase 0 M0.5 deliverable-identity reconciliation

**Date:** 26 November 2026  
**Status:** Non-normative source/identity clarification; no specification or roadmap precedence decision.  
**Scope:** Distinguish the two M0.5 deliverables defined in separate founder-supplied project documents.

## Finding

The identifier **M0.5** is used for two distinct deliverables in two separate project sources. Neither requirement should be discarded, renumbered or treated as satisfying the other.

1. **NEX v5.0 Development Proposal V2.1:** M0.5 requires answering six doctrine questions at the level supported by achieved evidence. This is the founder-authored proposal requirement.
2. **NEX v5.0 Master Technical, Research & Commercialization Roadmap v3.0 (20 November 2026):** Phase 0 M0.5 is **“Read-only Causal Pathway Trace.”** Its deliverables are `NEX_CAUSAL_TRACE_SAMPLE.json` and a default-OFF, read-only `InfluenceRecord` hook tracing Input Arrival → Candidate Generation → Salience/Workspace Selection → Gate → SQLite Writer Delta → Output, with a Fountain cycle and a Chat turn, and a zero-mutation comparison with the overlay on/off.

The roadmap source is recorded as `gemini.txt`, supplied in prior project context. The original full roadmap PDF was not located in the inspected archive; this clarification relies on the recovered roadmap extract and does not claim a fresh byte-level comparison against a complete PDF.

The Phase 0 InfluenceRecord/trace-overlay records were correctly using M0.5 in the **Roadmap v3.0** context. The defect was that several crosswalk/status documents did not identify that source, making the roadmap M0.5 easy to confuse with V2.1 M0.5.

## Evidence and status

| Source deliverable | Requirement | Evidence status |
|---|---|---|
| V2.1 M0.5 — six doctrine questions | Answer all six at the achieved evidence level | Not evidenced as complete in the inspected Phase 0 artifacts |
| Roadmap v3.0 Phase 0 M0.5 — Read-only Causal Pathway Trace | Default-OFF read-only trace from input through candidate generation, selection, gate, writer delta and output; capture Fountain and Chat; verify zero mutation with overlay on/off | Fixture-level and coarse seam evidence exists; full causal lineage, requested sample reconciliation and live zero-delta evidence remain incomplete/unknown |

### Roadmap v3.0 trace-overlay evidence

- The overlay remains default-OFF.
- The inspected implementation records two coarse output seams (Fountain and completed Chat turns), not the complete required stage-by-stage causal chain.
- The roadmap asks for `NEX_CAUSAL_TRACE_SAMPLE.json`; the active branch has `docs/phase0_influence_capture_fixture.jsonl`. Naming/schema reconciliation remains outstanding.
- The requested chain through candidate generation, salience/workspace selection, gate decision, SQLite writer delta and output is not demonstrated end-to-end.
- Live L4 capture and live zero-delta comparison have not been performed or authorised.

## Required handling

- Label each deliverable with its source: **V2.1 M0.5** or **Roadmap v3.0 Phase 0 M0.5**.
- Do not use fixture-level trace evidence to claim the six V2.1 doctrine questions are answered.
- Do not use doctrine-question answers to claim the Roadmap v3.0 causal trace is implemented or live-verified.
- Preserve both source requirements exactly. Do not renumber milestones, amend either source, infer precedence, or treat this note as an amendment.
- Keep the frozen S-01–S-25 register unchanged. The full repository SHA and clean/dirty checkout proof belong to the M0.1 baseline capture, not to a newly invented M0.5 requirement.

This note records a cross-document identifier collision and the evidence boundary. It does not amend the frozen register, V2.1 proposal, Master Roadmap v3.0, or runtime.
