# RDO generic objective intake

**Status:** RDO v1.3 §15–16 implementation increment; external/advisory tooling only.

The generic intake interface lets a human or an external language model submit one structured objective without coupling the deterministic RDO engine to a model provider. The RDO validates and preserves the source request, then reuses the existing expansion, reconciliation, graph, OFT, prioritisation and `CycleStore` pipeline.

## Input contract

The machine-readable contract is [`schemas/objective.v1.schema.json`](schemas/objective.v1.schema.json). It is versioned as `rdo.objective.v1`. The Python validator is deliberately stricter in several cross-field checks that JSON Schema alone cannot express.

Required information:

- **Identity and provenance:** `objective_id`, sequential `revision`, `owner`, `source.kind` and `source.reference`.
- **Original intent:** `original_text` retains the original request exactly; `intent` records the submitted interpretation. Both remain immutable across revisions. A genuinely different objective gets a new ID.
- **Scope and limits:** in-scope description, affected repository-relative paths, constraints, exclusions and assumptions.
- **Acceptance:** one or more reviewable acceptance criteria.
- **Initial development network:** seed obligations, their rationale, class, impact, evidence needs, confidence, typed relationships and optional repository-search signatures.
- **Expansion budget:** `max_depth` is bounded from 0 through 4. The caller cannot raise the engine's budget without changing the contract.

A seed obligation must provide a stable canonical key, title, engineering kind, classification, rationale, impact, evidence needs, assumptions and confidence. The evidence-needs field describes what must later be established; it is not evidence that the requirement is already satisfied.

### Evidence and authority boundary

The input does **not** accept reconciliation outcomes, source evidence, semantic-reuse decisions, approvals, gate authorisations, experiment-registry overrides, executable commands or deployment instructions.

- Human-provided seeds may be `stated` or `inferred`.
- External-LLM seeds must be `inferred`. The source reference is preserved in each seed's provenance.
- `measured` confidence is reserved for repository/evidence processing and cannot be asserted by the input author.
- Reconciliation is performed afresh against the selected repository snapshot.
- The active/pending experiment list is obtained through the Watcher registry. Unknown registry state remains fail-closed; the input cannot claim that the registry is empty.
- Work-package eligibility is advisory. The intake does not approve or execute any work.

## Commands

Submit one objective:

```bash
python -m rdo intake --input objective.json --repo . --out rdo/.cycles
```

Inspect immutable input revisions and the fields changed between them:

```bash
python -m rdo history --objective-id belief-decay-review --out rdo/.cycles
```

Reload the exact input revision and all persisted RDO cycles generated from it in a later process:

```bash
python -m rdo resume --objective-id belief-decay-review --revision 1 --out rdo/.cycles
```

The resume command retrieves the preserved input and completed planning records; it does not continue execution or grant approval.

## Revision behaviour

Input revisions are append-only JSON Lines under:

`rdo/.cycles/objectives/<objective_id>.jsonl`

Revision 1 uses `supersedes_sha256: null`. Each later revision must name the SHA-256 digest of the immediately preceding revision. Replaying identical revision content is idempotent; attempting to rewrite an existing revision is rejected. The original request text and its declared intent cannot be rewritten. Changes to scope, constraints, assumptions, acceptance criteria or seed content are recorded as a new revision, and the history command reports the changed top-level fields.

Each completed cycle stores a reference to the objective ID, input revision, canonical input digest and repository commit SHA. Cycle identity is deterministic for the objective revision and repository commit. The full objective revision remains in the append-only input ledger.

## Snapshot and reconciliation requirements

The selected repository must be a clean Git working tree with a full identifiable commit SHA. Dirty, untracked or unidentified repository state is rejected rather than being presented as a stable snapshot. Reconciliation signatures are bounded to repository-relative paths and read-only grep patterns. A signature hit is a source anchor, not semantic proof that a mechanism satisfies an obligation.

## Minimal example

See [`examples/objective.v1.example.json`](examples/objective.v1.example.json). It is an illustrative schema example, not a pre-approved NEX objective and not a command to change NEX.

## Scope

This is an external RDO intake increment. It creates files only in the RDO objective/cycle store and reads the selected repository snapshot. It does not modify NEX cognitive/runtime source, live databases, experiment registrations, baselines, tripwires, flags, services or deployment state. It does not invoke Claude Code, pytest or arbitrary commands.
