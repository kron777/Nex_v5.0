# NEX Discrimination and Evaluative Integration Audit
**Status:** Investigative workpaper — draft; not a Gate 0 submission or new acceptance specification  
**Programme boundary:** NEX v5.0, Master Roadmap v3.0, Phase 0 M0.3–M0.5 support  
**Repository:** `kron777/Nex_v5.0`  
**Prepared against:** PR #49 head `308f8e40ee97470b7770f73318996cf47f2994e3` (documentation branch; base `main` at `6e6712bd4bde15ad2288f220cd4438b11622c93c`)  
**Companion evidence:** `NEX_ARCHITECTURE_CROSSWALK_v2.md`, especially §§3.3, 3.11, 3.15, 3.19, 3.21 and subsequent source-audit addenda; `NEX_CHAT_PATHWAY_AUDIT.md`; `NEX_VERIFIED_DEFECT_BACKLOG.md`.  
**Authority qualification:** The exact Frozen V2.1 specification and Founder Sign-Off record were not present in the retrieved handover/library material. This workpaper therefore does not define or amend frozen acceptance criteria. It records questions, source-grounded leads and possible isolated tests only.

---

## 1. Purpose

Investigate whether existing NEX mechanisms can **distinguish materially different information, evaluate the distinctions appropriately, integrate relevant evaluations, and carry their consequences into later operation**.

The question is not whether NEX contains many scorers, classifiers, gates, memories or feedback loops. The question is whether those existing mechanisms form effective, traceable pathways in the actual system.

The audit must separate seven different claims:

1. **Detection:** the system notices a potentially meaningful feature or difference.
2. **Discrimination:** it distinguishes that feature from a relevant alternative, including close or misleading alternatives.
3. **Evaluation:** it assigns a reasoned value, confidence, relevance, risk or other assessment to the distinction.
4. **Integration:** competing assessments are reconciled or selected in context rather than merely accumulated side by side.
5. **Consumption:** a downstream selector, gate, retrieval process, response or action actually uses the assessment.
6. **Continuity:** the relevant distinction and its provenance survive the required persistence boundary and can be retrieved later.
7. **Adaptation:** a later prediction, evaluation or decision changes in a traceable way because of the earlier outcome.

Evidence for one stage must not be promoted into evidence for the next. A score being calculated does not establish that it is valid; a row being written does not establish that it is retrieved; retrieval does not establish reliance; reliance does not establish improved outcomes.

This is a functional engineering investigation. It makes no claim about consciousness, sentience, subjective experience or felt emotion and must not produce a consciousness score.

## 2. Scope and authority

### Included

- Read-only inspection of existing source, tests, schemas, documentation, callsites and consumers.
- Reconciliation with the existing Phase 0 forward and backward pathway audit.
- Classification of existing mechanisms by what they detect, evaluate, integrate, persist and consume.
- Identification of missing or ambiguous producer-to-consumer links.
- Development of falsifiable test designs using isolated fixtures, temporary databases and deterministic stubs where appropriate.
- Explicit separation of source facts, test evidence, simulated execution, host/runtime unknowns and behavioural validation.

### Excluded

- New NEX nodes, faculties, evaluators, scoring systems, databases, schemas, event stores or feedback loops.
- Changes to production prompts, scores, weights, thresholds, retrieval, ranking, gates, confidence, memory, scheduler or action selection.
- Enabling dark/default-OFF mechanisms or changing flags.
- Live database writes, synthetic live events, host restarts, deployment or changes to protected experiments, baselines and tripwires.
- Phase 1 behavioural experiments or fixes before Gate 0 founder approval.
- Reopening Frozen V2.1 decisions or changing roadmap order.

The audit is a supporting analytical workpaper for the existing Phase 0 crosswalk and causal-trace work. It is not a new NEX phase or a substitute for the M0.1–M0.5 deliverables.

## 3. Operational definitions

The word *discrimination* is used narrowly: the ability of an existing mechanism to produce appropriately different treatment for cases that differ in a specified, relevant property, while avoiding inappropriate differences when the property is absent.

Examples:

- A genuine contradiction should be distinguished from rhetorical negation or superficial lexical overlap.
- A relevant belief should be distinguished from a high-overlap but irrelevant belief.
- genuinely novel evidence should be distinguished from renamed or paraphrased repetition.
- reliable, corroborated evidence should be distinguished from unsupported repetition.
- a prediction failure should be distinguished from missing or incomparable outcome data.
- a meaningful change in context should be distinguished from noise or a transient signal.

*Evaluative integration* means that more than one existing assessment can be brought to bear on a decision in a traceable, context-appropriate way. It does not require every signal to be combined into one score. Appropriate integration may include prioritisation, conflict handling, explicit abstention, quarantine, or deliberate non-use.

The audit must not assume that more signals, more coupling, or more influence is always better. Each mechanism should have only the degree of influence justified by its responsibility, reliability and resource cost.

## 4. Existing system evidence: starting leads, not final verdicts

The current Phase 0 crosswalk already contains substantial source-level evaluation and feedback analysis. This workpaper must extend and reconcile that material, not duplicate it or treat its findings as live runtime proof.

