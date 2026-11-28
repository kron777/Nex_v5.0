# Sentience 5.5 → NEX cognitive wire trace (first pass)

**Date:** 2026-11-28  
**NEX base:** `main` at `bbca5deb3a0398331503ce61c95a62f8d1b3d33d`  
**Sentience source:** `kron777/Sentience_5.5` at `1767acf1fdb321d046261eb3c3059084c85fc0c8`  
**Status:** source-traced research artifact; no runtime behaviour, cognitive policy, feature flag, or frozen specification changed.

## 1. Why this trace exists

The purpose is not to add another “self-awareness node”. Sentience 5.5 already separates several functions that a human may casually group under that phrase. NEX also contains multiple related faculties. The work is to understand the existing functions and the effects of their connections before changing any wire.

This is a selected-path trace, not a complete audit of either repository. Claims below are classified as:

- **Verified source fact:** directly visible in the cited source.
- **Tested behaviour:** asserted by a named test, at the stated scope.
- **Open question:** requires further source tracing, controlled tests, or live evidence.

No claim of subjective experience is made by the presence of a self-model or self-awareness label.

## 2. Sentience 5.5: distinct functions that must not be collapsed

| Component | Actual responsibility in source | Inputs | Outputs / effects | Important boundary |
|---|---|---|---|---|
| `Self_Model_Node.py` | Registry and telemetry ledger for nodes | Explicit node registration, heartbeat calls, routed events | Node status, recent event snapshot, stale-node health label, known facts and explicit unknowns | Records and reports; it does not itself infer intentions or direct actions |
| `self_awareness_node.py` | Operational self-state counters | Integration frame's component confidence values; monitoring alerts; elapsed time | Mean confidence as `coherence`, uptime, anomaly count and last anomaly; SQLite rows | Its “coherence” is an arithmetic mean of supplied confidence fields, not a general measure of cognitive coherence |
| `Meta_Awareness_Node.py` | Second-order monitoring | Prediction confidence/accuracy, emotion/mood/intensity, narrative theme | Confidence/dissonance state, history, SQLite rows, queued reflection directives | Emits reflection directives, explicitly not actions |
| `Integration_Node.py` | Normalizes latest received outputs into versioned frames | HTTP inputs for decision, learning, communication, monitoring and adaptation | Versioned component snapshot and a default-wait/final-action frame in an async queue | It is not, by itself, proof that every node is connected to every other node or that the frame reaches the self-awareness endpoint |

### 2.1 Sentience connection observations

1. `Self_Model_Node` is an independent in-memory registry with a bounded 200-event history. Its `heartbeat()` registers an unknown node if necessary; `snapshot()` computes staleness using a five-second threshold. The shown implementation is not the same mechanism as `self_awareness_node.py`.
2. `self_awareness_node` accepts an integration payload and averages every numeric-looking `confidence` value supplied under `components`. If none are present, coherence becomes 0.0. It separately increments anomaly count when a monitoring payload says `alert`.
3. `Meta_Awareness_Node` adds 0.1 dissonance when emotion intensity exceeds 0.7, adds 0.2 when a narrative theme contains “conflict”, and adds the absolute confidence difference for an inaccurate prediction. On evaluation it emits a reflection directive when confidence is below 0.4 or dissonance above 0.6, then decays dissonance by 20%.
4. `Integration_Node` stores the most recent payload per input key, increments a version and emits a frame after each accepted input. It copies payloads into `components`; it does not derive a richer cognitive interpretation of them.
5. In the inspected repository tree, there is no test module specifically exercising the end-to-end connection between these four components. The latest commit message for Sentience's six doctrine checks reports 8 passed and 2 failed: the judgement-rationale record and external-content code-execution checks. That commit message is evidence about the reported run, not a fresh test run performed for this trace.

**Key research caution:** the code establishes separate telemetry, confidence/dissonance monitoring, frame aggregation and action-routing functions. It does not establish that those functions are fully orchestrated into one closed cognitive feedback cycle in the current repository.

## 2.2 Sentience 5.5: central coordination patterns are not one unified network

A broader tree inspection found several distinct coordination patterns in Sentience 5.5. They should not be treated as one proven end-to-end architecture:

### A. `The_Central_Column.py` — relevance-selected global workspace prototype

The file is stored as a Jupyter notebook serialized under a `.py` filename (the fetched file content is notebook JSON). Its `CentralColumn`:

- registers arbitrary node instances by name;
- stores the latest ten Signals in short-term memory;
- asks each registered node for `assess_relevance(signal, memory)`;
- selects nodes scoring at least 0.4;
- calls `process()` on selected nodes in descending relevance order;
- chooses the first node's content as primary output and merges all active nodes' context dictionaries.

Important observed properties and risks:

1. Despite a comment saying relevance polling is parallel, the implementation awaits each node sequentially.
2. Node process calls are also sequential, so later nodes see the shared short-term memory after the original stimulus and before the final synthesized signal is appended; they do not receive the previous node's response as their stimulus.
3. Context is merged with ordinary `dict.update()`; when two nodes emit the same key, the later node silently overwrites the earlier value.
4. The highest-relevance node controls primary content; there is no explicit conflict-resolution or evidence reconciliation step.
5. Per-node exceptions are logged and converted to zero relevance / skipped processing, allowing the cycle to continue without a structured partial-failure record.
6. The code shown contains no explicit recursion, propagation-depth bound, cycle detection, or causal trace identifier.

These are source observations, not a judgement that the prototype is useless. It is valuable evidence of the intended “aspects of mind” model: nodes assess relevance, contribute different effects, and synthesize into one signal. But it is not equivalent to a validated, dynamically propagating neural network.

### B. `Cognitive_Event_Bus.py` — synchronous event fan-out

The event bus records events in a bounded history (default 500), copies the current subscriber list under a lock, then invokes callbacks synchronously in the publishing thread. Callback exceptions are logged and swallowed. This makes the event path inspectable and simple, but one slow callback delays the publisher and all later callbacks. The bus itself does not interpret, prioritize, retry, or persist events.

### C. `Feedback_Loop_Node.py` — polling over latest-value slots

This node receives separate latest-value snapshots for actuator, emotion, motivation, value drift and world inputs. Its 500 ms loop derives at most one feedback record from those snapshots and persists it. The current `_generate_feedback()` uses sequential independent `if` statements for positive emotion, distress, and value drift; if multiple conditions are true, the last matching condition overwrites the earlier feedback type/target/payload. The ingested motivation and world values are read into local variables but are not used in the shown feedback decision logic. The node emits feedback records/directives; the file's own comments say it has no decision authority.

### D. `Orchestrator.py` — separate conversational stack

The command-line Orchestrator explicitly constructs Memory, Nonsense, Knowledge, Crawler, Evolver, Reasoning, LLM and Conversational Intelligence objects and passes dependencies into the chat object. This is a different coordination path from `The_Central_Column.py` and from the event bus. The repository therefore contains multiple architectural strands/prototypes, not one automatically unified central nervous system.

### E. Integration conclusion

Sentience 5.5 is valuable as a catalogue of cognitive functions and alternative connection patterns, but names and conceptual intent are not evidence that every node is wired into the same runtime. The next research pass must build a node-to-node edge inventory from actual constructors, callback registrations, method calls and event subscriptions. The NEX comparison must map functions and causal effects, not transplant Sentience's coordination model wholesale.

## 3. NEX: selected self-model and inside-membrane pathway

### 3.1 Forward path

```text
Internal sense adapters
  ├─ Proprioception ───────────────┐
  ├─ Temporal ────────────────────┤
  ├─ Interoception ───────────────┤
  └─ MetaAwareness ──> sense.db   │
                                  v
DynamicState.status() ───────> SelfModel.snapshot()
Beliefs DB ─────────────────>   ├─ inside-belief selection
                                ├─ attention branch summary
                                └─ formatted self-state
                                         |
User sentence -> Chat route -> MembraneClassifier
                                  ├─ INSIDE -> SelfModel + inside beliefs
                                  └─ OUTSIDE -> world-belief retrieval
                                         |
                          BehaviouralSelfModel (INSIDE only)
                                         |
                         other prompt faculties / LLM response
                                         |
                              conversations.messages
                                         |
                         BehaviouralSelfModel.observe()
                                         |
                       compare observed behaviour to seeds
                                         |
                    optional CoherenceGate -> beliefs.db
                                         |
                 source='behavioural_observation' is classified INSIDE
                                         |
                           future self-inquiry retrieval
```

