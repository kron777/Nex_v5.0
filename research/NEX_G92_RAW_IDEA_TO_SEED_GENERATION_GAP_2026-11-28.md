# G-92 raw-idea-to-seed generation boundary audit

**Date:** 28 November 2026  
**Status:** source-bounded research; no provider or generation architecture selected  
**Scope:** RDO candidate seed proposal intake only. This note does not change the frozen S-01–S-25/M1.8 register, Master Roadmap, Phase 0/Gate 0, objective.v1, review authority or runtime behavior.

## Finding

The candidate seed proposal and reviewed-intake lifecycle is implemented. The upstream transformation from a free-form raw idea into a complete `raw_objective` plus competing seed-graph alternatives is not implemented in the current CLI path.

This distinction matters: the current `seed-propose` command is a structured proposal **ingestion, validation and persistence** command. It is not a raw-idea parser and it does not invoke a model provider.

## Source evidence

1. **CLI input is already structured.** `rdo/__main__.py::_seed_propose()` (current main, lines 300–322) opens the supplied JSON file, rejects duplicate keys, requires `raw_objective`, `alternatives`, `proposer_kind`, `proposer_reference` and `source_reference`, then calls `SeedProposalStore.submit()`. It does not call a model/provider or derive alternatives from `original_text`.

2. **The raw-objective contract is complete, not free-form.** `rdo_adapters/seed_proposals.py::validate_raw_objective()` (lines 112–181) requires schema version, portable objective ID, revision and supersession digest, original text, intent, owner, source kind/reference, scope, constraints, exclusions, assumptions, acceptance criteria, reconciliation signatures and maximum depth. The command expects this structured object to exist before proposal submission.

3. **The candidate graph is supplied by the caller.** `_validate_proposal()` (lines 326 onward) requires 2–12 alternatives, distinct alternative IDs, distinct interpretations and distinct seed graphs. Each alternative contains the seed obligations, typed relationships, reconciliation signatures, assumptions, constraints, exclusions, acceptance-criterion coverage, open questions, disconfirming cases and evidence needs. The validator checks these; it does not generate them.

4. **The store persists; it does not generate.** `SeedProposalStore.submit()` (lines 616–639) validates the supplied raw objective and alternatives, checks proposal identity/supersession against the existing ledger, appends `proposal_submitted`, and returns the proposal. The provider/human is upstream of this call.

5. **External-model uncertainty is preserved.** `_validate_seed_list()` requires every external-LLM-derived seed obligation to have `confidence: "inferred"`. Proposer and reviewer labels remain caller-attributed, not identity-authenticated. The review API separately requires explicit approval to select one existing alternative.

6. **The downstream bridge is already separate.** The reviewed-selection bridge exposes read-only `seed-prepare` and explicit `seed-intake` (persistence plus advisory planning). Neither is an implicit side effect of generation or approval; neither automatically creates a Stage-7 handoff or execution authority.

## Exact remaining gap

No current `seed-propose` path accepts only a raw idea and then produces the structured raw-objective record and competing alternatives. No provider invocation is present in the inspected seed-proposal CLI/store path. The existing provider-neutral schema is suitable as a receiving contract, but the generation boundary is still a human or external-provider handoff.

This is not a missing review lifecycle, missing proposal ledger, or missing objective-intake bridge. Those are already implemented and must not be re-created.

## Provisional implementation directions

These are options for further research, not frozen decisions:

1. **Offline prompt/contract builder.** Accept a raw idea and caller-supplied identity/provenance metadata, then emit a provider-neutral prompt requesting the exact `seed-propose` JSON shape. No network, credentials or automatic submission. The generated response is still validated by `SeedProposalStore.submit()`.
2. **Injected provider protocol.** Define a small provider-neutral interface returning a structured draft; keep provider implementations outside the core RDO store. This provides a testable seam but is not useful by itself until an adapter is supplied.
3. **Explicit provider adapter.** Add a concrete local or remote provider only after the provider, model, credential handling, context exposure and data-egress policy are explicitly selected. External calls must never happen implicitly merely because `seed-propose` is invoked.

The safest first increment appears to be an offline prompt/contract builder because it standardizes the upstream request without selecting a provider or transmitting raw ideas. That is a provisional recommendation, not an architecture commitment.

## Required invariants for any future generator

- Preserve the raw idea verbatim in `raw_objective.original_text`; do not silently rewrite the source.
- Separate facts stated by the author from model-inferred intent, scope, constraints, assumptions and acceptance criteria.
- Produce genuinely competing alternatives, not cosmetic paraphrases or duplicate graphs.
- Preserve open questions, disconfirming cases and evidence needs; do not invent source citations or claim repository facts without evidence.
- Keep all external-LLM seed confidence `inferred`.
- Generation creates only an unreviewed candidate. It cannot approve, select, intake, plan, create a Stage-7 handoff, execute, activate rules or change NEX runtime state.
- Human review remains explicit; `seed-intake` remains a separate explicit persistence/advisory-planning operation.
- Any external provider call requires explicit opt-in to the provider and the data being sent. No credentials or outbound network should be added to the core proposal store.

## Observe / next research

Before implementation, compare the offline prompt contract against the exact validator fields and limits, then test representative raw ideas that are ambiguous, underspecified, multi-domain and potentially contradictory. Include a case where the provider must return questions/assumptions rather than fabricate affected paths or evidence. Revisit provider choice only after this contract is stable enough to test.

No source, schema, provider, credential, runtime or authority changes are made by this audit.
