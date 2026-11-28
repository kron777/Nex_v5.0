# Reviewed seed proposal → objective intake bridge

**Status:** implemented two-operation bridge. `prepare_reviewed_selection()` is read-only; `submit_reviewed_selection()` is the separate explicit persistence plus advisory-planning operation. Neither automatically creates a Stage-7 handoff or authorizes execution.

## Purpose

The bridge accepts only a proposal with an explicit recorded approval and exposes two intentionally separate operations:

- `prepare_reviewed_selection()` validates the approved selection, prepares a validated `rdo.objective.v1` payload, preserves a separate provenance envelope, and characterizes the selected graph with existing RDO cycle/SCC mechanisms. It is read-only: it appends neither ledger, runs no recursive expansion, creates no CycleRecord or Stage-7 handoff, and executes no work.
- `submit_reviewed_selection()` revalidates the approved selection, persists the objective and its lineage together through the existing objective-intake ledger, and runs the advisory RDO planning cycle. This is explicit persistence/planning, not an automatic side effect of approval or preparation.

The bridge does not automatically create a Stage-7 handoff, execute code, activate rules, or alter live NEX runtime state.

## Mapping

- Raw objective wording, intent, owner, source, scope, acceptance criteria and max depth are retained.
- Raw and selected-alternative constraints, exclusions and assumptions are combined in stable first-seen order without duplicates.
- The selected alternative supplies seed obligations, typed relationships and seed-keyed reconciliation signatures.
- Raw-level reconciliation signatures remain recoverable from the proposal ledger and are included in the returned lineage envelope; they are not incorrectly copied into the selected graph's seed-keyed signature map.
- Seed confidence is copied unchanged. An external-LLM proposal remains inferred; the bridge never upgrades it to stated or measured.
- Acceptance-criterion coverage is retained in the lineage envelope because objective.v1 v1 has no corresponding structured field.

## Two independent revision and digest chains

The raw proposal digest covers only the immutable raw-objective snapshot. The objective-input digest covers the complete validated objective.v1 record, including the selected graph. The bridge returns both and never substitutes one for the other.

The raw objective's supersedes_sha256 remains in the raw lineage. The objective.v1 record's revision and supersedes_sha256 are calculated from ObjectiveInputStore.history(), using the previous complete objective-input digest. Raw revision numbers and intake revision numbers are not assumed to be equal.

The lineage envelope binds the proposal ID, selected alternative, proposer attribution, approval event sequence/hash, acceptance-criterion coverage, and both revision/digest pairs. The read-only preparation API returns it without writing. The explicit intake API stores the envelope beside the objective record in the same objective-ledger append; it does not introduce a second transaction ledger or pretend that two files can be atomically committed.

## Graph diagnostics and bounded uncertainty

The bridge reuses rdo.graph.tarjan_sccs, rdo.tension._find_cycles, _classify_cycle and assess_system. It does not invent another graph or cycle engine.

Simple-cycle enumeration can grow exponentially in a dense strongly connected component. Tarjan SCC discovery remains available for all validated graphs, but detailed cycle enumeration/system assessment is performed only when every cyclic SCC is within the conservative limits of 7 nodes and 18 internal cycle edges. If any cyclic component exceeds either bound, the bridge skips detailed enumeration for the graph and leaves all cycle classifications/system assessments UNKNOWN. If any cyclic component exceeds either limit, the graph result is bounded_unknown; the component is reported without enumerating cycles or claiming a classification. This is an analysis bound, not a graph-size or objective-intake limit.

A depends_on cycle is reported as a prerequisite/build-order cycle. A cycle containing influences is a feedback loop, not automatically a defect. Unknown remains unknown. No edge is removed or rewritten.

## Durable intake and downstream lineage

The follow-on `submit_reviewed_selection()` API is the explicit persistence/planning operation. It re-reads the approved selection, prepares the validated objective.v1 record and lineage, then calls the existing objective intake pipeline.

- `ObjectiveInputStore` keeps objective.v1 unchanged. Its append-only JSONL wrapper accepts an optional, separately validated `lineage` member alongside `record` and `sha256`; legacy two-field wrappers remain readable.
- The objective record and its complete proposal lineage are written in one fsynced objective-ledger append. The proposal ledger is read-only during this operation, so no cross-ledger atomic-write claim is made.
- A retry finds the same proposal ID/alternative in objective history, reuses the same immutable objective revision, and reuses the deterministic CycleStore identity. A conflicting lineage for an existing revision is rejected.
- `CycleRecord.objective_lineage` preserves the exact envelope. `resume_objective()` and objective history expose it.
- Stage-7 `create_handoff()` requires the cycle lineage to match the objective ledger and includes the envelope in the immutable manifest digest. The handoff ID also includes the lineage digest when present.
- This explicit API runs only the advisory RDO planning cycle. It does not automatically create a Stage-7 handoff, authorize code execution, activate rules, or alter NEX runtime state.

The read-only `prepare_reviewed_selection()` remains available for inspection and does not append or plan. Persistence/planning occurs only when the separate `submit_reviewed_selection()` operation is invoked.

## Explicitly not done

- No automatic Stage-7 handoff or scope approval.
- No policy activation, code execution, deployment, runtime action or live NEX write.
- No change to objective.v1 schema, frozen S-01–S-25/M1.8 register or Master Roadmap.
