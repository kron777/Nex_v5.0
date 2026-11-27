# RDO Stage 3 — Graph Intelligence

**Working specification:** RDO v1.4 §29 places graph intelligence after the Extrapolator MVP and before the dedicated OFT assessment. “Stage 3” is retained here as the historical implementation label. One cohesive, read-only analysis module
(`rdo/graph.py`) that makes the Extrapolator *understand* the obligation graph it already
produces — it does not build a general-purpose graph platform and adds no new persistence,
merge or reconciliation mechanism.

**Coordination.** Branch `claude/rdo-stage3-graph-intelligence`, based on
`847af858147ff2681b334538fd4c60a8b0f95b0f` (Stage 2 head `847af85`, verified). `rdo/`-only.
The Stage 2 evidence branch is untouched. No Watcher, live-NEX, host-side or experiment changes.

Run it: `python -m rdo stage3 --out rdo/.cycles` → analyses the belief-decay graph and persists
`graph_analysis_belief_decay_mvp.json`. The analysis is deterministic and recomputes from the
persisted cycle in a fresh process.

## Reuse map (inspected by behaviour, not name)

| Stage 3 need | Reused from Stage 2 | Stage 3 addition |
|---|---|---|
| Typed edges | `Relationship.kind` vocabulary (`depends_on/produces_for/reuses/duplicates/influences`); `reconcile` already emits `reuses` | read + summarise actual types; derive `produces_for` (architecture) and `duplicates` (candidates) |
| Cycle handling | `tension._find_cycles`, `_classify_cycle` | Tarjan **SCC decomposition** on top |
| Safe convergence | `extrapolator._merge` + `MergeConflict` (exact-key) | **surface** semantic-duplicate candidates; never merge |
| Counts / frontier | `extrapolator.frontier_breakdown`, `CycleRecord.counts` | completeness analysis against the objective |
| Prioritisation | `prioritise` (priority ranking) | **dependency sequence** (distinct from priority) |

## The six capabilities

1. **Deduplication beyond exact-key** — `dedup_candidates` groups by kind and surfaces pairs that
   either reconcile to the **same mechanism** (`confirmed_equivalent`) or share child-kind/title
   (`uncertain_similar`). Candidates retain both keys, parents and provenance for review. **Nothing
   is merged** — the obligation set is unchanged (tested). Represented as `duplicates` typed edges.
2. **Typed relationships** — the graph is not a bare `depends_on` tree: `typed_edge_summary` reports
   actual types, `derive_produces_for` adds producer→consumer edges justified by the kinds (no new
   taxonomy), and `duplicates` candidate edges are kept distinct from dependencies. For belief-decay:
   `depends_on` 33, `produces_for` 4 (policy/daemon → the two consumers), `duplicates(candidate)` 12.
3. **SCC decomposition** — `scc_decomposition` (iterative Tarjan over `depends_on`+`influences`)
   finds strongly connected components, distinguishes individual cycles (reusing `_find_cycles`)
   from larger components, classifies each (`prerequisite_cycle` / `feedback_loop` / `unknown`), and
   reports internal cycles, external **prerequisites** and downstream **dependents**. Cycles are
   never auto-removed.
4. **Completeness** — `completeness` measures against the discovered obligations (not a target
   count): accounted (reuse / net-new / anti), unresolved (no signature), deferred (budget), and
   evidence gaps. For belief-decay: 41 discovered, 37 unresolved → honestly **not** complete.
5. **Sequence analysis** — `implementation_sequence` collapses `depends_on` SCCs to units, levelises
   the condensation (Kahn) into **parallelisable levels**, represents a cyclic component as a single
   unit (never linearised internally), and respects hard prerequisites. It is explicitly **not** a
   priority ranking.
6. **Convergence + cycles** — the genuine shared runtime-verification prerequisite stays one node
   (in-degree 2), and the merge-safety from Stage 2 is unchanged.

## Demonstration (regression baseline + fixture)

- **belief-decay graph** (real, from the Stage-2 artefact): acyclic; convergence preserved;
  12 duplicate candidates surfaced (none merged); typed edges beyond `depends_on`; 3 sequence
  levels (parallel width 34); honestly incomplete (37 unresolved).
- **deliberately-constructed cyclic component** `A↔B↔C`: decomposed as one `prerequisite_cycle`
  component, with external prerequisite `ext` and downstream dependent `down` correctly directed;
  the sequence places `ext` before the component-as-a-unit before `down`, with an independent node
  in parallel. A feedback (`influences`) cycle is classified `feedback_loop` and **not** removed.
- **Property tests:** SCCs partition all nodes; same-SCC ⇔ mutual reachability; every `depends_on`
  prerequisite precedes its dependent in the sequence.
- **Durability:** the analysis persists and recomputes identically in a fresh interpreter;
  canonical keys are the identity throughout; provenance is retained on every candidate.

Tests: `rdo/tests/test_stage3_graph_intelligence.py` (14 tests); full RDO suite **73 passing**.

## Verified vs. remaining

- **Verified:** all six capabilities above, with focused + property + end-to-end tests.
- **Bounded out (OFT):** no general graph platform; `produces_for` is derived only at the
  objective's top level; dedup surfaces candidates for a human/next step, it does not decide
  equivalence; sequence uses `depends_on` prerequisites only (`influences` are feedback, reported
  but not sequenced).
- **Unknown / out of scope:** runtime observation (host-only, NEX in standby); automatic
  resolution of duplicate candidates (deliberately left to review).

## Specification basis and remaining OFT boundary

The implementation cites **RDO v1.4** in docstrings; the governing sequence here is **v1.4 §29**.
The v1.2 / v1.3 / v1.4 texts, the Watcher v3.0 spec and the Master Roadmap v3.0 are not in the
workspace. No version reconciliation is assumed; the precedence remains for founder resolution.
