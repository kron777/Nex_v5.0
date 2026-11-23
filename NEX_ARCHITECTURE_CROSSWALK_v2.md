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

The validator checks map structure, source references, evidence/status metadata and freshness rules. It does not inspect the content or enforce the semantics of meta.constraint, scan runtime consumers of MIND_MAP.yaml, or test whether map labels can influence an action. The workflow therefore validates the map as a sourced document; it does **not** enforce the operational invariant that descriptive nodes cannot gate, score, block or veto actions. The inspected run.py does not load MIND_MAP.yaml or sentience_dag.json. A new draft Phase 0 test, tests/test_mind_map_authority_boundary.py, asserts the YAML's descriptive-only declaration and statically scans run.py plus gui/, speech/, substrate/ and theory_x/ for direct imports of mind_map or executable literal references to the two map files. The first PR #49 run (45243207500) failed; focused reproduction showed the string scan also matched two module docstrings, which describe the filenames but do not read them. The guard has now been narrowed to exclude module/class/function docstrings while retaining executable string-constant and direct-import checks. The full failed-run log was unavailable, so other failures, if any, remain unknown. The corrected PR #49 head `bbbd86bce7d24e2583aa1c882910915fc1914448` passed the full pytest workflow and the `Mind map stays sourced (no stale status claims)` step in run `45249262986`. The current PR #49 head `6f8d6185e6711bf3149ce315dc1bdb3dd103532a` passed the full pytest workflow and the `Mind map stays sourced (no stale status claims)` step in run `45250303734`. The earlier run `45250038331` covered the preceding code/test head `ab99ccd6d94b94bca4fa75293aec3d7b42bd41c2` and was superseded by the later push. This guard catches only the bounded static patterns it scans; it does not prove the absence of arbitrary dynamically constructed paths or every indirect control relationship.

### 2.2 Dependency DAG

Source: `sentience_dag.json`, 159 lines, 15 nodes.

The DAG describes a development dependency/buildability model. Its own `_rule` states that `live_unproven` and `terminal` prerequisites are treated as satisfied by the development-ordering tool, with warnings rather than blocking.

The inspected `run.py` boot path does not import or read `MIND_MAP.yaml` or `sentience_dag.json`. They are not established as runtime schedulers by this inspection.

### 2.3 Current conclusion

**Source-supported:** the mind map declares itself descriptive, and the inspected boot path does not load either map as an execution controller.

**Not yet proven:** a repository-wide absence of all map-derived gating or veto logic. That requires a complete source search, dynamic-dispatch review and targeted tests against the actual runtime interfaces.

## 3. Forward and backward pathway samples

### 3.1 Fountain path — source-traced to persistence and optional speech output

| Stage | Source location | Current source finding | Evidence ceiling |
|---|---|---|---|
| Boot | `run.py::main` | Constructs substrate, scheduler, gate and faculty dependencies; builds Fountain with the CoherenceGate. | [L1] |
| Scheduler | `theory_x/stage6_fountain/__init__.py::build_fountain` | Starts a daemon `fountain_loop`; loop waits for configured/mode interval, checks mode/readiness and calls `generator.generate()`. | [L1] |
| Candidate generation | `generator.py::FountainGenerator.generate` | Scores readiness, builds the prompt, invokes the configured voice path and returns a thought when one is produced. | [L1] |
| Salience/workspace | `generator.py` GLOBAL WORKSPACE block; `stage_tom/global_workspace.py::arbitrate` | Unless `NEX5_GLOBAL_WORKSPACE=0`, surveys candidates and prepends a non-empty winner to the focus block. Source default is enabled; host value UNKNOWN. | [L1]; [L2] UNKNOWN |
| Fire identity and event | `generator.py` at the `fountain_events` insert | Inserts the completed thought and retains the Writer-returned `fountain_event_id`. | [L1] |
| Post-thought scoring | `generator.py` / `stage_emphasis/emphasis_engine.py` | Scores the completed thought and writes an `emphasis_log` row keyed to the fire ID. This is post-hoc logging; no downstream consumer was identified in the bounded search. | [L1]; [L3] UNKNOWN |
| Crystallization quality gate | `generator.py` calls `FountainCrystallizer.crystallize()`; `crystallizer.py::_quality_check` | Quality/repeat checks run before the CoherenceGate. A quality rejection returns before the CoherenceGate is called. | [L1] |
| CoherenceGate | `crystallizer.py::crystallize` → `CoherenceGate.check()` | If a gate is supplied and quality passes, constructs a `ThoughtPacket(source_node="fountain")`; only ACCEPT proceeds to belief persistence. REJECT/HOLD/RESHAPE return without the belief insert. | [L1] |
| Belief persistence | `crystallizer.py::crystallize` | Inserts Tier-6 belief, then a `fountain_crystallizations` link keyed by `fountain_event_id` and `belief_id`. Confidence can be modified by `NEX5_SURPRISE_WEIGHT` (source default enabled), with fail-safe baseline 0.70. | [L1] |
| Speech decision | `crystallizer.py::crystallize` | For configured speakable belief categories and enabled SpeechConfig, consults SpeechGovernor; only SPEAK enqueues a `speech_queue` row. | [L1] |
| Speech output | `run.py` SpeechQueueConsumer startup; `speech/queue_consumer.py` | Consumer starts only when SpeechConfig is enabled; polls pending rows, synthesizes and plays audio, then updates status to spoken/failed/suppressed. | [L1]; host/config [L2] UNKNOWN |

**Important boundary:** the Fountain's CoherenceGate applies to crystallization, not to every generated thought. The event row and post-thought measurements can exist even when crystallization is rejected or not reached. Speech is a later, separately configured consumer of eligible crystallized beliefs.

Associated tests include `tests/test_fountain.py`, `tests/test_fountain_crystallizer.py`, `tests/test_coherence_gate.py`, speech queue/governor tests and related tests. These support component-level constructed/test behaviour, not a complete live causal trace.

**Current ladder:** relevant mechanisms are [L1] source-present and individually tested. Current [L2] host activation and event emission remain UNKNOWN. The source links the event, accepted belief and optional speech queue, but a live ID-linked [L3] trace has not been captured. [L4] behavioural improvement is not established.

### 3.1.1 Asynchronous speech consumer — row-identity hand-off (draft PR #65)

The speech path crosses an asynchronous boundary: Fountain commits a speech_queue row, while SpeechQueueConsumer polls the table independently. The current trace hand-off uses the exact persisted row identity:

1. FountainCrystallizer.crystallize() calls Writer.write() to insert the queue row and receives its ID.
2. After the write returns, it records output_queued with entity_ref="beliefs.speech_queue:<id>".
3. If that trace append returns a record ID, it registers the same entity reference through link_entity().
4. The consumer's _pending() query returns the row; _speak_one() opens begin_linked_trace() using that row ID. When the in-memory mapping exists, the consumer trace_start.parent_ids names the exact output_queued record.

PR #65 adds an isolated integration fixture that calls the real FountainCrystallizer.crystallize() method, uses real SQLite Writer/Reader instances, selects the actual pending row with _pending(), and processes it through _speak_one() with a deterministic backend and fake player. It asserts the consumer trace root's parent is the output_queued record for the exact queue-row ID and that the persisted queue status becomes spoken.

