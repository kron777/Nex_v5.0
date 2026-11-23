# NEX Architecture Crosswalk v2 — Working Draft

**Status:** Partial source crosswalk; not a Gate 0 submission  
**Inspected revision:** `6e6712bd4bde15ad2288f220cd4438b11622c93c`  
**Inspection date:** 2026-11-23  
**Scope:** Phase 0 M0.3–M0.4; source-level inspection only unless explicitly stated

> This is a bounded initial crosswalk, not a claim that every `theory_x/` faculty has been traced. The complete forward and backward audit remains open. Runtime evidence is unavailable and must remain UNKNOWN.

## 1. Evidence vocabulary — Master Roadmap v3.0

The Master Roadmap defines the following ladder. These labels are not interchangeable with the Research Framework's separate evidence terminology.

| Level | Roadmap definition |
|---|---|
| [L0] PROPOSED | Concept exists in design documents or hypotheses; no code proof |
| [L1] CONSTRUCTED | Code, schema and unit tests exist; no proof of integrated-loop runtime execution |
| [L2] RUNTIME-ACTIVE | Execution traces prove code runs during live/simulated operation and emits rows, logs or events; no proof of downstream use |
| [L3] OPERATIONALLY CONSUMED | End-to-end ID-linked trace proves a downstream decision gate, context selector or actuator reads and alters its state based on the output |
| [L4] EFFECTIVELY VALIDATED | Controlled A/B or 3-arm ablation against a frozen baseline on held-out tasks demonstrates statistically significant improvement on predeclared metrics without violating safety/grounding guardrails |

The roadmap also defines [L5] GENERALISED. Phase 0 specifically requests [L0]–[L4] labels. This document does not silently collapse [L5] into [L4].

Hard rule: write-only tables, HUD readouts and fluent first-person model explanations are at most [L2], never [L3] or [L4].

## 2. Descriptive map and operational authority

### 2.1 Mind map

Source: `mind_map/MIND_MAP.yaml`, 1,262 lines, 30 declared nodes.

Its `meta.constraint` states:

> Descriptive only. No node in this map may gate, score, block, or veto an action.

It also defines map evidence classes and modifiers, and requires sourced nodes with verification dates.

The CI workflow invokes:

```sh
python mind_map/mind_map.py --check --verify
```

The validator checks map structure, source references, evidence/status metadata and freshness rules. This establishes that the descriptive map is checked as a sourced document in CI. It does **not**, by itself, prove that no runtime module elsewhere has independently implemented a similarly named control or gate.

### 2.2 Dependency DAG

Source: `sentience_dag.json`, 159 lines, 15 nodes.

The DAG describes a development dependency/buildability model. Its own `_rule` states that `live_unproven` and `terminal` prerequisites are treated as satisfied by the development-ordering tool, with warnings rather than blocking.

The inspected `run.py` boot path does not import or read `MIND_MAP.yaml` or `sentience_dag.json`. They are not established as runtime schedulers by this inspection.

### 2.3 Current conclusion

**Source-supported:** the mind map declares itself descriptive, and the inspected boot path does not load either map as an execution controller.

**Not yet proven:** a repository-wide absence of all map-derived gating or veto logic. That requires a complete source search, dynamic-dispatch review and targeted tests against the actual runtime interfaces.

## 3. Forward and backward pathway samples

### 3.1 Fountain path — partially traced

| Stage | Source location | Current source finding | Evidence ceiling |
|---|---|---|---|
| Boot | `run.py:46` | `main()` is the unified boot entry point | Source present |
| Gate construction | `run.py:130–170` | Constructs `CoherenceGate`, resolver and trigger detector | [L1] candidate; tests require exact association |
| Fountain construction | `run.py:600` | Calls `build_fountain(..., coherence_gate=coherence_gate)` | Source present |
| Scheduler loop | `theory_x/stage6_fountain/__init__.py:139+` | `fountain_loop()` runs in a loop using configured interval | Source present |
| Candidate generation | `theory_x/stage6_fountain/generator.py:1596` | `generate()` is the generator entry point | Source present |
| Workspace selection | `theory_x/stage6_fountain/generator.py:3402+` | Under `NEX5_GLOBAL_WORKSPACE`, calls `global_workspace.arbitrate()` and prepends its result to the focus block | Source present; flag/runtime state unknown |
| Gate / crystallization | `theory_x/stage6_fountain/generator.py:2530`; `theory_x/stage6_fountain/crystallizer.py:290+` | Generator calls crystallizer; crystallizer calls `self._gate.check(packet)` when a gate is supplied | Source present |
| Persistence | `theory_x/stage6_fountain/crystallizer.py:350+` onward | Accepted path proceeds to belief/crystallization persistence; exact row-level write trace not captured here | Partial source trace |
| Downstream consumer | Not exhaustively mapped | No end-to-end ID-linked trace captured | UNKNOWN |