| Existing pathway / artefact | What the current crosswalk reports | Question for this audit |
|---|---|---|
| Fountain Global Workspace | Candidate competition can select a winner and add framing to the Fountain prompt; source default is enabled, host state unknown. | Does the winner distinguish task-relevant importance from a high-scoring but misleading candidate? What happens with ties, missing inputs and conflicting signals? |
| Chat Workspace | A bounded selection path exists behind a conditional flag; serial assembly remains the source fallback. The tested causal trace covers only represented route dependencies. | Does Chat selection discriminate useful context from distracting context, and are the actual selected items causally linked to the response? |
| CoherenceGate | Current checks include high lexical redundancy and a narrow direct-negation protection for locked anchors. The crosswalk explicitly says this is not a general contradiction or truth evaluator. | Which contradiction classes are actually distinguished, which are outside the rule's remit, and where is uncertainty or abstention appropriate? |
| BeliefRetriever / activation | The audited Chat retrieval path builds a keyword candidate pool and uses activation to adjust candidates in that pool; graph-only neighbours with no initial keyword match are not added in that path. | Does this candidate-generation boundary systematically omit relevant indirectly connected evidence? What is the intended retrieval contract? |
| EmphasisEngine | Computes post-thought measures and persists an `emphasis_log` record; the bounded search found no downstream decision consumer. One component was excluded from the composite after a reported null result. | Are the remaining measures valid for their intended constructs? Is any operational consumer missing, or is observation-only the correct functional level? |
| Warrant | Score construction/persistence exists, but normal boot construction of the scoring loop and a decision-sink reader were not established in the audited path. | Is the warrant score meant to be an evaluation artefact, or should an already-approved consumer exist? Do not create one by assumption. |
| Metacognition events | The crosswalk reports a Chat-turn path that can write and retrieve self-observation events into the same-turn prompt; separate Fountain use is conditional. | Does the event distinguish a useful recurring pattern from repeated detector output, and does its inclusion improve or distort later responses? |
| Predictive substrate / surprise | Prediction and surprise records have separate producers and consumers; the crosswalk records a main-boot gap in the surprise-promotion loop while AffectState has a separate raw-surprise input. | Are predicted and observed populations comparable? Are missing outcomes, internal telemetry and external observations kept distinct? |
| NovelAssociation / Tier-7 | The crosswalk distinguishes graph/annotation pathways from separate retrievable Tier-6 synthesis. | Does the system distinguish a useful relation from a prompt annotation, and is the intended downstream use actually present? |
| FocalSet / WorkingMemory | The crosswalk reports a process-global focal selector feeding session-keyed WorkingMemory and conditional prompt inclusion. | Are selection, retention and session boundaries correctly distinguished? Can shared selector state produce cross-session influence? |

These are leads already recorded in the companion crosswalk, not fresh independent source verification by this workpaper. Before any finding is promoted, re-open the exact current source at the current PR head, record the relevant blob/commit, inspect all callsites and consumers, and reconcile tests. Where the companion crosswalk itself marks a search as bounded, preserve that qualification.

## 5. Audit dimensions

### A. Content and evidence discrimination

For each existing mechanism, determine whether it distinguishes:

- contradiction from lexical opposition or rhetorical negation;
- redundancy from paraphrase, shared vocabulary or genuinely independent corroboration;
- relevance from similarity alone;
- novelty from vocabulary change, entity novelty or rephrasing;
- source reliability and provenance from repetition count;
- external observation from internally generated telemetry;
- prediction failure from absent, delayed or incomparable outcomes;
- uncertainty from a confident but unsupported classification.

For every classifier or rule, document the positive case, the closest negative case, known boundary cases, threshold source, fallback and abstention behaviour.

### B. Evaluative validity and calibration

For each score or evaluation, identify:

- the construct it claims to represent;
- its actual inputs and transformations;
- its output range, direction and missing-value behaviour;
- whether its weights/thresholds have an approved rationale;
- whether independent ground truth exists;
- whether historical results are comparable across versions;
- whether calibration, discrimination and overall accuracy are measured separately.

A plausible score is not automatically a valid measure. Do not infer truth, importance, morality, confidence or quality from a variable's name.

### C. Integration and competition

Trace how multiple signals interact at each actual decision point:

- which candidates are eligible to compete;
- which signals can affect ranking, gating, prompt inclusion or action;
- whether one high-magnitude signal can dominate;
- whether safety, provenance or uncertainty constraints are preserved;
- whether contradictory evaluations are reconciled, ignored, overwritten or left unresolved;
- whether default and optional pathways produce materially different policies;
- whether fallback behaviour silently changes the effective policy.

Do not presume that a central arbiter is required. First establish whether the existing local mechanisms already provide adequate integration for their responsibilities.

### D. Downstream consumption and causal influence

For every evaluation output, trace:

**producer → calculation → persistence (if any) → retrieval → selector/gate → decision/output sink → observed consequence**

Also trace backwards from important sinks to the evaluations they actually read.

Record separately:
- calculated;
- emitted/logged;
- persisted;
- retrieved;
- eligible;
- selected;
- relied upon;
- decision-changing.

A parent ID or trace edge must reflect an actual source-supported dependency. Chronological adjacency is not causality. Where the current observer cannot represent a dependency, record a trace gap; never fabricate a parent to make a graph appear complete.

### E. Continuity, revision and feedback

Determine whether an earlier evaluation can affect later operation through a real, inspectable path:

- Is the result persisted at the intended boundary?
- Can the correct consumer retrieve it?
- Is it still valid and comparable in the later context?
- Can contradictory evidence revise or supersede it without erasing provenance?
- Are repeated detector outputs deduplicated, cooled down or allowed to accumulate?
- Can self-generated summaries be mistaken for independent external evidence?
- Are feedback loops bounded, stable and protected against self-reinforcement?
- Does a restart preserve the intended state, and are process-local structures clearly distinguished from durable state?

A write, retention row or self-narrative statement is not proof of learning.

### F. Context, robustness and functional sufficiency

Check whether the mechanism behaves appropriately across:

- short and long contexts;
- single-turn and multi-turn interaction;
- different task families;
- sparse, noisy and conflicting evidence;
- missing optional faculties and dependency failures;
- default and explicitly enabled branches;
- restart/session boundaries;
- distinct model/backend configurations where the existing test design supports them.

The objective is not maximal coverage at any cost. Determine the smallest evidence set that can distinguish the competing explanations and establish the mechanism's appropriate functional level.

## 6. Competing hypotheses

Keep all hypotheses provisional. Multiple explanations may coexist, and evidence may reject all of them.