**Bounded evidence classification:** [L2] simulated/isolated execution is test-covered for this producer-to-consumer path. In the linked fixture, [L3] is demonstrated within the fixture: the consumer reads the exact persisted entity, processing invokes the test player and changes that row's status. In the controlled race fixture, the consumer trace is explicitly unlinked; that is honest evidence of a provenance gap, not a complete enqueue-to-consumer causal trace. Host activation and real audio output remain UNKNOWN; [L4] behavioural benefit is not established. The combined PR #65 head 2b246bbd045f2f243cc0209ab6389159361b73a8 passed the full pytest workflow (run 45243112976). Its earlier full-suite run had 2,192 passes, 7 skips and 40 passing subtests, with one failure caused by an unfrozen wall-clock spoken_at parameter in the paired test; the fixture clock was corrected before the passing rerun.

**Known race — missing parent is preserved, not repaired:** the database insert commits before Fountain records output_queued and calls link_entity(). A consumer can select the row during this interval. PR #65 includes a controlled interleaving using the production Writer.write() and _pending() methods; when the consumer reaches the row before registration, its trace starts unlinked. The in-memory registry cannot make the SQLite commit and registration atomic. No new lock, queue schema field, durable hand-off or JSONL recovery was added: those would exceed the current observer-only scope and could alter scheduling. Restart, registry eviction and the commit/register window therefore remain explicit false-negative provenance cases, not grounds to invent a parent.

**Event semantics:** the consumer records processing start, not an exclusive reservation. `synthesis_started` and `player_invocation_started` are pre-call attempt markers; by themselves they do not prove the call was entered, because a crash can occur between the trace append and the call. Completion/return or failure events provide stronger evidence of the call outcome. Synthesis completion proves the backend returned an audio/sample-rate pair, not that the waveform was valid or heard. `Player.play()` returning does not prove physical sound was audible. `queue_status_persisted` means the synchronous Writer call returned after its transaction completed; it is not a read-back verification that the intended row currently contains that status. Queue-status persistence is recorded separately from synthesis/player outcomes, including the existing fallback write after a failed spoken update.

**Conditional source defect:** Reader.read() returns sqlite3.Row, while the existing consumer fallback calls row.get("voice") if voice_state.current_name() returns empty or raises. Normal run.py startup supplies voice_state; therefore this is a conditional fallback defect, not evidence that the normal boot path fails. PR #65 tests and documents the mismatch but deliberately does not alter runtime behaviour.

This fixture does not combine the full daemon fountain_loop with asynchronous playback. PR #64 separately executes one synchronous production loop cycle. Neither PR captures the deployed host or establishes physical audio audibility.

**Completeness boundary:** an explicitly unlinked consumer trace is acceptable evidence that the observer did not fabricate a parent when the hand-off was unavailable. It must not be described as a complete end-to-end Fountain trace. Whether the Phase 0 deliverable requires every relevant consumer execution to have a causal parent, or permits a documented partial trace with this gap, is an acceptance decision not settled by the source or tests.

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


### 3.2.2 Explicit Chat causal edges — isolated route fixture (PR #62, carried in combined PR #65)

The explicit-parent stack records a Chat turn root and links the tested route's actual source dependencies rather than treating chronological adjacency as causation. PR #62 instruments the tested normal model-composition path and gap-refusal branch with explicit parent IDs; its paired fixture uses the real Flask route and isolated SQLite databases with a deterministic model stub.

The test checks trace integrity and OFF/ON equivalence for the exercised route: model request/response, persisted database state and Reader query sequence. This establishes a bounded simulated pathway and observer comparison, not host activation, all Chat branches, tool routes, retries, VoiceEngine short-circuits or behavioural benefit.

**Bounded evidence classification:** [L2] simulated trace emission is test-covered. Explicit [L3] edges are test-verified only for the represented Chat route dependencies; the influence of every context block and untested branch remains UNKNOWN. [L4] is not established. PR #65 now carries this Chat implementation alongside the Fountain and speech trace work so the combined stack can be tested together.

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
| Construction/registration | `run.py` section 9c | Constructs `Metacognition` with conversation Writer/Reader and beliefs Reader, then attempts registration in the Theory-X registry. No Metacognition background loop is started by `run.py`. | [L1] |
| Chat event production | `gui/server.py::api_chat` → `state.metacognition.tick()` | Chat calls `tick()` on each request. Detected events are written to `meta_cognition_events`; this is request-driven, not an autonomous continuous daemon. | [L1] |
| Same-turn retrieval | `tick()` → `_refresh_recent_cache()` → `get_recent()` | After event writes invalidate the cache, the same tick refreshes it by reading unresolved rows from `meta_cognition_events`. | [L1] |
| Chat injection | `api_chat` → `format_for_prompt()` | Chat appends a non-empty self-observation line to `belief_text` without checking `NEX5_METACOG_VOICE`. This is a same-turn producer→read→prompt path. | [L1] source; runtime [L2] UNKNOWN |
| Fountain injection | `generator.py` around the metacognition block | Separate Fountain insertion is gated by `NEX5_METACOG_VOICE=1`; a non-empty line is appended to the next fire's focus block. | [L1] source; runtime [L2] UNKNOWN |
| Other readers | `_maybe_engage_stillness()`, optional digest, `decay()` | Stillness counts recent groove rows; digest reads event-type counts only when its flag is armed; decay resolves stale rows when called. | [L1] |

**Correction to the supplied feedback map:** `meta_cognition_events` is not read only by the reaper and tests. The Chat request path reads it through `get_recent()` and can inject the selected event into that same turn. The table is not “written continuously” by a Metacognition daemon in the inspected boot path; writes are driven by Chat `tick()` calls and any explicit other callers. This is a real source-defined feedback edge, but host event production and behavioural benefit remain unverified.

### 3.3.4 Arc records: read attempt without usable prompt output

The Fountain calls `_fetch_arc_context()` and then `_format_arc_context()` before assembling `prompt_parts`. The fetch queries active arcs from the last two hours and recently closed arcs from the last four hours. However, the formatter's current implementation documents that both prompt-injection blocks were removed and, when records exist, falls through an empty `lines` list and returns an empty string. Consequently `arc_block` does not provide usable prompt context.

Separately, `run.py` sets `arc_loop = None`; its comment says the background ArcLoop was removed and was the only writer of the arc tables. The source therefore shows a residual read attempt but no current producer loop and no effective prompt consumer. Runtime database contents remain UNKNOWN.

### 3.3.5 Feedback-path summary

| Signal/mechanism | Writes or computes | Reaches a later thought in source? | Current classification |
|---|---|---|---|
| Global Workspace winner | Salience candidates and winner | Yes, conditional on non-empty winner and workspace flag | [L1]; runtime [L2] UNKNOWN |
| Empty-window surprise | Maximum score with NULL actual content | Can enter workspace unless non-empty guard enabled | [L1]; live occurrence UNKNOWN |
| Emphasis | Post-thought score and `emphasis_log` row | No consumer identified in this bounded pass | [L1]; [L3] UNKNOWN |
| Metacognition | Chat `tick()` writes/reads unresolved self-observation events and injects into same-turn Chat prompt; separate Fountain insertion is gated by `NEX5_METACOG_VOICE=1` | Yes in Chat source without that flag; conditional in Fountain | [L1]; runtime [L2] UNKNOWN |
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
| AffectState | Constructed in `run.py`, then `start_loop()` is called explicitly | Unconditional start attempt if import/init succeeds | [L1] |
| PredictiveSubstrate | Constructed in `run.py`, then `start_loop()` is called explicitly | Unconditional start attempt if import/init succeeds | [L1] |
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