Associated test files include `tests/test_fountain.py`, `tests/test_fountain_crystallizer.py`, `tests/test_coherence_gate.py` and related tests. Their existence supports constructed/test coverage at component level; it does not establish an integrated live causal edge.

**Current ladder:** source and component tests support [L1] for the relevant implemented mechanisms. [L2] current runtime evidence is UNKNOWN. [L3] end-to-end consumption is UNKNOWN. [L4] behavioural improvement is not established by this crosswalk.

### 3.2 Chat path — partially traced

| Stage | Source location | Current source finding | Evidence ceiling |
|---|---|---|---|
| HTTP input | `gui/server.py:1173+` | `POST /api/chat` parses and validates the incoming prompt | Source present |
| Session/input persistence | `gui/server.py:1190+` | Uses the conversations Writer for session and user-message inserts | Source present |
| Routing/retrieval | `gui/server.py:1240+` onward | Routes through membrane when available, otherwise calls world-model retrieval | Source present |
| Context assembly | `gui/server.py:202+` | `_assemble_chat_blocks()` concatenates blocks by default; `NEX5_CHAT_WORKSPACE=1` enables a bounded salience-selection path | Source present; flag state unknown |
| Model invocation/output persistence | `gui/server.py::api_chat()` through `state.voice.speak()` or optional `VoiceEngine.query_reply()`; then `_sanitize_reply()`, conversations Writer and `jsonify()` | Source path traced through model/substrate response, sanitization, assistant-message persistence and HTTP response. | [L1] source |
| CoherenceGate | No call found in the inspected route segment | Do not assume the Fountain gate is shared by Chat | Not established in Chat path |

Associated tests include `tests/test_chat_arbiter.py`, `tests/test_chat_blocks_budget.py`, `tests/test_chat_ablation.py` and `tests/test_writer_roundtrip.py`.

The current source has a Chat Workspace mechanism. This contradicts older unqualified documentation that describes Chat as only serial concatenation. Whether the mechanism is enabled in the deployed process remains UNKNOWN.

**Current ladder:** [L1] for the source/tested Chat assembly mechanism; current [L2] runtime activation UNKNOWN; [L3] causal influence on the emitted answer UNKNOWN; [L4] validation must be read from the relevant preregistered experiment and cannot be inferred from source.

### 3.2.1 Chat path — completed source-level terminal trace

The Chat handler's source path is now traced through its terminal response:

1. **Arrival and user persistence:** `POST /api/chat` validates the prompt, creates/reuses a session and writes the user message through the conversations Writer.
2. **Routing and retrieval:** when Membrane and WorldModel are available, `membrane.route()` determines the route and supplies `belief_text`; otherwise the handler calls the WorldModel retriever directly and applies Chat-specific filtering/capping.
3. **Context enrichment:** source contains conditional or state-dependent prompt enrichments from BehaviouralSelfModel, SelfModel, Harmonizer, disturbance state, ProblemMemory, Metacognition, NovelAssociation, SelfNarrative, AffectState, DriveEmergence, SelfMindView, SocialPresence, tools, spectrum beliefs, working memory and tagged-thought retrieval. The active status of each dependency/flag is not established by source alone.
4. **Metacognition distinction:** unlike the Fountain insertion, Chat calls `state.metacognition.tick()` and `format_for_prompt()` without the `NEX5_METACOG_VOICE` gate. A non-empty result is appended to Chat's `belief_text`. This is a source-defined Chat prompt path, not proof that the runtime object emits an event or that the text is behaviourally useful.
5. **Chat Workspace:** `_assemble_chat_blocks()` concatenates all ordered blocks when `NEX5_CHAT_WORKSPACE` is unset or not `1`. Bounded salience selection is conditional on `NEX5_CHAT_WORKSPACE=1`; source comments describe the mechanism as dark/default-off. `NEX5_SELF_PRESENT=1` optionally carries salience across turns.
6. **Response generation:** the optional substrate VoiceEngine path is used only when the request is not a probe/instruction query, VoiceEngine exists and `voice_mode == "use_substrate"`. Otherwise the handler calls `state.voice.speak(VoiceRequest(...))`. Additional repeat/provenance retries are conditional and fail-safe.
7. **Terminal sanitization and output:** the response is sanitized, written as role `nex` through the conversations Writer, then returned in the HTTP JSON response.

