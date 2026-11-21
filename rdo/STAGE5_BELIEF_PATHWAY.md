# RDO Stage 5 — First Belief-to-Mechanism Pathway

**Governing scope:** RDO v1.3 §16 Stage 5. Select and specify **one** low-risk, falsifiable
belief-to-mechanism pathway from the Stage-4 evidence, and verify it in **isolation** against the
real mechanism — no live NEX writes, injections, config/flag changes, restarts or experiment
modifications. Source presence and a passing isolated test are **not** treated as verified live
runtime behaviour; live confirmation is a host-only gate, kept explicitly UNKNOWN.

**Coordination.** Branch `claude/rdo-stage5-belief-pathway`, based on `bdeeea6` (Stage 4 head).
Earlier branches untouched. `rdo/pathway.py` is read-only and does **not** import `theory_x`/`substrate`
(the RDO independence invariant holds); the isolated verification lives in `tests/` (NEX side) where
importing the real mechanism is allowed.

Run: `python -m rdo stage5` prints the pathway spec and persists `belief_pathway.json`.

## Candidate evaluation

| Candidate | evidence | significance | risk | reversible | first-slice | decision |
|---|---|---|---|---|---|---|
| **confidence → world-model retrieval** (eligibility + relevance ordering) | high | high | low | high | **high** | **SELECTED** |
| belief_edges (typed) → spreading activation | high | medium | medium | high | medium | deferred (more complex) |
| belief_activation recency → candidate pool | medium | medium | low | high | medium | deferred (weaker, time-dependent) |
| **belief_boost → priority lever** | — | — | — | — | — | **EXCLUDED** — documented decision-INERT, "do NOT build" (`tools/check_belief_headroom.py:196`) |

## Selected pathway — causal proposition

> A belief's **`confidence`** value determines **(a)** whether it is **eligible** for world-model
> retrieval and **(b)** its **relevance rank** among keyword-matched beliefs.

- **Eligibility:** `tier<=6 AND paused=0 AND (locked=1 OR confidence>=0.15)` — `theory_x/stage3_world_model/retrieval.py:164`.
- **Relevance:** `score = keyword_overlap_fraction * confidence` — `retrieval.py:218`.
- **Mechanism:** `theory_x.stage3_world_model.retrieval.BeliefRetriever.retrieve` (dependency-injected
  `Reader`, so it runs against a fixture).
- **Observable consequence:** an unlocked belief below 0.15 is **absent** from retrieval; raising its
  confidence above the floor **admits** it; among equally keyword-matched beliefs, **higher confidence
  ranks higher** and is more likely to reach generation.

## Baseline, and isolated verification against the REAL mechanism

`tests/test_belief_confidence_retrieval_pathway.py` (9 tests) builds a **throwaway** SQLite fixture
from the **real** `substrate/schema/beliefs.sql`, seeds test beliefs, and runs the **real**
`BeliefRetriever` (read-only `Reader` over the fixture). It writes only the throwaway fixture — no
live DB.

- **Baseline (pre-intervention):** a query-relevant belief at confidence **0.10** (unlocked) is **not**
  retrieved.
- **Intervention (in-fixture, reversible):** the same belief at **0.50** **is** retrieved.
- **Ordering:** two equally keyword-matched beliefs rank by confidence (0.90 before 0.30).
- **Negatives / failures:** locked overrides the floor; paused excluded; `tier>6` excluded; no
  keyword overlap → not scored; empty query → eligible rows returned unscored (documented edge).

## Success / unsuccessful / inconclusive

- **Success (contract):** all of the above hold against the real mechanism — **verified** in isolation.
- **Unsuccessful:** an unlocked below-floor belief is retrieved, or confidence does not affect
  eligibility or ordering — **not observed**.
- **Inconclusive (kept UNKNOWN):** whether, on the **running system with the real belief population**,
  confidence actually changes what NEX surfaces is **not** established here. That is host-only.

## Rollback

**None required** — the Stage-5 work is read-only + isolated (throwaway fixture); no live NEX state
changed, so there is nothing to roll back. A **future LIVE intervention** (changing a real belief's
confidence to observe a retrieval change) **would** require: experiment-specific approval, a read-only
before snapshot, and a documented revert restoring the original confidence.

## Remaining approval gate (host-only, NOT performed)

To verify the pathway **live**: on the running machine, read-only (`mode=ro`) observe retrieval-pool
membership + ordering for a fixed query, before/after one belief's confidence crosses 0.15, and
confirm the predicted admission/ranking change. **Requires host access + experiment-specific approval**
— unauthorised here (NEX in standby).

## OFT note (module growth)

The RDO package is now 13 cohesive modules: the 10 engine/demo modules + `graph` (Stage 3),
`belief_audit` (Stage 4) and `pathway` (Stage 5) — each one authorised roadmap capability, reuse-first,
not proliferation. The self-check module tripwire was raised 12 → 13 (exactly the current count, so a
further module still trips the review), not gamed by merging distinct responsibilities.

## Specification-precedence note (unchanged, unresolved)

The implementation cites **RDO v1.4** in docstrings; the governing sequence is **v1.3 §16**. The
v1.2 / v1.3 / v1.4 texts, Watcher v3.0 and the Master Roadmap v3.0 are not in the workspace; no
version reconciliation is assumed, and the precedence remains for founder resolution.
