# RDO v1.4 — Implementation Gap Audit

**Date:** 27 November 2026  
**Working specification:** RDO v1.4 — Optimal Functional Tension  
**Specification provenance:** Founder-supplied 20 November 2026 text; 47,172 bytes; SHA-256 recorded in the 24 November conversation as `382d634d03bc15701d9de4dcbc2629b966ffd8370c370f0307a57a853f4db926`.  
**Working-status note:** On 24 November the founder indicated they believed v1.4 had been approved. Treat v1.4 as the current working specification. Preserve v1.3 as historical implementation lineage; do not claim the consolidated NEX S-register contains a formal frozen supersession record.  
**Repository evidence snapshot:** `main` at `f03a3d2e7b9c71801e44be73cf728c01cb791c9d`.

This is an implementation audit against the recovered v1.4 requirements, not a replacement specification. The raw v1.4 attachment is not mounted in the current repository/Library workspace, so exact clause wording and un-recovered thresholds remain UNKNOWN. The recovered requirements below are sufficient to identify implementation gaps without pretending to reproduce every source clause.

---

## 1. Executive finding

The RDO is not a blank design. It already contains a working deterministic recursive engine, repository reconciliation, canonical-key convergence, anti-requirements, typed graph analysis, a partial three-level OFT assessor, work-package generation, persistence/resume, learning records, and non-executing handoff infrastructure.

The Stage-2 belief-decay example is a genuine end-to-end vertical slice from **structured seed obligations** through expansion, reconciliation, graph/tension analysis, prioritisation, work packages, persistence and fresh-process resume. It is not yet a complete v1.4 vertical slice because:
- the input requires externally supplied seed obligations and reconciliation signatures; raw natural-language intent is not compiled into the initial obligation network by the RDO itself;
- accepted context such as scope, constraints, exclusions and acceptance criteria is preserved in the intake ledger but not enforced by the planner;
- the current relationship model is much thinner than the v1.4 Interface Tension Profile;
- OFT currently has three-level structure but not the full performance-margin, capacity/headroom, operating-envelope, multi-objective, feedback-stability/hysteresis and marginal-value machinery;
- the twelve adversarial cases are only partly represented in tests.

**The next vertical-slice increment is the typed Interface Tension Profile and evidence-backed performance margins.** It should extend the existing model, not replace the orchestrator or create a parallel RDO.

## 2. Current implementation inventory

| Area | Current implementation | Evidence / boundary |
|---|---|---|
| Objective intake | Provider-neutral JSON schema v1; append-only revisions; SHA-256 linkage; clean-repository requirement | `rdo_adapters/objective_intake.py`, `rdo/schemas/objective.v1.schema.json`, `rdo/tests/test_intake.py` |
| Initial seed creation | External caller supplies `seed_obligations`, relationships and reconciliation signatures | No internal raw-intent-to-seed compiler found |
| Recursive expansion | Fixed generic rule catalogue, terminal kinds, max-depth bound, explicit frontier stop reasons | `rdo/extrapolator.py` |
| Convergence | Canonical-key merge; compatible provenance merges; incompatible collisions raise `MergeConflict`; shared prerequisites | `rdo/extrapolator.py`, Stage-2 tests |
| Semantic duplicate discovery | Similarity/evidence candidates surfaced for review; no automatic semantic merge | `rdo/graph.py`, Stage-3 tests |
| Classification | Necessary, conditional, optional, future, hypothesis, unknown, anti-requirement | `rdo/model.py` |
| Repository reconciliation | Source signatures; missing/partial/unknown/signature-matched/reuse states; semantic reuse review required | `rdo/reconcile.py` |
| Graph intelligence | Typed edges, SCC decomposition, duplicate candidates, completeness, dependency sequencing | `rdo/graph.py`; 14 Stage-3 test functions |
| OFT | Node/relationship/system verdicts; evidence vs inference; basic cycle/readiness/resource-concentration checks; signal-authority audit | `rdo/tension.py`; partial v1.4 implementation |
| Prioritisation | Eligibility gates; importance, dependency centrality, readiness, uncertainty, reversibility; provisional uncalibrated sort score | `rdo/prioritise.py` |
| Work packages | Unresolved work/review obligations, blockers, anti-requirements | `rdo/prioritise.py` |
| Persistence/resume | CycleStore and fresh-process resume | `rdo/memory.py`, Stage-2 tests |
| Learning | Predicted vs actual, disconfirmation, candidate lessons, pattern provenance and confidence bounds | `rdo/memory.py`, Stage-6 tests |
| Handoff | Immutable handoff, scope review/acceptance records, independent Watcher source/path subprocess | Stage-7 modules; no arbitrary test execution |
| Runtime evidence | Host-only; cloud RDO cannot assert NEX runtime behaviour | Existing eligibility and handoff boundaries |