**Boundary finding:** the inspected `api_chat()` path does not call the Fountain `CoherenceGate`. Do not assume Chat and Fountain share identical gating or acceptance semantics.

**Evidence ceiling:** the complete source path supports [L1]. Runtime activation of optional branches, actual model calls, successful persistence and the causal contribution of individual context blocks remain [L2] UNKNOWN / [L3] UNKNOWN. No [L4] performance claim follows from this trace.

### 3.3 Evaluation, feedback and the next-thought pathway — bounded source trace

This section extends the initial Fountain sample with a source-level trace of several evaluation signals. It does not claim live activation or behavioural effectiveness. All source references below are from the inspected `main` revision `6e6712bd4bde15ad2288f220cd4438b11622c93c`.

### 3.3.1 Global Workspace and surprise

| Stage | Source evidence | Finding | Evidence ceiling |
|---|---|---|---|
| Prediction verification | `theory_x/stage_prediction/predictive_substrate.py::_verify_one` | When the target window contains no items, it writes `surprise_score=1.0` and `actual_content=None`. | [L1] source |
| Workspace candidate | `theory_x/stage_tom/global_workspace.py::_surprise_candidate` | Reads recent `surprise_events` with score > 0.3. Empty-window rows are excluded only when `NEX5_GW_SURPRISE_NONEMPTY=1`; that guard is default-OFF. | [L1] source |
| Arbitration | `theory_x/stage_tom/global_workspace.py::arbitrate` | Competes surprise with momentum, bonsai, stakes and drive candidates; the winning framing line is returned. | [L1] source |
| Fountain consumption | `theory_x/stage6_fountain/generator.py` around the GLOBAL WORKSPACE block | `NEX5_GLOBAL_WORKSPACE` defaults to enabled in source; a non-empty returned line is prepended to `focus_block`. Actual process environment remains UNKNOWN. | [L1] source; [L2] UNKNOWN |
| Separate belief promotion | `theory_x/life/surprise_loop.py::surprise_tick` | The function requires non-empty `actual_content` and `predicted_content` before promotion. Its runtime boot/scheduling caller was not established in this pass; do not infer that this promotion loop is active. This filter, even if active, does not protect the separate Global Workspace candidate path. | [L1] function present; activation UNKNOWN |

**Causal implication:** an empty prediction window can be assigned the maximum surprise score and can enter Global Workspace arbitration unless the optional non-empty guard is enabled. The source does not establish that such a row exists in the deployed database or wins a live fire. Do not report a live failure without runtime evidence.

### 3.3.2 Emphasis scoring

| Stage | Source evidence | Finding | Evidence ceiling |
|---|---|---|---|
| Construction | `run.py` / `theory_x/stage6_fountain/generator.py` | Fountain attempts to construct `EmphasisEngine`; construction failure is non-fatal. | [L1] |
| Scoring | `generator.py` after thought generation; `stage_emphasis/emphasis_engine.py::score` | Scores goal relevance, self relevance and novelty-proxy surprise. Drive resonance is still calculated and recorded but excluded from the combined score and dominant-signal choice. | [L1] |
| Novelty proxy | `stage_emphasis/prediction_tracker.py::expectation_error` | Measures the fraction of capitalised entities in the current thought absent from the union of entities in the previous 20 Fountain thoughts. This is a vocabulary/entity novelty proxy, not a prediction-outcome accuracy measure. | [L1] |
| Persistence | `generator.py` inserts the result into `emphasis_log` linked to `fountain_event_id`. | A post-thought record is written. The engine's own source describes this as log-only pending evidence that the measure tracks something real. | [L1] |
| Subsequent consumption | Bounded source search of the inspected revision | No downstream decision or prompt consumer was identified in this pass. Treat downstream use as UNKNOWN, not proof that no consumer exists anywhere. | [L3] UNKNOWN |