| ID | Hypothesis | Evidence that would support it | Evidence that would weaken or falsify it |
|---|---|---|---|
| H1 | **Evaluation fragmentation:** relevant assessments exist but are isolated or incompatible at the point of decision. | Two or more source-confirmed evaluators assess the same candidate, but the actual sink receives only one or receives no reconciled representation; controlled fixture shows conflicting inputs are mishandled. | Existing decision path demonstrably integrates the relevant signals correctly across representative cases. |
| H2 | **Non-consumption:** useful evaluations are calculated or persisted but do not reach a decision sink. | Complete source/consumer search shows no reader or the reader is unreachable in the relevant boot path; sink output is invariant to the evaluation in a controlled fixture. | Exact consumer path is exercised and its input is shown to alter the relevant selection or decision appropriately. |
| H3 | **Construct or calibration weakness:** evaluation outputs do not reliably measure the property their labels imply. | Minimal-pair or held-out tests show poor discrimination, systematic bias, unstable thresholds or non-comparable versions. | Independent held-out evidence supports the measure's intended interpretation and calibration. |
| H4 | **Continuity/retrieval gap:** a useful distinction is made but is not retained or retrieved when later needed. | Persistence/restart/session tests show loss, stale retrieval, wrong identity or provenance break. | Correct identity, provenance and intended retrieval are demonstrated across the required boundary. |
| H5 | **Feedback distortion:** repeated or self-generated signals amplify, contaminate or lock future evaluations. | Controlled repeated-input or provenance tests show amplification, duplicated evidence, drift or circular reinforcement. | Feedback is bounded, source-separated and stable under repeated and adversarial cases. |
| H6 | **Context/branch sensitivity:** a mechanism works in a narrow fixture but fails under realistic optional branches, longer contexts or dependency degradation. | Paired branch tests reveal material differences not explained by intended policy. | Representative branch and degradation tests preserve the intended behaviour. |
| H7 | **Measurement/trace limitation:** current instrumentation cannot distinguish a true capability gap from missing observation. | Relevant reads, selected IDs, prompt contributors or terminal outcomes are absent from the trace, so causal attribution cannot be made. | Required source-supported dependencies and terminal outcomes are captured with honest uncertainty and neutrality evidence. |

Do not select a preferred hypothesis before the evidence is gathered. In particular, do not turn H1 into a proposal for a new central evaluator or node.

## 7. Candidate isolated test families

These are test-design candidates, not authorisation to run live experiments. Each test should use the existing implementation and interfaces, fresh temporary state, deterministic fixtures where possible, and no production flag or database changes.

### T1 — Minimal-pair discrimination

Construct paired cases differing in one declared property: genuine contradiction vs rhetorical negation; redundancy vs independent corroboration; relevant vs lexically similar distractor; external observation vs internal telemetry.

Measure false acceptance, false rejection and the mechanism's stated outcome. Include near-boundary examples. A test that only checks the obvious positive case is insufficient.

### T2 — Evaluator input sensitivity

Hold all inputs constant except one evaluation signal. Verify whether the expected downstream value changes, and whether unrelated decisions remain invariant. Where the signal is deliberately observation-only, the expected result is no decision change.

This test distinguishes a real consumer from a table that merely accumulates scores.

### T3 — Multi-signal conflict and dominance

Supply controlled candidates with conflicting relevance, confidence, provenance, recency or risk attributes. Verify the actual existing selection/gate policy, including tie, missing-data and abstention paths. Do not invent a desired weighting rule; compare observed behaviour to the existing approved contract once available.

### T4 — Persistence and retrieval identity

Write a fixture evaluation through the existing writer, close/reopen the substrate, and verify that the intended reader retrieves the same entity with provenance intact. Include stale, superseded and contradictory records. Keep all writes in temporary databases.

### T5 — Feedback contamination and repetition

Replay the same source event, a paraphrase, an internally generated summary and an independent corroborating event. Verify whether the mechanism counts them distinctly and whether repeated detector conditions create duplicate unresolved records. Inspect cooldown, deduplication, expiry and source-exclusion behaviour.

### T6 — Branch and failure-mode comparison

Compare the normal path with existing optional dependencies absent, returning empty data or raising their documented exceptions. Record whether fallback changes the policy, suppresses an evaluation, silently inserts a different signal or fails open.

### T7 — End-to-end causal trace reconciliation

For a bounded Chat turn and a bounded Fountain cycle, reconcile evaluation producer IDs to selected candidate IDs, decision records, persistence IDs and terminal outputs. Use the existing default-OFF trace overlay and its paired OFF/ON equivalence harness; do not add a second trace store. A missing parent is an explicit gap, not an invitation to infer causality from record order.

## 8. Measurement rules

Use task-specific measures, not one composite “intelligence” score.

Possible measures, only where the relevant output exists and the test can define independent ground truth:

- classification: confusion matrix, false-positive/false-negative rates, precision, recall;
- ranking: top-k relevance and pairwise ordering accuracy;
- discrimination: ROC-AUC or signal-detection measures on a sufficiently sized, balanced sample;
- probability forecasts: Brier score or log loss against recorded outcomes, with calibration separated from discrimination;
- retrieval: relevant-evidence recall, precision and provenance correctness;
- integration: correct decision under controlled signal conflict, plus invariance to irrelevant signals;
- continuity: identity/provenance retention and correct retrieval after restart;
- feedback: duplicate rate, source contamination, drift and stability under repeated inputs;
- operational cost: latency, memory and trace overhead, reported separately from task quality.

Do not calculate a metric if its assumptions are not met. Report sample size, class balance, uncertainty, exclusions, baseline, missing data and negative/null results. A single successful fixture proves only that fixture.

## 9. Evidence and reporting format

Every finding must contain:

1. **Claim** — one narrow statement.
2. **Status** — hypothesis, source-confirmed, test-verified, simulated/runtime-observed, behaviourally measured, or UNKNOWN.
3. **Source anchor** — exact commit, file, symbol and relevant lines/blob hash.
4. **Forward path** — producer through actual consumer and sink.
5. **Backward path** — sink to the inputs it actually reads.
6. **Test coverage** — exact test and what it does not exercise.
7. **Counterexample/falsifier** — what evidence could disprove the claim.
8. **Impact boundary** — which path, branch, configuration or host is affected; live incidence remains UNKNOWN unless measured.
9. **Functional-sufficiency assessment** — whether the existing mechanism appears sufficient for its responsibility, insufficient, redundant, over-coupled or still indeterminate.
10. **Next authorised evidence step** — read-only inspection or isolated test; any protected/live action is explicitly deferred for approval.