### Test inventory at this snapshot

| Test file | Test functions |
|---|---:|
| `rdo/tests/test_stage2_extrapolator_mvp.py` | 24 |
| `rdo/tests/test_rdo.py` | 62 |
| `rdo/tests/test_stage3_graph_intelligence.py` | 14 |
| `rdo/tests/test_stage4_belief_audit.py` | 11 |
| `rdo/tests/test_stage5_pathway.py` | 6 |
| `rdo/tests/test_stage6_learning_loop.py` | 11 |
| `rdo/tests/test_stage7_execution_watcher.py` | 12 |
| `rdo/tests/test_intake.py` | 14 |
| `rdo/tests/test_handoff.py` | 18 |

These are function counts, not parametrised case counts or a claim that every v1.4 acceptance criterion is covered. The Stage-2 report's older count of 20 Stage-2 tests / 56 RDO tests is stale relative to the current source tree.

## 3. OFT implementation gap

v1.4's Optimal Functional Tension is a constrained multi-objective assessment across three levels:
- **Node:** capability, reliability, adaptability, observability and robustness weighed against resource consumption, complexity and maintenance burden.
- **Relationship/interface:** influence magnitude and boundaries, information timing/form, duplication, feedback sufficiency/stability and failure propagation.
- **System:** stability, resource distribution, growth room/headroom, bottlenecks/dominance and adaptability.

The recovered v1.4 summary also identifies operating envelopes (normal, busy, degraded, stress, recovery), capacity/headroom, capability-versus-authority, anti-requirements, marginal-value recursive stopping and hysteresis/stability windows.

The recovered mathematical framing includes:
- performance margin: `m_ij = q_ij - tau_ij`;
- net value of a proposed change: functional benefit minus resource, complexity, coupling and risk costs;
- a feasible Pareto-efficient configuration rather than maximising a single score.

Current source comparison:

| v1.4 concern | Current source behaviour | Status |
|---|---|---|
| Node-level tension | `assess_node` primarily interprets classification and repository reconciliation state | Partial |
| Relationship-level tension | `assess_relationship` checks unbounded influence and unresolved necessary dependencies | Partial |
| System-level tension | `assess_system` detects cycles, in-degree concentration (threshold 3), and necessary-obligation readiness | Partial |
| Interface Tension Profile | `Relationship` has only src, dst, kind, authority, reversible and note | Missing |
| Provider/consumer, purpose/direction, contract/schema | No typed profile fields | Missing |
| Provenance/quality, timing/latency/frequency | No typed profile fields or measured interface evidence | Missing |
| Influence magnitude/boundaries and authority | Basic authority field and separate source audit; magnitude/boundary profile incomplete | Partial |
| Failure semantics/observability | Not represented as interface dimensions | Missing |
| Capacity/headroom and operating envelopes | No capacity/headroom model or normal/busy/degraded/stress/recovery envelope | Missing |
| Feedback sufficiency/stability | Cycles are detected and classified; gain/stability/hysteresis are not measured | Partial |
| Duplication | Semantic duplicate candidates are surfaced by graph analysis | Partial-to-good; no interface-level duplication cost |
| Failure propagation | Not represented as a typed interface dimension | Missing |
| Performance margins q/tau/m | No explicit metric/threshold/margin model | Missing |
| NetValue and Pareto trade-off | Prioritisation uses separate dimensions plus an explicitly uncalibrated weighted sort score; no feasible Pareto comparison or net-value calculation | Missing |
| Marginal-value stopping | Depth/terminal/reuse stopping exists; no marginal-value threshold or hysteresis | Partial |

Important restraint: do not convert absent evidence into a positive “sufficient” verdict. Missing interface profiles, thresholds or measurements must remain UNKNOWN until evidence is supplied.

## 4. Twelve v1.4 adversarial cases — current coverage

The case labels below are concise summaries recovered from the v1.4 review context, not claimed verbatim titles.