The engine source records that drive resonance was dropped from the combiner after a ground-truth test reported p=0.190 and effect −0.013. Its other three combined signals are explicitly described as unvalidated in the source comments. Do not treat the combined score as a validated importance or quality measure.

### 3.3.3 Metacognitive observations

| Stage | Source evidence | Finding | Evidence ceiling |
|---|---|---|---|
| Construction/registration | `run.py` section 9c | Constructs `Metacognition` with conversation Writer/Reader and beliefs Reader, then attempts registration in the Theory-X registry. | [L1] |
| Event persistence | `stage9_metacognition/metacognition.py::_write_event` | Writes self-observation events to `meta_cognition_events`; cache is invalidated after a successful write. | [L1] |
| Retrieval/formatting | `get_recent()`, `format_for_prompt()` | Reads unresolved events and converts selected event types into short prompt text. | [L1] |
| Fountain injection | `generator.py` around the metacognition block | The prompt insertion is explicitly gated by `NEX5_METACOG_VOICE=1`; a non-empty formatted line is appended to the next fire's focus block. | [L1] source; [L2] UNKNOWN |

This is a real source-defined producer-to-prompt path, but not evidence that the flag is enabled on the host, that events are being produced, or that the injected text improves subsequent cognition.

### 3.3.4 Arc records: read attempt without usable prompt output

The Fountain calls `_fetch_arc_context()` and then `_format_arc_context()` before assembling `prompt_parts`. The fetch queries active arcs from the last two hours and recently closed arcs from the last four hours. However, the formatter's current implementation documents that both prompt-injection blocks were removed and, when records exist, falls through an empty `lines` list and returns an empty string. Consequently `arc_block` does not provide usable prompt context.

Separately, `run.py` sets `arc_loop = None`; its comment says the background ArcLoop was removed and was the only writer of the arc tables. The source therefore shows a residual read attempt but no current producer loop and no effective prompt consumer. Runtime database contents remain UNKNOWN.

### 3.3.5 Feedback-path summary

| Signal/mechanism | Writes or computes | Reaches a later thought in source? | Current classification |
|---|---|---|---|
| Global Workspace winner | Salience candidates and winner | Yes, conditional on non-empty winner and workspace flag | [L1]; runtime [L2] UNKNOWN |
| Empty-window surprise | Maximum score with NULL actual content | Can enter workspace unless non-empty guard enabled | [L1]; live occurrence UNKNOWN |
| Emphasis | Post-thought score and `emphasis_log` row | No consumer identified in this bounded pass | [L1]; [L3] UNKNOWN |
| Metacognition | Unresolved self-observation events | Yes, but `NEX5_METACOG_VOICE=1` required | [L1]; runtime [L2] UNKNOWN |
| Arcs | Fountain query of arc tables | No usable formatted prompt content; ArcLoop disabled in boot | Source path is a no-op |

**Interpretation:** the repository does not have one uniform “feedback missing” condition. It contains a mixture of (a) active-by-default source paths whose runtime state is unknown, (b) optional prompt feedback, (c) post-hoc measurement with no identified downstream consumer, and (d) residual readers whose output is currently empty. This supports keeping the missing-discrimination hypothesis open rather than declaring one root cause.

## 3.4 Sense scheduler — source-defined startup and stale documentation

| Stage | Source evidence | Finding | Evidence ceiling |
|---|---|---|---|
| Construction | `run.py` calls `build_scheduler()` during startup. | Scheduler is part of the normal boot path. | [L1] |
| Adapter set | `theory_x/stage1_sense/__init__.py::build_scheduler` | Constructs 28 adapters: four internal sensors and 24 external/diversification/research feeds. The function's docstring and comments say external feeds start paused. | [L1] |
| Thread startup | `theory_x/stage1_sense/scheduler.py::SenseScheduler.__init__` | Creates adapter threads and then unconditionally calls `self.start_all()`. External adapters are enabled and the global run event is set. | [L1] |
| Poll/emit | `scheduler.py::_AdapterThread._run` | External adapters poll only when both the global run event and local adapter event are set; `start_all()` sets both. Successful polls call `adapter.submit(events)`. | [L1] |
| Boot log | `run.py` | Logs “external feeds auto-start” and “23 adapters wired”, while the builder constructs 28. | [L1] |

