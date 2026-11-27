# RDO v1.4 — Implementation Gap Audit

**Date:** 27 November 2026  
**Working specification:** RDO v1.4 — Optimal Functional Tension  
**Specification provenance:** Founder-supplied 20 November 2026 text; 47,172 bytes; SHA-256 recorded in the 24 November conversation as `382d634d03bc15701d9de4dcbc2629b966ffd8370c370f0307a57a853f4db926`.  
**Working-status note:** On 24 November the founder indicated they believed v1.4 had been approved. Treat v1.4 as the current working specification. Preserve v1.3 as historical implementation lineage; do not claim the consolidated NEX S-register contains a formal frozen supersession record.  
**Repository evidence snapshot:** `main` at `09d98c554678b4675de7d1183c39d1213ccfd9ec` (including PRs #310, #314, #316, #321, #323, #324 and #328).

This is an implementation audit against the recovered v1.4 requirements, not a replacement specification. The raw v1.4 attachment is not mounted in the current repository/Library workspace, so exact clause wording and un-recovered thresholds remain UNKNOWN. The recovered requirements below are sufficient to identify implementation gaps without pretending to reproduce every source clause.

---

## 1. Executive finding

The RDO is not a blank design. It already contains a working deterministic recursive engine, repository reconciliation, canonical-key convergence, anti-requirements, typed graph analysis, a partial three-level OFT assessor, work-package generation, persistence/resume, learning records, and non-executing handoff infrastructure.

The Stage-2 belief-decay example is a genuine end-to-end vertical slice from **structured seed obligations** through expansion, reconciliation, graph/tension analysis, prioritisation, work packages, persistence and fresh-process resume. It is not yet a complete v1.4 vertical slice because:
- the input requires externally supplied seed obligations and reconciliation signatures; raw natural-language intent is not compiled into the initial obligation network by the RDO itself;
- accepted context is preserved; unmapped context blocks readiness and exclusions propagate to anti-requirements, but context is not yet comprehensively mapped into obligations or checked against a complete obligation/evidence network;
- the relationship model carries typed UNKNOWN-first Interface Tension Profile and operating-envelope evidence into relationship assessment, but its dimensions are not yet assessed against calibrated requirements;
- q/tau performance-margin evidence now validates arithmetic, identity and comparable envelope constraints, but capacity/headroom assessment, operating-envelope classification, feedback-loop stability, multi-objective trade-offs and marginal-value/hysteresis machinery remain incomplete;
- the twelve adversarial cases are only partly represented in tests.

**The next vertical-slice increment is closing evidence-to-assessment gaps in feedback stability, failure propagation and neighbouring-capability impact.** The interface profile, operating-envelope evidence and q/tau margin records now exist; the next work must connect observations to calibrated assessment without inventing thresholds or verdicts. Extend the existing model, not replace the orchestrator or create a parallel RDO.

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
| `rdo/tests/test_experiment_registry_entry_points.py` | 1 |
| `rdo/tests/test_experiment_registry_fail_closed.py` | 7 |
| `rdo/tests/test_feedback_loop.py` | 9 |
| `rdo/tests/test_handoff.py` | 19 |
| `rdo/tests/test_intake.py` | 14 |
| `rdo/tests/test_interface_profile.py` | 7 |
| `rdo/tests/test_interface_tension.py` | 25 |
| `rdo/tests/test_objective_context_contract.py` | 2 |
| `rdo/tests/test_operating_envelope.py` | 9 |
| `rdo/tests/test_performance_margin.py` | 12 |
| `rdo/tests/test_reconcile_path_boundary.py` | 2 |
| `rdo/tests/test_stage2_extrapolator_mvp.py` | 24 |
| `rdo/tests/test_rdo.py` | 62 |
| `rdo/tests/test_stage3_graph_intelligence.py` | 21 |
| `rdo/tests/test_stage4_belief_audit.py` | 11 |
| `rdo/tests/test_stage5_pathway.py` | 6 |
| `rdo/tests/test_stage6_learning_loop.py` | 23 |
| `rdo/tests/test_stage7_execution_watcher.py` | 12 |

**Total:** 18 test modules; 263 test functions at this repository snapshot.

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
| Relationship-level tension | Explicit unbounded-influence and unresolved-dependency findings remain; otherwise absent or uncalibrated interface evidence now yields UNKNOWN rather than inferred SUFFICIENT | Partial; fail-closed assessment improved |
| System-level tension | `assess_system` detects cycles, in-degree concentration (threshold 3), and necessary-obligation readiness | Partial |
| Interface Tension Profile | Typed UNKNOWN-first profile is attached optionally to `Relationship`; relationship assessment exposes validated dimension evidence and keeps absent/uncalibrated evidence UNKNOWN. PR #316 makes malformed serializers fail closed; PR #321 validates evidence status values | Evidence capture and summary implemented; calibrated assessment incomplete |
| Provider/consumer, purpose/direction, contract/schema | Typed profile fields exist and default to UNKNOWN | Foundation implemented |
| Provenance/quality, timing/latency/frequency/freshness | Evidence containers exist for provenance, data quality, timing, latency, frequency and freshness | Foundation implemented; no source measurements |
| Influence magnitude/boundaries, authority and coupling | Magnitude, authority-boundary and coupling evidence dimensions are represented | Foundation implemented; no calibrated bounds |
| Failure semantics/observability | Error handling, fallback, recovery and observability dimensions are represented | Foundation implemented; no failure-envelope assessment |
| Capacity/headroom and operating envelopes | Capacity/headroom evidence fields exist; `OperatingEnvelopeAssessment` represents NORMAL/BUSY/DEGRADED/STRESS/RECOVERY with separate declared/assessed states, load/capacity/headroom, transition/recovery evidence. PR #306 requires traceable assessment evidence, confidence and provenance for an assessed state. PR #310 is merged: relationship-level assessment exposes operating-envelope evidence, including explicit-defect paths; no classification or headroom calculation | Partial |
| Feedback sufficiency/stability | `FeedbackLoopAssessment` is merged with gain, delay, damping, oscillation, overshoot, recovery and observation-window evidence. PR #303 also merged UNKNOWN-first feedback records into `assess_system` cycle detection; PR #304 requires traceable assessment evidence, confidence and provenance for non-UNKNOWN verdicts. No stability calculation or hysteresis assessment | Partial |
| Duplication | Semantic duplicate candidates are surfaced by graph analysis; profile now carries a duplication evidence dimension | Partial-to-good; no measured duplication cost |
| Failure propagation | Merged PR #328 adds `failure_propagation_candidates()` over explicit `depends_on` paths, deterministic shortest paths, cycle detection, relationship provenance and UNKNOWN/partial input handling | **Partial** — structural candidates only; no runtime propagation, probability, severity, fallback/recovery assessment or causal claim |
| Performance margins q/tau/m | `PerformanceMargin` represents q, tau, unit, normalization, evidence and confidence; computes exact m=q-tau only for finite comparable values; exact zero remains a boundary, not a pass. PR #305 validates arithmetic/evidence and PR #323 validates identity, envelope comparability and overflow. PR #325 adds per-relationship margin evidence and only promotes complete q/tau reference pairs (pending exact-head CI) | **Partial** — evidence is attached to relationships; no calibrated threshold selection, margin aggregation or sufficiency verdict |
| NetValue and Pareto trade-off | Prioritisation uses separate dimensions plus an explicitly uncalibrated weighted sort score; no feasible Pareto comparison or net-value calculation | Missing |
| Marginal-value stopping | Depth/terminal/reuse stopping exists; no marginal-value threshold or hysteresis | Partial |

Important restraint: do not convert absent evidence into a positive “sufficient” verdict. Missing interface profiles, thresholds or measurements must remain UNKNOWN until evidence is supplied.

## 4. Twelve v1.4 adversarial cases — current coverage

The case labels below are concise summaries recovered from the v1.4 review context, not claimed verbatim titles.

| Case | Adversarial condition | Current evidence | Assessment |
|---|---|---|---|
| A | Underdeveloped node | `test_under_expansion_builds_children_when_missing` | **Covered** |
| B | Overdeveloped node | `test_over_expansion_stopped_by_reuse`; `recognize_sufficiency` | **Partial** — sufficiency/reuse restraint exists; no full complexity-vs-value assessment |
| C | Unstable feedback | Graph-cycle classification plus merged `FeedbackLoopAssessment`; PR #303 emits UNKNOWN-first evidence records for detected feedback cycles; PR #304 validates any assessor-supplied non-UNKNOWN verdict | **Partial** — topology and evidence capture are integrated; no measured gain/stability/hysteresis calculation or calibrated stability thresholds |
| D | Insufficient headroom | Capacity/headroom evidence dimensions and q/tau margin inputs exist; relationship-level envelope evidence integration is merged; no calibrated operating-envelope/headroom assessment | **Partial** — evidence representation and verdict provenance are stronger; no headroom calculation or sufficiency verdict |
| E | Excessive authority | `Relationship.authority`, `assess_signal_authority`, real-repository demo assertions | **Partial** — capability/authority distinction exists; no complete interface profile or dedicated adversarial threshold test |
| F | Duplicate discovery | Safe canonical convergence; `graph.dedup_candidates`; `test_safe_convergence_merge` | **Covered** |
| G | Speculative obligation | Hypothesis classification and `test_genius_feedback_is_hypothesis` | **Partial** — demonstrated for one domain hypothesis, not a general adversarial obligation-quality test |
| H | Protected experiment | Watcher registry and fail-closed eligibility; active/unknown registry tests | **Covered** |
| I | Local improvement causes global regression | No multi-objective local/global net-value comparison | **Missing** |
| J | Neighbouring capability changes | `run_cycle()` recomputes node, relationship and system tension; PR #329 adds a persisted-cycle before/after comparison for incident relationships, assessment dimensions/verdicts, missing/ambiguous evidence and endpoint integrity (pending exact-head CI) | **Partial** — differential structural/evidence changes can be surfaced; no causal attribution, net-value/harm calculation or automatic mutation |
| K | Excessive recursion | max-depth, terminal kinds and frontier reasons; `test_max_depth_bounds_expansion` | **Covered** |
| L | Negative development outcome | Predicted/actual comparison, disconfirmation and confidence reduction; PR #314 merged an objective-scoped regression-risk candidate into current main | **Partial** — a scoped candidate can be surfaced, but it does not yet mechanically reverse or restrict a recommendation |

A test with a similar name is not counted as full coverage unless it exercises the specified adversarial condition and asserts the required outcome.

## 5. Objective-context gap (G-91) — narrowed by merged implementation

PR #287 merged objective-context propagation into `run_cycle()`, cycle persistence, summary and handoff. The system now preserves intent, owner/source, scope, affected paths, assumptions, constraints, exclusions and acceptance criteria as context. It creates explicit UNKNOWN/unmapped context items, marks execution readiness BLOCKED while items remain unmapped, keeps bounded human handoff reviewable, and propagates exclusions into package anti-requirements. Legacy no-context cycles retain their prior readiness behaviour; legacy handoff manifests remain readable.

**Implemented and test-verified:** context is preserved; scalar intent is handled as a single item; unknown context remains unmapped; execution readiness is blocked; exclusions are propagated; cycle resume retains context; handoff carries the assessment; acceptance criteria expose `verification_status: unknown`, `mapped_obligations: []`, and `verification_evidence: []` (PR #296).

**Remaining gap:** context items are not yet mapped automatically or through a structured evidence-resolution workflow into obligations and independent evidence. Acceptance criteria now have an explicit UNKNOWN-first verification contract, but not automated mapping or independent completion evidence. Owner/source are provenance fields, not enforced authority. This remains a planning/review capability gap, not evidence of an execution incident.



**Evidence-integrity update (27 November 2026):** PR #298 makes malformed persisted interface-profile shapes explicitly diagnosable. PRs #304–#306 strengthen evidence completeness for feedback verdicts, performance margins and assessed operating envelopes. These changes enforce traceability and UNKNOWN handling; they do not supply missing v1.4 thresholds or implement stability/headroom calculations. PR #310 merged the relationship-level operating-envelope evidence connection. PR #314 merged objective-scoped regression-risk learning: traceable regression evidence produces a low-confidence, exact-objective candidate that is surfaced in later matching cycles. It does not automatically reverse or restrict recommendations. PR #316 made malformed interface-profile serializers fail closed. Merged PR #321 validates interface evidence status values. Merged PR #323 strengthens performance-margin identity, envelope and overflow validation. Merged PR #324 hardens exact-scope pattern collision, persistence and mutation integrity. PR #328 adds structural failure-propagation candidates. PR #329 adds differential neighbouring-impact analysis and is pending exact-head CI.

## 6. Next implementation slice

**Target:** Evidence-backed feedback-loop stability and calibrated system-level OFT assessment, building on merged structural failure candidates and pending relationship-level margin/differential-impact integration.

Completed foundation:
1. Added a typed, serialisable UNKNOWN-first interface profile to `Relationship`, preserving legacy positional construction.
2. Represented provider/consumer, purpose/direction, contract/schema, provenance/quality, timing/latency/frequency/freshness, influence magnitude/authority/coupling, reversibility, error handling, fallback/recovery, observability, capacity/headroom, feedback sufficiency/stability, duplication and failure propagation.
3. Relationship-level assessment now refuses to infer SUFFICIENT when the profile is absent or when evidence exists without calibrated thresholds/margins. Existing explicit findings for unbounded influence and unresolved necessary dependencies retain precedence.
4. Merged PR #310 carries operating-envelope evidence into relationship assessment, retaining declared/assessed separation and UNKNOWN where evidence is incomplete.
5. Merged PR #316 makes malformed custom interface-profile serializers fail closed as invalid shape.

Next bounded sequence:
1. Complete measured feedback-loop stability only when calibrated criteria, observation windows and evidence are grounded; preserve loop members and relationships, and never equate graph topology with instability or remove cycles automatically.
2. Merged PR #328 supplies structural failure-propagation candidates; next add evidence-backed runtime failure semantics only when failure mode, propagation, fallback, recovery and observation evidence are available. Do not infer runtime propagation from graph structure.
3. Complete and merge PR #325 relationship-level q/tau evidence integration after exact-head CI, preserving UNKNOWN for incomplete pairs and avoiding aggregation or verdicts.
4. Complete and merge PR #329 persisted-cycle differential neighbour analysis after exact-head CI; retain partial status for missing/ambiguous snapshots and do not infer causality.
5. Add insufficient-headroom and unstable-feedback adversarial cases with explicit evidence validation and UNKNOWN-first assertions.
6. Investigate local-improvement/global-regression with actual objective/evidence data before proposing net-value weights or Pareto rules.
7. Run the Stage-2 belief-development slice and fresh-process persistence/resume against current main.
8. Consider Pareto/net-value and marginal-value stopping only after grounded calibration and explicit separation from relationship evidence.

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
