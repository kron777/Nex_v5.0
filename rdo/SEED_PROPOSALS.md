# Provider-neutral raw idea and seed proposal lifecycle

## Purpose

RDO's normal `objective.v1` intake requires one or more seed obligations. That is appropriate for planning, but it left a gap between a raw human idea and a reviewed seed graph. This workflow stores an unseeded raw objective, preserves candidate seed-graph alternatives, and requires an explicit review before any candidate can enter planning.

The workflow is provider-neutral. A human, local model, hosted model or another tool can produce the JSON proposal. RDO does not call an LLM provider and does not select an alternative automatically.

## Contracts

- Raw idea: [`raw_objective.v1.schema.json`](schemas/raw_objective.v1.schema.json)
- Candidate proposal: [`seed_proposal.v1.schema.json`](schemas/seed_proposal.v1.schema.json)
- Example: [`seed_proposal.v1.example.json`](examples/seed_proposal.v1.example.json)

A raw objective contains the original wording, intent, owner, source attribution, scope, constraints, exclusions, assumptions, acceptance criteria and maximum expansion depth. It deliberately contains no seed obligations, relationships or reconciliation signatures.

A seed proposal contains 1–8 alternatives. Each alternative supplies a complete candidate seed graph plus:

- a distinct interpretation and rationale;
- assumptions and evidence needs;
- explicit mapping from every acceptance criterion to one or more seed keys;
- open questions and disconfirming cases;
- provenance references.

Each candidate graph is validated by merging it with the raw objective and passing the result through the existing `objective.v1` validator. External-LLM seeds must remain `inferred`; they cannot claim `stated` or `measured` confidence.

## Workflow

1. Create a provider-neutral JSON proposal from the raw idea and candidate alternatives.
2. Submit it with `seed-propose`. This only appends a candidate event; it does not create a CycleRecord or run planning.
3. Review it with `seed-review`. An approval must name exactly one alternative and include reviewer attribution, source reference, rationale and evidence references.
4. Run `seed-intake` with the approved proposal ID. This verifies the approval, creates the corresponding immutable `objective.v1` revision, and only then starts the ordinary RDO planning pipeline.
5. Stage-7 handoff creation carries the seed proposal reference in the handoff manifest. Loading or verifying that handoff rechecks the proposal ledger and selected approval.

Example commands:

```bash
python -m rdo seed-propose \
  --input rdo/examples/seed_proposal.v1.example.json \
  --out rdo/.cycles

python -m rdo seed-list --out rdo/.cycles

python -m rdo seed-review \
  --proposal-id seedprop_<id> \
  --decision approved \
  --reviewer human-reviewer-reference \
  --source-reference review:ticket-or-document \
  --rationale "The selected alternative covers the acceptance criteria." \
  --evidence-reference review:coverage \
  --evidence-reference review:disconfirming-case \
  --selected-alternative-id workflow_first

python -m rdo seed-intake \
  --proposal-id seedprop_<id> \
  --repo . \
  --out rdo/.cycles
```

For a non-approval decision, use `changes_requested` or `rejected` and omit `--selected-alternative-id`. A revised candidate may supersede a candidate that is still pending, changes-requested or rejected, provided it remains bound to the exact same raw-objective hash. An already approved proposal cannot be silently superseded in place; create a new raw-objective revision instead.

## Persistence and integrity

The ledger is stored at `<workdir>/seed_proposals.jsonl`. It is append-only, hash-chained, bounded to 32 MiB and 10,000 events, rejects duplicate JSON properties and refuses symlink paths. Raw-objective revisions cite the exact preceding raw-objective digest. Proposal and review events are independently hash-bound.

The cycle's `objective_input.seed_proposal` reference includes the proposal event digest, raw-objective digest and revision, selected alternative ID and approval-event digest. The handoff manifest carries that reference; RDO handoff loading verifies it against the current ledger and the immutable objective input. Removing or changing the ledger therefore prevents the corresponding handoff from being treated as verified.

Reviewer attribution is caller-supplied and is not authenticated by this local ledger. The ledger proves what was recorded and whether it was altered, not the real-world identity of the reviewer.

## Authority boundaries

- An unreviewed candidate cannot be used by `seed-intake`.
- A direct `intake` call with `source.kind = external_llm` is rejected unless it carries a verified approved seed-proposal reference.
- Approval selects a seed graph for planning only. It does not authorize source edits, tests, runtime changes, deployment or live-system access.
- Novel expansion-kind rule proposals remain separate. PR #352's `approved_for_catalogue` state remains inert and does not mutate `EXPANSION_RULES`.
- Existing human-authored `objective.v1` intake remains compatible.
