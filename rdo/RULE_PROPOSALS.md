# Novel-kind expansion rule proposals

The Recursive Extrapolator deliberately stops when it reaches an obligation kind
for which no expansion rule exists. The frontier item includes a
`rule_proposal_request`; it is a request for further engineering reasoning, not
permission to invent and execute a decomposition.

This module adds a governed lifecycle around that request:

1. Propose one or more competing decompositions.
2. Preserve assumptions, applicability, preconditions, exceptions,
   anti-requirements, evidence needs, disconfirming cases, provenance and both
   positive and negative test declarations.
3. Record a caller-attributed review decision in an append-only, hash-chained
   event ledger.
4. Only an explicit approval selecting one alternative adds that rule to the
   versioned approved catalogue.
5. A later objective cycle must explicitly select each approved rule kind. No
   approved rule is silently activated for every future objective.

PatternMemory remains a defeasible lesson store. Repeated observations,
corroboration counts or confidence values never promote an expansion rule.

## Candidate JSON contract

A proposal contains exactly these fields:

- `target_kind`: the novel obligation kind to decompose.
- `source_obligation`: the originating obligation (`key`, `title`, and
  matching `kind` are required).
- `alternatives`: 1–8 competing decompositions. Each alternative has a
  portable `id`, a description, and 1–32 steps. Each step specifies
  `child_kind`, `classification`, `rationale`, and optional
  `shared_target`.
- `assumptions`, `applicability`, `preconditions`, `exceptions`,
  `anti_requirements`, `evidence_needs`, `disconfirming_cases`,
  `provenance`, `positive_tests`, and `negative_tests`: lists of
  non-blank text references/descriptions. Applicability, provenance,
  disconfirming cases, and both test lists must be non-empty.

Example shape:

```json
{
  "target_kind": "specialized_deployment",
  "source_obligation": {
    "key": "deployment.specialized",
    "title": "Specialized deployment mechanism",
    "kind": "specialized_deployment"
  },
  "alternatives": [
    {
      "id": "environment_first",
      "description": "Validate the target environment before packaging.",
      "steps": [
        {
          "child_kind": "environment_check",
          "classification": "necessary",
          "rationale": "The target environment must be known.",
          "shared_target": null
        }
      ]
    }
  ],
  "assumptions": ["The target environment is supplied by the owner."],
  "applicability": ["Only objectives explicitly requesting this deployment kind."],
  "preconditions": ["A target environment has been identified."],
  "exceptions": ["Do not apply to documentation-only releases."],
  "anti_requirements": ["Planning must not deploy."],
  "evidence_needs": ["A source-backed environment description."],
  "disconfirming_cases": ["A deployment with no controllable target environment."],
  "provenance": ["frontier:cycle-id:deployment.specialized"],
  "positive_tests": ["tests/test_deployment_rule.py::test_environment_first"],
  "negative_tests": ["tests/test_deployment_rule.py::test_docs_only_not_decomposed"]
}
```

## CLI workflow

Create a candidate. This does not activate it:

```bash
python -m rdo rule-propose --input candidate-rule.json --dir rdo/.cycles
```

Review it. For approval, select exactly one declared alternative and provide
review evidence for every declared positive and negative test:

```bash
python -m rdo rule-review \
  --proposal-id <proposal-id> \
  --decision approved \
  --selected-alternative environment_first \
  --reviewer "reviewer attribution" \
  --source-reference "reference to the approval decision" \
  --evidence-reference "reference to the scope review" \
  --positive-test-evidence "tests/test_deployment_rule.py::test_environment_first" \
  --negative-test-evidence "tests/test_deployment_rule.py::test_docs_only_not_decomposed" \
  --dir rdo/.cycles
```

The other decisions are `rejected` and `changes_requested`. A rejected
proposal is terminal. A changes-requested proposal can receive another review.
An approved proposal is terminal; changing it requires a new proposal and review.

Inspect the approved catalogue:

```bash
python -m rdo rule-catalogue --dir rdo/.cycles
```

Explicitly opt a future objective cycle into an approved kind:

```bash
python -m rdo intake --input objective.v1.json \
  --approved-rule-kind specialized_deployment \
  --out rdo/.cycles
```

Repeat `--approved-rule-kind` to select more than one approved kind. The
default ledger is `<out>/rule_proposals.jsonl`; use `--rule-proposals` to
select another ledger.

The selected catalogue version and digest are recorded in the CycleRecord and
objective-input metadata, and the digest participates in cycle identity. A
cycle planned with a different approved catalogue cannot accidentally reuse a
cycle produced with an earlier one.

## Boundaries and evidence

- Built-in expansion kinds and terminal kinds cannot be overridden.
- A candidate or a changes-requested/rejected proposal never enters the
  approved catalogue.
- Approval requires a selected alternative, reviewer/source attribution,
  general evidence references, and references for all declared positive and
  negative tests.
- The RDO records those references; it does not execute candidate tests as part
  of approval. Independent test execution/verification remains a separate
  explicitly authorised Watcher operation.
- Reviewer identity is caller-attributed, not authenticated by this ledger.
- Applicability and preconditions are preserved as human-review constraints,
  not guessed by a lexical classifier. Selecting an approved kind for a cycle
  is an explicit caller decision; inspect the catalogue's scope and exceptions
  before doing so.
- The append-only ledger is hash-chained and fsynced. This detects accidental
  alteration; it is not a signature or protection against an actor able to
  rewrite the entire store.
- New child kinds that have no approved or built-in rule remain visible on the
  frontier. Approval of one rule does not recursively approve its descendants.
- No NEX runtime, database, feature flag, experiment, host state, deployment,
  frozen S-01–S-25/M1.8 specification or Gate 0 decision is changed.
