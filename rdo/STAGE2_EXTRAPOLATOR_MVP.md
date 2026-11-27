# RDO Stage 2 — Extrapolator MVP (vertical slice)

**Governing step:** RDO v1.3 §16 **Stage 2** (Extrapolator MVP). Kept distinct from
**Stage 4** (read-only belief audit): existing belief mechanisms are inspected
**read-only** only to ground reconciliation; nothing here touches the live store.

**Historical coordination.** The original implementation was isolated on
`claude/rdo-stage2-extrapolator-mvp`, based on `0cada90` (the former PR #48 head), with
`rdo/`-only ownership. As of 26 Nov 2026, foundational PR #46 has been merged and the Stage 2–7
capabilities are being integrated together through PR #124 on the hardened mainline. The older
stage branches are retained as source history, not as a separate merge sequence.

## The objective (a real belief-*development* objective)

> Add staleness-based confidence decay for beliefs: decay the confidence of beliefs not
> reactivated within a window, on a bounded schedule, never below a floor, without
> deleting beliefs or breaking consumers.

This is a *development* objective (build a mechanism), not an audit. It was chosen because
it reconciles against real belief infrastructure, distinguishes source anchors from semantic reuse,
and recurses into a multi-level obligation graph.

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
| Dependency-cycle detection | **REUSE (present + wired)** | `tension._find_cycles` (DFS over `depends_on`/`influences`) runs every cycle via `assess_system`; it surfaces a `feedback_cycles` system tension with the cycle path. The belief-decay slice is acyclic. (Correction: an earlier draft wrongly listed this as absent/Stage 3.) |
| SCC / completeness / sequence analysis, typed edges, dedup beyond exact-key | **MISSING → Stage 3** | not present in `rdo/`; these are RDO v1.3 §16 **Stage 3** (graph intelligence), not built here. |

No duplicate persistence, graph or reconciliation mechanism was created.

## Capabilities & acceptance rules → test evidence

The original isolated-stage report recorded 12 Stage-2 tests and 48 RDO tests passing. The
integration has since added semantic-reuse, fail-closed registry and evidence-provenance regressions;
the current full repository CI on PR #124 is the authoritative integrated result.

- **Accept/structure objective** → `test_accepts_and_structures_objective`
- **Recursive discovery** (8 seeds → 35 obligations, depth 2) → `test_recursively_discovers_obligations`
- **Per-obligation parent/rationale/class/confidence/impact/evidence** → `test_records_each_obligation_attribute`
- **Bounded reconciliation** (`belief_activation` is `signature_matched` pending independent semantic review; MISSING decay policy + daemon) → `test_reconciles_against_repository_evidence`
- **Duplication → anti-requirements** → `test_identifies_duplication_as_anti_requirements`
- **No verification without acceptance evidence** (source matches remain separate from reviewed reuse; no semantic reuse is claimed without an explicit current review) → `test_no_verification_without_acceptance_evidence`
- **Stable canonical IDs, no silent merge** → `test_stable_canonical_ids_and_no_silent_merge`
- **Traceable acyclic graph** (every node traces to a seed; `depends_on` depth-monotonic) → `test_traceable_acyclic_dependency_graph`
- **Cycles are actively detected** (`tension._find_cycles` flags a deliberate cycle; slice is clean) → `test_dependency_cycles_are_detected`
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

## Next in the v1.4 §29 order — graph intelligence

The MVP provides the obligation graph (`parent_key` tree + `depends_on` edges) Stage 3
builds on. Basic **cycle detection already exists** (`tension._find_cycles`, wired via
`assess_system`). Stage 3 adds what is *not* yet present: deduplication beyond exact-key
(currently exact-key only), typed edges beyond `depends_on`, **SCC** decomposition, and
completeness/sequence analysis.

## Specification basis and historical stage labels

RDO v1.4 — Optimal Functional Tension is the current working specification; the founder
indicated on 24 November that they believed it had been approved. The earlier v1.3 §16
sequence remains historical evidence for the stage labels used by this report and earlier
implementation work. Do not treat those historical labels as a replacement for the v1.4 §29
development order. The exact 47,172-byte v1.4 source was supplied in a prior conversation
(SHA-256 recorded there) but its raw bytes are not mounted in this repository workspace, so
this report does not claim a fresh byte-level clause crosswalk. The current implementation
gap audit records the requirements recovered from that source and the source-level evidence.

---

## Stage 2 acceptance audit (six repository-level gaps closed)

All changes are bounded to Stage 2, reuse existing mechanisms, keep canonical IDs and
persistence backward-compatible, and preserve unresolved/deferred information. No Stage 3
graph-intelligence (SCC/typed-edges/completeness) was started.

| # | §15 requirement | Implementation (path · symbol) | Test | Status |
|---|---|---|---|---|
| 1 | Shared prerequisite / converging branch demonstrated in real expansion | `extrapolator.py` — `consumer` rule's `runtime_verification` now a **shared** target (`shared_runtime_effect`); `knowledge.belief_decay_idea` has a 2nd consumer, so both converge via `_merge` (in-degree 2) | `test_convergence_shared_prerequisite` | **VERIFIED** |
| 2 | Prediction vs reviewed outcome + calibration | `report.run_stage2_belief_decay` records a caller-attributed **planning review** (`review_kind="planning_review"`, `kind` stays `native_planning`); the reviewer label is not independently authenticated, `compare` → `derive_lessons` → `PatternMemory` (durable) | `test_planning_review_and_calibration_are_durable` | **VERIFIED** (reviewer-attributed planning record, **not** an authenticated identity or execution outcome) |
| 3 | Expansion-budget frontier preserved + resumable | `run_cycle(max_depth=…)` exposed; full `frontier` (with reasons) persisted on `CycleRecord.frontier` | `test_frontier_preserved_under_expansion_budget` | **VERIFIED** |
| 4 | Complete, consistent six counts | `orchestrator.run_cycle` → `CycleRecord.counts` {discovered, unique, reuse, net_new, deferred, unresolved}, definitions in-code; `unique == discovered` proves no silent collision | `test_complete_counts_persisted_and_consistent` | **VERIFIED** |
| 5 | Meaningful work-package ordering + unresolved visible | `prioritise.build_work_packages` sorts packages eligible-first, then priority desc, then key (deterministic); `net_new` includes `RECON_UNKNOWN`; anti-requirements excluded | `test_work_packages_priority_ordered_not_alphabetical` | **VERIFIED** |
| 6 | Cycle detection **and** classification | `tension._classify_cycle` (prerequisite_cycle / feedback_loop / unknown) feeds `assess_system`: prerequisite cycle → `underdeveloped`, feedback/unknown → `unknown` (not forced) | `test_cycle_detection_and_classification` | **VERIFIED** |

End-to-end: `test_stage2_end_to_end`. Suite at the current source snapshot: **24** Stage-2 test functions; see the current RDO test files for broader suite counts.
Persisted artefact `cycle_belief_decay_mvp.json` (~65 KB) carries `counts`, `frontier`, the
reviewed `actual` (`native_planning`) and the full graph; it resumes in a fresh process.

### Count definitions (internally consistent)
- **discovered** — distinct obligation nodes (post-merge).
- **unique** — distinct canonical keys; `unique == discovered` is the no-silent-collision invariant.
- **reuse** — reconciled to an existing mechanism (`REUSE_EXISTING`).
- **net_new** — to build (`MISSING`/`PARTIAL`).
- **deferred** — frontier items (stopped with a recorded reason).
- **unresolved** — no reconciliation signature (`RECON_UNKNOWN`): an honest gap, surfaced as candidate work.

### What remains explicitly out of Stage 2 (not started)
Stage 3 graph intelligence: SCC decomposition, typed edges beyond `depends_on`/`influences`,
dedup beyond exact-key, completeness/sequence analysis. Implementation-outcome calibration
(execution, not planning review) is the **Stage 6** learning loop.

### Remaining v1.4 fidelity gaps
These six closures are a local Stage 2 acceptance audit, not proof that all v1.4 MVP criteria
or all twelve adversarial cases are satisfied. v1.4 is the current working basis; v1.3 remains
historical. The recovered source summary does not supply every exact OFT threshold or complete
Interface Tension Profile field definition, so those remain explicit UNKNOWNs pending direct
source reinspection. See RDO_V1_4_IMPLEMENTATION_GAP_AUDIT_2026-11-27.md.

---

## Integrity pass (trustworthiness, not test count)

Four correctness refinements on top of the §15 closures, bounded to Stage 2, reuse-first:

1. **Calibration provenance.** `run_stage2_belief_decay(review=None)` writes **no** pattern by
   default — a predetermined demonstration never becomes a learned production pattern (the CLI
   path writes nothing to `patterns.jsonl`). Calibration runs **only** from a supplied review,
   which must name its `reviewer`; derived patterns carry `…|planning_review|reviewer=<id>`
   provenance and the cycle stays `native_planning`, so a reviewed plan is never confused with an
   execution outcome. Deterministic fixture reviews live in the tests, in isolated temp stores.
2. **Deferred accounting.** `counts["deferred"]` is now **genuinely-deferred only** (budget /
   no-rule); anti-requirement and already-satisfied stops are no longer double-counted (they live
   under anti-requirements and reuse). The complete frontier is retained on `CycleRecord.frontier`
   and categorised by `extrapolator.frontier_breakdown` into
   `{deferred, anti_requirement, already_satisfied, other}`, surfaced as `frontier_*` counts that
   sum to `frontier_total`. For the belief-decay slice: `deferred=0`, `frontier_total=4`
   (3 anti-requirement + 1 already-satisfied).
3. **Safe convergence.** `extrapolator._merge` now refuses to collapse obligations that do not
   mean the same thing: a different **kind**, or a build-vs-anti-requirement classification, under
   one canonical key raises **`MergeConflict`** (surfaced, never silent). Compatible convergence
   keeps one node, both parent relationships, both provenance paths, and takes the stronger
   classification (recording the raise). The shared runtime-verification node merges cleanly.
4. **Work-package ordering (honest).** The guarantee is exactly: eligible (buildable) tier before
   blocked tier, then priority desc, then canonical key (deterministic). It is **NOT** a full
   prerequisite topological order — blocked packages are ranked by score among themselves, so one
   blocked package can precede another it depends on. Hard blockers and unresolved prerequisites
   stay visible (`WorkPackage.blockers`); full prerequisite ordering is left to Stage 3.

Tests: +3 focused regressions (26 Stage-2 tests; **59** RDO tests pass). The default CLI artefact
carries no production pattern; a reviewer-attributed calibration is durable and resumable.


## Integration evidence correction (26 Nov 2026)

The current hardened RDO distinguishes three states that earlier Stage-2 notes conflated:
a source signature match, independently reviewed semantic reuse, and missing/partial/unknown.
The `belief_activation` table is **source-matched** as the recency mechanism, but this Stage-2
slice does not carry a current semantic-review decision for its exact obligation. It is therefore
reported in `signature_matches`, not `reused`, and its dependent work is not cleared by the
signature alone. The decay policy and applier remain net-new/missing.

The stage runner now obtains active experiment state from the Watcher registry. An unavailable,
unmeasured or malformed registry returns UNKNOWN and blocks eligibility; only an explicitly
verified empty list represents no active/pending experiment. Tests that need a known-empty registry
must pass `active_experiments=[]` explicitly.

This correction preserves the reuse-first design while preventing source presence from being
promoted into semantic satisfaction without review.


### Controlled-fixture persistence boundary

A `controlled_fixture_review` can exercise the comparison and lesson-candidate pipeline, but its
candidate lessons are **not** written to reusable `PatternMemory`. Its cycle record and provenance
remain available for the test/report; fixture-derived candidates cannot influence later RDO cycles.
Only an explicitly caller-attributed `planning_review` follows the durable calibration path, and the
reviewer identity remains unverified by the tool.
