# RDO development history

A chronological record of how the RDO itself was developed, and of each cycle's
prediction-versus-actual and lessons. This is deliberately **separate** from the
RDO's own Pattern Memory catalogue (`rdo/.cycles/`): cycles the RDO ran against
NEX live there as structured, comparability-governed records; the development of
the *instrument* is recorded here as prose, so it never silently enters the
efficiency/comparability machinery.

Governing principle: engineering, integration, observation, refinement — and
allowing engineering to unfold. Build the instrument, then let its use reveal
what it needs next. Size thresholds are observational tripwires, not targets.

---

## Executed cycles against NEX (the comparability corpus)

These are the four `executed_verified` cycles that the catalogue counts. They
are summarised here for continuity; the authoritative records are in
`rdo/.cycles/` and `run-all` / `patterns`.

| cycle | engineering pattern | predicted | actual | note |
|---|---|---:|---:|---|
| `arc_closers_regtest` | migration_guard | 1 | 2 | missed a legacy upgrade path — expansion under-counted |
| `affinity_regtest` | migration_guard | 1 | 1 | — |
| `config_invariant` | invariant_guard | 1 | 1 | source scan, no DB fixture |
| `recorder_consolidation` | refactor | 1 | 1 | consolidated duplicated executed-cycle recorders |

Honest comparability: the largest genuinely-comparable group (same engineering
pattern) is **2** (the two migration guards). The RDO therefore makes **no
efficiency or acceleration claim** — three comparable cycles are required and do
not yet exist.

---

## Instrument-development cycles (not catalogue cycles)

### 2026-11 — Bounded orchestrator responsibility split (PR #48)

A refactor of the RDO itself, recorded here rather than as a fifth
`executed_verified` cycle. Adding it to the catalogue would change
`executed_cycles` 4 → 5 and invalidate the behaviour-preservation comparison
that defines this cycle's success, so it is kept out of the comparability
machinery. It is **not** paired with `recorder_consolidation` as a
"refactor vs refactor" comparison — two cycles sharing the word "refactor" is
not a comparability relationship.

**Prediction (recorded before the work):**
- Effort ≈ 2 units: one new module, move functions, update importers + tests,
  add a domain-free guard test.
- Reuse by *moving* functions, not rewriting them.
- Anti-requirements: one module (not several); no new abstractions; no
  behaviour/output change; no import cycles; no scope creep into semantic
  matching or prediction.
- Acceptance: the driver becomes domain-free and smaller; the full suite passes
  with behavioural equivalence; the CLI is unchanged; the dependency graph stays
  acyclic.

**Actual:**
- `orchestrator.py` 453 → 113 non-comment LOC (−340); new `report.py` +340
  (a near 1:1 move of the demonstration/reporting layer); `knowledge.py`
  277 → 296 (+19, the genius authority audit relocated to the domain module).
  Net package change **+19 non-comment LOC**. No new abstractions.
- Behavioural equivalence verified against the pre-split head: catalogue keys,
  the four executed cycles, authority counts (9 consumers / 6 behavioural),
  change categories and the comparability finding all matched. The only output
  delta was `selfcheck`'s module count **9 → 10** — the honest consequence of
  `report.py` now existing as a reviewed module.
- Dependency graph acyclic; the driver imports no domain module; `knowledge`
  has no upward dependency; `report` is imported only by the CLI shell. A new
  guard (`test_orchestrator_is_domain_free`) parses the driver with
  docstrings/comments stripped and asserts the code names no domain token.
- CI green on the final commit.

**Lessons:**
- A responsibility boundary has an irreducible small cost (+19 non-comment LOC
  here). Separating cohesive concerns was worth it, but "no net LOC growth" is
  not an achievable anti-requirement for a split — the effort prediction held;
  LOC grew slightly and that is the honest price.
- Process: the first domain-free guard was too strict (it matched the module
  docstring's own prose). The guard caught its own over-strictness; it was
  reworked to test code rather than text. A guard that reads source should test
  the *code*, not the prose.

---

## Where the RDO stands, and what use must reveal next

Provisional structural sufficiency is accepted. The next frontier is not more
internal restructuring; it is evidence from genuine use. **Do not manufacture
work to generate data.**

### What the RDO can currently do reliably
- Run one bounded cycle from a seed idea + repo: depth-capped recursive
  obligation expansion, grep-verified reconciliation (reuse / missing /
  anti-requirement), false-dependency pruning, OFT assessment
  (node / relationship / system), eligibility-gated prioritisation into work
  packages, and verification that every reuse claim is backed by file evidence.
- Audit a signal's *authority* by relationship rather than by count
  (capability ≠ authority).
- Persist cycles append-only (JSONL) with deterministic confidence
  reconstruction; corroborate/refute with de-duplication and explicitly
  **heuristic, uncalibrated** confidence.
- Hold itself to OFT via `selfcheck`, flagging size tripwires without
  auto-refactoring.
- Stay advisory: it never imports the NEX runtime (test-enforced) and never
  executes changes.

### What it has demonstrated
- Four executed-and-verified cycles across three engineering patterns (two
  migration guards, one invariant guard, one refactor), each with a recorded
  prediction and actual, including one honest miss (`arc_closers`, 1 → 2).
- Honest cross-cycle accounting: explicit denominators, a largest-comparable
  group of 2, and no efficiency claim asserted on that sample.

### What remains unproven (the comparable sample is small)
- No efficiency or acceleration claim is warranted: the largest comparable
  group is 2 (< 3).
- Prediction accuracy rests on four points across three patterns — too few to
  characterise bias or variance.
- Pattern-confidence weights are heuristic, not calibrated against outcomes.
- Cross-cycle transfer is observed structurally, not shown to be predictive.

### What evidence to accumulate through genuine development work
- At least three genuinely-comparable executed cycles of the **same**
  engineering pattern, enabling a first honest efficiency observation.
- More predicted-versus-actual points, to calibrate prediction error and
  confidence weights against real outcomes.
- Cycles that exercise the unproven areas — e.g. on-host runtime verification —
  to test whether advisory recommendations hold when actually executed.
- All of it driven by real NEX development needs, not invented tasks.
