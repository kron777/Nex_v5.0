# NEX Recursive Development Orchestrator (RDO)

An **external, advisory** engineering system that turns Watcher evidence into
bounded development decisions. It discovers the development network hidden inside
an idea, reconciles it against the **real** codebase, assesses it for Optimal
Functional Tension, and proposes bounded work — then learns from what actually
happens.

It is **not** a NEX cognitive faculty and **not** a replacement for the Watcher.

## The separation it preserves

| Layer | Role | This package |
|---|---|---|
| **NEX** | the cognitive architecture (`theory_x` / `substrate`) | never imported |
| **Watcher** | read-only NEX observation; writes its own evidence artefacts | **consumed** (reuses `watcher.evidence`, `watcher.registry`; independent source/path verifier) |
| **RDO** | development reasoning, planning, learning | **this package** |
| **Claude** | engineering execution (bounded, authorised) | acts on RDO output |
| **Human** | objectives & consequential decisions | approves gated work |

`ADVISORY_ONLY = True`: the RDO proposes work packages; it never changes NEX.
Nothing here imports `theory_x` or `substrate` (enforced by a test).

## The cycle

```
IDEA → RECURSIVE EXPANSION → RECONCILIATION → DEDUPLICATION →
RELATIONSHIP MAPPING → OPTIMAL FUNCTIONAL TENSION → PRIORITISATION →
WORK PACKAGE → EVIDENCE ACCOUNTING → (persist) → LEARN
```

- **Expansion** (`extrapolator.py`) — a small seed of obligations expands via
  generic engineering rules (a persistence obligation implies a schema, a write
  path, provenance, a test…). Recursion is **bounded**: depth cap, terminal
  kinds, and — crucially — a source-signature match alone does **not** stop
  expansion. Expansion stops only after explicit semantic-satisfaction review.
  Convergent branches merge; every stop records its reason.
- **Reconciliation** (`reconcile.py`) — each obligation with a *signature* is
  checked against text-readable source files in the **actual tree** (read-only grep; the ignored `rdo/.cycles` output directory is excluded so prior RDO plans cannot become their own source evidence):
  all configured signatures match → `signature_matched`; some → `partial`; none in a completed
  scan → `missing`; unavailable scan/no signature → `unknown`. A signature hit
  is a source anchor, not proof that the full obligation is satisfied. Necessary
  obligations remain readiness-unknown until a separate semantic review decision
  and its traceable review-evidence reference are both recorded. Candidate dependency pruning also requires that separate
  semantic review; signature matches alone do not remove prerequisite work.
- **Optimal Functional Tension** (`tension.py`) — node / relationship / system
  assessment. Not a single score: every verdict is evidence-backed or explicitly
  marked `inference`. It also **recognises when further development is not
  justified** (restraint is half the principle) and flags *capability ≠
  authority* (a signal consumed by many subsystems is an influence-authority
  risk).
- **Prioritisation** (`prioritise.py`) — two stages: a hard **eligibility** gate
  (protected experiments, unbuilt dependencies, and active behavioural changes
  that need a preregistered gate) that no priority can override, then dimensions
  reported **separately** (a provisional weighted figure is labelled
  uncalibrated). Work packages carry their **anti-requirements**.
- **Memory & learning** (`memory.py`) — a Development Pattern Memory (patterns
  keep provenance, finite confidence bounded to 0.0–0.9, and exceptions — never
  universal from one success). Finite out-of-range confidence is clamped; non-numeric
  and non-finite values are rejected on insertion or load. The learning loop compares
  **predicted vs actual** outcomes
  (missed obligations, over-expansion, inappropriate reuse, effort error) across
  cycles. No acceleration is claimed until enough cycles exist to support it.
  The per-cycle store accepts only 1–128 portable filename characters for cycle IDs;
  path separators and traversal-shaped IDs are rejected before any file access.

## Run it

