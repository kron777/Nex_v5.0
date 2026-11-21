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
# full cycle on the real genius-tagger objective -> the six demonstration outputs
python -m rdo run-demo

# audit how many subsystems consume a signal (capability != authority)
python -m rdo influence --signal genius --subtree theory_x

# the accumulated development patterns
python -m rdo patterns

# the tests (isolated fixtures + one real-repo smoke test)
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
