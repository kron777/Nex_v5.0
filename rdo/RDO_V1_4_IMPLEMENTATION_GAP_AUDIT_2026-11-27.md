# RDO v1.4 — Implementation Gap Audit

**Date:** 27 November 2026  
**Working specification:** RDO v1.4 — Optimal Functional Tension  
**Specification provenance:** Founder-supplied 20 November 2026 text; 47,172 bytes; SHA-256 recorded in the 24 November conversation as `382d634d03bc15701d9de4dcbc2629b966ffd8370c370f0307a57a853f4db926`.  
**Working-status note:** On 24 November the founder indicated they believed v1.4 had been approved. Treat v1.4 as the current working specification. Preserve v1.3 as historical implementation lineage; do not claim the consolidated NEX S-register contains a formal frozen supersession record.  
**Repository evidence snapshot:** `main` at `eabeeec51845fd36102d3e5b4fa7ab0420a92852` (after merged PRs #310, #313, #316 and #314).

This is an implementation audit against the recovered v1.4 requirements, not a replacement specification. The raw v1.4 attachment is not mounted in the current repository/Library workspace, so exact clause wording and un-recovered thresholds remain UNKNOWN. The recovered requirements below are sufficient to identify implementation gaps without pretending to reproduce every source clause.

---

## 1. Executive finding

The RDO is not a blank design. It already contains a working deterministic recursive engine, repository reconciliation, canonical-key convergence, anti-requirements, typed graph analysis, a partial three-level OFT assessor, work-package generation, persistence/resume, learning records, and non-executing handoff infrastructure.

The Stage-2 belief-decay example is a genuine end-to-end vertical slice from **structured seed obligations** through expansion, reconciliation, graph/tension analysis, prioritisation, work packages, persistence and fresh-process resume. It is not yet a complete v1.4 vertical slice because:
- the input requires externally supplied seed obligations and reconciliation signatures; raw natural-language intent is not compiled into the initial obligation network by the RDO itself;
- accepted context such as scope, constraints, exclusions and acceptance criteria is preserved in the intake ledger but not enforced by the planner;
- the relationship model now carries a typed UNKNOWN-first Interface Tension Profile and operating-envelope evidence into relationship assessment, but calibrated requirements and thresholds remain absent;
- q/tau performance-margin arithmetic and relationship-level operating-envelope evidence integration are present, but capacity/headroom calculation, operating-envelope classification, measured feedback-loop stability, multi-objective trade-offs and marginal-value/hysteresis machinery remain incomplete;
- the twelve adversarial cases are only partly represented in tests.

**The next vertical-slice increment is closing evidence-to-assessment gaps in feedback stability, failure propagation and neighbouring-capability impact.** Interface profiles, q/tau margin records and relationship-level envelope evidence integration now exist; connect observations to calibrated assessment without inventing thresholds or verdicts. Extend the existing model, not replace the orchestrator or create a parallel RDO.

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
| `rdo/tests/test_interface_profile.py` | 5 |
| `rdo/tests/test_interface_tension.py` | 22 |
| `rdo/tests/test_objective_context_contract.py` | 2 |
| `rdo/tests/test_operating_envelope.py` | 9 |
| `rdo/tests/test_performance_margin.py` | 8 |
| `rdo/tests/test_rdo.py` | 62 |
| `rdo/tests/test_reconcile_path_boundary.py` | 2 |
| `rdo/tests/test_stage2_extrapolator_mvp.py` | 24 |
| `rdo/tests/test_stage3_graph_intelligence.py` | 14 |
| `rdo/tests/test_stage4_belief_audit.py` | 11 |
| `rdo/tests/test_stage5_pathway.py` | 6 |
| `rdo/tests/test_stage6_learning_loop.py` | 18 |
| `rdo/tests/test_stage7_execution_watcher.py` | 12 |

**Total:** 18 test modules; 245 test functions at this repository snapshot.

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
| Interface Tension Profile | Typed UNKNOWN-first profile is attached optionally to `Relationship`; relationship assessment exposes dimension evidence and keeps absent/un-calibrated evidence UNKNOWN | Evidence capture and summary implemented; calibrated assessment incomplete |
| Provider/consumer, purpose/direction, contract/schema | Typed profile fields exist and default to UNKNOWN | Foundation implemented |
| Provenance/quality, timing/latency/frequency/freshness | Evidence containers exist for provenance, data quality, timing, latency, frequency and freshness | Foundation implemented; no source measurements |
| Influence magnitude/boundaries, authority and coupling | Magnitude, authority-boundary and coupling evidence dimensions are represented | Foundation implemented; no calibrated bounds |
| Failure semantics/observability | Error handling, fallback, recovery and observability dimensions are represented | Foundation implemented; no failure-envelope assessment |
| Capacity/headroom and operating envelopes | Capacity/headroom evidence fields exist; `OperatingEnvelopeAssessment` represents NORMAL/BUSY/DEGRADED/STRESS/RECOVERY with separate declared/assessed states, load/capacity/headroom, transition/recovery evidence. PR #306 now requires traceable assessment evidence, confidence and provenance for an assessed state. PR #310 is merged: relationship-level assessment exposes operating-envelope evidence, including explicit-defect paths; no classification or headroom calculation | Partial |
| Feedback sufficiency/stability | `FeedbackLoopAssessment` is merged with gain, delay, damping, oscillation, overshoot, recovery and observation-window evidence. PR #303 also merged UNKNOWN-first feedback records into `assess_system` cycle detection; PR #304 requires traceable assessment evidence, confidence and provenance for non-UNKNOWN verdicts. No stability calculation or hysteresis assessment | Partial |
| Duplication | Semantic duplicate candidates are surfaced by graph analysis; profile now carries a duplication evidence dimension | Partial-to-good; no measured duplication cost |
| Failure propagation | A failure-propagation evidence dimension is represented; propagation analysis is not implemented | Partial |
| Performance margins q/tau/m | `PerformanceMargin` represents q, tau, unit, normalization, evidence and confidence; computes exact m=q-tau only for finite comparable values; exact zero remains a boundary, not a pass. PR #305 requires valid margin arithmetic, traceable q/tau evidence and nonblank confidence before `evidence_complete` is true. PR #323 proposes nonblank metric/envelope validation and guards against extreme numeric overflow | Evidence model implemented; calibrated threshold selection and relationship-level integration still missing |
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
| D | Insufficient headroom | Capacity/headroom evidence dimensions and q/tau margin inputs exist; relationship-level envelope evidence is integrated by PR #310 | **Partial** — evidence representation and relationship integration are present; no headroom calculation or sufficiency verdict |
| E | Excessive authority | `Relationship.authority`, `assess_signal_authority`, real-repository demo assertions | **Partial** — capability/authority distinction exists; no complete interface profile or dedicated adversarial threshold test |
| F | Duplicate discovery | Safe canonical convergence; `graph.dedup_candidates`; `test_safe_convergence_merge` | **Covered** |
| G | Speculative obligation | Hypothesis classification and `test_genius_feedback_is_hypothesis` | **Partial** — demonstrated for one domain hypothesis, not a general adversarial obligation-quality test |
| H | Protected experiment | Watcher registry and fail-closed eligibility; active/unknown registry tests | **Covered** |
| I | Local improvement causes global regression | No multi-objective local/global net-value comparison | **Missing** |
| J | Neighbouring capability changes | `run_cycle()` recomputes every node, relationship and system tension assessment on each cycle (`rdo/orchestrator.py`); typed interface profiles and relationship-level envelope evidence are now available | **Partial** — no differential before/after impact analysis identifies which neighbouring relationships changed because a capability changed, or explains the resulting system consequences |
| K | Excessive recursion | max-depth, terminal kinds and frontier reasons; `test_max_depth_bounds_expansion` | **Covered** |
| L | Negative development outcome | Merged PR #314 derives a low-confidence, exact-objective regression-risk candidate from traceable reported regressions and surfaces it in later matching cycles | **Partial** — candidate surfacing does not mechanically reverse or restrict a recommendation; the underlying regression report is not independently verified by this change |

A test with a similar name is not counted as full coverage unless it exercises the specified adversarial condition and asserts the required outcome.

## 5. Objective-context gap (G-91) — narrowed by merged implementation

PR #287 merged objective-context propagation into `run_cycle()`, cycle persistence, summary and handoff. The system now preserves intent, owner/source, scope, affected paths, assumptions, constraints, exclusions and acceptance criteria as context. It creates explicit UNKNOWN/unmapped context items, marks execution readiness BLOCKED while items remain unmapped, keeps bounded human handoff reviewable, and propagates exclusions into package anti-requirements. Legacy no-context cycles retain their prior readiness behaviour; legacy handoff manifests remain readable.

**Implemented and test-verified:** context is preserved; scalar intent is handled as a single item; unknown context remains unmapped; execution readiness is blocked; exclusions are propagated; cycle resume retains context; handoff carries the assessment; acceptance criteria expose `verification_status: unknown`, `mapped_obligations: []`, and `verification_evidence: []` (PR #296).

**Remaining gap:** context items are not yet mapped automatically or through a structured evidence-resolution workflow into obligations and independent evidence. Acceptance criteria now have an explicit UNKNOWN-first verification contract, but not automated mapping or independent completion evidence. Owner/source are provenance fields, not enforced authority. This remains a planning/review capability gap, not evidence of an execution incident.



**Evidence-integrity update (27 November 2026):** PR #298 makes malformed persisted interface-profile shapes explicitly diagnosable. PRs #304–#306 strengthen evidence completeness for feedback verdicts, performance margins and assessed operating envelopes. These changes enforce traceability and UNKNOWN handling; they do not supply missing v1.4 thresholds or implement stability/headroom calculations. PR #310 merged relationship-level operating-envelope evidence. PR #316 makes malformed interface-profile serializers fail closed. PR #314 adds exact-objective negative-outcome candidate learning; a reported regression remains advisory evidence rather than an independently verified or mechanically enforced veto. PR #321 proposes validating interface evidence against the RDO evidence-status vocabulary (`measured`, `implemented`, `static`, `inferred`, `unknown`) and keeping numeric envelope measurements strictly `measured`; exact-head CI is pending at this snapshot. PR #323 separately hardens performance-margin identity, envelope labels and numeric overflow; its CI is pending.

## 6. Next implementation slice

**Target:** Close remaining evidence-to-assessment gaps around feedback stability, failure propagation, adjacent-capability impact and system-level trade-offs without inventing calibration.

Completed foundation:
1. Added a typed, serialisable UNKNOWN-first interface profile to `Relationship`, preserving legacy positional construction.
2. Represented provider/consumer, purpose/direction, contract/schema, provenance/quality, timing/latency/frequency/freshness, influence magnitude/authority/coupling, reversibility, error handling, fallback/recovery, observability, capacity/headroom, feedback sufficiency/stability, duplication and failure propagation.
3. Relationship-level assessment now refuses to infer SUFFICIENT when the profile is absent or when evidence exists without calibrated thresholds/margins. Existing explicit findings for unbounded influence and unresolved necessary dependencies retain precedence.
4. Merged PR #310 attaches operating-envelope evidence to relationships and carries validated declared/assessed state and measurement summaries into relationship assessment; it does not calculate headroom or classify the envelope.
5. Merged PR #316 makes malformed custom interface-profile serializers fail closed as invalid shape rather than letting assessment crash or imply recorded evidence.

Next bounded sequence:
1. Complete measured feedback-loop stability only when calibrated criteria, observation windows and evidence are grounded; preserve loop members and relationships, and never equate graph topology with instability or remove cycles automatically.
2. Add evidence-backed failure-propagation assessment and differential adjacent-capability impact analysis: compare the existing full-cycle relationship reassessments, identify affected neighbours after a capability change, and explain before/after differences. Keep UNKNOWN where propagation evidence or calibrated bounds are absent.
3. Add adversarial insufficient-headroom and unstable-feedback cases with evidence validation and UNKNOWN-first assertions.
4. Add the neighbouring-capability-change adversarial case, proving that a changed capability produces a traceable before/after impact report for affected relationships without automatically mutating unrelated components.
5. Address local-improvement/global-regression only after inspecting the actual objective and evidence model; do not invent net-value weights, Pareto dominance rules or trade-off thresholds.
6. Run the existing Stage-2 belief-development slice and persist/resume it against current main to prove backward compatibility.
7. Only then consider system-level Pareto/net-value evaluation and marginal-value stopping, with grounded calibration and explicit separation from relationship evidence work.

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
