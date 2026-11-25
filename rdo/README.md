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
| **Watcher** | observation & evidence (read-only) | **consumed** (reuses `watcher.evidence`, `watcher.registry`) |
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
  checked against text-readable files in the **actual tree** (read-only grep):
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
  keep provenance, bounded confidence and exceptions — never universal from one
  success) and a learning loop that compares **predicted vs actual** outcomes
  (missed obligations, over-expansion, inappropriate reuse, effort error) across
  cycles. No acceleration is claimed until enough cycles exist to support it.

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

`rdo selfcheck` holds the RDO to the principle it applies to NEX: 9 modules,
~1340 LOC, no NEX-runtime import, reuses Watcher infrastructure — functionally
sufficient and lean. It honestly flags the largest module and one minor
function overlap, and the OFT-correct response to both is restraint: splitting or
deleting would trade a small smell for module proliferation, which OFT also
forbids.

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