**Reconciliation:** the top-level `run.py` module docstring and builder comments describe feeds as paused, but the implementation unconditionally starts them. The scheduler itself contains a dated comment stating that automatic startup was restored on 2026-05-09 at the founder's request. Therefore this is not evidence of an accidental runtime activation bug; it is a documentation/count discrepancy. Actual deployed activation remains UNKNOWN until host evidence is collected.

The 23-versus-28 count discrepancy is source-visible: the builder instantiates 28 adapters; the startup log says 23. Confirm whether the count is an intentional legacy log string or a change in intended adapter inventory before changing it.

## 3.5 Boot and autonomous-loop inventory — source-only

This is a boot-path inventory, not a claim that the deployed host currently runs these paths. It records the startup mechanism visible in `run.py` and the relevant constructors.

| Faculty / service | Boot wiring | Activation condition visible in source | Current source classification |
|---|---|---|---|
| SenseScheduler / Stage 1 | `build_scheduler()`; constructor creates adapter threads and calls `start_all()` | Unconditional; internal and external adapter threads start | [L1] |
| Dynamic / Stage 2 | `build_dynamic()` | Constructed during normal boot | [L1] |
| WorldModel / Stage 3 | `build_world_model()` | Constructed during normal boot | [L1] |
| Membrane / Stage 4 | `build_membrane()` | Constructed during normal boot | [L1] |
| CoherenceGate / HoldingZone / TriggerDetector | Constructed in `run.py`; gate passed into Dynamic, WorldModel and Fountain | Unconditional construction; actual call paths differ by entry point | [L1] |
| SelfNarrative / GoalManager / Metacognition | Constructed and registered where registry call succeeds | Unconditional construction; Chat and Fountain consumers have different gating | [L1] |
| NovelAssociation | Constructed in guarded try block | Unconditional attempt; non-fatal on failure | [L1] |
| ThrowNetMonitor | Engine and monitor constructed | `start_loop()` only when `NEX5_THROWNET=1`; otherwise explicitly not started | [L1], default source path off |
| SubstrateHarmonic / GeniusTagger / CounterfactualNode | Constructed in guarded boot blocks | Construction attempted; do not infer autonomous execution solely from construction | [L1] |
| DriveEmergence / CompetingDrives / VoiceEngine | Constructed during normal boot | Passed into Fountain/Chat consumers; loop/consumer details require faculty-level trace | [L1] |
| WarrantRecorder | Constructed in guarded block | Only when `NEX5_WARRANT_RECORD=1` | [L1], default source path off |
| AffectState | Constructed; its constructor starts a 300-second daemon tick | Unconditional construction if import/init succeeds | [L1] |
| PredictiveSubstrate | Constructed; its constructor starts its 300-second loop | Unconditional construction if import/init succeeds | [L1] |
| PersonaResponder | Constructed and its loop started | Only when `NEX5_PERSONA_RESPONDER=1` | [L1], default source path off |
| SelfMindView | Constructed and supplied to AppState / Metacognition | Unconditional construction attempt | [L1] |
| WorldPredictionLoop | `start_loop()` called | Only when `NEX5_WORLD_PRED=1` | [L1], default source path off |
| SelfPredictionLoop | `start_loop()` called | Only when `NEX5_SELF_PRED=1` | [L1], default source path off |
| SelfMaintainShadow | `start_loop()` called | Only when `NEX5_SELF_MAINTAIN_SHADOW=1` | [L1], default source path off |
| SocialPresence | Explicitly assigned `None`; explanatory cut comment | Not booted in current `run.py` path | Source-disabled |
| Fountain | `build_fountain()` starts its daemon loop internally | Unconditional build attempt | [L1] |
| SpeechQueueConsumer | Constructed and `.start()` called | Only when parsed `SpeechConfig.enabled` | [L1], config-dependent |
| SignalLoop | `build_signal_loop()` called | No explicit `.start()` at this call site; constructor/factory activation requires separate inspection | [L1] constructed; running UNKNOWN |
| DiversityLoop | `build_diversity_loop()`, then `.start()` | Unconditional | [L1] |
| ArcLoop | Explicitly set to `None` | Not started | Source-disabled |
| EdgeGeneratorLoop | `build_edge_generator_loop()`, then `.start()` | Unconditional | [L1] |
| DecoderLoop | Daemon thread started after AppState construction | Unconditional attempt; failure is non-fatal | [L1] |

