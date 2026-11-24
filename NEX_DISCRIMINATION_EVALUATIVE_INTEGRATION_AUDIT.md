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