Keep the Master Roadmap's L0–L5 definitions separate from the Research Framework's evidence terminology. For Phase 0, apply the roadmap labels only where their stated proof requirements are met. Do not call a simulated fixture live runtime evidence.

## 10. Initial decision posture

Based on the current Phase 0 crosswalk, the defensible starting position is **mixed and unresolved**, not “NEX lacks evaluation” and not “NEX has integrated evaluation.”

The repository already contains multiple distinct forms of discrimination, evaluation and selection: lexical redundancy/anchor checks, keyword and activation retrieval, workspace candidate competition, prediction/surprise signals, metacognitive event production, emphasis scoring, warrant calculations, affect/drive signals and persistence/retrieval paths. The crosswalk also records cases where outputs are prompt-consumed, cases where consumption is conditional, and cases where a bounded search has not found a decision consumer.

Therefore:
- Do not collapse these mechanisms into one generic evaluator.
- Do not infer that every score should influence every decision.
- Do not treat all non-consumption as a defect; observation-only may be intentional.
- Do not equate prompt inclusion with model reliance or improved task outcomes.
- Do not infer learning from persistence alone.
- Do not infer a global absence from a bounded search.
- Do not promote a source-level finding to host/runtime fact.
- Do not add mechanisms until a specific, evidence-backed deficiency survives competing explanations and the governing approval boundary.

The next audit pass should reconcile this workpaper line-by-line with the current Crosswalk and Defect Backlog, then select the smallest isolated test set capable of discriminating the live hypotheses. It should not change NEX behaviour.

## 11. Completion conditions for this workpaper

This workpaper is ready for review only when:

- each existing relevant evaluator/selector has an owner, inputs, output, callsites and actual consumers mapped;
- source and test evidence are revision-bound;
- observation-only, conditionally consumed, operationally consumed and unknown pathways are distinguished;
- the principal candidate hypotheses have at least one explicit falsifier each;
- candidate isolated tests specify controls, outcome definitions and limitations;
- duplicate coverage in the existing Crosswalk is reconciled rather than copied;
- no production behaviour, flags, databases, protected experiment or roadmap criterion has been altered.

Completion of this workpaper does **not** mean Gate 0 is complete, does not authorise Phase 1 and does not establish that any mechanism improves cognition. It is one supporting analysis within the existing Phase 0 evidence package.

---

## 12. Provenance note

This draft was assembled from the existing Phase 0 handover and the current PR #49 documentation branch. The initial pathway leads in §4 are summaries of the companion crosswalk, not independent re-verification of every cited source path. The next revision must bind each detailed claim to the current source/test revision and preserve the crosswalk's explicit host/runtime unknowns.

No NEX runtime code, tests, schema, database, flags, experiments, baselines, tripwires, host state or deployment was changed in preparing this workpaper.


## 13. Source reconciliation pass 1 — revision-bound findings (24 Nov 2026)

### 13.1 Revision and method

This pass re-opened the companion Crosswalk, Defect Backlog, Chat Pathway Audit and ADR-001 on the Phase 0 documentation branch, then inspected the relevant implementation files at PR #65 source head `cffbbc94b5a494247d127abf2720886a08f7a567`. This is an exact, public GitHub source snapshot; it is not proof that the deployed host runs this revision. Source blob IDs are recorded below so later changes can be detected.

The following findings are a bounded source reconciliation, not a claim that every evaluator or every consumer in the repository has been exhausted. The Crosswalk and Defect Backlog remain the companion authority for their wider inventories. In particular, the exact Frozen V2.1 specification and Founder Sign-Off remain unavailable.

### 13.2 Finding EVI-01 — Global Workspace is a prompt-framing selector, not a general evaluator

**Claim:** the Fountain Global Workspace gathers a bounded set of heterogeneous candidates, assigns source-specific salience values, selects one maximum-salience candidate and prepends its framing text to the Fountain focus block. It does not assess the truth or evidential quality of the selected candidate.

- **Status:** source-confirmed [L1]; host activation [L2] UNKNOWN; behavioural value [L4] UNKNOWN.
- **Source anchors at PR #65 head:**
  - `theory_x/stage_tom/global_workspace.py`, blob `54ddab05112702eef34faaa4f24d45139350b349`, lines 38–80: source weights and surprise candidate admission.
  - Same file, lines 130–168: `arbitrate_candidates()` uses `max(..., key=salience)`; ties retain the first maximum; Chat budget selection is a separate stable-order policy.
  - Same file, lines 245–289: candidates are surprise, momentum, bonsai, stakes and drive; winner is returned as the framing line.
  - `theory_x/stage6_fountain/generator.py`, blob `d57bde71eca5f5968964b2846b8a34cffa8964a2`, lines 3558–3578: `NEX5_GLOBAL_WORKSPACE` defaults to `1`; a non-empty winner is prepended to `focus_block`.
- **Forward path:** candidate sources → salience constants / candidate functions → max-salience winner → returned framing line → Fountain focus prompt. The source does not establish that the language model relies on the frame or that it improves the generated thought.
- **Backward path:** the prompt insertion reads the single returned winner; it does not receive a separately computed truth, provenance, uncertainty or independent-corroboration assessment.
- **Discrimination boundary:** this mechanism distinguishes candidates by configured source salience, not by semantic correctness. The first-maximum tie rule is deterministic but is not an evidential tie-break.
- **Known interacting issue:** `_surprise_candidate()` admits recent scores above 0.3. The empty-window exclusion is conditional on `NEX5_GW_SURPRISE_NONEMPTY=1`; the source comment records that empty prediction windows can carry score 1.0 with NULL actual content. The companion Defect Backlog tracks this as DRAFT-011. Do not duplicate it as a new defect here; retain it as a high-value T1/T3 crosswalk case.
- **Falsifier / next evidence:** show an existing source-supported evaluator upstream of arbitration that validates candidate content/provenance and is actually read by the selector, or a controlled isolated test showing the selector's intended policy includes such a distinction. No such dependency was established in this pass.
- **Functional sufficiency:** potentially sufficient for its narrow responsibility of choosing a prompt frame by salience; insufficient evidence to call it an evaluator of truth, relevance or importance in a general sense. A central evaluator is not implied.