```bash
# one full cycle on the real genius-tagger objective -> the six demonstration outputs
python -m rdo run-demo

# three discovery cycles (feature-deploy + two defect variants) + cross-cycle learning metrics
python -m rdo run-all

# source-grounded influence-AUTHORITY audit of a signal (relationships, not a file count)
python -m rdo influence --signal genius

# subject the RDO to its own Optimal Functional Tension
python -m rdo selfcheck

# the accumulated development patterns
python -m rdo patterns

# the tests (isolated fixtures + real-repo smoke tests)
python -m pytest rdo/tests -q
```

## Worked example — the genius auto-tagger

Test case: `WHATS_NEXT.md §3b` / `GENIUS_SCORE_v2.md §7a–7e` — "deploy the genius
auto-tagger and its consumers." The priority doc is from **May 2026**, so the
point is reconciliation against HEAD. The cycle finds:

1. **Discovered** — the full obligation network (table, daemon, boot wiring, API,
   panel, score, two consumers, runtime verification, + anti-requirements).
2. **Signature matches located** (each backed by a configured `file:line`
   anchor): `genius_tags` (`substrate/init_db.py`), the `GeniusTagger` daemon
   (`theory_x/genius/tagger.py` + boot in `run.py`), `/api/genius/recent` + panel,
   the v2 score, **and** a fountain-source reference (`generator.py` contains a
   `genius_tags` read). These matches locate relevant source; they do not by
   themselves establish that each complete API, UI, calibration or consumer
   obligation is semantically satisfied.
3. **Anti-requirements retained** — no second score and no duplicate tags store.
   Source-signature matches do not, by themselves, justify rejecting further
   discovery or implementation work.
4. **Recommended work** — the remaining obligation network is expanded
   conservatively where semantic satisfaction has not been reviewed. Active
   behavioural work remains subject to its preregistered gate; runtime verification
   remains host-only while NEX is in STANDBY.
5. **Evidence coverage** — each reported signature match has a file anchor.
   This is not semantic verification, test execution, or runtime verification.
6. **Learned** — candidate patterns retain their recorded provenance and are not
   promoted to universal rules merely by repeated appearance. The influence-authority
   review remains a source-based assessment, not a runtime finding.

The bounded result: the May-2026 proposal has several **source signature matches**
   in the current tree. Those matches identify locations for review; they do not
   establish that the full tagger, API, score, panel or consumer obligations are
   satisfied. The recursive expansion remains active unless a separate semantic
   review is recorded; no runtime behaviour is inferred.

## Generalisation — three discovery cycles across two patterns

The second and third discovery cycles (`run-all`) run **defect-remediation** objectives (the
`WHATS_NEXT.md` open-question migration bugs: `beliefs.content` UNIQUE dedup and
the `arc_closers` column) through the *same* engine. Generalising to a new pattern
required **one** new expansion rule set (`defect` → reproduce / root_cause / fix /
regression_test / migration / verification); reconciliation, OFT, prioritisation
and learning applied unchanged. The result is genuinely different from the genius
cycle: the `beliefs.content` fix is applied and guarded by
`tests/test_beliefs_content_dedup.py`, which exercises both production partial
unique indexes: duplicates within one problem and among orphan beliefs are rejected,
while equal content across different problems remains allowed. The RDO now matches
the specific regression-test declaration in that file, rather than accepting an
incidental token anywhere under `tests`; obligation-level reconciliation evidence
is included in cycle output. The
`arc_closers` migration is also already guarded by `tests/test_arc_closers_migration.py`,
including the actual legacy-upgrade path; it should not be described as unguarded
or recommended as net-new test work. The work remains surfaced, but its package is blocked while
necessary prerequisite evidence is unresolved; unknown obligations remain
investigable and are not treated as confirmed missing. This is distinct from the
behavioural gate applied to the genius consumer. The historical
`tests/test_arc_closers_migration.py` work is recorded as executed+verified. A third
discovery cycle covers the separate `beliefs.affinity` migration-only schema-drift
guard; its regression test is also recorded as executed+verified.