## 3.7 M0.5 trace identity — existing anchors and missing links

The source inspection found useful existing identities, but no existing end-to-end `trace_id` / `parent_ids` propagation.

| Path | Existing identity | What it anchors | Missing for M0.5 |
|---|---|---|---|
| Fountain | `fountain_event_id`, returned by `substrate.Writer.write()` when `fountain_events` is inserted | A completed thought/fire and several downstream rows such as emphasis, retrieval manifests, context blocks and crystallization links | It is created after candidate generation and workspace selection. No top-level trace ID or parent chain is carried through the earlier stages. |
| Chat | `session_id` plus Writer-returned message row IDs | Conversation/session and individual persisted messages | `session_id` spans multiple turns; the user-message and assistant-message write return values are not retained as a per-turn causal chain. No turn-level trace ID or parent chain was found. |
| Writer | Synchronous `write()` returns `cursor.lastrowid`; `write_many()` returns row IDs | Actual persistence identity for a successful write | No generic trace metadata is attached to a write request. The trace must observe actual returned IDs without changing SQL, parameters or write order. |

A bounded source search of the inspected Fountain generator, crystallizer, Chat handler and Writer found no existing `trace_id`, `parent_ids` or general request-correlation mechanism. This is a source-search result, not a claim about every third-party or host logging layer.

**Design consequence for M0.5:** reuse `fountain_event_id`, `session_id` and Writer-returned row IDs as entity anchors; add a separate top-level trace identity only where necessary; and record parent relationships only when the call/data dependency is explicit. Do not fabricate a parent edge from temporal proximity. Trace artifacts must remain outside the cognitive databases and must not alter prompts, candidate order, gate decisions, Writer SQL/parameters or outputs.

## 3.8 P0 diagnostic-log privacy inventory — source verified

The source contains several ad-hoc diagnostic files under `/tmp` that record raw cognitive or conversational content:

| Path | Writer | Content and write mode | Source finding |
|---|---|---|---|
| `/tmp/nex5_last_chat_prompt.log` | `gui/server.py::api_chat` | Overwrites with timestamp/register, raw user prompt and full voice prompt sent to the LLM | Raw private conversation/context content; no explicit file mode or retention |
| `/tmp/nex5_deflection.log` | `gui/server.py::api_chat` | Appends JSON containing session ID, query excerpt, user mirror, raw LLM output and final response | Raw conversation and model output; unbounded append; no explicit file mode or retention |
| `/tmp/nex5_last_prompt.log` | `FountainGenerator.generate` | Overwrites with the complete assembled Fountain prompt | May include retrieved beliefs and internal context; no explicit file mode or retention |
| `/tmp/nex5_retrieval_history.log` | Fountain retrieval path | Appends retrieved belief source and up to 120 characters of content per result | Persistent content-bearing retrieval history; no explicit rotation/retention |
| `/tmp/nex5_executive_control.log` | Chat route | Appends the first 200 characters of the user query with register metadata | Raw query excerpt |
| `/tmp/nex5_behavioural_self_model.log` | Chat route | Appends up to 120 characters of the injected behavioural-self-model text | Raw self-model prompt content |
| `/tmp/nex5_problem_memory.log` | Chat route | Appends the first 200 characters of the user prompt with problem-match metadata | Raw query excerpt |
| `/tmp/nex5_goal_manager.log` | Chat route | Appends goal title and first 200 characters of user prompt | User query and goal content |
| `/tmp/nex5_metacognition.log` | Chat route | Appends metacognition text and first 200 characters of user prompt | Raw self-observation and query content |
| `/tmp/nex5_novel_association.log` | Chat route | Appends novel-association text | Raw cross-branch association content |
| `/tmp/nex5_focal.log` | Chat FocalSet path | Appends query excerpt and selected focal belief contents | Raw query and belief content |
| `/tmp/nex5_working_memory.log` | Chat Working Memory path | Appends query excerpt and active working-memory belief contents | Raw query and belief content |
| `/tmp/nex5_self_model.log` | Chat route | Appends counts and text length only | Metadata-only in inspected write |
| `/tmp/nex5_harmonizer.log` | Chat route | Appends active-paradox/injected booleans and text length | Metadata-only in inspected write |

The source does not specify restrictive permissions at creation; actual host file modes and umask are UNKNOWN. The files are not a causal trace: they have no trace IDs or parent links, and the overwrite/append patterns do not establish complete cycle history. The bounded search of the repository's `scripts/` Python tools did not identify consumers of these four exact paths; this is not proof that no external host script consumes them.

**Risk classification:** source-confirmed raw-content logging; actual exposure depends on host permissions, filesystem state and access. Do not claim a confirmed disclosure without inspecting the host. The correct remediation should preserve only necessary diagnostics (for example, lengths, bounded IDs and hashes), or use an explicitly approved restricted diagnostic path. Do not silently delete files or alter live logging until consumers and retention requirements are checked.

## 3.9 M0.5 trace overlay implementation status

Draft PR #54 now contains a source/test prototype for the two required end-to-end paths:

- Fountain cycle/input, candidate generation, Global Workspace selection, fire persistence, quality decision, CoherenceGate outcome, belief/crystallization Writer IDs and speech-queue enqueue.
- Chat input, user-message persistence, retrieval, context assembly, VoiceEngine/VoiceClient input/output, gap-gate pass/deflect, assistant-message persistence and response completion.
- Existing `fountain_event_id`, belief IDs, `session_id` and Writer-returned message IDs are reused as entity anchors.
- The collector is default-OFF and requires an explicit external JSONL path. It hashes payloads rather than writing raw content, rejects the configured/default NEX data directory, and swallows trace-write failures.
- The full repository CI suite, including the mind-map freshness check, passed on PR #54 head `a76709ad10cd9932cd2feb60e913f7de02303b8f`.

**Not yet established:** no host flag has been enabled; no live Fountain cycle or Chat turn has been captured; no deterministic ON/OFF comparison has demonstrated exact prompt/selection/gate/Writer/output invariance; the later TTS playback is not correlated across the consumer thread. PR #54 remains draft and unmerged. This is not Gate 0 approval and does not authorise live activation.

## 3.10 P0 runtime/WSGI, connection and path hygiene — source findings

| Area | Source evidence | Finding | Evidence ceiling |
|---|---|---|---|
| HTTP server | `run.py::main` and `gui/server.py::main` | Both entrypoints start Flask with `app.run(..., debug=False, use_reloader=False)`. No production WSGI server is wired in these entrypoints. | [L1] |
| Entry-point configuration | `run.py` reads `NEX5_HOST/NEX5_PORT`; `gui/server.py` reads `NEX5_GUI_HOST/NEX5_GUI_PORT` | Two boot entrypoints expose different host/port variable names. Both default to loopback and port 8765. | [L1] |
| Process/loop ownership | `run.py` starts background schedulers, Fountain and other loops before serving Flask | A blind multi-worker WSGI replacement could duplicate autonomous loops and split in-process state. Production WSGI choice requires explicit single-owner/thread/process design; do not substitute Gunicorn multiprocess by default. | [L1] |
| Writer connection | `substrate/writer.py::Writer` | One Writer per database, one worker thread and one long-lived write connection; queue serialises writes. This is the intended one-pen architecture. | [L1] |
| Reader connection | `substrate/reader.py::Reader` | Each `read/read_one` opens a fresh read-only connection and closes it via a context manager. Callers can explicitly reuse `Reader.connection()` across multiple queries. | [L1] |
| SQLite factory | `substrate/db.py::connect` | Centralises WAL, busy timeout, foreign keys and optional schema tripwire. | [L1] |
| Database paths | `substrate/paths.py::db_paths` | Six database paths resolve from `NEX5_DATA_DIR` at use time. | [L1] |
| Other diagnostic paths | Chat/Fountain diagnostic logs in §3.8 | Multiple content-bearing logs remain hardcoded under `/tmp`; their consumers, host modes and retention need separate reconciliation. | [L1]; host [L2] UNKNOWN |