### 13.3 Finding EVI-02 — EmphasisEngine is deliberately observational; its score is persisted but not shown to alter selection

**Claim:** EmphasisEngine computes a three-signal equal-weight mean plus a separately logged drive-resonance value, and Fountain persists the result against the generated `fountain_event_id`. The inspected call path labels this post-hoc/observation-only and does not feed the score back into the thought or a later decision in the inspected generator path.

- **Status:** source-confirmed [L1]; runtime execution [L2] UNKNOWN; downstream decision consumption [L3] not established; behavioural validation [L4] UNKNOWN.
- **Source anchors:**
  - `theory_x/stage_emphasis/emphasis_engine.py`, blob `21d67aa1b86fe224d30dd17fed64cba987e71a6c`, lines 1–25 and 212–255: observation-only contract; `goal_relevance`, `self_relevance`, `surprise` are equally averaged; `drive_resonance` is still computed but excluded from `combined` and `dominant_signal`. The module records a prior ground-truth test of drive resonance as null (p=0.190, effect -0.013); the other three signals are explicitly described as untested, not validated.
  - `theory_x/stage6_fountain/generator.py`, blob `d57bde71eca5f5968964b2846b8a34cffa8964a2`, lines 1125–1165: engine construction is local to FountainGenerator and fail-safe; emphasis table is created lazily.
  - Same file, lines 2393–2413: scoring occurs before the `fountain_events` insert and is described as not touching the thought or upstream state.
  - Same file, lines 2414–2465: after the event insert returns `fountain_event_id`, an `emphasis_log` row is written with that ID and the component signals/combined/dominant value.
- **Forward path:** generated thought → score computation → event insert returns ID → `emphasis_log` persistence keyed by that ID. This establishes identity association, not downstream use.
- **Backward path:** no read of `emphasis_log` or `EmphasisResult` by the inspected Fountain selection/crystallization path was established in this bounded source pass. The score is retained in `_last_result` for node state/inspection; a full repository-wide sink audit remains open.
- **Falsifier / next evidence:** locate and trace a consumer that reads the stored emphasis row or current result and changes an actual selection, gate, prompt, confidence or action; otherwise a controlled fixture should show that changing the emphasis signal leaves downstream decisions invariant.
- **Functional sufficiency:** observation-only may be the correct functional level. Lack of a decision consumer is not automatically a defect, because the stated contract explicitly defers influence pending evidence that the measure tracks something real. Do not wire it into selection merely to increase its evidence level.

### 13.4 Finding EVI-03 — CoherenceGate applies a bounded heuristic acceptance policy, not general contradiction or truth evaluation

**Claim:** the inspected CoherenceGate evaluates candidate text against a limited set of recent beliefs, locked Tier-1 anchors, active goal titles and open-problem titles. Its decisions are rule-based and order-sensitive; it does not establish factual truth or comprehensively reconcile contradictory evidence.

- **Status:** source-confirmed [L1]; Fountain construction in `run.py` source [L1]; actual runtime calls/host activation [L2] UNKNOWN; behavioural validity [L4] UNKNOWN.
- **Source anchors:**
  - `theory_x/stage_gate/coherence_gate.py`, blob `39f73108cb36e886cfc8dafe045646acba15549e`, lines 291–400: Jaccard redundancy rejection; direct negation comparison against selected locked anchors; Jaccard HOLD band; goal/problem title overlap rules; novel connection ACCEPT; opt-in reshape; default ACCEPT.
  - Same file, lines 402–477: bounded substrate queries and gate-decision logging.
  - `run.py`, blob `73a2c58a4f5f0348135a46eb83d6cdd61db874e7`, lines 124–155: constructs and supplies the gate to dynamic formation.
- **Forward path:** ThoughtPacket → fresh bounded substrate reads → ordered heuristic checks → GateDecision → caller-specific handling. The Fountain crystallizer's actual ACCEPT/REJECT/HOLD handling is separately mapped in the Crosswalk and trace stack; this gate is not shown as a general Chat response gate.
- **Backward path:** decision inputs are candidate text/packet metadata, selected anchor content and IDs, recent belief content, active goal titles and open-problem titles. The inspected rules do not query independent external sources or a general truth/uncertainty evaluator.
- **Discrimination boundary:** the direct-negation rule only applies when token overlap and anchor-negation difference meet its conditions; a paraphrase with lower Jaccard can pass that specific check. Goal/problem checks use title-token overlap and negation, not full semantic entailment. A default ACCEPT means “no configured rule fired”, not “verified true”.
- **Falsifier / next evidence:** representative minimal pairs across paraphrase, contradiction, scope, temporal change, source conflict and factual error could show that the existing gate reliably meets a broader approved contract. That contract must first be taken from the governing specification; do not infer it from class names or comments.
- **Functional sufficiency:** plausibly sufficient as a bounded coherence/redundancy gate for its declared responsibility; not sufficient evidence for a universal evaluator. This does not justify broadening its remit.

### 13.5 Finding EVI-04 — Metacognition produces self-observation events that can become prompt context; prompt inclusion is not proof of correction

**Claim:** the Chat path calls Metacognition's detector tick, obtains a formatted recent observation and appends non-empty text to the current Chat belief context. Fountain has a separate conditional injection path behind `NEX5_METACOG_VOICE=1`. This is a real source-level feedback-to-context path, but not evidence that the model recognises, accepts or corrects the detected pattern.