Every obligation is scope-tagged — **general** (reusable engineering rule) /
**domain-specific** (the idea's seeds) / **context-dependent** (conditional) /
**anti-requirement** / **novel** (no rule — surfaced, never force-fit). Generalising
needed one new *general* rule set in the engine; all domain specifics stay in
`knowledge.py`, and a test asserts the engine names no domain — so domain rules can
be added, compared and reused without contaminating it.

## Influence authority, assessed by relationship (not counted)

The genius signal is read by nine files, but **authority is not the count**. The
audit (`rdo influence`) classifies each consumer from source — direct vs indirect,
read vs behavioural, conditional vs unconditional, magnitude, safeguards, evidence
class — and checks that each curated source anchor is present in the cited file.
This is an **anchor-presence check**, not semantic verification of the row's
classification or proof that the described behaviour occurs. The graph's
`source_implemented` and `test_verified` flags are curated assertions; they are not
automatically derived links to per-edge source and test evidence. Six are behavioural and
**all six are safeguarded** (bounded weights, clamps, neutral defaults, opt-in
flags, strict gates). Exactly one path — `quality_synthesis → attention`
(a 1.20×/0.82× multiplier) — is both unconditional and material; that path, plus
the **self-reinforcement** question (a self-evaluation signal amplifying the
attention that regenerates it; gain unknown in STANDBY), is the review target. The
count is not. The complete potential path, its gain variables, the existing
countervailing safeguards (`bonsai.py` diversity mechanisms, windowed averaging) and
the runtime observations needed to decide it are documented as a **HYPOTHESIS**; no
multiplier or influence behaviour is changed until runtime evidence establishes it.

## Cross-cycle learning (measured, not claimed)

`run-all` reports eight per-cycle measures — reconciliation-status coverage (completed scan/review result, not precision),
missed-obligation count, duplicate-discovery rate, signature evidence coverage,
prediction error, rework, engineering effort, and completeness of file-anchor
coverage — with **per-measure denominators and missing values**. Evidence coverage
is not semantic reuse accuracy; coverage completeness is not successful test or
execution verification. Omitted actual outcome fields remain unknown (not zero),
and an outcome record is complete only when all four outcome lists are explicitly
reported. Cycles are tagged by kind:
`imported_retrospective` (seeded history), `native_planning` (RDO ran it, no work
executed yet), and `executed_verified` (recommended work actually built + verified).
**Only executed+verified cycles are efficiency-comparable** — an imported
retrospective is never counted as a completed RDO-guided cycle, and a planning-only
cycle contributes process measures only. The report makes **no efficiency or
acceleration claim** until at least three *comparable* cycles exist. There are
currently two recorded executed+verified test-work cycles: `arc_closers` and
`beliefs.affinity`. The catalogue has six rows: one imported retrospective, three
native discovery cycles and two execution records. Both historical execution records now carry exact, independently checkable CI provenance:

- **`arc_closers`** — source commit `c352f6a83bec2136d5eff518deb210fc3cd4b3a2`,
  workflow run [`44855260626` (#182)](https://github.com/kron777/Nex_v5.0/actions/runs/44855260626),
  pytest job `136695850460`: success. The commit contains all six tests in
  `tests/test_arc_closers_migration.py`, including the real `_apply_migrations`
  legacy-upgrade fixture, backfill, default-on-insert and idempotent re-run.
- **`beliefs.affinity`** — the same exact commit and successful workflow run. The commit
  contains both tests in `tests/test_affinity_columns_migration.py`, covering fresh
  migration provisioning, nullable columns and the unrated-state query.

The workflow ran `scripts/check_test_baseline.py`, which invoked the full `pytest -q`
suite with zero known-intentional tests deselected. Result: **2,219 passed, 7 skipped,
40 subtests passed**. The earlier successful run `44853759854` (#181, 2,214 passed)
was on the initial `arc_closers` test commit before the legacy-upgrade fixture was added;
it is intermediate evidence, not the final verification used above.

These are source-commit and CI-run/job references, not a separate database snapshot or
runtime artifact. They verify the committed regression tests in CI; they do not establish
deployed-host behaviour. Later CI runs are not substituted for this exact historical run.


## The RDO under its own OFT

`rdo selfcheck` now distinguishes the core reasoning package from its external
input boundary. The last recorded self-assessment baseline contained **14 modules / 3,775
non-comment LOC**; the provider-neutral objective-intake and Stage-7 handoff
adapters are separately reported at **3 modules / 1,538 non-comment LOC** under
`rdo_adapters/`. The typed objective-context and acceptance-verification increment
adds code to existing core modules rather than creating another reasoning module.
The self-assessment must be rerun against the current head before publishing a
new LOC total; the baseline figures above are historical, not a claim about the
current branch's exact footprint.

The size result is intentionally not described as lean: the self-check's
existing 1,800-LOC heuristic still returns **needs review** for the 3,775-LOC
core. It flags the largest modules for examination. That is a review signal,
not an instruction to split files mechanically; any restructuring must be
justified by responsibility, coupling, tests and functional tension.

## Scope & limitations

- The RDO **obeys its own principle**: it reuses Watcher infrastructure, it is
  lean, and it stays advisory. It is not a development bureaucracy.
- LLM/human reasoning seeds obligations and signatures (`knowledge.py`). The
  tree establishes only whether configured anchors were found; it does not
  independently establish semantic satisfaction. A separate review is required
  before necessary obligations can contribute to a `sufficient` readiness verdict;
  the review flag alone is insufficient without a recorded review-evidence reference.
- The maths (Pareto framing, weighted priority) is scaffolding and is labelled
  uncalibrated — the early value is in structure (obligations, reconciliation,
  anti-requirements, tension), not equations.
- Runtime observation is **host-only**. Cloud-side cycles never claim a runtime
  behaviour was observed; they recommend verification and leave it blocked.

## RDO development order (v1.4 §29 — current working basis)

The working development order is the sequence recorded in founder-supplied
RDO v1.4 §29. The founder indicated on 24 November that they believed v1.4 had
been approved; it is therefore the current working specification. RDO v1.3 is
preserved as historical source and as the lineage for earlier stage labels and
implementation reports. This README does not retroactively rewrite that history.

The v1.4 order is:

1. Repository reconciliation.
2. Watcher.
3. Extrapolator MVP — the first complete idea-to-work-package vertical slice.
4. Graph intelligence.
5. Tension assessment / Optimal Functional Tension (OFT).
6. Belief audit.
7. Bounded belief-development pathway.
8. Learning loop.
9. Expansion.

Current code mapping (capability status is not the same as stage completion):

- **Extrapolator MVP:** bounded recursive obligation discovery, repository
  reconciliation, safe convergence, anti-requirements, frontier accounting,
  work-package generation and resumable cycles. Its current seed input is
  structured; it does not yet compile raw natural-language intent itself.
- **Graph intelligence:** typed relationships, SCCs, semantic-duplicate
  candidates, completeness and dependency sequencing are implemented in
  `rdo/graph.py`.
- **OFT:** a partial three-level assessor exists in `rdo/tension.py`, but the
  full v1.4 interface profile, operating envelopes, capacity/headroom,
  multi-objective margins, stability/hysteresis and marginal-value stopping
  are not yet implemented. See the v1.4 implementation gap audit.
- **Belief audit:** source-grounded and read-only; it does not query or modify
  the live DB.
- **Bounded pathway:** isolated, gated pathway analysis; no live confidence or
  retrieval write is performed.
- **Learning:** prediction/outcome comparison, provenance, disconfirmation and
  confidence reduction are implemented; the complete adversarial negative-
  outcome acceptance case still needs an explicit regression test.
- **Expansion:** remains a later v1.4 development step, not a licence to bypass
  safety gates or the frozen NEX roadmap.

Historical stage commands remain available and produce artifacts under
`rdo/.cycles`; they do not activate NEX, modify the live belief store, change
feature flags, start or stop services, deploy code, or claim runtime
verification. Stage 7's fixture authorizes only its own exact
repository-relative test path.

See [the v1.4 implementation gap audit](RDO_V1_4_IMPLEMENTATION_GAP_AUDIT_2026-11-27.md)
and [the specification-version reconciliation](RDO_SPECIFICATION_VERSION_RECONCILIATION_2026-11-26.md)
for the current working basis, historical crosswalk and remaining fidelity gaps.



## Generic objective intake (v1)

The RDO now accepts a versioned, provider-neutral objective record through `python -m rdo intake`. The contract preserves the original request, intent, owner/source, scope, constraints, exclusions, assumptions, acceptance criteria, seed obligations, typed relationships and reconciliation signatures. External-LLM seeds remain inferred proposals; measured evidence, semantic-reuse decisions and approvals cannot be injected through the input.

```bash
python -m rdo intake --input objective.json --repo . --out rdo/.cycles
python -m rdo history --objective-id my-objective --out rdo/.cycles
python -m rdo resume --objective-id my-objective --revision 1 --out rdo/.cycles
```

Each input revision is append-only and linked by SHA-256. The original wording and intent are immutable; a cycle stores the input revision/digest and a clean repository commit SHA. The selected repository must be a clean Git snapshot. The Watcher experiment registry still controls eligibility and unknown registry state remains blocked. On first revision creation, the ledger file is fsynced and its parent directory is fsynced so the new directory entry is included in the durability boundary; later revisions fsync the existing ledger file. Objective ledger and lock paths must be regular files, not symlinks or special files; opens use no-follow semantics where supported to close the check/open race.

See [the intake contract](OBJECTIVE_INTAKE.md), [the JSON Schema](schemas/objective.v1.schema.json), and [an example input](examples/objective.v1.example.json). This is advisory planning only; it does not execute work or alter NEX runtime state.

## Candidate seed proposal lifecycle (pre-intake review)

The provider-neutral `rdo_adapters.seed_proposals.SeedProposalStore` preserves
an exact raw-objective revision and competing seed-graph interpretations in an
append-only, hash-linked proposal/review ledger. The CLI exposes
`seed-propose`, `seed-review`, `seed-history` and `seed-selection`.
External-LLM seed confidence remains inferred, and approval must explicitly
select one existing alternative. Proposer/reviewer labels are caller-attributed,
not identity-authenticated.

The reviewed-selection bridge is implemented separately:
`seed-prepare` is read-only, while `seed-intake` explicitly persists the
approved objective and provenance lineage and runs advisory RDO planning.
Neither operation automatically creates a Stage-7 handoff, executes code,
activates rules or changes live NEX runtime state. The handoff remains a
separate explicit operation.

See [the candidate seed proposal lifecycle](SEED_PROPOSAL_LIFECYCLE.md) and
[the reviewed seed bridge](REVIEWED_SEED_BRIDGE.md) for schemas, ledger
integrity, replay behavior, provenance and authority boundaries.

## Stage-7 handoff (non-executing)

For an actual persisted objective cycle, create an immutable manifest for one
work package:

\`\`\`bash
python -m rdo handoff-create \\
  --objective-id my-objective --revision 1 \\
  --cycle-id <cycle-id> --work-package <work-package-key> \\
  --repo . --out rdo/.cycles
python -m rdo handoff-history --handoff-id <handoff-id> --out rdo/.cycles
\`\`\`

A separate human scope review can be appended with \`handoff-review\`; human
acceptance is a separate \`handoff-acceptance\` event. These records are
caller-attributed, not identity-authenticated. Approval can only authorize a
scoped proposal; it cannot authorize tests, arbitrary commands, live NEX writes,
experiment changes, services or deployment. The handoff does not launch an
agent. Test execution remains not authorized until a disposable, no-secrets
sandbox is independently designed and verified.

After an explicit human scope review, run independent source/path verification
with `python -m rdo handoff-verify --handoff-id <handoff-id> --repo . --out rdo/.cycles`.
This starts the trusted Watcher package as a separate process; it does not execute
tests or project commands. **Stage 7 is not complete** until test evidence is
safely authorised and independently verified, host-only runtime evidence is
addressed under founder authority, and a real objective-to-verified delivery is
demonstrated. Issue #87 tracks the remaining work.

See [Stage-7 handoff boundaries](STAGE7_HANDOFF.md).



## Read-only persisted-cycle graph analysis

Two commands expose the Stage-3 structural analyses over saved CycleRecord files.
They load cycle JSON and do not mutate the records or NEX runtime state.

```bash
python -m rdo failure-propagation --cycle-id <cycle-id> --failed-key <obligation-key>

python -m rdo failure-propagation --cycle-id <cycle-id> \
  --failed-key storage.schema --failed-key storage.write_path

python -m rdo impact --before-cycle-id <before-id> --after-cycle-id <after-id> \
  --changed-capability storage --dir rdo/.cycles
```

failure-propagation follows depends_on edges only and reports structural candidates.
It does not claim that a runtime failure propagated, or estimate severity, probability or
causality. Unknown roots, malformed graph records and unresolved dependency edges keep the
result partial.

impact compares incident relationship records and their before/after tension assessments.
It distinguishes relationship changes from assessment-only changes and reports missing or
ambiguous evidence as partial. A difference is correlation between two persisted snapshots,
not proof that the named capability caused the change, nor a benefit/harm/sufficiency verdict.

Both commands are read-only. Exit status is 0 for a complete analysis, 1 for a partial or
invalid analysis, and 2 when a requested cycle cannot be loaded or the input is invalid.


## Observed failure evidence

Structural failure-propagation candidates from `failure-propagation` are not runtime
observations. The separate `rdo.failure_evidence` data model can record a measured
failure event against an exact `depends_on` edge, preserving independent Watcher
Evidence records for the failed prerequisite and (when observed) affected consumer.
It retains a timezone-aware observation window, typed operating-envelope evidence,
origin, evidence class, source references and caller-attributed assessment provenance.

Association defaults to UNKNOWN. Co-observation, temporal association and causal
attribution are distinct reviewer-supplied states; the record validates required
evidence but does not infer causality, propagation probability, severity, headroom
or an OFT verdict. Records are appended to a CycleRecord's trailing
`observed_failure_evidence` field and survive CycleStore reload; legacy cycles
without the field remain loadable. See [OBSERVED_FAILURE_EVIDENCE.md](OBSERVED_FAILURE_EVIDENCE.md).


## Persistence failure safety

`CycleStore.save` serializes a complete cycle to a same-directory temporary file,
flushes and fsyncs it, then atomically replaces the prior cycle file and fsyncs
the directory. A failure before replacement leaves the previous cycle intact.

`PatternMemory.add` and `PatternMemory.refute` now prepare candidate snapshots,
append and fsync them before publishing the updated in-memory pattern. A failed
append therefore does not advance the in-memory learning state. This is a
single-writer failure-safety guarantee; concurrent multi-process PatternMemory
transactions are not yet serialized and must not be assumed safe.


## Novel-kind proposal boundary

When the Extrapolator encounters an obligation kind with no active expansion rule,
it still leaves that obligation in the frontier rather than inventing children.
The frontier entry now carries a `rule_proposal_request` containing the complete
source obligation, the known rule kinds, terminal kinds, and the review dimensions
needed for a candidate decomposition.

This is a provider-neutral handoff to a human or external LLM, not an
automatically generated or activated rule. The candidate/review lifecycle is
implemented in `rdo_adapters/rule_proposals.py`: proposals preserve applicability,
constraints, exceptions, anti-requirements, alternatives, evidence,
disconfirmations and positive/negative test plans. Even
`approved_for_catalogue` is inert; activation requires a separate reviewed
source change, tests and CI. Repeated pattern frequency alone does not activate
a rule.


## Novel expansion-rule proposals

A novel obligation kind remains a visible frontier item; it is never silently expanded. Its provider-neutral request carries the source obligation, review requirements, and a digest of the exact expansion-rule/terminal-kind catalogue snapshot. Requests from an older schema or changed catalogue are rejected as stale.

`rdo_adapters.rule_proposals.RuleProposalStore` records candidate proposals and explicit caller-attributed review decisions in an append-only, hash-chained JSONL ledger. Candidates must retain applicability, preconditions, constraints, exceptions, anti-requirements, assumptions, alternative interpretations, evidence references, disconfirming cases, and positive/negative test plans. The store does not execute proposal content or import generated code.

Even `approved_for_catalogue` means only that a candidate is eligible for a separate code/catalogue change review. There is deliberately no activation API: `EXPANSION_RULES` remains the only active catalogue and changes only through an ordinary reviewed source change with tests and CI. Proposer/reviewer labels are caller-attributed, not identity-authenticated.

The `rule-history` and `seed-history` commands derive proposal statuses and event rows from one locked ledger read apiece, so a concurrent review cannot make the two sections disagree.

The lifecycle is available through three provider-neutral CLI commands. Supply
a JSON file containing exactly `request`, `candidate`, `proposer_kind`,
`proposer_reference` and `source_reference`; an optional
`supersedes_proposal_id` may identify a prior changes-requested/rejected
proposal.

The `request` is the exact `rule_proposal_request` emitted at an RDO novel-kind
frontier. The `candidate` remains human- or external-provider-supplied: these
commands persist and review it but do not invoke a model or implement an
autonomous raw-idea-to-rule generator.

```bash
python -m rdo rule-propose --input rule-proposal.json
python -m rdo rule-history
python -m rdo rule-review --proposal-id ruleprop_<id> \
  --decision approved_for_catalogue --reviewer founder \
  --source-reference review:1 --rationale "Candidate merits separate source review" \
  --evidence-reference evidence:positive --evidence-reference evidence:negative
```

`approved_for_catalogue` remains inert. It does not alter
`EXPANSION_RULES`, execute proposal content, create a runtime rule or grant
action authority. The CLI exposes no activation command. Regression coverage
is in `rdo/tests/test_rule_proposal_cli.py`.

## Feedback-loop evidence updates

Measured dimensions and independently attributed stability reviews can be
appended to an existing loop record without changing its topology or
calculating a stability verdict. See [FEEDBACK_LOOP_EVIDENCE.md](FEEDBACK_LOOP_EVIDENCE.md)
for the measurement/review commands, hash-chained event ledger and replay path.


## Candidate seed proposals (G-92)

Seed proposals are advisory interpretations upstream of objective intake. Supply
a JSON file containing exactly `raw_objective`, `alternatives`,
`proposer_kind`, `proposer_reference`, and `source_reference`; an optional
`supersedes_proposal_id` may identify a prior changes-requested/rejected
proposal. The raw objective and at least two competing alternatives must satisfy
the schemas in [SEED_PROPOSAL_LIFECYCLE.md](SEED_PROPOSAL_LIFECYCLE.md).

```bash
python -m rdo seed-propose --input proposal.json
python -m rdo seed-history
python -m rdo seed-review --proposal-id seedprop_<id> \
  --decision approved --selected-alternative-id alternative-a \
  --reviewer founder --source-reference review:1 \
  --rationale "Selected after evidence review" \
  --evidence-reference evidence:one
python -m rdo seed-selection --proposal-id seedprop_<id>
```

The proposal and review ledger is append-only and hash-chained. Approval selects
one existing alternative but does not create an `objective.v1` record, start an
RDO cycle, create a Stage-7 handoff, execute code, or activate rules. Reviewer
and proposer labels remain caller-attributed, not identity-authenticated.


## Reviewed seed intake and provenance (G-92)

The reviewed-selection bridge exposes two separate operations. The read-only
`prepare_reviewed_selection()` validates an explicit approval and prepares
`objective.v1` plus its dual-chain lineage. The explicit
`submit_reviewed_selection()` operation stores the objective and lineage in
one objective-ledger append, then runs the advisory RDO planning cycle. It
preserves provenance through CycleStore and the Stage-7 manifest; it does not
automatically create a handoff or authorize execution. See
[REVIEWED_SEED_BRIDGE.md](REVIEWED_SEED_BRIDGE.md) for persistence, replay,
integrity and authority boundaries.


The final bridge steps are explicit:

```bash
# Read-only: inspect the validated objective.v1 candidate and provenance.
python -m rdo seed-prepare --proposal-id seedprop_<id>

# Explicit persistence and advisory RDO planning; still no Stage-7 handoff/execution.
python -m rdo seed-intake --proposal-id seedprop_<id> --repo .
```

`seed-prepare` never appends or plans. `seed-intake` appends the objective and
verified proposal lineage together, then runs the existing advisory RDO planner.
A Stage-7 handoff remains a separate explicit command.