**Reconciliation:** the current Writer/Reader connection design is not itself a one-open defect: it intentionally uses one long-lived writer connection and short-lived read-only connections. The outstanding hygiene questions are direct SQLite access outside the substrate, the two entrypoint/configuration differences, production WSGI deployment and raw-content diagnostic paths. These require separate source/consumer and runtime evidence before code changes.

## 3.11 A1 finitude / cost ledger — shadow-to-live gap and invariants

| Layer | Source evidence | Verified status |
|---|---|---|
| Live Chat budget | `gui/server.py::_assemble_chat_blocks` reads `NEX5_CHAT_WORKSPACE_BUDGET` (default 1400) and passes that fixed integer to `select_within_budget()` when `NEX5_CHAT_WORKSPACE=1`. | [L1] live source path; actual flag value [L2] UNKNOWN |
| Shadow Balance | `theory_x/stage_finitude/budget_shadow.py::Budget` | [L1] implementation; module explicitly says NOT IN LIVE PATH |
| Spend ledger | `Budget.spend()` inserts into `shadow_budget_spend` and decrements in-memory `_spent` only after successful write. | [L1] source; no live consumer identified |
| Ledger primitives | `theory_x/stage3_world_model/ledger_primitives.py::refuse/consolidate/recall` | [L1] implementation; module explicitly says NOT IN LIVE PATH |
| Tests | `tests/test_shadow_budget.py`, `tests/test_ledger_primitives.py` | Component-level tests; synthetic 200-moment budget corpus and synthetic 20-pair refusal-rate corpus, not live chat/tension samples |
| Mind map | `mind_map/MIND_MAP.yaml::p13_finitude` | Says `evidence: implemented` and `dark: true`; its short `sketch` says “real ceiling enforced live”, while its detailed notes correctly say the spend ledger and Balance are not used by the live caller |

**Verified conclusion:** the live 1,400-character selector exists, but the per-moment Balance, persisted spend ledger and ledger primitives are not wired into the live Chat/Fountain path. The shadow calls the real pure selector with its own `remaining`, but that proves only the selector's response to a supplied budget—not that live spends are debited and passed to it. The spend table is written by shadow tests/primitives; no live read/consumer was found in the traced entrypoints.

### CTL v0 questions that must be resolved before wiring

1. **No-rewind / moment lifetime:** `Budget._spent` is process memory. `shadow_budget_spend` stores `moment_id` and `remaining_after`, but the constructor does not rehydrate from those rows. Reconstructing a Budget with the same moment ID after process restart resets `_spent` to zero. The module says a moment balance should not survive restart; the roadmap's “no-rewind” requirement therefore needs an explicit definition of whether a moment ends at process restart or must survive it.
2. **Conservation semantics:** `refuse()` accumulates cost on re-facing the same pair. But `consolidate()` collapses duplicate rows by summing `seq` and taking the maximum individual `cost`, while returning the discarded sum-minus-max as `cost_delta`. This preserves distinct-pair count and facing count, but does not preserve cumulative cost if `cost` means “cumulative cost paid across every facing” as the module docstring says. The intended meaning of cost (cumulative paid vs current holding price) must be fixed before changing this.
3. **Atomicity under concurrency:** `refuse()` performs read-then-write for an open pair without a unique constraint visible in the table definition; the module acknowledges a concurrent race and delegates duplicate cleanup to `consolidate()`. That cleanup uses multiple Writer calls, not one explicit transaction. A crash between update/delete operations could leave a partially consolidated group.
4. **Reader/consumer:** the persisted spend ledger is not read back into a live balance or selector. A write-only ledger records history but cannot, by itself, prevent a rewind or prove a live price was applied.

**Phase boundary:** these are source-level design/evidence gaps, not authorisation to wire the shadow into Chat, alter the 1,400-character live budget, or change held-tension behaviour. A1's conservation/no-rewind semantics need founder/spec reconciliation before implementation. Keep `p13_finitude` dark until a live consumer and its invariants are verified.

## 3.12 Genius/STRIKING signal — producer and consumer activation audit

### Producer

`run.py` constructs `GeniusTagger` and calls `start_loop()` unconditionally in the normal boot path. The tagger backfills recent Fountain fires, then scores new fires every 60 seconds and writes `conversations.db.genius_tags` keyed by `(fountain_event_id, weights_version)`. This is [L1] source-defined startup; actual host weights, DB writes and tag population remain [L2] UNKNOWN.

The `GeniusTagger` module and `run.py` still describe the tagger as “LOG-ONLY” and say future consumers do not exist. That description is stale against the current source consumers below.

### Consumer matrix

| Consumer | Reads `genius_tags`? | Activation / effect | Classification |
|---|---|---|---|
| Recent STRIKING prompt block | Yes — `generator.py::_build_recent_striking_block` | Included unless `NEX5_GENIUS_PROMPT_OFF=1`; selects from recent STRIKING fires, filters <5 min, deduplicates, samples up to 2 and applies groove/topic filters. | Source-default active; host [L2] UNKNOWN |
| Readiness mood modulation | Yes — `readiness.py::_genius_modulation` | Active unless `NEX5_FOUNTAIN_READINESS_MOD_OFF=1`; requires minimum sample size; can subtract up to 0.15 from readiness. | Source-default active, sample-dependent |
| Reanimation governor | Yes — `generator.py` governor brick 1 | Active unless `NEX5_GOVERNOR_OFF=1`; on >=4 recent rows and striking rate <=5%, cadence changes 20→5 and a self-rut notice may be written at most once per 2h. | Source-default active, threshold-dependent |
| Continuity block | Yes — `generator.py` continuity layer | Requires `NEX5_CONTINUITY_N>0`; source default is 0. When enabled, retrieves top-scoring prior fires into the next prompt. | Implemented, default-OFF |
| VoiceEngine candidate grading | Yes — `stage_throw_net/voice_engine.py::_enrich_with_genius` | Adds latest tag score to belief candidates unless `NEX5_GENIUS_GRADE_OFF=1`; the score contributes through the Genius axis with weight 0.15. Actual VoiceEngine use depends on caller/mode. | Implemented, conditional consumer |
| Snapshot retention scoring | **No direct `genius_tags` read found.** `theory_x/snapshots/snapshots.py::score_pending_snapshots` independently calls `score_v2.compute_features` and loads the same weights to assign retention tiers. | Invoked by `tools/snapshots.py` CLI; no boot loop found. Pruning is dry-run unless `--commit` is supplied. | Parallel scorer/manual tool, not a live table consumer |

**Count correction:** the “six consumers” description is only accurate if “Genius signal” includes both direct `genius_tags` readers and the separate snapshot scorer using the same scoring model. The source shows five direct table-reader mechanisms above; of those, three are source-default active (subject to sample/host state), continuity is default-OFF, and VoiceEngine grading is caller/mode-dependent. Snapshot retention is a separate manual scoring path, not a sixth live `genius_tags` consumer.

