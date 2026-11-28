# RDO candidate seed proposal lifecycle

**Status:** implemented G-92 proposal/review lifecycle plus the separate reviewed-selection bridge. Proposal approval remains advisory; `seed-prepare` is read-only and `seed-intake` explicitly persists objective lineage and runs advisory planning.  
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

## CLI and Python API

The provider-neutral store is exposed through `seed-propose`, `seed-review`, `seed-history` and `seed-selection`. The reviewed-selection bridge adds `seed-prepare` and `seed-intake`. The Python API remains available for integrations:

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

This proposal store itself does **not**:
- create or update an `objective.v1` intake record;
- run recursive expansion, graph analysis, planning or prioritisation;
- create a Stage-7 handoff;
- execute candidate code, load rules or activate policy;
- write NEX runtime databases, change feature flags, or start/stop services.

An approved candidate is still only a selected proposal until the separate reviewed-selection bridge is explicitly invoked. That bridge preserves the exact raw-objective hash and proposal/alternative identity, maps the selected graph into objective.v1, retains competing interpretations and evidence gaps in lineage, and keeps the relevant human/authority gates separate.

## Reused graph-analysis mechanisms

The reviewed-selection bridge adapts validated proposal edges into the existing `Relationship` model and reuses `rdo.graph.tarjan_sccs`, `rdo.tension._find_cycles`, `_classify_cycle` and `assess_system`. The classifier distinguishes `prerequisite_cycle`, `feedback_loop` and `unknown`: prerequisite cycles are build-order blockers, while influence feedback loops are not automatically defects. Enumeration is bounded per cyclic SCC (7 nodes / 18 internal cycle edges); if any cyclic SCC exceeds either bound, detailed classifications and system assessments remain UNKNOWN. This analysis informs the explicit review/intake path; it does not silently approve, reject or activate a candidate.


## Integration contract and resolved bridge into objective.v1

The existing objective intake already accepts nearly the same source/context fields and the same seed-obligation/relationship structures. A naive dictionary copy is nevertheless unsafe because the two ledgers have distinct identities and provenance:

1. **Two different digests.** The proposal store's `raw_objective_sha256` hashes only the immutable raw objective. `ObjectiveInputStore` hashes the full validated `objective.v1` record, including the selected seed graph. These hashes are expected to differ and must never be substituted for one another.
2. **Two revision chains.** The proposal's `raw_objective.supersedes_sha256` links raw-objective revisions. The intake record's `supersedes_sha256` links complete objective-intake revisions. They are separate chains with separate meanings.
3. **Proposal provenance is not in objective.v1 v1.** The current schema has `additionalProperties: false` and no structured fields for `proposal_id`, `selected_alternative_id`, `proposer_kind` or `raw_objective_sha256`. Adding these directly to v1 would be rejected; a schema change requires a deliberate versioned contract.
4. **Raw source and seed proposer are distinct.** The raw objective may originate from a human while its candidate seed graph was generated by an external LLM. The proposal store records both identities separately and enforces that external-LLM seed confidence remains `inferred`. Objective.v1's `source.kind` alone cannot represent both facts.

The original bridge design question was how to carry a stable, machine-readable cross-reference from the objective intake record back to the proposal, selected alternative, raw-objective digest and review event without changing objective.v1. This is now resolved by the v2 lineage envelope: the complete approval event is hash-verified and stored beside the objective record in the objective-ledger wrapper. The raw and objective-input digest/revision chains remain independent; the original raw-source reference is preserved; inferred external-LLM seed confidence is not promoted.

The mapping preserves the raw objective's exact wording, intent, owner/source, scope, constraints, exclusions, assumptions, acceptance criteria and depth. The read-only preparation operation returns a candidate after explicit selection. A separate explicit intake operation persists it and runs advisory planning; neither operation automatically creates a Stage-7 handoff or authorizes execution. Regression coverage now checks both digest chains, approval-event integrity, replay and downstream lineage.


## Reviewed-selection bridge

The bridge has two separate operations, documented in REVIEWED_SEED_BRIDGE.md. `prepare_reviewed_selection()` is read-only and returns a validated objective.v1 candidate plus approval-event and dual-chain lineage. `submit_reviewed_selection()` is the separate explicit persistence/planning operation: it writes the objective and lineage together in the objective ledger and runs advisory RDO planning. Neither operation automatically creates a Stage-7 handoff or authorizes execution.


## Durable reviewed intake and lineage propagation

The reviewed-selection bridge now has two deliberately separate operations:

- `prepare_reviewed_selection()` is read-only. It validates an explicit approval, maps the selected alternative into objective.v1, and returns graph diagnostics plus the dual-chain lineage envelope.
- `submit_reviewed_selection()` is the explicit persistence/planning operation. It writes the validated objective and lineage together in one objective revision-ledger wrapper, then invokes the existing advisory RDO cycle pipeline.

The objective.v1 schema remains unchanged. The optional wrapper-level `lineage` field is validated against the objective ID/revision/digest and approval record; legacy `{record, sha256}` entries remain compatible. The lineage is copied into `CycleRecord.objective_lineage`, survives `resume_objective()`, and is included in the Stage-7 immutable manifest. Repeating the same approved selection is idempotent; a different lineage for the same stored revision is rejected.

Planning does not automatically create a Stage-7 handoff or authorize execution. Scope review, delivery verification, human acceptance and any later execution remain separate boundaries.
