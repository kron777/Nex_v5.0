# Reviewed seed proposal → objective intake bridge

**Status:** first read-only preparation increment; no persistence or RDO cycle execution.

## Purpose

The prepare_reviewed_selection() function accepts only a proposal that SeedProposalStore.approved_selection() confirms has an explicit recorded approval. It prepares a validated rdo.objective.v1 payload, preserves a separate provenance envelope, and characterizes the selected graph with existing RDO cycle/SCC mechanisms.

The function is deliberately read-only. It reads the proposal ledger and objective-intake history, but it does not append either ledger, call submit_objective(), run recursive expansion, create a CycleRecord, create a Stage-7 handoff, or execute work.

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

The returned lineage envelope also binds the proposal ID, selected alternative, proposer attribution, approval event sequence/hash, acceptance-criterion coverage, and both revision/digest pairs. It is a returned preparation artefact in this increment, not yet a durable bridge ledger.

## Graph diagnostics and bounded uncertainty

The bridge reuses rdo.graph.tarjan_sccs, rdo.tension._find_cycles, _classify_cycle and assess_system. It does not invent another graph or cycle engine.

Simple-cycle enumeration can grow exponentially in a dense strongly connected component. Tarjan SCC discovery remains available for all validated graphs, but detailed cycle enumeration/system assessment is performed only when every cyclic SCC is within the conservative limits of 7 nodes and 18 internal cycle edges. If any cyclic component exceeds either limit, the graph result is bounded_unknown; the component is reported without enumerating cycles or claiming a classification. This is an analysis bound, not a graph-size or objective-intake limit.

A depends_on cycle is reported as a prerequisite/build-order cycle. A cycle containing influences is a feedback loop, not automatically a defect. Unknown remains unknown. No edge is removed or rewritten.

## Explicitly not done

- No objective-input ledger append.
- No call to submit_objective() and no RDO expansion/reconciliation/planning cycle.
- No work-package generation, Stage-7 handoff, policy activation or execution.
- No schema-v1 change and no change to the frozen S-01–S-25/M1.8 register or Master Roadmap.

A later increment may add a separately authorized durable bridge ledger and explicit append/recovery protocol. That work must handle the fact that two append-only ledgers cannot be updated atomically by a single filesystem append; it must not silently assume cross-ledger atomicity.