**Feedback conclusion:** this is not a disconnected score table. There are genuine producer-to-next-thought paths through the striking prompt block, readiness modulation and reanimation governor, plus conditional continuity and VoiceEngine ranking. However, the producer's “log-only/no consumers” comments and any dashboard that labels all six as unconditionally live are inaccurate. Runtime consumption and behavioural benefit still require an ID-linked trace and controlled comparison.

## 3.13 A2 morality-table prerequisite — no source table identified

A bounded inspection of all six current SQL schema files (`beliefs.sql`, `conversations.sql`, `dynamic.sql`, `intel.sql`, `probes.sql`, `sense.sql`), `MIND_MAP.yaml`, and the repository's `strikes/` package found no dedicated table or module named for morality, ethics, virtue or Dharma.

The `strikes/` package is a catalogue/protocol mechanism for manual striking experiments; it is not a morality table and no automatic consumer path from it into Fountain was established. The `genius_tags` table records a separate Genius/STRIKING classification signal and has the consumers described in §3.12; it is not evidence of a moral judgment table.

**A2 is therefore a roadmap requirement whose source object and semantics are not yet identified.** Before creating consumers, establish the intended table/schema, what constitutes a moral observation versus a STRIKING event, how evidence is accumulated, how contradictory observations are handled, and which existing faculties should consume it. Do not repurpose `genius_tags`, the `strikes/` catalogue or `held_tensions` by name similarity.

## 3.10 Sense-feed activation — apparent mismatch resolved by source history and tests

An initial comparison of startup comments suggested that external sense feeds were described as paused while `SenseScheduler.__init__()` called `start_all()`. The deeper source/test review resolves the operational question:

- `theory_x/stage1_sense/scheduler.py::SenseScheduler.__init__` explicitly calls `self.start_all()`.
- The immediately adjacent source comment dates the change to 2026-05-09 and says feeds auto-start on boot per Jon's request; it also identifies removal of that line as the reversion path.
- `tests/test_sense.py::TestScheduler.test_init_starts_all` was updated on 2026-05-09 and asserts `global_running` is true and external adapters are enabled.
- `run.py`, `theory_x/stage1_sense/__init__.py` and parts of the scheduler module docstring still describe external feeds as paused by default.

**Correct Phase 0 finding:** the current source and test contract is auto-start on boot. The "paused" descriptions are stale documentation, not evidence that the runtime is paused. This was an intentional historical change and must not be reverted as a supposed bug. Whether a deployed host actually started the scheduler remains UNKNOWN without runtime evidence.

## 3.14 Harmonizer / held-tension prompt path — activation and measurement qualification

| Stage | Source evidence | Finding |
|---|---|---|
| Loop boot | `build_world_model()` starts `_harmonizer_loop` as a daemon thread | The Harmonizer scan/tick loop is source-started unconditionally by the WorldModel builder. |
| Tension creation | `Harmonizer._hold_as_tension()` | Writes `held_tensions` only when `NEX5_HELD_TENSION=1`; source default is OFF. Otherwise the escalation follows the retire/synthesize path. |
| Chat consumer | `gui/server.py::api_chat` calls `state.world_model.harmonizer.format_for_prompt()` and appends non-empty text to `belief_text` | This is a real Chat prompt consumer. |
| Content-specific line | `Harmonizer._content_specific_tension_line()` | Requires `NEX5_HELD_TENSION=1`; reads the newest open `held_tensions` pair and inserts clipped belief contents (up to 90 characters each). |
| Generic count line | `Harmonizer.tick()` → `format_for_prompt()` | When the held-tension flag is off, the content-specific line is empty; Chat may receive only “Holding N unresolved tensions…” from the cached `active_paradox` count. |
| Count correctness | `NEX5_HARMONIZER_TENSION_COUNT_FIX` | Default OFF. The uncorrected tick counts all `harmonizer_events` rows with resolution='paradox', not the latest unresolved state per pair. Source comment records a measured 73 all-time vs 40 actually open (2026-11-07). Thus the Chat line can overstate unresolved tensions. |
| GUI visibility | `GET /api/harmonizer/tensions` | Read-only HUD endpoint lists up to 200 held_tensions rows and belief contents; it is not itself a cognitive/Chat consumer. |
| Resolution/decay | `Harmonizer.decay()`, `sweep_resolved_tensions()`, `retry_bridge_for_tensions()` | `decay()` docstring says no live caller; `_harmonizer_loop` calls scan/resolve and tick only. Do not assume stale held tensions are swept in live operation. |

**Distinction:** the Chat unresolved-tension line is not proof that the `held_tensions` table is populated or that the ledger primitives are live. With the held-tension flag OFF, the generic line is derived from `harmonizer_events` and can be miscounted. With the flag ON, the content-specific path can read actual open held-tension rows. Actual host flag values and table contents remain UNKNOWN.

## 3.11 Evaluation and self-observation paths — source-to-consumer corrections

The supplied feedback-map hypothesis needs refinement against the current source. The following are source-confirmed; they do not establish live host activation.

### Predictive substrate and surprise

- `run.py` constructs `PredictiveSubstrate` and calls `start_loop()` without an environment flag in the inspected startup path. It predicts internal-belief and external-input windows, then verifies expired predictions and writes `surprise_events` plus prediction verification fields.
- `theory_x/stage_affect/affect_state.py::_compute_arousal_delta()` reads recent flagged `surprise_events` and uses their mean surprise score to adjust arousal. `run.py` constructs AffectState and calls `start_loop()` in the inspected startup path. This is a concrete downstream affect-state use.
- `theory_x/stage_prediction/surprise_weighting.py` also reads recent `surprise_events`; `FountainCrystallizer.crystallize()` calls its `confidence_for_fire()` path when `NEX5_SURPRISE_WEIGHT` is enabled (default documented as ON). This is a separate downstream use of surprise score in belief confidence.
- `theory_x/life/surprise_loop.py` contains a reader/promoter that converts qualifying surprise rows into Tier-6 beliefs, which would make them available to normal belief retrieval. However, the inspected `run.py`, `gui/server.py` and `theory_x/life/__init__.py` contain no startup/wiring call for this loop. Treat the promotion path as IMPLEMENTED but its automatic activation/consumption as UNKNOWN until all external launch paths are checked.
- `PredictionTracker.expectation_error()` is a separate mechanism: it derives a novelty ratio from the last 20 Fountain thoughts, not the predictive substrate's stored prediction verdicts. `EmphasisEngine.score()` calls it for the surprise component. Do not conflate these two surprise mechanisms.

### Emphasis

- `EmphasisEngine.score()` computes goal relevance, self relevance and PredictionTracker novelty, plus drive resonance as a separately logged signal. Its own source documentation says log-only; the inspected code returns an `EmphasisResult`, and Fountain writes its fields to `emphasis_log`.
- The inspected consumer path does not establish that the combined emphasis score changes candidate selection, crystallization acceptance or future prompt composition. The fact it is calculated on every fire is not evidence that it influences cognition. The image-map claim of zero readers for `emphasis_log` remains a plausible source-level finding, but a complete repository-wide reader search is still required before marking it definitive.

### Metacognition events

The image-map statement that `meta_cognition_events` is read only by the reaper and tests is contradicted by the inspected source:

- `Metacognition.get_recent()` reads unresolved rows from `meta_cognition_events`.
- `_refresh_recent_cache()` selects the recent rows (or salient-ranked candidates when its flag is enabled).
- `format_for_prompt()` turns the selected event into a self-observation string.
- `gui/server.py::api_chat` calls `tick()`, calls `format_for_prompt()`, and appends a non-empty result to `belief_text` before the model request.

This establishes an implemented Chat context-consumption path, not proof that the injected observation changes the model's subsequent cognition in a controlled or durable way. The table is not simply write-only.

### Warrant and earned-ness

- `WarrantRecorder` is explicitly gated by `NEX5_WARRANT_RECORD=1` and records conflict-survival checks and use-days in side tables.
- `WarrantPass` is separately gated by `NEX5_WARRANT=1` in its own `start_loop()` method and persists computed values into `belief_warrant`. However, the inspected `run.py` constructs/starts `WarrantRecorder` conditionally and contains no construction or start call for `WarrantPass`. Thus the compute/persist implementation exists, but normal startup activation is not established by this entrypoint.
- The inspected `run.py` startup contains the conditional recorder construction/start; the flag's deployed value remains UNKNOWN.
- A complete downstream consumer search for `belief_warrant` is still open. Do not treat the existence of the computation/table as operational influence or say categorically that there are no readers until that search is complete.

## 3.15 Novel Association / Tier-7 retrieval gap — content versus annotation

| Stage | Source evidence | Finding |
|---|---|---|
| Producer boot | `run.py` constructs `NovelAssociation` and calls `start_loop()` | Source-default background loop starts; cadence is 30 minutes. Actual host initialization remains UNKNOWN. |
| Candidate pool | `NovelAssociation._pull_candidates()` | Reads unpaused, branch-tagged beliefs with confidence >=0.15, sampling up to 10 per branch. It does not filter by tier. |
| Edge production | `NovelAssociation._write_association()` | For cross-branch pairs with cosine >=0.72, writes a `belief_edges` row of type `synthesises` and a `novel_association_log` row. It does not create a new belief. The module's comments describe the topology as T7 cross-domain. |
| Standard retrieval pool | `BeliefRetriever.retrieve()` | Initial candidate query filters `tier <= 6`. `row_map` is built only from those eligible rows. |
| Spreading activation | `BeliefRetriever.retrieve()` → `ActivationEngine.activate()` | Activation may return scores for graph neighbours, but the final merge drops any ID absent from `row_map`. Therefore a Tier-7-only Novel Association endpoint cannot appear in standard retrieval results. |
| Chat annotation | `gui/server.py::api_chat` → `NovelAssociation.format_for_prompt()` | A recent unannotated log row can produce a short metadata line naming the two branch IDs and similarity. This reaches Chat, but not the underlying belief content. |
| Separate Synergizer | `BeliefSynergizer.synthesize()` | Different mechanism: writes a new Tier-6 belief (source `synergized`), which is eligible for standard retrieval. Do not conflate it with NovelAssociation's T7 edge-only topology. |

**Correction to the feedback map:** the statement “synthesises edges cannot reach prompts” is true for the underlying Tier-7 belief content through the standard retriever, but not for all signal. The Chat route can receive a metadata-only NovelAssociation annotation. The separate Tier-6 Synergizer output is a different path and can be retrieved. The source gap is therefore specifically: T7 edge topology is generated, activation may traverse it, but final retrieval filters out IDs not present in the Tier<=6 candidate map.

## 3.16 Self-maintain shadow — self-reader versus cognitive consumer

- `run.py` constructs and starts `SelfMaintainShadow` only when `NEX5_SELF_MAINTAIN_SHADOW=1`; source default is OFF.
- The module is explicitly log-only: it computes would-pause/would-unpause counts and writes one row per hourly tick; it does not pause or unpause beliefs.
- The module **does read its own table** in `_setpoint()` to compute a rolling median after at least 24 hourly rows exist. If insufficient, it falls back to internal interoception snapshots.
- The bounded source search found no other cognitive faculty consuming `self_maintain_shadow`. Thus “nothing reads its table” is too broad literally; the accurate statement is “no external cognitive consumer; only the shadow's own setpoint calculation reads its history.”
- Because the loop is default-OFF and has no external consumer, its runtime data and any influence on cognition remain UNKNOWN / absent by source design.

This is a monitoring self-read, not a closed cognitive feedback loop. Do not wire its would-pause decisions into belief pausing without the roadmap's separate Phase D approval.

## 3.12 Arc subsystem — disabled producer and inert prompt reader

The arc path is a useful example of why a SQL read is not automatically an operational consumer:

- `run.py` sets `arc_loop = None`; its dated comments say the loop was disabled from 2026-05-30 and removed from startup wiring. The source explicitly says `build_arc_loop` has no other caller and that the detector was the only writer of `arcs`, `arc_members` and `arc_closers`.
- `theory_x/arcs/loop.py` still contains a functioning `ArcLoop` / `build_arc_loop()` implementation, but the inspected startup path does not construct or start it.
- `FountainGenerator._fetch_arc_context()` still queries active arcs within 7,200 seconds and recently closed arcs within 14,400 seconds. This is a reader at the SQL level.
- However, `_format_arc_context()` contains a dated comment explaining that the two prompt-injection blocks were removed and the function now returns an empty string even when rows exist. The caller's `if arc_block:` therefore does not add arc context to the prompt.

**Correct classification:** arc detection is CONSTRUCTED but its normal startup producer is disabled; the remaining Fountain read/format path is operationally inert for prompt influence. The image-map shorthand "zero readers" is not literally accurate (a query remains), but it is accurate to say no functioning downstream cognitive consumer is established in this startup path. Existing rows may remain in the database; host contents and freshness are UNKNOWN.

## 3.17 Auto-probe / GrooveBreaker — confirmed double-dead path

- `theory_x/auto_probe/groove_breaker.py` has module constant `ENABLED=False` (disabled 2026-05-02). `check_and_maybe_log()` immediately returns when false; the observation writer is therefore inactive.
- The 2026-07-26 file comment says the live construction/call sites were removed from `run.py`, `stage6_fountain/__init__.py` and `generator.py`. Current source confirms no GrooveBreaker construction in `run.py` and no `get_pending_probe_text()` call in the Fountain generator.
- The intended delivery reader `get_pending_probe_text()` queries `auto_probe_log.delivered_at` and `selected_probe_text`. The constructor's cooldown reader and pending-approval reader also query `auto_probe_log`.
- No `auto_probe_log` table definition exists in any of the six current canonical SQL schema files. The observation writer is disabled, the runtime object/call path is absent, and the intended reader has no current schema contract.
- The separate `probes` table in `probes.db` is a probe catalogue; it does not substitute for `auto_probe_log`.

**Conclusion:** this is not an active feedback edge. It is a retired, unwired subsystem with a disabled producer and a missing persistence contract. The map's “double-dead” description is supported, with the qualification that there are several dormant readers inside the orphaned class, not one active runtime reader. Do not restore the old wiring without first deciding whether the subsystem is still wanted and defining its schema/phase.

## 3.18 Fountain prompt-block manifest — persistent trace already exists

The Fountain already has a more durable per-block trace than the one-prompt temporary file:

- FountainGenerator creates `fountain_prompt_blocks` in the dynamic database at startup. It is deliberately not dropped on restart.
- After the Fountain event is written, it uses `Writer.write_many()` to insert one row per prompt block: `fire_id`, ordinal, block name, SHA-256 hash, character count, bounded prefix and timestamp.
- A 30-day reaper runs once at process start. The documented estimated cost is about 1.8 KiB/fire (16 blocks), ~930 KiB/day at 530 fires/day and ~27 MiB steady state.
- The manifest write is after the fire is already written and is fail-safe; a manifest write failure does not change what the Fountain said.
- The raw `nex5_last_prompt.log` full-prompt overwrite still exists despite the persistent manifest. The manifest provides per-block retrospective shape/hash/prefix evidence, while the temporary file exposes the complete assembled prompt and only preserves the most recent fire.

**Consumer status:** the bounded source search found the manifest writer and schema/reaper but no runtime reader or repository script consumer. It is manually queryable from the dynamic database. It is a persistent trace substrate, not yet a demonstrated cognitive consumer or complete cross-system CTL.

**A1 implication:** reuse this existing fire/block identity and manifest before adding another Fountain trace store. The new M0.5 overlay supplies the missing Chat/gate/Writer parent chain; it should not duplicate Fountain block payloads. The full raw temporary prompt file is a candidate for removal or restricted opt-in after external/manual consumer confirmation.

## 3.19 CoherenceGate Check 1a/1b — narrow rules, not a general contradiction evaluator

Current source and tests define two separate checks:

- **Check 1a:** Jaccard token overlap >=0.70 with an existing belief → REJECT as redundant.
- **Check 1b:** direct negation of a locked Tier-1 anchor with at least four shared words → REJECT. The test suite explicitly verifies a minimal-pair direct negation is rejected, while two-word overlap and rhetorical-negation cases are not rejected.
- The earlier broad token-overlap contradiction approach was removed after false positives. Current Check 1b is a narrow locked-anchor protection, not a general contradiction detector and not a truth-evaluation mechanism.
- The source comments describe a large prior reject population dominated by Throw-Net traffic; those historical counts should not be mistaken for the current Check 1b distribution.
- The supplied map's statement that Check 1b “passes direct contradictions” is not supported for direct negations of locked T1 anchors: the current code explicitly rejects those. The cited 47.7% counterfactual REJECT statistic was not reproduced from current source/tests and remains UNKNOWN without its dataset and calculation.

This gate preserves locked axioms and filters near-duplicate thoughts. It does not establish whether a novel contradiction to a non-locked belief is true, useful, or worthy of being held as tension.

## 3.20 Prediction families — separate autonomous substrate from gated scorecards

The repository has three distinct prediction mechanisms that should not be conflated:

| Mechanism | Boot state | What it writes/reads | Does it become a belief? |
|---|---|---|---|
| `PredictiveSubstrate` | `run.py` starts it unconditionally; 300s interval | Verifies prior `predictions`, creates internal-belief/external-input predictions, writes `surprise_events`. Global Workspace reads surprise candidates. | No direct belief promotion in this path; it can influence the next prompt through Global Workspace. |
| `WorldPredictionLoop` | Requires `NEX5_WORLD_PRED=1`; default OFF | Voice crypto-direction prediction plus random control; resolver stamps correct/wrong in `world_predictions`; scorecard reports performance. | No belief insert in `world_predictions.py` or the loop's current path. |
| `SelfPredictionLoop` | Requires `NEX5_SELF_PRED=1`; default OFF | Predicts fire/no-fire against a random control, resolves against persistent `fountain_events`, writes `self_predictions` and scorecards. | No belief insert in the inspected path. `adapt_threshold()` is explicitly monitor-only; its docstring says the actual update loop is elsewhere (`selfdesc_novel`). |

The reported “2,705 market + 5,228 self predictions resolved” is a historical database claim, not something source code alone verifies. Current host flag values and table counts are UNKNOWN. The current source shows the two scorecard loops are optional and do not automatically promote their outcomes into beliefs. By contrast, PredictiveSubstrate is source-default active and its surprise events can influence the next thought through Global Workspace, even though the prediction itself is not promoted as a belief.

### Pattern loop distinction

`theory_x/life/pattern_loop.py` is a daily-activity pattern summariser: it reads identity/activity records, writes `pattern_log` and may write a Tier-6 `pattern_loop` belief. It does not generate falsifiable outcome predictions or resolve them against actual outcomes. No normal `run.py` start call was found for this loop. Do not call it the same thing as the world/self prediction scorecards.

## 3.21 Evaluation artefacts vs downstream decision influence — source audit

This audit separates evaluation output from an actual downstream consumer. It is a source-level finding against the inspected repository revision; it is not a claim about current host flags or live runtime behaviour.

### `belief_warrant` — score construction exists; normal boot consumer is not established

- `theory_x/stage_warrant/warrant.py::compute_all()` calculates survival, sustain, independent support and cross-branch synthesis components. Its `persist()` function creates/upserts the `belief_warrant` side table through the beliefs Writer.
- `WarrantPass.start_loop()` checks `NEX5_WARRANT=1`, but the inspected `run.py` startup path does not construct or start `WarrantPass`. It does contain a separate `NEX5_WARRANT_RECORD=1` startup block for `WarrantRecorder`. The validation utility `tools/warrant_validate.py` calls `compute_all()` directly; it is an offline/read-only evaluation path, not a runtime consumer of the persisted table.
- `WarrantRecorder.use_cycle()` reads non-identity `fountain_retrieval_log` rows, Fountain anchors, synergizer events, lineage and arc membership to build `belief_use_day(s)`; its survival pass writes `belief_survival`. These are recorder outputs and input features for the warrant calculation, not a read of `belief_warrant` by a decision sink.
- The inspected decision sinks do not use `belief_warrant`: `BeliefRetriever` scores keyword/semantic relevance with confidence and graph activation; `VoiceEngine` uses semantic similarity, confidence, tier, reinforcement recency, drive alignment and genius score; `GlobalWorkspace` arbitrates surprise, momentum, bonsai, stakes and drive candidates. No `belief_warrant` read was found in those audited paths.
- Important distinction: the warrant sustain component treats eligible retrieval/association records as use-days. That establishes recorded exposure/association under its operational definition; it does **not** by itself establish that a thought relied on the belief or that the belief changed a decision.

**Classification:** score and persistence functions are constructed [L1]. A normal boot-time producer/consumer path for the `belief_warrant` table is not established in the inspected startup and decision paths. Host flag values and any external/manual invocation are UNKNOWN. Do not classify the score as influencing retrieval, retention or selection.

### `emphasis_log` — post-generation observation, not a selection signal

- `FountainGenerator` constructs `EmphasisEngine`, creates `emphasis_log`, scores a thought after generation, then writes the result against the newly created `fountain_event_id`.
- `EmphasisEngine.score()` computes goal relevance, self relevance and prediction surprise as the current equal-weight combined score. Drive resonance is still separately computed/logged but was removed from the combined score after its prior ground-truth test was null (p=0.190, effect -0.013). The other three signals are explicitly unvalidated in the module documentation.
- The score is post-hoc: it is computed after the candidate thought already exists. The inspected `generator.py`, `global_workspace.py`, `BeliefRetriever` and `VoiceEngine` paths contain no read of `emphasis_log` or use of the returned `EmphasisResult` to alter candidate choice, crystallization, belief retrieval or subsequent thought selection.

**Classification:** constructed observation/evaluation mechanism [L1]; actual host/runtime writes remain UNKNOWN. No downstream decision influence is established in the inspected paths. Treat `emphasis_log` as a measurement record, not an active attention or retention mechanism.