| Case | Adversarial condition | Current evidence | Assessment |
|---|---|---|---|
| A | Underdeveloped node | `test_under_expansion_builds_children_when_missing` | **Covered** |
| B | Overdeveloped node | `test_over_expansion_stopped_by_reuse`; `recognize_sufficiency` | **Partial** — sufficiency/reuse restraint exists; no full complexity-vs-value assessment |
| C | Unstable feedback | `test_cycle_detection_and_classification`; feedback loops remain UNKNOWN and are not removed | **Partial** — topology classification only; no gain/stability/hysteresis measurement |
| D | Insufficient headroom | No capacity/headroom profile or operating-envelope model | **Missing** |
| E | Excessive authority | `Relationship.authority`, `assess_signal_authority`, real-repository demo assertions | **Partial** — capability/authority distinction exists; no complete interface profile or dedicated adversarial threshold test |
| F | Duplicate discovery | Safe canonical convergence; `graph.dedup_candidates`; `test_safe_convergence_merge` | **Covered** |
| G | Speculative obligation | Hypothesis classification and `test_genius_feedback_is_hypothesis` | **Partial** — demonstrated for one domain hypothesis, not a general adversarial obligation-quality test |
| H | Protected experiment | Watcher registry and fail-closed eligibility; active/unknown registry tests | **Covered** |
| I | Local improvement causes global regression | No multi-objective local/global net-value comparison | **Missing** |
| J | Neighbouring capability changes | No typed interface profile or adjacent-capability impact re-assessment | **Missing** |
| K | Excessive recursion | max-depth, terminal kinds and frontier reasons; `test_max_depth_bounds_expansion` | **Covered** |
| L | Negative development outcome | Predicted/actual comparison, disconfirmation and confidence reduction | **Partial** — negative evidence is representable; no explicit adversarial test proves the negative result reverses/restricts the next recommendation |

A test with a similar name is not counted as full coverage unless it exercises the specified adversarial condition and asserts the required outcome.

## 5. Objective-context gap (G-91)

The objective intake validates and preserves `intent`, `owner`, `scope`, `constraints`, `exclusions` and `acceptance_criteria`. However, `submit_objective()` passes only original text, top-level assumptions, supplied seed obligations, relationships, reconciliation signatures and expansion depth into `run_cycle()`. The contextual fields remain in the append-only ledger but are not translated into obligations/anti-requirements or checked against proposed work packages; acceptance criteria are not used as a completion-verification contract.

This is an advisory capability gap, not an execution incident. The full input is auditable, but a plan can fail to reflect all preserved context. A future increment should translate context into typed obligations/anti-requirements and an explicit acceptance-verification record.

## 6. Next implementation slice

**Target:** Interface Tension Profile + evidence-backed performance margins.

Bounded sequence:
1. Add a typed, serialisable interface profile to the existing relationship model, preserving backward compatibility for existing relationships.
2. Represent provider/consumer, purpose/direction, contract/schema, provenance/quality, timing/latency/frequency, influence magnitude/authority, reversibility, failure semantics, observability, capacity/headroom, feedback sufficiency/stability, duplication and failure propagation. Fields without evidence default to UNKNOWN.
3. Add explicit `q`, `tau`, and `m=q-tau` margin records with units, evidence references and confidence. Do not invent thresholds; a missing threshold produces UNKNOWN.
4. Extend relationship-level OFT to report dimensions and blockers without collapsing them into an uncalibrated “magic score”.
5. Add focused tests for missing profile, unknown evidence, below-threshold headroom, unbounded influence, unstable feedback and failure propagation.
6. Run the existing Stage-2 belief-development slice and persist/resume it to prove backward compatibility.
7. Then add system-level operating envelopes and Pareto/net-value evaluation; do not mix those into the first profile commit.

This increment remains external/advisory RDO code. It does not change NEX runtime, the frozen S-register, Master Roadmap, feature flags, live beliefs or protected experiments. It does not authorise the final v1.4 expansion stage to bypass existing safety and approval gates.

---

## 7. Source anchors

- `rdo/model.py` — `Obligation`, `Relationship`, `TensionAssessment`, `WorkPackage`.
- `rdo/tension.py` — `assess_node`, `assess_relationship`, `assess_system`, `assess_signal_authority`, `recognize_sufficiency`.
- `rdo/extrapolator.py` — `EXPANSION_RULES`, `expand`, merge safety, frontier reasons.
- `rdo/prioritise.py` — eligibility and provisional dimensions.
- `rdo/graph.py` — SCCs, duplicate candidates, typed edges, completeness and sequence.
- `rdo_adapters/objective_intake.py` — validation and `submit_objective()`.
- `rdo/tests/test_stage2_extrapolator_mvp.py`, `rdo/tests/test_rdo.py`, `rdo/tests/test_stage3_graph_intelligence.py`.

**Conclusion:** RDO has a credible working Extrapolator vertical slice and meaningful parts of v1.4. It does not yet implement the full OFT model. The next justified development step is to enrich the existing relationship model with the v1.4 Interface Tension Profile and evidence-backed margins, then expand the adversarial suite.