- **Status:** source-confirmed [L1]; Chat/Fountain live activation and emitted event counts [L2] UNKNOWN; model reliance/decision change [L3] UNKNOWN; improved behaviour [L4] UNKNOWN.
- **Source anchors:**
  - `theory_x/stage9_metacognition/metacognition.py`, blob `de853bd93a11dcfe39ee8afa30a84e5c7b1f8b08`, lines 242–369: `tick()` runs detectors, writes events, refreshes a recent-event cache; `get_recent()` retrieves unresolved events; optional salience ranking is conditional.
  - Same file, lines 369–408: `format_for_prompt()` formats the top cached event as a short self-observation.
  - `gui/server.py`, blob `d67df10f4449004c255e38b11b4a1888a4e4934c`, lines 1519–1537: Chat calls `tick()`, formats and appends non-empty output to `belief_text`.
  - `theory_x/stage6_fountain/generator.py`, blob `d57bde71eca5f5968964b8a34cffa8964a2`, lines 3643–3655: Fountain prompt injection is conditional on `NEX5_METACOG_VOICE=1`.
- **Forward path:** detector inputs → event write → unresolved-event retrieval/cache → formatted self-observation → Chat context append (or conditional Fountain append). The current path does not establish a subsequent acknowledgement, correction, changed detector threshold or durable policy revision.
- **Backward path:** the prompt text depends on the selected top recent event; by default the selection is recent-first, with an optional severity/decay ranking behind `NEX5_SALIENT_SELF_OBS`. The model receives the formatted phrase, not necessarily the full evidence, detector inputs or competing interpretations.
- **Discrimination boundary:** event production, event retrieval and formatted prompt inclusion are separate stages. A detector's event may be stale, noisy or wrong; prompt presence alone does not validate it. Repeated detector outputs and their provenance remain relevant to H5.
- **Falsifier / next evidence:** an isolated controlled fixture can compare correct, false-positive, stale and contradictory detector events, then inspect whether the downstream response appropriately uses, qualifies or rejects the observation. A true correction claim would additionally require a source-supported later state change.
- **Functional sufficiency:** sufficient to surface an observation into Chat context under the inspected path; not evidence of a self-correcting feedback loop. Do not infer adaptation from prompt inclusion.

### 13.6 Finding EVI-05 — Warrant calculation/persistence and operational use remain distinct, with boot wiring unresolved

**Claim:** Warrant has a defined computation and persistence mechanism, and its background pass is flag-gated. In the inspected `run.py` blob at the source revision, no `WarrantPass` construction/start call was found. The class docstring says it is constructed and started only when `NEX5_WARRANT=1 (run.py)`, but the inspected boot file does not substantiate that statement. This is a documentation/source-wiring discrepancy to resolve, not proof that warrant never runs in another host wrapper or alternate entrypoint.

- **Status:** computation/persistence source [L1]; normal `run.py` construction not established; runtime [L2] UNKNOWN; decision consumer [L3] UNKNOWN.
- **Source anchors:**
  - `theory_x/stage_warrant/warrant.py`, blob `a15bc9d012fffac319adf1634f52eb1fde0e35b6`, lines 105–190: read-only calculation from belief graph/lineage, historical usage and dynamic event records; combines four components and persists to `belief_warrant`.
  - Same file, lines 205–255: `WarrantPass` background loop and `NEX5_WARRANT` guard in `start_loop()`.
  - `run.py`, blob `73a2c58a4f5f0348135a46eb83d6cdd61db874e7`: inspected full 812-line boot file; no `WarrantPass` reference was found in this file.
  - `tests/test_warrant.py`, blob `99e639bcf3bd8c1f6e5ab1acbf5b61f20e438b51`, lines 101–121: computation test and flag-off thread-start test; these do not prove normal boot wiring or a consumer.
- **Forward path:** source data → `compute_all()` → weighted warrant values → `belief_warrant` upsert through Writer, if `run_once()` is called by an active pass.
- **Backward path:** no operational reader of `belief_warrant` was established in the bounded inspected callsites. The computation's inputs are historical survival/promotion, distinct-day usage and cross-branch support/synthesis signals.
- **Falsifier / next evidence:** locate an alternate boot/host entrypoint that constructs and starts the pass, then trace a reader from the persisted table to a decision sink; or establish that the pass is intentionally dormant/analysis-only under the approved contract.
- **Functional sufficiency:** the calculation may be adequate as an offline/observational “earnedness” measure. Its present role cannot be upgraded to an operational belief evaluator without proving both authorised activation and actual consumption.

### 13.7 Finding EVI-06 — Surprise has distinct consumers with different admission semantics

**Claim:** the same `surprise_events` records feed several distinct pathways that do not share the same validity filter. The SurpriseLoop requires non-empty predicted and actual content plus `surprise_flag=1`; the Fountain confidence weighting reads the latest score without checking `actual_content`, `surprise_flag` or `big_surprise`; Global Workspace has a separate optional empty-window filter. This creates a source-confirmed semantic mismatch across consumers.

- **Status:** source-confirmed [L1]; frequency and active host flags [L2] UNKNOWN; impact on actual beliefs/thoughts [L3] UNKNOWN; behavioural effect [L4] UNKNOWN.
- **Source anchors:**
  - `theory_x/life/surprise_loop.py`, blob `bb1869e3d5784ca668ca37e8c76cc25998d7a381`, lines 96–118: promotion query explicitly requires flagged events and non-empty actual/predicted content.
  - `theory_x/stage_prediction/surprise_weighting.py`, blob `10db4a80a31c065b113290f21d89bd16743a89fb`, lines 37–67: confidence weighting selects the latest event in a 60-second window and uses `surprise_score` alone to compute the boost.
  - `theory_x/stage_tom/global_workspace.py`, blob `54ddab05112702eef34faaa4f24d45139350b349`, lines 63–80: empty-window exclusion is conditional on `NEX5_GW_SURPRISE_NONEMPTY=1`.
  - `theory_x/stage6_fountain/crystallizer.py`, blob `62cbb62cf55b8c39ab1301b9d89d36b37cc16bfc`, lines 489–496: confidence weighting is called when `NEX5_SURPRISE_WEIGHT` is unset or `1` (source default `1`).