### Do not conflate `belief_warrant` with `śraddhā`

`theory_x/stage_affect/sraddha.py` is a separate prompt-composition mechanism. It selects relevant Tier-6/7 beliefs using raw confidence, corroboration count and belief-edge degree; it does not query the `belief_warrant` table. `gui/server.py` adds its returned block to Chat context only when `NEX5_SRADDHA=1` and the session is admin-authorised. This is a source-level prompt influence path [L1], with the flag's live value UNKNOWN; it is not evidence that the warrant score is consumed.

### A known evaluation-to-selection path: Genius score in VoiceEngine

A distinct path does have a source-level downstream selection consumer:

- `VoiceEngine._enrich_genius_scores()` reads `genius_tags` and attaches the corresponding score to eligible belief candidates.
- `VoiceEngine._score_candidate()` includes the continuous genius score with weight 0.15 (unscored candidates receive the neutral 0.5 value); `query_reply()` selects the highest-scoring candidate and applies the `min_score` threshold.
- This is an evaluation-to-candidate-ranking path in source when the VoiceEngine route is used. It is not a belief-warrant or emphasis-log consumer, and source presence does not prove live activation or improved task outcomes. No persistence/retention effect is established by this path.

### Evidence vocabulary — do not collapse these states

| Evidence state | What currently establishes it | What it does not establish |
|---|---|---|
| **Written** | A Writer insert/upsert creates a belief or evaluation row with an ID. | That another mechanism ever reads it. |
| **Retrieved** | A retrieval result or `fountain_retrieval_log` row records a belief drawn into a retrieval/context path. | That it was attended to, relied upon, or changed a choice. |
| **Context-present** | The belief is included in an assembled prompt/context block. | That the model used it in its reasoning or output. |
| **Selected** | A specific candidate/winner ID and its score are recorded at the selection point. | That the selected item changed a later decision or outcome. |
| **Retained-to-commit** | `generator.py` passes the top-ranked `own_sense` retrieval candidate as `retained_candidate_id` to crystallization; `crystallizer.py` emits a log linking that ID to the new crystallized belief ID. | A durable structured relation: the current smṛti link is an application log entry, not a new relational row. |
| **Relied upon** | A downstream mechanism reads a specific item and uses it in a defined operation/decision, with an ID-linked trace. | That the result would differ if the item were absent. |
| **Decision-changing** | A controlled ablation/counterfactual shows a downstream decision or outcome changes when the item/mechanism is removed. | Generalisation beyond the tested tasks. |

The retrieval/warrant recorder's use-day metric must therefore be described as *retrieval/association exposure*, not as proven reliance. The smṛti hand-off is stronger than mere retrieval because the selected ID is passed into the crystallization call, but its current log-only link is not yet a durable, independently queryable retention edge.

### Immediate Phase 0 trace implication

The causal trace should preserve the distinction above. The current PR #54 source branch now records the selected VoiceEngine candidate as a source-scoped `entity_ref` (`voice_candidate:<source>:<origin_id>`) and records the hit/miss outcome; the candidate score and content remain inside the payload digest rather than being stored raw. This avoids mislabelling novel-association, arc or problem IDs as belief IDs. The Fountain trace should distinguish retrieved IDs, the retained-candidate hand-off, crystallization ID and any later speech-queue disposition. The current draft envelope stores payloads as digests, not readable numeric measurements; if the final VoiceEngine score must be independently inspectable, that requires explicit reconciliation of the trace schema rather than silently adding a new field. A retrieval row or evaluation score alone must never be labelled a relied-upon or decision-changing belief.

No behavioural change, new evaluation, flag activation or schema migration is authorised by this audit. The next proof level for decision-changing effects belongs to the roadmap's later controlled ablation work, not to Phase 0 instrumentation.

## 3.22 Chat source-to-sink expansion — PR #65 integrated branch

A separate revision-bound Chat pathway audit has been added in `NEX_CHAT_PATHWAY_AUDIT.md`, inspected against PR #65 integrated source head `3d5df48e6539818097b58b6e936059fae946ceca`. It expands the `gui/server.py::api_chat` path into the shared entry/routing stage, conditional gap refusal, direct VoiceEngine substrate hit, VoiceClient composition, retry/sanitization/persistence branches, and the source contributors that can populate the prompt.

Two important qualifications from that audit:

- Chat has distinct direct-substrate and model-composition routes. A VoiceEngine hit can be returned directly (except in the operator-hybrid case); it is not accurate to represent every Chat turn as an LLM composition.
- The FocalSet block is labelled “log-only”, but it adds selected belief contents to session Working Memory; the later same-turn WorkingMemory branch can inject those contents into the prompt for a Conversational register when the precomputed belief count meets the threshold. This is a source-confirmed conditional prompt-influence path and an omitted causal edge in the current trace. It is not a claim of deployed activation or a behavioural defect.

The audit also identifies prompt contributors whose provenance is currently collapsed into the single `context_selection` digest, including tool results, disturbance/problem context, optional faculties, random spectrum rows, and the VoiceEngine TimeFetch candidate/enrichment pipeline. The current trace parent list is therefore not a complete causal closure for Chat.

The tool-path expansion also identifies conditional defect DRAFT-002: the natural-language math heuristic selects `python_exec`, but the caller passes the original query as code through an empty-code fallback, so ordinary calculation phrasing is not executable Python. This is recorded in the Reality Report defect backlog and Chat audit with source/test hashes. No runtime repair or severity assignment is included.

**Evidence boundary:** static inspection only; PR #65 head and source file hashes are recorded in the audit. Its latest CI pass validates the tested suite, not every branch or deployed-host behaviour. The audit remains partial and does not satisfy Gate 0.

## 4. Top documentation/source discrepancies

These are discrepancies to reconcile, not automatic instructions to modify code or documentation.

1. **Architecture status and test count conflict.** The opening of `ARCHITECTURE.md` says “Phase 9 complete” and “189 tests passing”, while later text in the same header records 1,987 tests as of the 2026-11-07/08 session. The status is not a reliable current Phase 0 baseline.
2. **R77 status is stale in the architecture narrative.** `ARCHITECTURE.md` describes `NEX5_CHAT_WORKSPACE` as armed and mid-measurement as of 2026-11-07. `observation_reports/r77.md` records a Branch C disarm on 2026-11-20 after a tripwire breach, with the variable removed from `nex_keepalive.sh`. The observation report is later and records the closeout; live host state still requires verification.
3. **Chat arbitration documentation lags source.** `SENTIENCE_PROGRAM.md` describes Chat as concatenating approximately 16 blocks without arbitration. Current `gui/server.py` contains `_assemble_chat_blocks()` and a conditional `NEX5_CHAT_WORKSPACE` salience/budget selection path. This establishes code presence, not current activation.
4. **Mind-map authority invariant was not enforced by the original map validator.** The workflow's `mind_map/mind_map.py --check --verify` step validates document structure, references, evidence/status metadata, stale-source warnings and configured absence checks; it does not enforce the semantics of `meta.constraint` or inspect runtime consumers. A new draft pytest guard on PR #49 now checks the declared constraint and scans the runtime source roots for direct imports or literal filename references. This improves the CI boundary but cannot detect arbitrary dynamically constructed paths or prove all indirect control relationships. The YAML's descriptive-only rule is explicit, and `run.py` does not load the map. No evidence currently shows a runtime node gating an action.
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
