# RDO v1.4 — Implementation Gap Audit

**Date:** 28 November 2026  
**Working specification:** RDO v1.4 — Optimal Functional Tension  
**Specification provenance:** Founder-supplied file `/home/rr/Desktop/NEX — RECURSIVE DEVELOPMENT ORCHESTRATOR## Version 1.4.txt`; dated 20 November 2026; 47,172 bytes; SHA-256 `382d634d03bc15701d9de4dcbc2629b966ffd8370c370f0307a57a853f4db926`. Its own header identifies it as a **Proposed implementation specification**. The exact source file is not present in the current Library or repository workspace; its provenance and hash are recorded from the founder's 24 November statement.  
**Working-status note:** On 24 November the founder recalled, uncertainly, “yeah i think i did” approve it. No explicit contemporaneous approval wording or separate approval record was recovered. Use v1.4 as the current engineering working baseline under the founder's present direction to continue RDO v1.4 development, but do not describe it as formally signed, frozen, or as a proven supersession of v1.3. The 20 November v1.3 PDF remains the latest independently retrievable RDO specification in the Library. Preserve the v1.4 proposed status and do not invent missing thresholds or clauses.  
**Repository evidence snapshot:** `main` at `11970fc98f2f811c64123c440d5287fb1906ecd8` (27 November 2026, 22:14:24 UTC; includes PRs #331, #332, #333 and #334, as well as prior merged work).

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

**Current vertical-slice status:** persisted-cycle CLI exposure from #331, typed observed-failure evidence from #339, and context-mapping/criterion-review events from #343 are now merged. The remaining work is to connect these records into one traceable cycle-level assessment path without collapsing structural candidates, measured observations and reviewed interpretations into one claim. No causal attribution, propagation probability, stability calculation or calibrated threshold is supplied by these increments. Extend the existing RDO; do not replace the orchestrator or create a parallel system.

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

### Test inventory at the pre-graph-merge audit snapshot

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
| `rdo/tests/test_stage3_graph_intelligence.py` | 14 |
| `rdo/tests/test_stage4_belief_audit.py` | 11 |
| `rdo/tests/test_stage5_pathway.py` | 6 |
| `rdo/tests/test_stage6_learning_loop.py` | 18 |
| `rdo/tests/test_stage7_execution_watcher.py` | 12 |

**Total:** 18 test modules; 251 test functions at this repository snapshot.

**Post-merge update (28 November 2026):** PR #331 added `rdo/tests/test_graph_analysis_cli.py` (6 test functions); PR #333 brings `rdo/tests/test_feedback_loop.py` to 12; PR #334 brings `rdo/tests/test_stage3_graph_intelligence.py` to 22. The 251-function total above is a historical baseline, not a current-main total; a full recount of all test modules has not been performed in this refresh.

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
| Interface Tension Profile | Typed UNKNOWN-first profile is attached optionally to `Relationship`; relationship assessment exposes dimension evidence and keeps absent/uncalibrated evidence UNKNOWN | Evidence capture and summary implemented; calibrated assessment incomplete |
| Provider/consumer, purpose/direction, contract/schema | Typed profile fields exist and default to UNKNOWN | Foundation implemented |
| Provenance/quality, timing/latency/frequency/freshness | Evidence containers exist for provenance, data quality, timing, latency, frequency and freshness | Foundation implemented; no source measurements |
| Influence magnitude/boundaries, authority and coupling | Magnitude, authority-boundary and coupling evidence dimensions are represented | Foundation implemented; no calibrated bounds |
| Failure semantics/observability | Error handling, fallback, recovery and observability dimensions are represented | Foundation implemented; no failure-envelope assessment |
| Capacity/headroom and operating envelopes | Capacity/headroom evidence fields exist; `OperatingEnvelopeAssessment` represents NORMAL/BUSY/DEGRADED/STRESS/RECOVERY with separate declared/assessed states, load/capacity/headroom, transition/recovery evidence. PR #306 requires traceable assessment evidence, confidence and provenance for an assessed state. PR #310 is merged: relationship-level assessment exposes operating-envelope evidence, including explicit-defect paths; no classification or headroom calculation | Partial |
| Feedback sufficiency/stability | `FeedbackLoopAssessment` is merged with gain, delay, damping, oscillation, overshoot, recovery and observation-window evidence. PR #303 also merged UNKNOWN-first feedback records into `assess_system` cycle detection; PR #304 requires traceable assessment evidence, confidence and provenance for non-UNKNOWN verdicts. No stability calculation or hysteresis assessment | Partial |
| Duplication | Semantic duplicate candidates are surfaced by graph analysis; profile now carries a duplication evidence dimension | Partial-to-good; no measured duplication cost |
| Failure propagation | A failure-propagation evidence dimension is represented; PR #328 adds structural dependent candidates for explicitly supplied failed keys via `depends_on` paths only; merged PR #334 corrects cross-branch cycle detection in that traversal | Partial — no measured failure-event evidence is linked to each path and no runtime propagation, severity or probability is assessed |
| Performance margins q/tau/m | `PerformanceMargin` represents q, tau, unit, normalization, evidence and confidence; computes exact m=q-tau only for finite comparable values; exact zero remains a boundary, not a pass. PR #305 requires valid margin arithmetic, traceable q/tau evidence and nonblank confidence before `evidence_complete` is true; PR #323 additionally validates margin identity and comparable envelope constraints, and rejects numeric overflow | Evidence model implemented; calibrated threshold selection and sufficiency verdicts missing |
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
| J | Neighbouring capability changes | `run_cycle()` recomputes assessments; PR #330 adds `compare_adjacent_relationship_impacts()` and PR #331 exposes persisted before/after comparison through the RDO CLI | **Partial** — CLI exposure is complete; the comparison reports structural association/correlation, not causal attribution or an automatic system-level net-benefit/harm verdict |
| K | Excessive recursion | max-depth, terminal kinds and frontier reasons; `test_max_depth_bounds_expansion` | **Covered** |
| L | Negative development outcome | Predicted/actual comparison, disconfirmation and confidence reduction; PR #314 merged an objective-scoped regression-risk candidate into current main | **Partial** — a scoped candidate can be surfaced, but it does not yet mechanically reverse or restrict a recommendation |

A test with a similar name is not counted as full coverage unless it exercises the specified adversarial condition and asserts the required outcome.

## 5. Objective-context gap (G-91) — narrowed by merged implementation

PR #287 merged objective-context propagation into `run_cycle()`, cycle persistence, summary and handoff. The system now preserves intent, owner/source, scope, affected paths, assumptions, constraints, exclusions and acceptance criteria as context. It creates explicit UNKNOWN/unmapped context items, marks execution readiness BLOCKED while items remain unmapped, keeps bounded human handoff reviewable, and propagates exclusions into package anti-requirements. Legacy no-context cycles retain their prior readiness behaviour; legacy handoff manifests remain readable.

**Implemented and test-verified:** context is preserved; scalar intent is handled as a single item; unknown context remains unmapped; execution readiness is blocked; exclusions are propagated; cycle resume retains context; handoff carries the assessment; acceptance criteria expose `verification_status: unknown`, `mapped_obligations: []`, and `verification_evidence: []` (PR #296).

**Remaining gap:** context items are not yet mapped automatically or through a structured evidence-resolution workflow into obligations and independent evidence. Acceptance criteria now have an explicit UNKNOWN-first verification contract, but not automated mapping or independent completion evidence. Owner/source are provenance fields, not enforced authority. This remains a planning/review capability gap, not evidence of an execution incident.



**Evidence-integrity update (27 November 2026):** PR #298 makes malformed persisted interface-profile shapes explicitly diagnosable. PRs #304–#306 strengthen evidence completeness for feedback verdicts, performance margins and assessed operating envelopes. PR #310 merged the relationship-level operating-envelope evidence connection. PR #314 merged objective-scoped regression-risk learning: traceable regression evidence produces a low-confidence, exact-objective candidate surfaced in later matching cycles; it does not automatically reverse or restrict recommendations. PR #316 makes malformed interface-profile serializers fail closed; PR #321 validates interface evidence status values; PR #323 strengthens performance-margin identity, envelope and overflow validation. PR #324 merges exact-scope objective-learning collision and mutation hardening. PR #325 adds validated performance-margin evidence to relationship assessments without calibrated verdicts. PR #328 adds structural failure-propagation candidate tracing from explicit failed keys, not observed propagation. PR #330 adds differential before/after comparison for adjacent relationships and their recorded tension assessments; earlier PRs #327 and #329 closed without merge as superseded attempts. Exact-head CI for PR #330 passed (run 46068454644). PR #331 is merged: persisted-cycle CLI commands expose structural failure candidates and before/after neighbour comparisons without mutating cycle records. PR #333 is merged: directed-cycle identity now uses canonical rotation, preserving distinct directed traversals that share the same member set while deduplicating rotations. Its regression tests cover the graph helper, system-level feedback records and relationship-order determinism. PR #334 is merged: Kahn topological elimination detects reachable dependency cycles that cross BFS branches, while convergence-only paths remain non-cyclic. Both fixes passed exact-head GitHub Actions full-suite `pytest` jobs before merge. The merged increments improve traceability and access to analysis; they do not supply missing v1.4 thresholds or implement stability/headroom calculations.

## 6. Next implementation slice

**Target:** Evidence-backed feedback-loop stability, failure propagation, adjacent-capability impact and remaining system-level OFT gaps.

Completed foundation:
1. Added a typed, serialisable UNKNOWN-first interface profile to `Relationship`, preserving legacy positional construction.
2. Represented provider/consumer, purpose/direction, contract/schema, provenance/quality, timing/latency/frequency/freshness, influence magnitude/authority/coupling, reversibility, error handling, fallback/recovery, observability, capacity/headroom, feedback sufficiency/stability, duplication and failure propagation.
3. Relationship-level assessment now refuses to infer SUFFICIENT when the profile is absent or when evidence exists without calibrated thresholds/margins. Existing explicit findings for unbounded influence and unresolved necessary dependencies retain precedence.
4. Merged PR #310 carries operating-envelope evidence into relationship assessment, retaining declared/assessed separation and UNKNOWN where evidence is incomplete.
5. Merged PR #316 makes malformed custom interface-profile serializers fail closed as invalid shape.

Next bounded sequence:
1. Keep measured feedback-loop stability blocked until the exact v1.4 criteria, observation windows and supporting measurements are recoverable. Preserve loop members and relationships; never equate graph topology with instability or remove cycles automatically.
2. **Completed:** persisted-cycle CLI exposure for structural failure candidates and before/after neighbour comparisons (PR #331 merged). Fixture-backed tests verify persisted CycleRecord reads, UNKNOWN/PARTIAL results and no mutation of cycle files. Actual host-saved cycle stores remain unverified from the cloud workspace.
3. Add an evidence-linking failure-propagation assessment only after defining how observed failure events, relationship identity, observation window, operating envelope and provenance are represented. Do not infer observed propagation from `depends_on` topology alone.
4. Extend adversarial coverage for insufficient headroom, unstable feedback and neighbouring-capability changes. Assert evidence completeness and UNKNOWN-first behaviour where thresholds or measurements are absent.
5. Investigate local-improvement/global-regression with actual objective/evidence data before proposing net-value weights or Pareto rules.
6. **Completed baseline:** Stage-2 belief-development and fresh-process CycleStore persistence/resume are already implemented and covered by `rdo/tests/test_stage2_extrapolator_mvp.py`; exact-head full-suite CI passed them. Preserve this regression rather than rebuilding Stage 2.
7. Consider Pareto/net-value and marginal-value stopping only after the exact specification criteria and grounded calibration are available.

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

**Conclusion:** RDO has a credible working Extrapolator vertical slice and meaningful parts of v1.4. It does not yet implement the full OFT model. The next justified development step is to define and test a traceable observed-failure evidence record linked to canonical relationship identity, observation window, operating envelope and provenance. Keep it distinct from structural failure-path candidates. Do not implement calibrated propagation, severity or probability verdicts until the exact v1.4 criteria and source measurements are available.


## Update 2026-11-28 — post-merge implementation evidence

### Merged slices

- **#341:** directed-cycle identity now preserves distinct directed paths and deterministic ordering.
- **#342:** Watcher ledger evidence-reference validation and disk-before-memory append ordering are merged.
- **#339:** typed observed-failure evidence is persisted separately from structural failure-path candidates. It requires an exact dependency edge and canonical source/destination obligation endpoints, retains measured evidence and operating-envelope context, and does not infer causality or propagation probability.
- **#343:** context mapping and criterion verification now use the existing digest-bound, append-only Stage-7 decision ledger. The independent Watcher validates both event kinds, their manifest identity, canonical obligation links, evidence-reference containers, status, timestamps and ordering.

### CI evidence

- #339 exact-head full suite: **2,819 passed, 7 skipped, 45 subtests passed**.
- #343 exact-head full suite: **2,812 passed, 7 skipped, 45 subtests passed**.
- Both exact-head runs completed the mind-map verification: 30 nodes, 0 unverified. Existing warnings remain for missing `VIRTUE_SLATE.md`, missing `mental_factors_inventory_alobha_spec.txt`, and overdue P13 finitude unblock.
- Combined post-merge mainline CI is tracked on the main commit separately; exact-head PR success is not substituted for that result.

### Corrections to earlier gap statements

**Adversarial case J:** PR #331 already exposes adjacent-relationship impact comparison through the RDO CLI. The remaining limitation is interpretive: the comparison is correlation/structural impact, not causal attribution, and it does not automatically produce a system-level net-value or harm verdict.

**G-91 — context mapping:** partially closed by #343. Human reviewers can now map each context item to canonical obligations and record criterion-level pending/passed/failed/not-applicable outcomes with provenance. Remaining: no automatic mapping, no independent dereferencing/authentication of caller-supplied evidence references, and no automatic application of reviewed mappings to a subsequent cycle. Context-review events do not rewrite the original cycle or handoff manifest.

### G-92 — first-level decomposition and novel expansion-rule lifecycle (open)

The current objective intake requires externally supplied seed obligations; the recursive cycle starts from those seeds. The Extrapolator has a finite static rule catalogue. When a novel kind has no rule, the system records a frontier rather than inventing one. PatternMemory stores lessons, confirmations and disconfirmations, but it does not create or promote executable rules.

This means the current repository can recursively expand a supplied seed graph, but it does not independently convert arbitrary raw objective text into a complete first-level seed graph or derive executable rules for every novel kind. The external LLM/human seed-proposal boundary is usable, but no provider is integrated.

Recommended next research/development: a provider-neutral proposal contract for seed obligations and candidate expansion rules, preserving competing interpretations, assumptions, applicability, exceptions, disconfirmations, provenance and tests. Candidate rules must remain inactive until reviewed and approved; frequency alone must never promote a rule.

### G-93 — feedback-loop assessment persistence (open)

`assess_system` already creates a `FeedbackLoopAssessment` for each detected influence cycle, serializes it into `TensionAssessment.dimensions.feedback_loop_assessments`, and persists it inside `CycleRecord.tension`. The topology and UNKNOWN-first placeholders are therefore present. The missing capability is a traceable update path for measured dimensions and independently reviewed stability evidence; no CLI/API path currently accepts those updates. The model does not calculate stability, gain, damping or thresholds. A future evidence-bound update path should preserve original topology, validate measurement evidence, observation windows and provenance, preserve legacy-cycle loading, and leave stability UNKNOWN unless a separately reviewed assessment is supported.

### Next sequence

1. Verify combined mainline CI after #339 and #343.
2. Extend the existing seeded-objective end-to-end test to cover a completed criterion outcome through the independent Watcher, while preserving the pending-state regression. Keep raw-idea-to-seed generation explicitly external until a provider-neutral proposal contract is designed.
3. Design the candidate-rule proposal and approval lifecycle for novel kinds.
4. Persist FeedbackLoopAssessment with UNKNOWN-first semantics and measured evidence only.
5. Preserve the already implemented Stage-2 belief-development and fresh-process CycleStore-resume tests as a regression baseline; focus next on novel-kind rule proposals and the raw-idea-to-handoff boundary.

No frozen S-01–S-25/M1.8 specification content or NEX runtime/deployment path was changed by these slices.


### Stage-2 status correction — completed baseline

The earlier next-step wording to run the Stage-2 belief-development slice and fresh-process persistence/resume is stale. The repository already contains `rdo/STAGE2_EXTRAPOLATOR_MVP.md` and `rdo/tests/test_stage2_extrapolator_mvp.py`. The test exercises the belief-decay objective through the existing Extrapolator/reconciler/CycleStore and launches a fresh Python subprocess to reload the persisted cycle, checking discovered counts, deferred frontier and native-planning kind. It also guards against writing reusable patterns from deterministic fixture reviews without authorised review provenance.

The #339 and #343 exact-head full-suite runs passed this test. This is isolated repository/test-store verification only; it is not live belief-database or host-runtime evidence. Keep it as a regression baseline and do not rebuild Stage 2.


## 2026-11-28 — Novel expansion-rule proposal lifecycle (candidate-only increment)

The frontier request for a novel obligation kind is now version 2 and carries a SHA-256 fingerprint of the full expansion-rule content plus terminal-kind catalogue. A request is rejected by the proposal store if it was generated against an older schema or a different catalogue snapshot.

New boundary adapter: `rdo_adapters/rule_proposals.py`.

- Candidate proposals are provider-neutral structured data; arbitrary code, callables and unknown fields are rejected.
- Required content includes decomposition steps, applicability, preconditions, constraints, assumptions, exceptions, anti-requirements, alternative interpretations, evidence references, disconfirming cases, and positive and negative test plans.
- The append-only JSONL event ledger is hash-chained, sequence-checked, fsynced and protected by an exclusive file lock. Review decisions are separate events.
- Review outcomes are `changes_requested`, `approved_for_catalogue`, or `rejected`. A changed candidate is a new proposal linked to its predecessor.
- `approved_for_catalogue` does not activate a rule. There is deliberately no activation API and no dynamic rule loading; `EXPANSION_RULES` remains the only active catalogue and still requires an ordinary reviewed source change and tests.
- Proposer/reviewer labels are caller-attributed and not identity-authenticated. The ledger is tamper-evident, not an authentication or authorization system.

**Validation status:** focused proposal-store tests and the full repository CI are pending on the exact PR head. No active rule has been added, no existing rule has been changed, and no RDO specification has been amended.



## Update 2026-11-28 — G-93 update path merged; G-92 decomposition boundary narrowed

### G-93 — feedback-loop measurement and review update path (closed for this capability slice)

PR #357 merged as `6f12f403e13b94a4b019aa666abac448b8a9a62d`.

- `FeedbackLoopAssessment` remains UNKNOWN-first. A dimension with status `measured` now requires a finite numeric value, unit, evidence references and confidence.
- `FeedbackLoopEvidenceStore` appends measurement and stability-review events to a separate hash-chained JSONL ledger.
- Every event is bound to the exact loop ID, member list and directed relationships. Replay refuses to apply events if the loop topology changes.
- Measurements do not calculate stability. A measurement recorded after a stability review invalidates that review and resets the current verdict to UNKNOWN until another explicit review is recorded.
- A non-UNKNOWN verdict requires a separate review event with reviewer attribution, source reference, assessment evidence and confidence. Reviewer identity remains caller-supplied and unauthenticated by this local ledger.
- Applied events are also persisted in the trailing `CycleRecord.feedback_loop_evidence_events` field. Legacy CycleRecords load with an empty event list. The replay command recovers the cycle snapshot if the ledger append succeeded but the snapshot save did not.
- CLI: `feedback-measure`, `feedback-review`, `feedback-replay`. Operator instructions are in `rdo/FEEDBACK_LOOP_EVIDENCE.md`.

Exact-head full sandbox run `46101032854`: **2,864 passed, 7 skipped, 45 subtests passed**. Mind-map verification completed: 30 nodes, 0 unverified. Existing warnings remain for the missing doctrine files and overdue P13 finitude unblock.

The G-93 update-path gap is closed for measured evidence and separately reviewed state updates. Calibrated stability, gain/damping/oscillation thresholds, causal propagation and automated verdicts remain deliberately unimplemented. The code does not infer thresholds or stability from graph topology.

### G-92 — candidate rule proposals merged; raw-idea seed boundary remains open

PR #352 is now part of main and provides the provider-neutral, append-only, hash-chained candidate-rule proposal lifecycle. Its `approved_for_catalogue` decision is intentionally inert: it does not mutate `EXPANSION_RULES`, dynamically load code or automatically activate a new decomposition rule. The proposal ledger preserves review decisions, provenance and supersession history.

The remaining G-92 gap is upstream of recursive expansion: objective intake still requires seed obligations supplied by a human or external LLM. There is no integrated raw-idea → candidate seed alternatives → explicit review/approval → objective.v1 intake → recursive expansion → Stage-7 handoff path.

### Next bounded development: provider-neutral candidate-seed lifecycle

Research and implement the seed proposal boundary using existing objective validation, immutable objective-input revisions, CycleStore and Stage-7 handoff evidence. Candidate alternatives should preserve competing interpretations, seed graphs, relationships, assumptions, constraints, evidence needs, acceptance-criterion coverage, open questions, disconfirming cases and provenance. Approval must select one alternative explicitly and bind it to the exact raw-objective revision/hash. The resulting objective input and later handoff must retain that lineage.

Do not run a planning cycle from an unreviewed external-LLM seed proposal. Keep candidate expansion rules inert until a separate explicit activation authority is designed and approved. Do not change the frozen S-01–S-25/M1.8 register or infer missing v1.4 thresholds.