- **Forward paths:** one producer/table → (a) SurpriseLoop's filtered promotion to Tier-6 belief, (b) confidence weighting of a later crystallized Fountain belief, and (c) Global Workspace candidate admission/framing. These are separate consumers with different contracts.
- **Backward path:** the confidence sink reads the latest score, not the validation fields selected alongside it; the promotion sink filters those fields; the Workspace sink uses its own flag-controlled content/score filter.
- **Discrimination boundary:** a numeric score is not interchangeable with a validated, content-bearing prediction error. A high sentinel score can be “no usable observation” for one consumer but a maximal weight for another.
- **Falsifier / next evidence:** a temporary-database test should insert matched rows (valid content, NULL actual, empty actual, unflagged, boundary score) and assert each consumer's documented admission result. This is a proposed isolated test only; it has not been run in this pass.
- **Functional sufficiency:** each consumer can be locally coherent under its own contract, but the current cross-consumer semantic mismatch is a strong T1/T2/T3 candidate. Do not change filters or defaults before the governing acceptance contract and existing defect record are reconciled.

### 13.8 Finding EVI-07 — FocalSet and WorkingMemory are a selection-to-context pathway, not merely a log

**Claim:** the Chat handler updates the process-global FocalSet from retrieved belief candidates, adds the selected focal beliefs to a session-specific WorkingMemory object, and then reads/logs active WorkingMemory items. The current code section shown here does not itself prove the later prompt-injection branch; the companion Chat Pathway Audit and Crosswalk trace that downstream conditional append. Thus the “log-only” comments are not an accurate description of the full pathway.

- **Status:** source-confirmed [L1] for selection and session-memory writes; prompt-injection path source-confirmed in the companion audit; live activation [L2] UNKNOWN; model reliance [L3] UNKNOWN.
- **Source anchors:**
  - `gui/server.py`, blob `d67df10f4449004c255e38b11b4a1888a4e4934c`, lines 114–135: process-global FocalSet and module-level setup.
  - Same file, lines 1672–1725: retrieved candidates → FocalSet update → focal IDs → session WorkingMemory additions → active-item read/log.
  - `theory_x/focal_set.py`, blob `e12531f2858085778ebca75f73a7dee6ec8ce416`, lines 56–184: salience smoothing, open-mode selection and top-K/protection policy.
- **Forward path:** retrieval candidates → FocalSet priorities/selection → focal belief IDs → session WorkingMemory additions → active items; companion Chat audit traces the conditional same-turn/cross-turn prompt append.
- **Backward path:** selected IDs depend on the retrieved candidate pool and FocalSet's current process state, including smoothed priorities/protected prior focal members. WorkingMemory is keyed by session ID, while the FocalSet instance is process-global.
- **Discrimination boundary:** retrieval candidate generation limits what FocalSet can choose; FocalSet does not independently discover omitted candidates. The shared selector state and per-session memory boundary are distinct and should not be collapsed into one “memory” claim.
- **Falsifier / next evidence:** paired isolated requests with overlapping/disjoint belief IDs across sessions can establish whether shared focal state changes later selection; a separate trace should identify exactly which WorkingMemory IDs enter each prompt. Do not interpret this coupling as a privacy leak without demonstrating cross-session content transfer.
- **Functional sufficiency:** the selector can be sufficient as a bounded attention mechanism over the supplied candidate set. Whether process-global state across sessions is intended is unresolved; no redesign is proposed.

### 13.9 Reconciliation summary and next smallest evidence set

This pass confirms that “evaluation” in NEX is not one homogeneous function. At least six different responsibilities are visible in the inspected source: prompt-frame salience competition (Global Workspace), a bounded coherence gate (CoherenceGate), observation-only post-thought measurement (EmphasisEngine), self-observation surfaced as context (Metacognition), an earnedness computation with unestablished boot/consumer wiring (Warrant), and surprise consumers with non-equivalent admission semantics. FocalSet is an attention selector whose outputs can reach Chat context through WorkingMemory.

The evidence does **not** support a blanket claim that NEX has no evaluation, nor a blanket claim that these mechanisms form an integrated evaluative system. It supports a mixed arrangement with local evaluators/selectors, observation-only measurements, conditional prompt feedback, and at least one source-confirmed cross-consumer semantic mismatch.

**Smallest proposed isolated test set (not run in this pass):**
1. **T1/T2 surprise admission matrix:** one temporary DB, paired event rows varying only actual-content presence, surprise flag and score; inspect promotion, confidence weighting and workspace admission independently.
2. **T2 emphasis non-consumption check:** vary one EmphasisResult signal under a deterministic Fountain fixture and compare generated thought, gate outcome, crystallized belief and speech queue; expected invariance is consistent with the observation-only contract.
3. **T1 CoherenceGate minimal-pair matrix:** near-duplicate, paraphrase, direct negation, scope/temporal qualifier and goal-title overlap; assert actual GateDecision and reason without interpreting ACCEPT as factual truth.
4. **T2/T4 Metacognition context test:** inject valid, false-positive, stale and conflicting event fixtures; inspect formatted context and downstream model stub inputs, without claiming model reliance.
5. **T2/T4 FocalSet session-boundary fixture:** overlapping and disjoint candidates across two session IDs; inspect selected IDs and prompt-contributing WorkingMemory IDs.
6. **Warrant wiring inspection:** read-only search of all boot/entrypoint variants and all readers of `belief_warrant`; do not arm `NEX5_WARRANT` or start the background pass.

No new tests were added or executed in this pass. The proposed tests remain within the Phase 0 isolated-evidence boundary but must be reconciled against the exact governing acceptance criteria before implementation. No production source, runtime code, flags, database, experiment, baseline, tripwire, host or deployment was changed.


## 13.10 Warrant wiring correction — recorder is boot-wired; scorer remains separate

