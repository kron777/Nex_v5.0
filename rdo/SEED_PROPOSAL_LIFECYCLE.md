# RDO candidate seed proposal lifecycle

**Status:** first bounded G-92 increment; advisory proposal/review only.  
**Implementation:** `rdo_adapters/seed_proposals.py`.  
**Tests:** `rdo/tests/test_seed_proposals.py`.

## Purpose and position in the flow

This boundary sits before the existing `objective.v1` intake. It accepts an exact raw-objective revision and multiple competing seed-graph alternatives, then records an explicit review decision. It does not replace the existing intake, Stage-2 recursive extrapolator, Stage-3 graph intelligence, or Stage-7 handoff.

The lifecycle preserves the source request before interpretation. A proposal carries:
- exact raw objective content, intent, revision and SHA-256 lineage;
- multiple distinct alternatives with seed obligations and typed relationships;
- rationale, impact, assumptions, constraints, exclusions, acceptance-criterion coverage, open questions, disconfirming cases and evidence needs;
- proposer kind and source references.

Each acceptance criterion must map to at least one declared seed obligation. External-LLM-derived obligations must remain marked `inferred`; human-authored obligations may be marked `stated`.

## Python API

There is no CLI command or GUI for this first increment. Use the provider-neutral store directly:

```python
from rdo_adapters.seed_proposals import SeedProposalStore

store = SeedProposalStore("rdo/.cycles/seed_proposals.jsonl")
candidate = store.submit(
    raw_objective,
    competing_alternatives,
    proposer_kind="external_llm",  # or "human"
    proposer_reference="provider/model or human source",
    source_reference="source revision/reference",
)
proposal_id = candidate["proposal"]["proposal_id"]

reviewed = store.review(
    proposal_id,
    "approved",  # or "changes_requested", "rejected"
    reviewer="founder",
    source_reference="review record/reference",
    rationale="Why this alternative is or is not accepted.",
    evidence_references=["evidence:one", "evidence:two"],
    selected_alternative_id="the-exact-existing-alternative-id",
)
selection = store.approved_selection(proposal_id)
```

Approval must select exactly one alternative already present in the proposal. Non-approval decisions cannot select an alternative. A proposal can have only one review decision; a revised candidate must explicitly supersede a changes-requested or rejected proposal.

The API returns a selected candidate only through the explicit `approved_selection()` read. Proposer and reviewer labels are caller-attributed and are not identity-authenticated.

## Ledger integrity

The JSONL ledger is append-only through this API, sequence-numbered and SHA-256-linked. It rejects duplicate JSON keys, broken event chains, invalid event shapes, invalid raw-revision lineage, duplicate alternatives/graphs, unknown relationship endpoints, duplicate edges, empty acceptance-criterion coverage, symlinked ledger paths, and bounded-size/event-limit violations.

Appends are serialized with `flock`, validated against the entire prospective ledger while holding the lock, flushed and fsynced. The parent directory is fsynced when the ledger is first created. The hash chain detects inconsistent/tampered records on replay; it is not an authenticated signature system and cannot prove who supplied a proposer or review label.

## Deliberate non-authority

This proposal store does **not**:
- create or update an `objective.v1` intake record;
- run recursive expansion, graph analysis, planning or prioritisation;
- create a Stage-7 handoff;
- execute candidate code, load rules or activate policy;
- write NEX runtime databases, change feature flags, or start/stop services.

An approved candidate is still only a selected proposal. Any later bridge must preserve the exact raw-objective hash and proposal/alternative identity, reconcile the proposed obligations against the existing NEX/RDO architecture, retain competing interpretations and evidence gaps, and require the relevant separate human/authority gates.

## Reuse opportunity for the next increment

The validator currently enforces structural endpoint validity and distinct graph payloads; it does not classify cycles or derive a build sequence. The RDO already has cycle detection/classification in `rdo.tension._find_cycles` and Stage-3 graph intelligence in `rdo.graph`. The next review/bridge increment should reuse those mechanisms to characterize candidate graphs (distinguishing prerequisite cycles from feedback loops) rather than invent a second cycle engine. This analysis should inform review; it must not silently approve, reject or activate a candidate.