This is a real feedback path, not merely a conceptual similarity. Its timing, candidate selection and effect size still need controlled observation.

### 3.2 Source-traced edges

| Edge | Origin → destination | Verified operation | Propagation / effect |
|---|---|---|---|
| NEX-SM-01 | Stage 1 internal adapters → `sense.db` | Scheduler constructs Proprioception, Temporal, Interoception and MetaAwareness adapters; MetaAwareness polls writer queue depths, scheduler status and error-channel length | Writes timestamped internal sense events |
| NEX-SM-02 | `sense.db` → Stage 4 `SelfModel.snapshot()` | Snapshot reads `internal.proprioception`, `internal.temporal`, `internal.interoception`, and attempts to read `internal.meta_awareness` | Produces a structured inside-state snapshot |
| NEX-SM-03 | DynamicState → SelfModel | Snapshot reads `dynamic_state.status()` for active branches, hottest focus, aggregate texture and pipeline status | Dynamic attention/status contributes directly to the self-state representation |
| NEX-SM-04 | `beliefs.db` → SelfModel | Selects unpaused beliefs at tier ≤6 from `_INSIDE_SOURCES`, classifies them INSIDE, weights by tier and returns up to five | Existing internal beliefs become part of the represented self-state |
| NEX-SM-05 | User query → membrane router | Classifier selects INSIDE or OUTSIDE; INSIDE calls SelfModel and inside-belief retrieval | Changes which information is assembled for the response |
| NEX-SM-06 | SelfModel snapshot → Chat prompt | Router formats the snapshot as natural-language self-state on INSIDE route | The model receives a textual representation of selected internal telemetry and beliefs |
| NEX-SM-07 | Recent NEX responses → BehaviouralSelfModel | Reads the last 100 NEX messages; calculates hedge rate, position rate, belief-use rate, dominant register and average response length | Creates a second-order description of observed output behaviour |
| NEX-SM-08 | BehaviouralSelfModel → Chat prompt | On INSIDE routes, Chat calls `tick()` and appends `format_for_prompt()` when sample data exists | Behavioural metrics can influence later self-inquiry responses |
| NEX-SM-09 | BehaviouralSelfModel → `beliefs.db` | Four-hour loop compares metrics with keystone expectations; deduplicates identical content; optionally checks CoherenceGate; writes Tier-6 `behavioural_observation` beliefs | The behavioural observation becomes persistent material for downstream retrieval |
| NEX-SM-10 | Behavioural observation belief → future INSIDE retrieval | `behavioural_observation` is explicitly in the membrane classifier's `_INSIDE_SOURCES` | The system can later retrieve its own prior behavioural observations while answering self-inquiry |

### 3.3 A subtle but important broken/unused edge

In `SelfModel.snapshot()`, the code reads the latest `internal.meta_awareness` payload into `meta_p`, but the subsequent `meta_awareness` object is populated from `dynamic_state.status()`. The values in `meta_p` are not used in the returned snapshot.

Therefore:

- the Stage 1 MetaAwareness adapter is active and writes operational telemetry;
- Stage 4 attempts to read its stream;
- the read payload currently has no effect on the returned SelfModel snapshot;
- similarly named “meta-awareness” fields in the snapshot instead describe selected DynamicState metrics.

This is not yet a recommendation to connect the payload. It is a traced edge whose intended semantics and downstream consequences must be determined first. The two data sources measure different things: scheduler/Writer/error telemetry versus dynamic pipeline/branch state. Combining them without preserving their distinction could distort the main self-representation.

### 3.4 The recurrent behavioural loop deserves special care

The following chain is source-confirmed:

1. Recent NEX responses are measured by `BehaviouralSelfModel.observe()`.
2. `compare_to_seeds()` turns deviations into divergence records.
3. `write_behavioural_beliefs()` may persist those records as Tier-6 beliefs with source `behavioural_observation`.
4. The membrane classifier explicitly classifies that source as INSIDE.
5. The SelfModel's inside-belief selection can therefore include those records.
6. The INSIDE query path can place the resulting text back into the next response context.