**Important limit:** this table establishes only the boot construction/start mechanisms and explicit flag conditions visible in source. It does not establish host environment values, successful initialization, actual emitted events, downstream use or behavioural effect. The remaining M0.3–M0.4 work is to trace each faculty's own emission and terminal consumer, then link those paths to the backward audit from Chat output, Fountain action and belief writes.

## 3.6 Writer substrate

Source: `substrate/writer.py`

The Writer describes one database, one write connection and one worker thread. Its public synchronous methods include `write()` and `write_many()`. `run.py` constructs writers for the configured database paths.

This supports the intended single-writer abstraction at the inspected source boundary. It does not establish that every write in the repository uses this interface or that no direct-write exception exists. A repository-wide write-path audit remains required.

## 4. Top documentation/source discrepancies

These are discrepancies to reconcile, not automatic instructions to modify code or documentation.

1. **Architecture status and test count conflict.** The opening of `ARCHITECTURE.md` says “Phase 9 complete” and “189 tests passing”, while later text in the same header records 1,987 tests as of the 2026-11-07/08 session. The status is not a reliable current Phase 0 baseline.
2. **R77 status is stale in the architecture narrative.** `ARCHITECTURE.md` describes `NEX5_CHAT_WORKSPACE` as armed and mid-measurement as of 2026-11-07. `observation_reports/r77.md` records a Branch C disarm on 2026-11-20 after a tripwire breach, with the variable removed from `nex_keepalive.sh`. The observation report is later and records the closeout; live host state still requires verification.
3. **Chat arbitration documentation lags source.** `SENTIENCE_PROGRAM.md` describes Chat as concatenating approximately 16 blocks without arbitration. Current `gui/server.py` contains `_assemble_chat_blocks()` and a conditional `NEX5_CHAT_WORKSPACE` salience/budget selection path. This establishes code presence, not current activation.
4. **Mind-map CI validation is not a global runtime proof.** CI validates the map's schema, references and verification metadata. The YAML's descriptive-only constraint is explicit, but the validator alone does not statically prove that no other runtime code gates actions using related concepts.
5. **The DAG's “build order” is not the runtime boot order.** The DAG describes development prerequisites and is not imported by the inspected `run.py`. Its own rule treats `live_unproven` and `terminal` as satisfied prerequisites while flagging them. Reports must not describe this as an execution gate without further evidence.

## 5. M0.3–M0.4 work still required

- Complete forward audit for every relevant faculty under `theory_x/`: declaration → boot → scheduler → emission → consumer.
- Complete backward audit from Chat output, Fountain action and belief writes to upstream producers.
- Identify direct calls, events, shared-state reads, DB read-after-write, optional enrichments and inferred relationships separately.
- Map exact schemas, feature flags, failure fallbacks and persistence for every edge.
- Review all source/test call sites and dynamically selected imports.
- Inspect actual deployed runtime wiring and capture trace IDs when host access and approvals permit.
- Reconcile every relevant claim against the exact Frozen V2.1 specification and founder approval record when supplied.

## 6. Open cognitive research question

The Z.ai “missing discrimination” hypothesis is retained as an open research question. This crosswalk does not classify it as a defect.

Competing explanations remain live:

- evaluation capability absent;
- evaluation exists but is not consumed;
- evaluation is poorly calibrated;
- evaluation and subsequent cognition operate on mismatched timescales;
- architecture is fragmented across pathways;
- measurement/instrumentation is insufficient.

Causal tracing should help distinguish these possibilities; it does not predetermine the answer.

## 7. Gate status

This draft is not a complete crosswalk and does not satisfy Gate 0. It records a bounded, revision-specific source map and identifies the remaining work. No Phase 1 behavioural work is authorised by this document.
