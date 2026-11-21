# RDO Stage 2 — Extrapolator MVP (vertical slice)

**Governing step:** RDO v1.3 §16 **Stage 2** (Extrapolator MVP). Kept distinct from
**Stage 4** (read-only belief audit): existing belief mechanisms are inspected
**read-only** only to ground reconciliation; nothing here touches the live store.

**Coordination.** Isolated workstream on `claude/rdo-stage2-extrapolator-mvp`, based on
`0cada90ede00ef21602740f16f1481df0574704f` (PR #48 head). File ownership: `rdo/` only —
no Watcher, NEX-runtime, experiment, baseline, tripwire or live-state edits. PRs #45–48
remain open and unmerged.

## The objective (a real belief-*development* objective)

> Add staleness-based confidence decay for beliefs: decay the confidence of beliefs not
> reactivated within a window, on a bounded schedule, never below a floor, without
> deleting beliefs or breaking consumers.

This is a *development* objective (build a mechanism), not an audit. It was chosen because
it reconciles against real belief infrastructure with an honest mix of reuse and net-new
work, and recurses into a multi-level obligation graph.

Run it: `python -m rdo stage2 --out rdo/.cycles` → prints the result and persists
`cycle_belief_decay_mvp.json`. Resume in a new process:
`python -c "from rdo.memory import CycleStore; print(CycleStore('rdo/.cycles').load('belief_decay_mvp').objective)"`.

## Reuse / adapter / missing (established before building)

| Capability the MVP needs | Decision | Mechanism / evidence |
|---|---|---|
| Accept + structure an objective | **REUSE** | `orchestrator.run_cycle` / `_run_one` |
| Recursive obligation discovery | **REUSE** | `extrapolator.expand` (parent_key / depth / rationale) |
| Bounded repository reconciliation | **REUSE** | `reconcile` (grep-verified, read-only) |
| Existing-mechanism + duplication id | **REUSE** | reconcile + anti-requirements + `prune_false_dependencies` |
| Traceable dependency graph | **REUSE** | `Relationship` (`depends_on`) + `parent_key` tree |
| Persist + resume in a new process | **REUSE** | `CycleStore.save` / `.load` (`CycleRecord(**json)`) |
| Record `impact` per obligation | **ADDED (field)** | new optional `Obligation.impact` — the one attribute with no home; a field, not a new mechanism |
| Explicit dependency-cycle / SCC detection | **MISSING → Stage 3** | not present in `rdo/`; expansion is acyclic *by construction* (parent_key tree, strictly increasing depth). Full SCC/completeness analysis is RDO v1.3 §16 **Stage 3**. |

No duplicate persistence, graph or reconciliation mechanism was created.

## Capabilities & acceptance rules → test evidence

All in `rdo/tests/test_stage2_extrapolator_mvp.py` (12 tests, all passing); full `rdo`
suite 48 passing.

- **Accept/structure objective** → `test_accepts_and_structures_objective`
- **Recursive discovery** (8 seeds → 35 obligations, depth 2) → `test_recursively_discovers_obligations`
- **Per-obligation parent/rationale/class/confidence/impact/evidence** → `test_records_each_obligation_attribute`
- **Bounded reconciliation** (REUSE `belief_activation` recency table; MISSING decay policy + daemon) → `test_reconciles_against_repository_evidence`
- **Duplication → anti-requirements** → `test_identifies_duplication_as_anti_requirements`
- **No verification without acceptance evidence** (every reuse claim file-backed) → `test_no_verification_without_acceptance_evidence`
- **Stable canonical IDs, no silent merge** → `test_stable_canonical_ids_and_no_silent_merge`
- **Traceable acyclic graph** (every node traces to a seed; `depends_on` depth-monotonic) → `test_traceable_acyclic_dependency_graph`
- **Hard prerequisites not bypassed** (blocked packages name blockers) → `test_hard_prerequisites_not_bypassed`
- **Unresolved/deferred branches survive persistence** (31 `unknown`-recon obligations reload unchanged) → `test_unresolved_branches_survive_persistence`
- **Persist + resume identity** (byte-for-byte) → `test_persist_and_resume_identity`
- **Resume in a new process** (fresh interpreter) → `test_resume_in_a_new_process`

### A real reconciliation finding (honesty check)
An initial `belief_decay_daemon` signature was repo-wide and matched a **journal** note of
an `apply_decay` daemon — a *false reuse* (prose, not code). It was tightened to scan
`substrate/` code, which has **no** belief-confidence decay applier, so the obligation now
reports **missing** correctly. This exercised the "no verification without acceptance
evidence" rule on the slice itself.

## What works vs. what remains unverified

- **Works (source + test verified):** the full slice above — deterministic core,
  reconciliation, traceable graph, persistence, cross-process resume.
- **Unverified (runtime):** none of this is `runtime_observed`; the belief store is not
  touched. The decay mechanism itself is **not implemented** — the MVP *plans* it; building
  it is downstream work, gated and out of scope here.

## Stage 3 readiness (RDO v1.3 §16)

The MVP provides the obligation graph (`parent_key` tree + `depends_on` edges) Stage 3
builds on. Stage 3 adds: deduplication beyond exact-key (currently exact-key only), typed
edges beyond `depends_on`, explicit **cycle/SCC detection**, and completeness/sequence
analysis — none of which exist yet in `rdo/`.

## Specification-discrepancy note (unresolved — awaiting governing PDFs)

The implementation's docstrings cite **RDO spec v1.4** (`§3.4, §4, §5, §6, §13, §14, §20,
§23, §24, §26, §28, §30`). The governing sequence here is **v1.3 §16**. The v1.2 / v1.3 /
v1.4 texts, the Watcher v3.0 spec, and the Master Roadmap v3.0 (with its authority
hierarchy) are **not** in the workspace. No version reconciliation is asserted and no
implementation was altered to match an assumed version; this is recorded for founder
resolution when the originals are provided.