This means the behavioural self-observer is not simply a dashboard. It can participate in a recurrent representational loop: response → observation → belief → retrieval → response.

The code includes exact-content deduplication and an optional CoherenceGate check, but these do not by themselves establish that the loop is stable, correctly calibrated, non-amplifying, or causally useful. Those are empirical questions. The next step should be a trace/fixture that measures how a single controlled behavioural change propagates through the chain, including whether the generated belief is retrieved and changes the assembled prompt.

## 4. What the tests establish — and what they do not

### NEX evidence

- `tests/test_self_model.py` tests SelfModel/BehaviouralSelfModel protocol and local behaviour. Its own module docstring explicitly says it does **not** test the wiring in `gui/server.py`.
- `tests/test_influence_trace_integration.py` tests that trace instrumentation preserves selected outputs at several seams, including membrane candidate generation and global-workspace arbitration. It is not a complete test of the behavioural-belief feedback loop above.
- New characterization test `tests/test_behavioural_self_model_propagation.py` exercises the real isolated-substrate path from recent NEX messages through BehaviouralSelfModel belief creation, INSIDE classification, actual BeliefRetriever/QueryRouter prompt assembly, and counterfactual deletion of the generated belief. It is a test of this bounded recurrence, not a claim about live behaviour or whether the recurrence is desirable.
- New characterization test `tests/test_meta_awareness_wire_characterization.py` uses isolated fakes to demonstrate that the Stage 1 MetaAwareness payload currently has no effect on the Stage 4 SelfModel snapshot: with no DynamicState the fields remain null; with DynamicState the returned values come from DynamicState, not the Stage 1 telemetry payload. This records current dataflow, not a desired permanent contract.
- Both tests are in draft PR #359. GitHub Actions is rerunning the disposable sandbox/full baseline suite for successive branch commits; no pass count is claimed until the latest-head run completes.
- The current-main CI run for `bbca5deb3a0398331503ce61c95a62f8d1b3d33d` was **in progress** when this trace was prepared. No final pass count is claimed here.
- The latest mainline commit is G-84 step 2: it quiesces registered AppState producers against one shared five-second deadline before Writers close. The commit explicitly leaves some run.py-only producers outside the registry. This is a runtime lifecycle change, not evidence that the cognitive feedback path is complete.

### Sentience evidence

- The inspected tree contains six doctrine-check test modules, but no dedicated end-to-end test for the four self-model/meta-awareness/integration components described above.
- Sentience's latest commit message reports two intentionally visible failures: an unstructured judgement-rationale path and code execution built from caller-supplied strings in Ingenuity paths. They are not silently treated as passes or as part of this NEX integration trace.

## 5. Connection-effect register

| ID | Connection | Current disposition | Next evidence required |
|---|---|---|---|
| NEX-SM-01…04 | Internal sensing and dynamic state into SelfModel | Existing, source-traced | Fixture each input separately and measure which snapshot fields change |
| NEX-SM-05…06 | Sentence classification and SelfModel injection | Existing, source-traced | End-to-end Chat route test with INSIDE and OUTSIDE controls; verify only intended blocks differ |
| NEX-SM-07…08 | Observed behaviour into future prompt | Existing, source-traced | Controlled message corpus; establish metric sensitivity and exact prompt delta |
| NEX-SM-09…10 | Behavioural belief persistence and re-entry | Existing, source-traced recurrent edge | One-change propagation test: write → candidate selection → retrieval → prompt; measure repetition/amplification and dedup behaviour |
| NEX-SM-MA-01 | Stage 1 MetaAwareness payload into Stage 4 SelfModel | Read attempted, payload currently unused | Confirm intended role and decide whether this is an intentional dead-end, stale read, or missing connection; do not wire speculatively |

## 6. Bounded development increment now in progress

**No new cognitive node has been added. No prompts, thresholds, belief weights, feature flags, or action policy have been changed.**

A test-only causal propagation harness has been added in `tests/test_behavioural_self_model_propagation.py` around NEX-SM-07 → NEX-SM-10:

1. Creates isolated temporary substrate databases.
2. Inserts ten controlled NEX messages with a known high-hedging signal.
3. Runs the actual BehaviouralSelfModel observation and belief-write path.
4. Confirms the persisted `behavioural_observation` source is classified INSIDE.
5. Exercises the actual BeliefRetriever and QueryRouter to compare the pre-write and post-write prompt.
6. Deletes only the generated behavioural-observation beliefs and confirms their contribution disappears from the next prompt (counterfactual subtraction).

**Validation status:** the test is committed to the draft research PR; the updated-head GitHub Actions result is pending. It has not been represented as passed.

Next, once CI reports, inspect the exact result, correct any test defect without weakening the causal claim, then rescan the changed code and tests. If the test passes, it establishes that this one feedback edge is executable in an isolated fixture; it does not establish that it is stable or beneficial in live operation.

This is the first practical experiment matching the requested “wire” method: inspect the root, observe before connection, follow propagation, and evaluate the whole path.

## 7. Governance boundary

- Preserve the frozen S-01–S-25 register.
- Preserve the M0.1–M0.5 → Founder Gate 0 → M1.1–M1.10 order.
- NEX M1 remains declarative and schema-constrained; no generated Python execution.
- No live service restart, feature-flag activation, prompt/threshold change, live substrate write, or Gate 0 bypass is authorised by this research artifact.
- Mind-map entries remain descriptive; they do not gate, score, block or veto actions.
- This trace is not an implementation claim, runtime certification, or assertion of subjective consciousness.

## 8. Primary source files

### NEX 5.0 (base `bbca5deb3a0398331503ce61c95a62f8d1b3d33d`)

- `run.py`
- `theory_x/stage1_sense/__init__.py`
- `theory_x/stage1_sense/internal/meta_awareness.py`
- `theory_x/stage4_membrane/__init__.py`
- `theory_x/stage4_membrane/self_model.py`
- `theory_x/stage4_membrane/behavioural_self_model.py`
- `theory_x/stage4_membrane/classifier.py`
- `theory_x/stage4_membrane/router.py`
- `gui/server.py`
- `tests/test_self_model.py`
- `tests/test_meta_awareness_wire_characterization.py`
- `tests/test_behavioural_self_model_propagation.py`
- `tests/test_influence_trace_integration.py`
- `mind_map/MIND_MAP.yaml`

### Sentience 5.5 (base `1767acf1fdb321d046261eb3c3059084c85fc0c8`)

- `README.md`
- `Base_Node.py`
- `Self_Model_Node.py`
- `self_awareness_node.py`
- `Meta_Awareness_Node.py`
- `Integration_Node.py`
- `Cognitive_Reasoning_Node.py`
- `Cognitive_Control_Node.py`
- `tests/test_check1_judgement_rationale.py` through `tests/test_check6_doctrine_anti_theatre.py`


## 9. NEX cross-faculty interaction trace: attention, affect, drives and workspace

This second pass follows interactions beyond the self-model pathway. It is intended to test the network model: a faculty's output may alter another faculty's selection, framing or state, but these effects occur through specific edges and gates.

### 9.1 External sense → Stage 2 A–F pipeline → Bonsai focus

Verified source path:

`sense_events row → pipeline.step_A → step_B(_match_branches) → step_C(_magnitude_for) → step_D(membrane aperture) → step_E(valence) → step_F(tree.attend) → Bonsai focus/texture → DynamicState snapshot → Fountain branch selection`

- `pipeline.py` implements the A–F sequence and logs intermediate B/D/E/F events.
- `attention.py` derives branch matches from stream names and payload tokens, computes magnitude and uses direct stream-to-branch mappings.
- `_magnitude_for()` returns zero for every `internal.*` stream. The source comment records why: internal telemetry had been pinning `systems` focus at its ceiling and starving other branches. This is an important *negative edge*: internal telemetry can feed the SelfModel representation, but it is intentionally excluded from Stage-2 attention steering.
- `pipeline.step_F()` calls `tree.attend()` only when magnitude is at least 0.001. Thus the internal-stream zero magnitude does not update Bonsai focus through this path.
- Fountain reads branch focus values for its own branch-selection mechanism; the workspace can also consume the hottest branch as a candidate.

This is a clear example of why connecting every available wire is not correct. The same signal can be useful for self-monitoring but harmful when interpreted as attention-driving cognitive content.