The first pass's EVI-05 correctly noted that the inspected `run.py` does not construct/start `WarrantPass`, but its summary was incomplete because it did not distinguish the separately named `WarrantRecorder`.

**Verified source distinction at the same source revision:**

- `run.py`, blob `73a2c58a4f5f0348135a46eb83d6cdd61db874e7`, lines 355–374: `WarrantRecorder` is constructed and started when `NEX5_WARRANT_RECORD=1`. This is a real boot callsite, conditional on the flag. It is not the `WarrantPass`.
- `theory_x/stage_warrant/recorder.py`, blob `ade231c1fc7c8da7f90f8f7ab375d352837a7c79`, lines 1–38 and 140–220: the recorder writes append-only `belief_survival`, `belief_use_day`, `belief_use_days` and cursor records. Its survival checks are a shadow conflict check; it does not mutate belief state.
- `theory_x/stage_warrant/warrant.py`, blob `a15bc9d012fffac319adf1634f52eb1fde0e35b6`, lines 1–105 and 105–190: `compute_all()` currently reconstructs survival from `beliefs.promotion_log` and sustain from the existing retrieval/anchor/synthesis/lineage/arc event sources. The inspected implementation does not read the recorder's `belief_survival` or `belief_use_days` side tables.
- Same `warrant.py`, lines 205–255: `WarrantPass` is the separate periodic computation-and-persistence loop, guarded by `NEX5_WARRANT=1`; no construction/start call was found in the complete inspected 812-line `run.py`.
- `tools/warrant_validate.py`, blob `19f0873c65fa97c192ed4cdba421a6d7dc6df8c5`, lines 1–30 and 54–62: the validation tool calls `compute_all()` read-only. It does not read the recorder side tables as its evidence source.
- `tests/test_warrant.py` covers the computation and the off-gate; `tests/test_warrant_recorder.py` covers recorder cycles and its off-gate. Those tests do not establish a data handoff between recorder outputs and the scorer.

**Updated classification:** recorder boot wiring is source-confirmed but conditional [L1]; actual activation and accumulated rows [L2] UNKNOWN. The scorer's existing compute/persist code is source-confirmed [L1], but normal `run.py` activation is not established. The recorder-to-scorer integration is **not present in the inspected source path**. This is stronger and more precise than saying simply “Warrant has no boot wiring”: one data-collection component can be armed while the separate score computation remains dormant, and the newly recorded evidence is not consumed by that computation in the inspected implementation.

**Interpretation boundary:** do not assume this is an accidental defect. The recorder's stated purpose is to accumulate evidence for re-validation after a prior gate failure. The correct next question is whether a later authorised validation step is meant to read those tables, or whether a future scoring revision is planned. The current evidence does not authorise enabling either flag, changing the scorer, or inventing a bridge.

## 13.11 Isolated characterization test added — surprise weighting admission

Added `tests/test_surprise_weighting_admission.py` on the Phase 0 branch. It uses a temporary SQLite database and tests the existing `confidence_for_fire(dynamic_db=...)` function without touching project databases or runtime flags.

The two cases characterize the current source behaviour:
1. A recent event with `surprise_flag=0` and `actual_content=NULL` still raises confidence according to its numerical score.
2. Such a newer empty event supersedes an older content-bearing event for the weighting consumer.

These are characterization assertions, **not** an assertion that this is the desired policy. They make the observed consumer boundary reproducible and give a future policy decision a precise regression surface. Existing `tests/test_gw_surprise_nonempty.py` already characterizes the separate Workspace empty-window flag behaviour; SurpriseLoop's stricter promotion query remains visible in its source and should be tested independently if the approved contract requires it.

The test was committed as a test-only change. It does not alter production code, flags, runtime state, databases or the roadmap. CI has been triggered by this commit; results are pending at the time of this note.


## 13.12 FocalSet / WorkingMemory sink qualification — prompt use is conditional, selector state is shared

A targeted re-read of the full Chat handler resolves two details that should not be compressed into “FocalSet feeds memory”:

- `gui/server.py`, blob `d67df10f4449004c255e38b11b4a1888a4e4934c`, lines 114–141: one module-level `_focal_set = FocalSet(K=4)` is created and registered for the process; separately, `_working_memory_by_session` is a dictionary of WorkingMemory instances keyed by session ID.
- Same file, lines 1672–1726: when the world-model retriever returns candidates, the single process-level FocalSet is updated; its focal IDs are then added to the current request's session-specific WorkingMemory. The current focal candidate contents are taken from this request's retrieved candidate map.
- Same file, lines 1849–1864: WorkingMemory is actually consumed into `belief_text` only when there is a session ID, active items, `register.name == "Conversational"`, and `belief_count >= CHAT_GAP_MIN_BELIEFS`. At most five active items are appended under “Recently attended (cross-turn)”. This is a conditional prompt-context sink, not unconditional memory injection.
- `theory_x/focal_set.py`, blob `e12531f2858085778ebca75f73a7dee6ec8ce416`, lines 92–184: FocalSet retains priorities, focal IDs, last-shift tick and mode between requests; returning IDs reuse smoothed priority and the hold-time gate can protect current focal members still present in a later candidate pool.

**Updated impact boundary:** the source confirms a shared process-level attention selector whose state can influence which candidates are selected in a subsequent session. It does not establish that one session's private WorkingMemory contents are copied into another session's WorkingMemory: those buffers are separately keyed. Nor does it establish an actual privacy breach. The plausible cross-session effect is indirect selector-state influence (priority smoothing / hold protection), not direct content transfer. Whether that coupling is intended requires the governing spec and, if relevant, a controlled two-session fixture.

**Evidence classification:** selection-to-session-memory write [L1]; conditional same-turn/cross-turn prompt inclusion [L1]; model reliance [L3] UNKNOWN; beneficial or harmful cross-session effect [L4] UNKNOWN. Existing tests cover FocalSet selection and WorkingMemory behaviour separately, but the inspected test set does not establish this full handler pathway or its two-session interaction.
