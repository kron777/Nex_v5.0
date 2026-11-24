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
WORK PACKAGE → VERIFICATION → (persist) → LEARN
```

- **Expansion** (`extrapolator.py`) — a small seed of obligations expands via
  generic engineering rules (a persistence obligation implies a schema, a write
  path, provenance, a test…). Recursion is **bounded**: depth cap, terminal
  kinds, and — crucially — an obligation already satisfied by a real mechanism is
  **not** expanded. Convergent branches merge; every stop records its reason.
- **Reconciliation** (`reconcile.py`) — each obligation with a *signature* is
  checked against the **actual tree** (read-only grep): all signatures match →
  `reuse_existing`; some → `partial`; none → `missing`; no signature → `unknown`
  (an honest gap, never a fabricated status). It also prunes *false dependencies*
  (a "build X first" edge whose X already exists).
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
2. **Correctly reused** (each backed by a real `file:line`): `genius_tags`
   (`substrate/init_db.py`), the `GeniusTagger` daemon (`theory_x/genius/tagger.py`
   + boot in `run.py`), `/api/genius/recent` + panel, the v2 score, **and** the
   fountain consumer (`generator.py` reads `genius_tags`).
3. **Rejected / deferred** — rebuilding any of the above, plus two explicit
   anti-requirements (no second score; no duplicate tags store).
4. **Recommended work** — only the genuinely-missing **retrieval consumer** (with
   its `bounded_influence` / `reversibility` / `gate` sub-obligations) and
   **runtime verification**. Both **blocked**: an active behavioural change needs a
   preregistered gate, and runtime evidence is host-only while NEX is in STANDBY.
5. **Verified** — every reuse claim re-checked against file evidence.
6. **Learned** — the stale-doc pattern (*planning docs and code docstrings older
   than HEAD understate built state; reconcile first*), corroborated by the
   just-completed Watcher cycle, and an OFT flag: the genius signal is consumed by
   ~9 files → recommend an influence-authority review.

The headline result: the May-2026 "build the tagger (≈2.5h)" item is **already
built**, and so are most of its consumers — so the honest recommendation is *don't
rebuild; verify at runtime and review the signal's influence*, not a checklist.

## Generalisation — three discovery cycles across two patterns

The second and third discovery cycles (`run-all`) run **defect-remediation** objectives (the
`WHATS_NEXT.md` open-question migration bugs: `beliefs.content` UNIQUE dedup and
the `arc_closers` column) through the *same* engine. Generalising to a new pattern
required **one** new expansion rule set (`defect` → reproduce / root_cause / fix /
regression_test / migration / verification); reconciliation, OFT, prioritisation
and learning applied unchanged. The result is genuinely different from the genius
cycle: the `beliefs.content` fix is applied and its regression-test obligation is
currently classified as reused; that reuse still requires a semantically relevant
test reference, not merely a matching token anywhere under `tests`. The
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

`run-all` reports eight comparable per-cycle measures — expansion precision proxy,
missed-obligation count, duplicate-discovery rate, reuse accuracy, prediction
error, rework, engineering effort, verification success — with **explicit
denominators, missing values and comparability**. Cycles are tagged by kind:
`imported_retrospective` (seeded history), `native_planning` (RDO ran it, no work
executed yet), and `executed_verified` (recommended work actually built + verified).
**Only executed+verified cycles are efficiency-comparable** — an imported
retrospective is never counted as a completed RDO-guided cycle, and a planning-only
cycle contributes process measures only. The report makes **no efficiency or
acceleration claim** until at least three *comparable* cycles exist. There are
currently two recorded executed+verified test-work cycles: `arc_closers` and
`beliefs.affinity`. The catalogue has six rows: one imported retrospective, three
native discovery cycles and two execution records. The historical execution
records retain their recorded test claims but do not yet carry independently
checkable CI-run/artifact references. Their evidentiary classification remains a
Founder decision. Patterns corroborate slowly and never become universal rules
merely for appearing twice.

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
- LLM/human reasoning seeds obligations and signatures (`knowledge.py`); the
  **tree is the authority**. Proposals never silently become fact.
- The maths (Pareto framing, weighted priority) is scaffolding and is labelled
  uncalibrated — the early value is in structure (obligations, reconciliation,
  anti-requirements, tension), not equations.
- Runtime observation is **host-only**. Cloud-side cycles never claim a runtime
  behaviour was observed; they recommend verification and leave it blocked.