### 9.2 Affect → affect state → Chat representation and optional Fountain selection

Verified source path:
- `run.py` constructs `AffectState`, starts its background loop and passes it into the application state.
- `AffectState._background_tick()` reads substrate-derived valence/arousal and flagged surprise events, integrates/decays values, writes the single-row `affect_state` state and appends `affect_history`.
- `gui/server.py` appends `affect_state.format_for_prompt()` to Chat's context when the faculty is present.
- Fountain's `_valence_reach()` reads valence/arousal and passes the resulting multiplier into `_curiosity_score()` only when `NEX5_VALENCE_DRIVE=1`. The source default is OFF. The multiplier is bounded, and the strongly negative anti-rut zone returns 1.0.
- Fountain's separate compositional mood prompt injection is gated by `NEX5_MOOD=1`.

Interpretation: affect has a Chat representation path, and it has a separate optional mechanical influence on Fountain selection. These should be measured independently. Prompt narration is not proof of selection influence.

### 9.3 Competing drives and DriveEmergence are distinct wires

- `run.py` constructs and starts `CompetingDrives`.
- Fountain reads the persisted curiosity and exploration values to scale candidate scoring; it separately appends the CompetingDrives tension prompt block when available.
- Fountain records the current CompetingDrives weights in its per-fire state snapshot and attaches activation records to the resulting Fountain event where possible.
- Global Workspace's `drive` candidate is supplied from `DriveEmergence.format_for_prompt()`, not from CompetingDrives. The two are distinct mechanisms and must not be treated as one unified drive subsystem.
- The source supports multiple influence types: numeric selection scaling, prompt contribution, event attribution and workspace framing. Their causal efficacy remains a separate measurement question.

### 9.4 Two workspaces arbitrate different objects

**Fountain Global Workspace:** `NEX5_GLOBAL_WORKSPACE` defaults to enabled in the inspected source. It compares available surprise, momentum, Bonsai-attention, stakes and DriveEmergence candidates, then prepends the winning framing line to the focus block. Other faculty blocks are still appended. It chooses the leading frame; it does not remove every non-winning faculty contribution.

**Chat workspace:** `NEX5_CHAT_WORKSPACE` is a separate, opt-in path. It ranks already-assembled faculty blocks against a character budget, preserves exempt blocks and returns selected blocks in original assembly order. It is not the same operation as the Fountain's single-winner framing.

### 9.5 Bounded interaction test added; next seam remains open

A test-only characterization has been added to `tests/test_dynamic.py`:

- The external positive control sends an `ai_research.arxiv` title through the real A–F pipeline and asserts that the matching Bonsai branch's focus and texture increase.
- The internal negative control confirms that `internal.proprioception` matches the `systems` branch at the stream-matching layer, but `_magnitude_for()` returns zero; running the pipeline produces no focus/texture change and no F-step event.
- This test makes the exclusion operationally observable rather than merely asserting that the internal magnitude helper returns zero.

**Validation:** the test is committed on the PR branch. The updated exact-head full-suite CI is pending; no pass is claimed. It is an isolated fixture, not live runtime evidence.

The next separate test should feed a controlled Bonsai snapshot into Fountain's branch-selection seam and Global Workspace arbiter, then compare branch selection and winning frame under a baseline perturbation. Keep affect and competing-drive perturbations separate so effects remain attributable to one edge at a time. Do not use live databases, turn on feature flags, or alter production selection weights.

### 9.6 Evidence and source anchors

NEX main source snapshot: `bbca5deb3a0398331503ce61c95a62f8d1b3d33d`.

- `theory_x/stage2_dynamic/pipeline.py`
- `theory_x/stage2_dynamic/attention.py`
- `theory_x/stage2_dynamic/bonsai.py`
- `tests/test_dynamic.py` (new Stage-2 attention/Bonsai positive-control and internal-telemetry negative-control characterization)
- `theory_x/stage6_fountain/generator.py`
- `theory_x/stage_tom/global_workspace.py`
- `theory_x/stage_affect/affect_state.py`
- `theory_x/stage_drives/competing_drives.py`
- `gui/server.py`
- `run.py`

No runtime wire, flag, threshold, prompt policy, database schema or frozen specification was changed by this research pass.
