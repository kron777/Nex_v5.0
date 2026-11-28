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

## 6. Proposed next bounded development increment

**Do not add another cognitive node yet. Do not change prompts, thresholds, belief weights, feature flags, or action policy.**

Build a test-only causal propagation harness around the already-existing NEX-SM-07 → NEX-SM-10 chain:

1. Create isolated temporary substrate databases.
2. Insert a controlled set of NEX messages whose only difference is one known behavioural feature.
3. Run BehaviouralSelfModel observation and seed comparison.
4. Exercise the actual belief-write path with a controlled CoherenceGate fixture.
5. Confirm whether the resulting belief is selected by the actual INSIDE source filter.
6. Exercise the membrane/router path and capture the assembled prompt.
7. Compare baseline and changed cases, recording each intermediate value and the exact changed prompt segment.
8. Add a counterfactual case in which the behavioural belief is absent, to show whether it actually changes the downstream representation.
9. Keep the test isolated; no live database, feature flag or running NEX process is touched.

This is the first practical experiment that matches the requested “wire” method: inspect the root, observe before connection, follow propagation, then evaluate the whole path. It is a characterization step, not a claim that the behaviour is desirable.

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
