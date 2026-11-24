# NEX Architecture Crosswalk v2 — Working Draft

**Status:** Partial source crosswalk; not a Gate 0 submission  
**Current documentation branch revision:** `07f6ebe42a1ac99a8038a73476782d1542704296`  
**Boot/source inventory rechecked:** `run.py` blob `73a2c58a4f5f0348135a46eb83d6cdd61db874e7` (23 Nov 2026)  
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

A further membrane boundary finding is recorded as DRAFT-003: the classifier uses substring matching for `"you"`, so a world query containing the product name `YouTube` is classified INSIDE and routed through the self-model/INSIDE retrieval path. The source/test evidence and limits are documented in the Reality Report and Chat audit. No runtime repair or severity assignment is included.

The Chat audit now also expands the internal membrane dependencies: INSIDE routing combines a SelfModel snapshot (sense-event reads and its own top-five inside-belief selection) with a separate query-ranked INSIDE BeliefRetriever pass; OUTSIDE routing uses DynamicState-derived branch hints and a separate retriever call. Both are collapsed at the current Chat trace's retrieval boundary, which does not record the underlying selected row IDs or activation dependencies.

The FocalSet/WorkingMemory inspection further identifies an unresolved session-isolation boundary: a single process-global FocalSet is updated across requests, while WorkingMemory is session-keyed in a process-local dictionary. Shared FocalSet hold/priority state can affect later sessions' selection where belief IDs overlap; the dictionary helper has no session-key deletion/eviction path in the inspected module. These are design/acceptance and lifecycle questions, not asserted defects absent the Frozen V2.1 criteria.

**Evidence boundary:** static inspection only; PR #65 head and source file hashes are recorded in the audit. Its latest CI pass validates the tested suite, not every branch or deployed-host behaviour. The audit remains partial and does not satisfy Gate 0.

## 4. Additional architecture-documentation/source discrepancies

The five highest-impact runtime-contract/code-comment discrepancies are ranked separately in NEX_VERIFIED_DEFECT_BACKLOG.md and ADR-001. This section retains five additional architecture-documentation/source discrepancies for reconciliation; it is not a competing priority list. These are not automatic instructions to modify code or documentation.

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


**VoiceEngine / TimeFetch qualification (23 Nov 2026):** The candidate pool is assembled from four ordered source sweeps (beliefs, novel associations, arcs, open problem gaps), each with its own cap, followed by exact-content deduplication (first source wins) and a global cap of 40 before scoring. This means source order and SQL retrieval limits shape the set being ranked; it is not an exhaustive global semantic ranking. The optional Genius enrichment selects the latest tag per fountain event but does not filter or preserve the selected `weights_version`; compatibility across versions remains unverified. The score uses six components with total maximum weight 1.15 (the Genius 0.15 term is intentionally not renormalized), while module-level prose still calls it five-axis. A test named for embedding exceptions supplies a zero vector instead; it does not exercise the exception path. These are source/documentation/test-evidence qualifications, not independently asserted behavioural defects. See the VoiceEngine/TimeFetch addendum in `NEX_CHAT_PATHWAY_AUDIT.md`.


**Open-problem candidate boundary:** TimeFetch's gap candidates originate from `ProblemMemory.find_matching()`: open problems are traversed in `last_touched_at DESC` order and retained at a threshold of two shared cleaned content tokens. The matches are not pre-ranked by overlap count or semantic similarity before entering VoiceEngine's later scoring stage. Whether recency-first candidate inclusion is the intended balance is unresolved without the authoritative acceptance criteria. Source hash: `4a9dcc839bf0be7bf28338168d8946309c7002f5`.


**Genius tag versioning cross-check:** `GENIUS_SCORE_v2.md` says tags coexist per `(fountain_event_id, weights_version)` so old and new scores can be compared. VoiceEngine currently takes the newest timestamped tag without an active-version filter. The evidence supports “most recently tagged score”, not necessarily “approved/current weights score”; intended consumer semantics remain open pending the authoritative version contract. Design doc hash: `be73cb4f7b494c48eb37eeec8635aba89ea5751e`.


**FocalSet integration boundary:** The Chat handler updates a process-global FocalSet from each request's top-10 belief candidates, then copies its selected IDs into the requesting session's own WorkingMemory. Up to five active items are later injected into the composition prompt only for Conversational turns with at least two retrieved belief blocks. Shared FocalSet hold/last-shift state can influence another session's selected IDs when candidate sets overlap; session WorkingMemory itself remains separately keyed. No inspected integration test interleaves two chat sessions through this path. Whether attention continuity is intended to be process-global or session-scoped remains an explicit acceptance question; do not infer a defect or change the architecture without the governing sign-off. See Section 12 of `NEX_CHAT_PATHWAY_AUDIT.md`.


**Prompt timing qualification:** The `Recently attended (cross-turn)` block is assembled after the current request's FocalSet update and WorkingMemory add operation. It may therefore contain both same-turn selected beliefs and retained earlier items, not only cross-turn carry-over.


## Independent review reconciliation — causal and authority qualifications (23 Nov 2026)

The exact-head independent review confirms that this crosswalk remains partial and is not a Gate 0 submission. The authority-artifact absence is bounded to the inspected repository/PR material: canonical Frozen V2.1 and Founder Sign-Off/approval records remain unlocated there, but their non-existence elsewhere is not established. The Master Roadmap's reported retrieval from the Library does not substitute for a canonical, versioned artifact in the review evidence. Gate 0 remains unestablished pending authority reconciliation and the required Founder approval.

### Additional Chat trace distinctions

- The VoiceEngine input trace record currently lists the general Chat retrieval record as a parent. The VoiceEngine call receives the query/session/turn values and performs its own TimeFetch retrieval; the general Chat retrieval result is not passed into it. The parent edge is therefore not established by the inspected data dependency. Treat it as a trace-parentage concern requiring explicit reconciliation, not a behavioural defect.
- The handler's `use_substrate` comment says a substrate miss suppresses LLM fallback, but the inspected miss path leaves `text` unset and proceeds to `state.voice.speak()`. The default `VoiceClient.speak()` implementation invokes its request function and its default request function sends an HTTP request to llama-server. Runtime substitutions/configuration remain unverified. Record a source-confirmed comment/control-flow mismatch with unresolved runtime effect; do not change behaviour without authority.
- A Chat model-input marker and aggregate context digest do not identify every selected retrieval item, faculty, tool result, WorkingMemory contribution or substrate read. A trace edge is not proof that the downstream model relied on that material.
- The paired Chat fixture validates its minimal configured route only. It is not evidence for every feature flag, optional faculty, VoiceEngine direct hit/miss, tool route, retry or exception path.

### Speech and observer qualifications

- The controlled commit/register race proves a possible unlinked trace at the tested interleaving, not its deployed frequency.
- Pending-row selection followed by a later status update is not an exclusive claim. Overlapping consumers could select the same row; actual deployment overlap and duplicate processing are unknown.
- Synchronous JSONL writes under a shared trace lock create possible latency/contending-writer cost. The benchmark smoke test is diagnostic only; no host latency distribution or acceptance threshold is established.
- A player-call return and a persisted `spoken` status do not prove physical audibility or listener receipt. A processing-start event does not prove exclusive ownership.

### Exact-head CI correction

PR #49 head `d046d5beadd640cca6df6631d9dbd3166d16fccf` passed pytest run `45255379806`; PR #65 head `3d5df48e6539818097b58b6e936059fae946ceca` passed pytest run `45250499152`. These are separate workflow runs on separate PR heads. They supersede stale pending/failure statements for those exact revisions, but do not establish runtime behaviour, complete causal coverage or Gate 0 approval. Historical CI tables in the ADR remain historical records and should not be presented as current status.

No runtime, schema, architecture, queue, retry, flag, host, experiment or deployment change is authorised or proposed by this reconciliation.


## Original Master Roadmap v3.0 reconciliation (23 Nov 2026)

The original full **NEX v5.0 — Master Technical, Research & Commercialization Roadmap v3.0** (20 Nov 2026) is available in the ChatGPT Library as `gemini.txt` (44,167 bytes; Library result reference `turn390file0`). This confirms the original roadmap is available outside this PR's repository tree; the PR tree's bounded absence is not a global absence. The exact Frozen V2.1 specification and Founder Sign-Off/approval record remain unlocated in the searched material.

The roadmap's Phase 0 requirements are:
- M0.1–M0.2: exact repository/environment/test baseline, target-host measurements, runtime database/snapshot hashes, full pytest reconciliation and Reality Report.
- M0.3–M0.4: cross-check the named architecture sources, verify descriptive mind-map nodes cannot gate/veto, forward and backward audit every `theory_x/` faculty, and deliver Crosswalk/ADR.
- M0.5: default-OFF read-only causal trace, one complete Fountain cycle and one complete Chat turn, and OFF/ON no-mutation verification; deliver `NEX_CAUSAL_TRACE_SAMPLE.json`.

Current drafts and isolated CI fixtures do not establish all of these deliverables. In particular, no target-host measurements or complete production-host trace sample are established, and the forward/backward faculty audit remains partial.

### Two internal roadmap inconsistencies

1. Evidence levels: §1.2 defines a six-level L0–L5 ladder (including L5 generalisation), while §6.2 instructs the crosswalk to assign L0–L4. Do not silently collapse or choose between these instructions; obtain Founder clarification, preserving the distinction in the evidence model meanwhile.
2. Chat Arbiter sequencing: §5.1 places read-only Phase 0 trace first and Chat Arbiter experiment in Phase 1.1 second. §6.3 makes Gate 0 Founder approval of the Reality Report, Crosswalk and verified defect backlog a condition before any behavioural edits. Yet §12.3's 30-day checklist places implementation and a three-arm Chat Arbiter benchmark in Week 3, with Gate 0 sign-off in Week 4. Since §7.1 separately defines the Arbiter as a Tier B Phase 1.1 experiment, this is a material sequencing conflict. It is not resolved here; no Chat Arbiter behavioural experiment should begin before the explicit Gate 0 condition is satisfied and the Founder resolves the conflicting checklist wording.

**Disposition:** This Crosswalk remains partial and not a Gate 0 submission. Continue Phase 0 evidence work only; no Phase 1 behavioural change is authorised.


## 3.23 Boot-level forward audit — exact PR #49 branch revision (23 Nov 2026)

This pass re-read `run.py` and the relevant factory/loop implementations at the PR #49 branch revision `07f6ebe42a1ac99a8038a73476782d1542704296`. It corrects several boot-inventory descriptions and extends the forward map. These are source-level construction/start findings only; actual host environment, successful runtime ticks, row emission and downstream behavioural influence remain unobserved here.

### Stage 1 — SenseScheduler and adapters

- `run.py::main` calls `build_scheduler(writers, readers, mode_state=mode_state)`.
- The builder's adapter list contains 28 adapters: four internal sensors and 24 external feeds.
- `SenseScheduler.__init__` creates one daemon thread per adapter and unconditionally calls `start_all()`. `start_all()` sets the global run event and enables each external adapter; the adapter thread's `_should_run()` requires both global and local events for external feeds. Internal sensors are enabled at construction.
- Thus the executable source starts external feeds automatically; the module docstring/comments that say external feeds start paused are stale relative to the constructor. The run.py startup log says "23 adapters wired" although the builder list contains 28. These are confirmed source/documentation discrepancies. Whether all feed polls succeed is runtime UNKNOWN.
- Builder source hash: `theory_x/stage1_sense/__init__.py` `aa98057657ed631efdceae9a8419c9d9f7324825`; scheduler `a8cc64da406ffa49ad8d59c5134560c4cbb2fdd9`.

### Stage 2 — Dynamic formation and life loops

`build_dynamic()` constructs its DynamicState and starts daemon threads for nine core loops: sense polling/A–F pipeline, aperture recalculation, accumulator decay/flush, crystallization, consolidation, sense distillation, snapshot/tier sampling, health reporting, and emergent-drive detection. It then appends further loop functions when imports succeed: witness, pattern, identity, affinity, scorecard, surprise, remember, wonder, fetch, daily-life, sustained-focus, signal-to-problem, diversity edge-builder, gate retention, and the loops returned by `get_moltbook_loops()`. The factory starts every assembled loop before returning the state. This is stronger than merely constructing a Stage 2 object; it is a source-defined autonomous-loop startup path. It still does not prove each loop's first tick succeeded or produced a useful downstream effect.

Source hash: `theory_x/stage2_dynamic/__init__.py` `7b35f304cf823b555a4c6ec78722a07d017de576`.

### Stage 3 — WorldModel background loops

`build_world_model()` constructs retrieval, promotion, harmonization, activation, erosion, pipeline hooks and synergizer components, then starts six daemon loops: decay, harmonizer, cross-domain, erosion, synergizer and world consolidation. The earlier table's broad [L1] label is retained; the exact six-loop start is now explicit. Individual loops have distinct read/write paths and must be traced separately before assigning any downstream-consumption level.

Source hash: `theory_x/stage3_world_model/__init__.py` `6cbde28b64315b869a260298ddec887d1b9bb0ae`.

### Stage 4 — Membrane

`build_membrane()` constructs classifier, SelfModel, QueryRouter and BehaviouralSelfModel. When the conversations Reader is available (it is supplied by the normal boot path), it starts a daemon behavioural loop that waits four hours before attempting `write_behavioural_beliefs()`, passing the CoherenceGate. Chat route invocation of `membrane.route()` is a separate synchronous path; construction of the membrane does not mean every request uses it. Both loop activation and request routing remain host/runtime observations to be verified.

Source hash: `theory_x/stage4_membrane/__init__.py` `2450572707cd4164d0e877e0b039f8369b1ac395`.

### Stage 5 — Self-location commitment

The import of `SelfLocationCommitment` is not merely unused wiring: `run.py` constructs it during boot and calls `commit(writers["beliefs"], readers["beliefs"])`, logging the returned belief ID. This is a one-time boot operation, not a daemon loop. The source establishes the attempted write path; whether a new row is inserted or an existing commitment is returned depends on the implementation/database state and must be inspected before describing each boot as a new insertion.

### Stage 6 — Fountain

`build_fountain()` starts a daemon `fountain_loop` before returning its FountainState. The loop periodically evaluates readiness, invokes `generator.generate()`, attempts the drive-probe opportunity, and writes a state snapshot when configured. This is source-defined startup, not evidence of a live fire or accepted belief. The detailed generation → crystallization → gate → persistence → optional speech path remains in Sections 3.1 and 3.1.1.

Source hash: `theory_x/stage6_fountain/__init__.py` `43515f025e7279a6891dd0a630f79b84df198e0c`.

### Additional boot-wiring corrections

| Mechanism | Exact source finding | Evidence boundary |
|---|---|---|
| SignalLoop | `run.py` calls `build_signal_loop()`; the factory itself calls `loop.start()`. The earlier table's "no explicit .start() at this call site" is true but its implication that running state is unresolved from source is incomplete. | Thread-start attempt established; successful tick/output and consumers need separate tracing. |
| DiversityLoop | `run.py` calls builder then `.start()`; the loop runs groove detection, dormancy scan and clock tick, with 60-second wait. | Thread-start attempt established. |
| EdgeGeneratorLoop | Builder constructs and returns the object; `run.py` calls `.start()`, which creates the daemon thread. The loop has a 60-second boot delay and 30-minute tick; it reads unedged Fountain/synergized beliefs and may persist proposed belief edges. | Start and source read/write path established; live output UNKNOWN. |
| Reshape/HoldingZone resolver | `run.py` constructs the resolver, attaches gate/transformer and calls `start_loop()`. | Start attempt established; actual held-row resolutions not established. |
| ThrowNet | TriggerDetector is constructed and receives gate/gap-related telemetry. TimeFetch, RefinementEngine and ThrowNetEngine are constructed; ThrowNetMonitor loop starts only with `NEX5_THROWNET=1`, otherwise the source explicitly leaves the autonomous monitor stopped. | Trigger observation and autonomous processing must not be conflated. |
| CounterfactualNode | Constructed in a guarded block and `start_loop()` called when construction succeeds. Its `_maybe_promote()` currently returns immediately; auto-promotion is explicitly disabled. | Loop-start attempt does not imply the disabled promotion path runs. |
| NovelAssociation | Constructed, `start_loop()` called and registry registration attempted in a guarded block. | Start attempt established; association writes/consumers need separate trace. |
| SubstrateHarmonic / GeniusTagger | Both constructed and their `start_loop()` methods called; boot comments classify their outputs as log-only. | Loop-start attempt and table writes do not establish downstream decision use. |
| DriveEmergence / AffectState / PredictiveSubstrate / SelfMindView | Each is constructed and its `start_loop()` is called in a guarded boot block; these are not merely importable modules. | Source-defined start attempts; exact writes, readers and prompt consumers require faculty-specific trace. |
| WarrantRecorder | `start_loop()` is called only when `NEX5_WARRANT_RECORD=1`. | Default source path off. |
| PersonaResponder / WorldPredictionLoop / SelfPredictionLoop / SelfMaintainShadow | Start calls are explicitly environment-gated (`NEX5_PERSONA_RESPONDER`, `NEX5_WORLD_PRED`, `NEX5_SELF_PRED`, `NEX5_SELF_MAINTAIN_SHADOW`). | Runtime flag values UNKNOWN. |
| SpeechQueueConsumer | Started only if parsed `SpeechConfig.enabled`; the normal boot path passes a VoiceState and preloaded backend. | Config-dependent; host value and actual playback UNKNOWN. |
| ArcLoop / SocialPresence / GrooveBreaker | Current boot path explicitly leaves ArcLoop and SocialPresence unset; GrooveBreaker wiring is removed and its module-level ENABLED constant is documented as false. | Source-disabled, not "active but unobserved". |

### Corrected SignalLoop factory evidence

`theory_x/signals/loop.py::build_signal_loop()` constructs SignalLoop, calls `loop.start()`, and returns it. The SignalLoop tick reads sense/belief data, invokes detectors, writes emitted signal rows and may write matched patterns. This confirms that the run.py factory call initiates the loop, unlike a factory that only returns a dormant object. Source hash: `6453c1ca9ac3ef1ffc8d84b46de87c3c6b3f981e`.

### What this pass does not close

This is a boot-level inventory correction, not the full M0.3–M0.4 forward audit. For each started faculty, the remaining work is to identify exact trigger, data reads, transformation, writes/events, failure behaviour, and each downstream reader/decision/prompt sink; then verify whether the backward Chat/Fountain/belief-write map captures it. Source presence and thread-start calls remain [L1] evidence. Host activation, successful emission and operational consumption are not upgraded without trace evidence.

No runtime code, schema, flags, scheduler policy, host, experiment, merge or deployment was changed.


## 3.24 Stage 2 life-loop source-to-sink expansion (23 Nov 2026)

At branch revision `07f6ebe42a1ac99a8038a73476782d1542704296`, the Stage 2 factory was inspected beyond its nine core loops. It also assembles and starts witness, pattern, identity, affinity, scorecard, surprise, remember, wonder, fetch, daily-life, sustained-focus, signal-to-problem, diversity edge-builder, gate-retention and available Moltbook loops.

| Producer | Source output | Next identified consumer / boundary |
|---|---|---|
| IdentityLoop | `identity_log` and Tier-6 `identity_loop` belief | PatternLoop reads identity statements; Fountain has a separate identity-context read. |
| PatternLoop | `pattern_log` and Tier-6 `pattern_loop` belief | WitnessLoop reads pattern statements. |
| WitnessLoop | `witness_log` and Tier-6 `witness_loop` belief | Subsequent retrieval is possible subject to normal belief filters; live selection is UNKNOWN. |
| Remember/Wonder/Fetch | Tier-6 beliefs generated from old+recent beliefs, recent sense entities, or URL-backed feed content | General belief candidate pool, subject to query and retrieval filters. |
| SurpriseLoop | Tier-6 belief from unpromoted surprise events; qualifying large surprise can signal current focus | Belief retrieval; FocusLoop's current-focus path requires a separate event/condition trace. |
| ScorecardLoop | Refreshes fixed-source Tier-1 locked market self-belief through `ground_self_belief.refresh_self_belief()` | Eligible for belief retrieval; actual selection is query-dependent. |
| AffinityLoop | Updates `beliefs.affinity` | Inspected BeliefRetriever and VoiceEngine scoring paths do not read this field; no consumer identified in this bounded pass. |
| SignalToProblem | Reads unactioned `signals`; marks them actioned and inserts `open_problems` | FocusLoop reads open problems and writes `current_focus`; this establishes a source-defined signal → problem → focus chain. |
| FocusLoop | Reads open problems, belief overlap, Fountain thoughts and chat activity | Upserts `current_focus`, updates problem observations/state, and may write a NEX chat message when stuck. |
| Diversity EdgeBuilder | Reads belief content/edge counts and embedding similarity | Inserts `belief_edges`; BeliefRetriever reads edges and blends spreading activation (60/40 in the inspected implementation). |
| Gate retention | Reads age-bounded `gate_decisions` / `throw_net_sessions` | Deletes old rows in bounded batches; maintenance, not an identified prompt selector. |
| DailyLife | Reads clock, sense, belief, focus, problem and external interaction state | Writes `daily_activities` and conversation sessions/messages. User delivery and later Chat read path remain to be traced. |

**Recursive self-observation chain:** IdentityLoop → PatternLoop → WitnessLoop is source-supported by table reads/writes, with belief rows also written by each level. This is a constructed feedback pathway, not proof of autonomous successful ticks or improved self-understanding.

**Retrieval boundary:** the inspected BeliefRetriever candidate pool admits tier ≤6 beliefs when unpaused and locked or confidence ≥0.15, then applies query relevance and optional edge-based spreading activation. Thus a Tier-6 belief write or Tier-1 locked self-belief can become eligible, but row creation alone does not prove selection, prompt injection or model reliance.

**Affinity boundary:** the inspected retrieval score and VoiceEngine score do not consume `beliefs.affinity`. Do not claim affinity updates change those ranking paths without identifying another consumer.

**Scorecard boundary:** ScorecardLoop refreshes the fixed-source market-prediction self-belief from the scorecard; it is not itself a new prediction experiment. The refreshed belief's prompt use remains query-dependent.

Source hashes and per-loop read/write detail are recorded in the Reality Report's M0.3–M0.4 continuation addendum. This expands the forward map but does not close the full faculty audit or the backward map. No runtime behaviour, schema, loop interval, feature flag, retention policy or deployment was changed.


## 3.25 Stage 3 WorldModel feedback and retrieval closure (23 Nov 2026)

At source revision `07f6ebe42a1ac99a8038a73476782d1542704296`, `build_world_model()` starts six daemon loops: decay (hourly), harmonizer (every two hours), cross-domain detection (every six hours), erosion (every six hours), synergizer (60-second wake with 5-minute cooldown and 25-minute timer trigger), and world consolidation (environment-gated).

| Mechanism | Source write / state change | Identified consumer |
|---|---|---|
| Promotion/decay | Changes belief tier and corroboration metadata | BeliefRetriever limits its candidate pool to tier ≤6; tier changes affect later eligibility. |
| Harmonizer | Pauses/unpauses contradictory beliefs; writes harmonizer events, held tensions and belief edges | Retriever filters paused beliefs; ActivationEngine reads belief edges; separate Chat/Fountain prompt paths can read held-tension summaries. |
| Cross-domain detection | Adds cross-domain belief edges | ActivationEngine reads edges; retrieval blends normalized keyword and activation scores 0.4/0.6 when activation exists. |
| Erosion | Retrieval calls `record_use()`; periodic erosion advances `erosion_stage` and resets reinforcement counters | Usage/erosion feedback is source-defined. Base retrieval SQL does not filter `erosion_stage`; no direct candidate exclusion claim is made. |
| Synergizer | May insert synthesized beliefs and `synergizer_log` rows | Later belief retrieval can consider the inserted belief under ordinary eligibility/query filters. |
| World consolidation | Clusters Tier-7 world beliefs; may corroborate/promote bounded items | Thread exits if `NEX5_WORLD_CONSOLIDATE` is empty; `dry/report/test` is report-only and `1/on/true/yes` arms. Promoted tier may affect later retrieval eligibility. |

**Retrieval closure:** eligible beliefs are selected by tier, pause and lock/confidence conditions; keyword and optional semantic candidates are ranked; the top five keyword candidates seed ActivationEngine; edges contribute spreading activation; the normalized keyword/activation scores are blended; selected results then call `ProvenanceErosion.record_use()`. Thus edge creation can influence a later retrieval ranking in source, and selected retrieval results feed later use/erosion state. A particular edge changing a particular Chat/Fountain selection and response has not been demonstrated by a live ID-linked trace.

**Evidence boundary:** this establishes source-defined write/read relationships, not successful host ticks, actual edge creation, tier changes, candidate selection or model reliance. The WorldConsolidation thread is not unconditionally active; its environment gate and dry/armed modes must remain explicit.

Per-module hashes and detailed source observations are recorded in the Reality Report. No runtime, schema, scoring, edge, tier, erosion, flag or deployment change was made.


## 3.26 Stages 4–10 — boot wiring and Chat consumer verification (23 Nov 2026)

At source revision `07f6ebe42a1ac99a8038a73476782d1542704296`, the following source-level paths were checked against `run.py` and `gui/server.py::api_chat`:

- **Stage 4 Membrane:** `build_membrane()` constructs classifier, SelfModel, QueryRouter and BehaviouralSelfModel; with the normal conversations Reader it starts the behavioural loop. Chat's membrane route is separate from the INSIDE-only BehaviouralSelfModel prompt append. The latter is not a universal Chat context block.
- **Stage 5 SelfLocation:** boot calls `SelfLocationCommitment.commit()` once; it inserts-or-ignores the fixed-source locked Tier-1 belief and reads its ID back. It is eligible for retrieval but not necessarily selected.
- **Stage 7 ProblemMemory:** constructed as a service object, not started as an autonomous loop. Chat calls `find_matching()` and `format_for_prompt()`; VoiceEngine TimeFetch also calls `find_matching()`; Fountain receives the object for task-bearing context.
- **Stage 8 GoalManager:** constructed, registered and exposed through the goal API. Chat calls `get_active()` for logging, but a handler comment explicitly states goal text is no longer appended to the Chat prompt. It is not a current Chat prompt contributor.
- **Stage 9 Metacognition:** constructed/registered without a `run.py` daemon loop; Chat calls `tick()` and `format_for_prompt()` per request and may append the result. Fountain has a separate flag-gated insertion.
- **Stage 10 NovelAssociation:** constructed and its loop is started; Chat calls `format_for_prompt()` and may append non-empty association text, marking it annotated.
- **SelfNarrative:** constructed/registered early and passed as a write-trigger target to CoherenceGate, ProblemMemory and NovelAssociation; Chat calls topic-conditioned `format_for_prompt()` and may append entries.
- **AffectState / DriveEmergence / SelfMindView:** each has a boot-time loop start attempt; Chat may append their DB-backed prompt summaries. VoiceEngine separately receives DriveEmergence for drive-topic embedding alignment.

The source-defined Chat prompt append paths are distinct and conditional: BehaviouralSelfModel (INSIDE only), ProblemMemory (matching query), Metacognition, NovelAssociation, SelfNarrative, AffectState, DriveEmergence and SelfMindView. These are upstream contributors to `belief_text`, not proof of model reliance. The current trace's aggregate context digest does not identify every selected row. Direct VoiceEngine-hit responses can bypass model composition.

**Correction:** GoalManager should not be described as a Chat prompt contributor in the current source. Its active goal is checked/logged, while the text append was removed.

Detailed source hashes and boundaries are in the Reality Report addendum. This section establishes source-level construction/call paths only; host execution, prompt payloads on a live request, and downstream model reliance remain unobserved. No runtime or prompt behaviour was changed.


## 3.27 Fountain prompt, selection feedback and alternate-output branches (23 Nov 2026)

A deeper read of `theory_x/stage6_fountain/generator.py` expands the earlier Fountain pathway. The generator has multiple early returns and non-LLM alternatives; it must not be represented as one uniform "prompt → LLM → crystallizer" path.

### Prompt and selection feedback

- `NEX5_GLOBAL_WORKSPACE` defaults to enabled in source. A non-empty arbitration result is prepended to the DRIFT focus block. It is deliberately not carried into wide EXPLAIN/ARGUE mode unless `NEX5_WIDE_FOCUS=1`.
- `recursive_self.format_for_prompt()` is called without an environment gate; a non-empty line is appended to the focus block. Its separate perturbation state is sampled for `recursion_attrib`; that attribution write is not itself proof of selection change.
- `NEX5_MOMENTUM` defaults to enabled. After a normal fire, `capture_momentum()` stores a thought fragment and carry branch. The next `_curiosity_pick()` reads the persisted momentum row and uses its unfinished-thread/carry-count state in candidate scoring. `NEX5_CARRYOVER=1` additionally stamps whether the previous fire crystallized. This is a source-defined cross-fire selection feedback path.
- The generator directly reads the latest `identity_log` statement, latest `self_downtime` belief, recent `surprise` belief (six-hour window), random inward/outward `spectrum` beliefs, and affinity-selected favourites. These are prompt contributors independent of the optional `NEX5_IDENTITY_BLOCK` feature.
- **Affinity correction:** the inspected BeliefRetriever and VoiceEngine scoring paths do not read `beliefs.affinity`, but Fountain does: it selects up to ten beliefs with affinity > 0.40 and randomly appends up to two. AffinityLoop therefore has a source-confirmed Fountain prompt consumer. The affinity self-rating remains unvalidated; the module itself documents anchor-copying behaviour in its prior rating test. This is prompt consumption, not validation of preference quality.
- `NEX5_METACOG_VOICE`, `NEX5_MOOD`, `NEX5_AMOHA`, `NEX5_AFFLICTIONS`, `NEX5_L4_STAKES` and `NEX5_WIDE_FOCUS` gate distinct optional faculty lines. Their source presence does not establish host activation.
- `NEX5_HOT_OBSERVER=1` gates post-fire meta-belief writing. Those beliefs can later enter retrieval; actual downstream selection is not established here.
- `NEX5_SELF_NARRATIVE=1` enables a separate Stage-TOM SelfNarrative instance in the Fountain generator; it is not the same object as the Stage 26 `stage_self_narrative.SelfNarrative` constructed by `run.py`. Its Fountain prompt block is additionally flag-gated.

### Alternate and early-return branches

1. **SubstrateVoice:** before normal prompt construction, the generator may return a Tier-1/2 anchor verbatim when groove/cooldown/anchor conditions hold and `NEX5_RECONCILE != 1`. A source comment says the deployment has `NEX5_RECONCILE=1`; actual host environment has not been observed, so live activation is UNKNOWN.
2. **Quiescent:** every fifth counter cycle, a bare external sense item (or tick fallback) is written as a Fountain event and returned before normal LLM composition/crystallization.
3. **Stillness:** duplicate own-slot retrieval can write an empty-thought Fountain event and stillness row, then return without generated content; after three consecutive stillness events the next cycle is forced with a quiet notice.
4. **Substrate Emit:** `NEX5_SUBSTRATE_EMIT=1` can render top activated substrate beliefs directly instead of the LLM thought.
5. **Reconcile Emit:** `NEX5_RECONCILE=1` can compose a joint-progress prompt from open problems. This is a distinct prompt path.
6. **Frame retry:** `NEX5_FRAME_GATE=1` can trigger one regeneration attempt after the register-template detector trips.
7. **Parallel substrate fire:** every fifth main-path fire according to the post-increment counter condition can persist a separate rendered substrate output in `substrate_fires`; it is not the same as replacing the main Fountain output.

### Observer/persistence boundaries

- `emphasis_log`, `fountain_retrieval_log` and `fountain_prompt_blocks` are written after the thought/event is already produced; they are not upstream causes of that same fire.
- `fountain_retrieval_log` is normally dropped/recreated at startup, except for its conditional legacy-FK migration branch. It records only selected retrieval slots and is used within the process for recent retrieval-duplicate detection.
- `fountain_prompt_blocks` persists with 30-day pruning and stores block identity/hash/length/bounded prefix. No runtime reader was identified in this pass. It is useful retrospective shape evidence, not a complete contributor graph or proof of model reliance.

**Correction to Section 3.24 / Reality Report:** Affinity's downstream consumer is not globally absent. It is absent from the inspected retriever/VoiceEngine score calculations but present in Fountain prompt assembly as described above.

**Evidence boundary:** source-level control flow only. Host flag values, actual branch frequency, live prompt block composition, selected candidate IDs on a live fire, model reliance and physical output remain UNKNOWN. Detailed source evidence is recorded in the Reality Report. No behaviour, prompt, flag, selection policy, schema or deployment change was made.


## 3.28 Predictive, counterfactual and optional faculty wiring (23 Nov 2026)

Additional boot-managed paths were checked against `run.py`, their implementations and Chat consumers:

- **PredictiveSubstrate:** constructed and loop-started during boot when initialization succeeds; 300-second cadence. It predicts internal-belief regions from beliefs/open problems/drive and external-input regions from external sense events/user messages. Later verification writes `surprise_events`; Stage 2 SurpriseLoop can turn unpromoted events into Tier-6 beliefs, and Fountain reads recent surprise beliefs. Empty target windows are scored as surprise 1.0 with no actual content.
- **CounterfactualNode:** loop-started during boot when dependencies exist; 300-second cadence. It processes one oldest-touched open problem, obtains TimeFetch candidates, scores them with RefinementEngine, submits buildable candidates to CoherenceGate and inserts ACCEPT candidates as Tier-3 `counterfactual_node` beliefs. The subsequent review_queue auto-promotion is disabled by immediate return in `_maybe_promote()`; the belief-insertion path remains.
- **Throw-Net:** TriggerDetector/engine are constructed when dependencies exist; detector can record gate-reject and gap-deflection triggers. ThrowNetMonitor's periodic consumer starts only with `NEX5_THROWNET=1`; default is off. Trigger logging must not be described as active Throw-Net processing.
- **Chat provenance:** only active when `NEX5_PROVENANCE=1` and the session is admin-scoped. It snapshots pre-turn retrieved beliefs (or recency fallback), focus, latest Fountain thought and affect; after the reply it computes mirror/copy metrics. A mirror-dominant cue can cause one retry, kept only if the mirror score falls. It is not purely a log-only observer when armed. The grounding hint is explicitly unproven; there is no self-grounded verdict.
- **WorldPredictionLoop:** starts only with `NEX5_WORLD_PRED=1`; its scorecard output is read by ScorecardLoop for the fixed-source self-belief.
- **SelfPredictionLoop:** starts only with `NEX5_SELF_PRED=1`; self/authored/self-description predictions are recorded, but its threshold adaptation is explicitly a monitor and is not wired to the live fire gate. Owned-belief/commitment/reconciler paths have separate flags.
- **SelfMaintainShadow:** optional `NEX5_SELF_MAINTAIN_SHADOW=1`; writes hypothetical regulator metrics only. Module says it changes no beliefs and its table has no reader.
- **WarrantRecorder:** optional `NEX5_WARRANT_RECORD=1`; records survival/use evidence in side tables and is not a thought/retrieval/output selector.
- **PersonaResponder:** optional `NEX5_PERSONA_RESPONDER=1`; generates an external-interlocutor response and writes external-other-mind sense events. Fountain's SOCIAL input has a separate read gate.
- **SocialPresence:** boot explicitly sets the AppState object to None and passes None into Metacognition; module snapshot table has no external reader in inspected source.
- **Finitude BudgetShadow:** module source explicitly states it is not imported by `gui/server.py` or `selector.py`; not in the inspected live path.

These distinctions are source-level activation and consumer paths, not host-state observations. Optional environment values, successful ticks, writes, and model reliance remain UNKNOWN unless a runtime trace proves them. Per-file hashes are recorded in the Reality Report. No runtime or schema changes were made.



## 3.29 Cross-path feedback, annotation and analytical consumers (23 Nov 2026)

This section extends the Stage 1–10 map across the shared annotation, coincidence, affect and drive pathways. It records actual source edges, not assumed cognitive effects.

| Origin / producer | Intermediate state | Verified consumer / sink | Boundary |
|---|---|---|---|
| Fountain event → operator coin/maybe/non annotation | fountain_events.tag; word_contexts.fountain_tag; coincidence_context snapshot | GUI coincidence analytics; conditional Chat and Fountain tag retrieval; conditional IdentityLoop tag-count clause | Retrieval and identity feedback require NEX_TAG_FEEDBACK_ON=1. Tag queries are global over the shared Fountain corpus, not session-keyed. |
| Fountain event → coincidence decoder | word_contexts rows containing unique tokens and time/substrate context | GUI recent-fire ticker, top-word view, word fingerprint and tag aggregates | run.py starts the decoder loop at boot; no prompt/selector consumer of word_contexts was identified in this pass. |
| AffectState background tick | affect_state current row; append-only affect_history | Chat current-affect prompt block; CompetingDrives affect-variance calculation → Fountain tension block | AffectState starts at boot when construction succeeds. NEX5_EXPECT_MOOD is an additional optional event_valence input, not the default mood source. |
| AffectCarry Chat request | per-session conversations.db carry weight | admin-scoped Chat tone-colouring block | On-demand only; requires NEX5_AFFECT_CARRY=1. Separate from AffectState. |
| DriveEmergence background tick | drives row and drive_emergence_log | Chat drive prompt; Fountain workspace candidate and separately appended drive block; VoiceEngine scoring alignment | Drive is a direct prompt contributor even when it does not win workspace arbitration. |
| GlobalWorkspace candidate survey | one selected framing line | Fountain focus_block prefix | Fountain default source gate is enabled unless NEX5_GLOBAL_WORKSPACE is explicitly not 1. It is not a global broadcast to every faculty. |
| CoherenceGate evaluation | GateDecision + gate_decisions row | Calling producer path; reject may feed TriggerDetector; hold/reshape may feed holding zone | Internal exceptions are converted to ACCEPT/gate_error_fallback. This is a fail-open exception branch. |

### Annotation and decoder sequence

1. A Fountain thought is persisted as a fountain_events row.
2. The boot-managed decoder polls Fountain events every 30 seconds, tokenizes eligible thoughts and writes word_contexts. It is a retrospective analytical path and advances its cursor even when an event yields no tokens.
3. The coincidence tag endpoint can update the Fountain event tag, propagate it to existing word_contexts rows, capture a coincidence_context snapshot and attempt hypothesis auto-scoring.
4. With NEX_TAG_FEEDBACK_ON=1, the shared tag corpus can be reintroduced into a later Chat voice prompt (summary plus keyword matches), sampled into a later Fountain prompt (25% random branch), and counted in a later IdentityLoop self-description.
5. Rich tag retrieval reads coincidence_context for aperture, branch and fire-count annotations. It does not derive those annotations from word_contexts.

This closes a previously under-described human-annotation feedback edge. It does not establish that the tag feature is active on the deployed host, that labels are accurate, or that a model relies on them.

### Workspace and drive qualification

- Fountain's GlobalWorkspace arbitration considers surprise, momentum, bonsai, stakes and drive candidates and prepends the highest-salience framing line to focus_block. The source comment's use of “broadcast” describes the prompt framing metaphor; the observed consumer is the Fountain prompt.
- The same DriveEmergence line is also appended independently after the workspace line. Arbitration therefore does not select whether the drive block is present; it selects the leading frame. Depending on the winning candidate, the drive can be represented in both places.
- Chat's NEX5_CHAT_WORKSPACE path is a separate budgeted selector over Chat faculty blocks. Its exempt blocks are never evicted, so the configured character budget is not a strict maximum if exempt blocks alone exceed it.

### Affect and expectations qualification

- AffectState reads high-tier belief text for lexical polarity, belief creation rate for arousal, flagged surprise events for a further arousal bump, and stability inputs; it writes both affect_state and affect_history. Chat consumes the current row; CompetingDrives consumes the history.
- When NEX5_EXPECT_MOOD is enabled and the eligibility gate passes, AffectState may add a capped nudge from event_valence. The expectations module implements ingest/reconcile, and commitments implements scan/evidence, but no direct invocation of expectations.reconcile() or commitments.scan() was found in the inspected run.py boot wiring or gui/server.py request path. External/manual invocation remains possible and unverified; do not infer a live event_valence feedback loop from module presence alone.
- AffectCarry is an admin-scoped, per-session request-time tone mechanism. It is not the same state store, cadence or consumer path as AffectState.

### Gate exception semantics

CoherenceGate.check() documents that it never raises and implements this by converting an internal exception to ACCEPT with reason gate_error_fallback before logging the decision. The exception branch is therefore fail-open. This is a source-level property; exception frequency, actual exposure and acceptance criteria are unknown. It should be considered in any future universal-gate claim, but no behaviour change is proposed in Phase 0.

### Source revision

This section was checked against the PR #49 source revision preceding the documentation-only commits that add this section. Source hashes are listed in the matching M0.3–M0.4 extension in NEX_REPOSITORY_REALITY_REPORT.md. No runtime or test behaviour, schema, flag, host state, experiment, merge or deployment was changed.



## 3.30 Active Diversity ecology, reanimation and retention reconciliation (23 Nov 2026)

| Mechanism | Producer / cadence | Consumer / sink | Qualification |
|---|---|---|---|
| GrooveSpotter | Active DiversityLoop thread calls detect_all() every 60s; writes groove_alerts and signal_cooldown | Fountain curiosity candidate scoring reads active cooldown content; Fountain feedback/selection paths read recent groove_alerts | Genuine selection feedback path. Curiosity re-ranks the candidate set rather than dropping candidates. |
| DormancyScanner | Active DiversityLoop thread scans incrementally every 60s and again in ClockRunner's fast path; writes dormant_beliefs | ClockRunner wake_one() marks one candidate and sets pending state; Fountain pop_reanimated() can inject the belief into later context | Source comments define nominal 20-fire reanimation, accelerated to 5 during a low-striking-rate trough. Actual cadence depends on 60s polling and fire bursts. |
| Rut mirror | Fountain's low-striking-rate governor can write a Tier-6 self_rut_notice, throttled to once per two hours | Belief enters the substrate and can later be retrieved by normal belief paths | A state write, not merely diagnostic logging. |
| Boost decay | ClockRunner fast pass calls apply_decay() | Fountain own-belief retrieval LEFT JOINs belief_boost and applies a bounded recency bonus | Decay consumer/selection path is verified; current producer of new boost rows is not established in the inspected active loop. |
| CrossbreedGrader | Constructed by DiversityLoop; grade() writes collision_grades | ClockRunner summaries/evolver and diversity panel read collision_grades | DiversityLoop._run() never calls self.grader.grade(). The active production producer is not established by this loop; other callers are not globally excluded. |
| Three clocks | ClockRunner thresholds 20/200/2000 fire-count increments; polled by DiversityLoop every 60s | Fast: boost decay/dormancy/reanimation; medium: groove/collision summaries; slow: GraderEvolver | Thresholds are nominal and may coalesce under bursts because each poll runs a given clock at most once. |
| Residue | Fountain saves unselected oversampled own-belief candidates and pops up to two previous rows on later cycles | Residue beliefs are fetched and prepended to the next context candidate set | Live cross-fire context path. |
| ArcLoop | run.py sets arc_loop=None; the background loop is disabled | Warrant/recorder code can read arc_members if present | Do not infer active arc formation from schema or read paths. |

### Important details

- Fountain calls notify_fire() after a completed output, incrementing a process-local counter observed by DiversityLoop. The active loop calls GrooveSpotter, DormancyScanner and ClockRunner; it constructs CrossbreedGrader but does not call its grade() method in the active loop body.
- wake_one() writes reanimated_at and sets a module-level pending candidate. Fountain's later pop_reanimated() call is the observed hand-off. ClockRunner also retains a per-instance copy and exposes get_reanimated_belief(), but no consumer of that getter was identified in this path.
- The governor's low-striking-rate branch changes the reanimation cadence and can write a first-person self_rut_notice belief. This is a source-level adaptive feedback edge, not proof that the belief changes subsequent decisions.
- belief_boost is read by Fountain retrieval and decayed by the fast clock. The inspected active loop does not call apply_boost(); a current production producer for new boosts remains unresolved.
- Groove alerts and cooldown rows are not passive logs: Fountain reads them while scoring or shaping later candidate selection. The candidate selector's source comment says it re-ranks rather than drops the candidate set.

### Residue retention correction

The module docstring in theory_x/diversity/residue.py says unconsumed residue is absent from nex_db_reaper TARGETS and never ages out. That is contradicted by the inspected nex_db_reaper.py revision, whose TARGETS explicitly includes beliefs.db.residue with a two-day created_at retention. residue.py's local cleanup only deletes consumed rows older than seven days; the separate reaper supplies the shorter all-row TTL. The repository also contains a systemd service/timer describing a nightly run, but deployed installation/enabled state is UNKNOWN. This is a documentation discrepancy, not a basis for changing retention or deleting data.

### Evidence boundary

The exact source hashes are listed in the matching M0.3–M0.4 section of NEX_REPOSITORY_REALITY_REPORT.md. Findings are source-level only. No runtime/test behaviour, schema, data, retention policy, flags, host state, experiment, merge or deployment was changed.



## 3.31 Optional Chat affect and operator prompt faculties (23 Nov 2026)

These mechanisms are not numbered boot loops. The inspected Chat handler calls them on the voice-composition path only, and each call requires both its own flag and an admin session. They produce prompt blocks; no routing or belief-selection change is established by these blocks.

| Faculty | Inputs / state read | Output / downstream effect | Boundary |
|---|---|---|---|
| OperatorModel | Configured operator-intake document | Formatted operator-read block in Chat prompt | NEX5_OPERATOR_MODEL=1 + admin. Missing/unreadable file yields empty block. |
| OperatorAnchor | No external state; constant addressee instruction | Direct second-person address instruction in Chat prompt | NEX5_OPERATOR_ANCHOR=1 + admin. |
| Compassion | Current message embedding against distress anchors; persistent compassion_state | Care/non-harm stance in Chat prompt; advances single-row compassion state | NEX5_COMPASSION=1 + admin. State row is global id=1, not session-keyed. NEX5_COMPASSION_V2 separately gates the alternate anchor handling. |
| Compass | Current-message distress, Amoha detector, self_binding._cluster_reads() affliction signals | Held-open moral weighing in Chat prompt | NEX5_COMPASS=1 + admin; prompt-only, not a rule verdict. |
| Equanimity | Raga, Dvesa and Compassion distress read | Hold-steady cue when a pull is hot and Compassion is not live | NEX5_EQUANIMITY=1 + admin. |
| Apramada | Global momentum carry and open ProblemMemory items | Vigilance cue when the current turn risks dropping a held thread | NEX5_APRAMADA=1 + admin. |
| Virya | Current focus/open problem and recent Fountain thoughts; yields to full Equanimity | Re-engagement cue when recent thought has drifted from a hard thread | NEX5_VIRYA=1 + admin. |
| Sraddha | Prompt-relevant live Tier-6/7 beliefs, confidence, corroboration and edge degree | Supported-belief confidence cue | NEX5_SRADDHA=1 + admin. Does not read belief_warrant. |
| Prasrabdhi | Raga plus Virya's focus/drift read | Let-it-move cue when circling is off-focus | NEX5_PRASRABDHI=1 + admin. |

### Cross-faculty qualifications

- Compassion is stateful: its stance call advances and persists a single conversations.db compassion_state row. Unlike AffectCarry, that state is not keyed by session_id. The source boundary is global across admin sessions; actual multi-admin concurrency is unknown.
- Compass calls private helper self_binding._cluster_reads() and uses the affliction thresholds, but this does not mean the SelfBinding script or self_state history process is running.
- Equanimity suppresses its stance when Compassion distress is live. Virya yields when Equanimity is FULL. Prasrabdhi checks the same focus/drift evidence and is intended to nudge only off-focus circling. These are source-defined precedence relationships.
- Sraddha is separate from the belief_warrant score. It selects relevant live Tier-6/7 beliefs and scores support using confidence, corroboration and graph degree; no belief_warrant read is part of this prompt path.
- FountainGenerator contains no import or flag reference for these Chat-specific modules in the inspected source revision. Do not infer that the blocks are shared with Fountain.
- NEX5_CHAT_WORKSPACE is a separate optional selector over the assembled Chat blocks. Source comments mark it default OFF; its exempt blocks can exceed the nominal character budget.

The full per-file hashes and source notes are in the corresponding Reality Report section. Host flags, operator document presence, concurrent admin use, prompt contents and model reliance remain UNKNOWN. No runtime or test behaviour was changed.



## 3.32 Reshape outcome accounting and warrant activation boundary (23 Nov 2026)

| Mechanism | Verified producer / operation | Consumer / result | Evidence boundary |
|---|---|---|---|
| Holding-zone reshape | Resolver transforms up to ten reshape_pending rows and calls CoherenceGate.check(new_packet) | Original held row receives terminal "reshaped" status and transformed preview | Returned GateDecision is discarded. If gate.check raises, exception is logged but original row is still marked "reshaped". Thus status means attempted transformed resubmission, not verified gate acceptance. |
| Warrant evidence recording | WarrantRecorder, gated by NEX5_WARRANT_RECORD=1, appends belief_survival and accumulates belief_use_day / belief_use_days | Raw survival/use evidence for later warrant computation | run.py wires the recorder, not the separate WarrantPass. |
| Warrant score computation | WarrantPass.run_once() calls compute_all() and persist() | belief_warrant side table | WarrantPass is described as NEX5_WARRANT-gated in its module, but no construction/start was found in inspected run.py, gui/server.py or Stage 2 dynamic startup. Normal activation is unestablished; manual/other callers not globally excluded. |

### Reshape semantics

Do not equate "reshaped" with "accepted". The resolver calls the gate, but ignores its returned outcome. A REJECT/HOLD/RESHAPE result is not reflected in the original row's resolution status, and an exception still leads to "reshaped". This is an outcome-accounting gap; the transformed content is still submitted to the gate, so it is not evidence of a gate bypass. Whether the status label is intentionally defined as "transformed and resubmitted" must be checked against the authoritative spec.

### Warrant evidence completeness

WarrantRecorder's Fountain retrieval/event and synergizer cursors use monotonic row IDs. Its lineage and arc-membership cursors use timestamp-only cursors with strict greater-than reads. If a capped batch splits rows sharing one timestamp, the remaining same-timestamp rows can be skipped after the cursor advances. This is a conditional source-level risk; no incidence is claimed. A future test should create more tied-timestamp rows than one batch and verify no evidence loss, but no test or runtime change was made in this phase.

The Reality Report contains exact source hashes and the detailed activation/wiring evidence. No runtime/test behaviour, schema, data, flags, host state, experiment, merge or deployment was changed.



### Existing regression-test coverage

The inspected test files do not currently close the two identified edges:

- tests/test_reshape.py verifies normal resubmission and transformer failure, but not gate.check() raising during resolver resubmission or the original held row's status for non-ACCEPT gate outcomes.
- tests/test_warrant_recorder.py does not cover timestamp ties across a capped lineage/arc cursor page.
- tests/test_warrant.py verifies the disabled WarrantPass loop is inert, but does not verify enabled startup wiring from run.py.

These are coverage gaps only. The source review did not execute or alter the tests. Exact test-file hashes are recorded in the matching Reality Report section.



## 3.33 Recursive self-binding and quality-signal reach (23 Nov 2026)

| Path | Producer / source | Consumer / effect | Qualification |
|---|---|---|---|
| Recursive self-reading | FountainGenerator calls recursive_self.format_for_prompt() during prompt composition; recursive_self.perturbation() calls self_binding.bind() | Bound self-state becomes a possible prompt nudge; generator captures nudge state in recursion_attrib at fire completion | Generator calls perturbation() a second time after format_for_prompt(), so self_binding.bind() writes self_state_history twice per fire in this source path. |
| Recursion attribution | Generator writes nudge_active, current branch, prior branch and movement at fire completion | _fixation_teeth() reads latest branch when NEX5_RETRIEVAL_TEETH=1 | This is an inline generator sampler; recursion_attribution.py's standalone watcher is not the only route. |
| Value drift | value_drift_monitor.check() can write value_drift_log | self_binding.bind() writes self_state.drift | Despite its comment, bind() sets drift="clean" unconditionally and does not read value_drift_log. The monitor is not found in inspected normal boot/fire wiring. |
| Quality synthesis | Optional NEX5_QUALITY_SYNTH loop scores genius_tags by Fountain branch and writes quality_signal.json | Stage 2 attention reads the JSON and computes 1.20/0.82 multipliers | _magnitude_for() returns before applying the multiplier for string and numeric payloads. The multiplier is only reached for other payload types, so its documented effect is narrower than the module description implies. |

### Interpretation boundaries

- The duplicate self_binding writes are confirmed by the call graph and the append to self_state_history; live write volume is unknown. Whether history is meant to count bind invocations or fires is not established.
- Value drift's constant "clean" is a placeholder field, not a measured clean verdict. The separate check may still be run manually or externally.
- Quality synthesis is a genuine feedback edge because attention reads its file. Do not call it log-only. Equally, do not assume its branch multiplier changes ordinary text or numeric feed magnitudes in the current implementation.
- Exact source hashes and the full source-level analysis are in the matching Reality Report section.

No runtime/test behaviour, schema, data, flags, host state, experiment, merge or deployment was changed.


## 3.34 Stage-TOM / Stage-Affect — structured attention, self-observation and readiness

Inspected against PR #65 integrated source head `3d5df48e6539818097b58b6e936059fae946ceca`. All activation flags and live runtime values remain UNKNOWN.

| Mechanism | Actual source path / consumer | Evidence and limits |
|---|---|---|
| Structured present | `gui.server._assemble_chat_blocks` calls `self_present.update` only when Chat workspace and SelfPresent flags are ON; the blended per-session salience vector is passed to `global_workspace.select_within_budget` | Persists vector/winner/turn count to conversations.db. Unit tests cover carry, persistence and helper-level integration; not live-route activation or concurrent multi-session isolation. |
| HOT observer | FountainGenerator calls `hot_observer.observe` under `NEX5_HOT_OBSERVER`; every third eligible fire writes a Tier-3 `hot_observer` belief | SelfNarrative reads the latest such belief; Fountain separately samples recent HOT beliefs for prompt retrieval. Counter is process-local and resets on restart. |
| Self-model aggregation | SelfNarrative calls `aggregate_self_model`; it summarizes recent HOT beliefs when at least five exist in the 24h window | Actual downstream consumer exists; summary is derived from the observer belief corpus and is not an independent validation of self-knowledge. |
| Source identity | `source_identity.py` provides map/census/backfill; `--backfill --apply` writes old belief rows | No caller found in inspected boot/Chat/Fountain entry points. Distinct from automatic source-kind stamping in `substrate/source_kind.py`. |
| Stakes approach | Readiness adds `appraise_approach` bonus under `NEX5_APPROACH` | Separate conditional source path; tests cover it individually. |
| Stakes aversive | Readiness subtracts `appraise_groove` under `NEX5_STAKES` | Comment declares mutual exclusion with approach, but the two independent `if` blocks do not enforce it. Both terms apply if both flags are set; no both-on test was found in `tests/test_stakes_appraisal.py`. |
| Legacy L4 stakes | Fountain checks `stakes_monitor.check_world_contact` every fifth fire under `NEX5_L4_STAKES`; resulting state reaches workspace arbitration and grounding override | Distinct from the readiness `NEX5_STAKES` cost. Do not merge these flags/concepts in reports. |
| AffectState | `run.py` starts its 300s daemon; state persists in conversations.db; Chat formats it into the prompt | Fountain reads valence/arousal for novelty reach only under `NEX5_VALENCE_DRIVE`; optional composed-emotion line uses `NEX5_MOOD`; event-valence nudge uses `NEX5_EXPECT_MOOD`. |
| Optional affect faculties | Admin-scoped Chat blocks: Compassion, Compass, Equanimity, Apramada, Virya, Sraddha, Prasrabdhi, AffectCarry | Compassion and Compass are exempt from Chat workspace eviction; remaining listed blocks compete for budget. Flags are source conditions, not observed runtime values. |
| Conviction | Module documentation records prior Chat regroup/order consumers as removed after measured-null results | No current caller found in inspected boot/Chat/Fountain paths; retained source is not evidence of an active faculty. |

### Conditional finding DRAFT-004 — readiness arm mutual exclusion is not enforced

The source comment in `ReadinessEvaluator.score()` says `NEX5_APPROACH` and `NEX5_STAKES` are mutually exclusive, but the implementation evaluates them in separate `if` statements. If both flags are set, both the positive approach bonus and negative groove cost are applied. `tests/test_stakes_appraisal.py` tests each flag independently and does not cover the combined state. This is a source-confirmed conditional guard gap; live flag values and incidence are UNKNOWN. No behavioural change or severity assignment is made pending the authoritative specification and Gate 0.



## 3.35 MIND_MAP descriptive-only authority boundary

MIND_MAP.yaml declares that it is descriptive only and that no node may gate, score, block or veto an action. The renderer's prior check validated source references and map structure but did not enforce this policy or verify that runtime source remained independent of the map. The CI workflow already invokes the renderer's --check --verify command, so the gap was in the checker rather than workflow wiring.

**DRAFT-005:** this was a source-confirmed CI enforcement gap, not evidence that the live runtime consumed the map. The separate sentience_dag.json is a development-planning DAG and must not be conflated with MIND_MAP or treated as a runtime faculty.

PR #72 adds a static policy check and focused tests. It preserves the existing blocked status modifier while rejecting explicit authority fields, checks the required metadata constraint, and scans NEX runtime roots for imports or direct reads of MIND_MAP.yaml. RDO/Watcher/developer tools remain allowed to consult the map as evidence. Exact-head CI is pending; this is not yet a verified or merged control.



## 3.36 Optional Moltbook — dormant boot path, external side effects and dry-run accounting

The Stage-7 Moltbook package contains a DM listener, outbound post loop, DM responder and one-shot DM seeder. These can approve DMs, publish Fountain beliefs and send replies. The client defaults MOLTBOOK_DRY_RUN to 1, and non-GET requests return a dry-run stub rather than performing HTTP POST.

The consumers currently treat any returned result as success: listener persists approved=1, poster advances the queue and records posted, and responder records sent, even when the client returned the dry-run stub. The one-shot seeder also has a separate dry_run parameter that is not propagated to the client; with the client default dry-run enabled, it can report a send without an external POST.

No construction/start of DMListenLoop, PostLoop or DMResponder was found in the inspected run.py or gui/server.py; the GUI Moltbook route is read-only. The existing optional-Moltbook tests cover schema absence/presence and HUD/daily-life reads, not the external-action loops or dry-run state accounting. Thus this is a conditional source defect in a dormant/optional integration, not evidence of live activity. Credentials, flag values and actual activation remain UNKNOWN. No external network action was made and no runtime correction is applied pending Gate 0 and explicit external-action policy approval.



### Host-log qualification — Moltbook activation and checkout identity (23 Nov 2026)

The supplied host log file `Pasted text(10).txt` records repeated `theory_x.stage7_moltbook` warnings on 16 Nov 2026 between 10:52 and 10:56: the integration was disabled because `/home/rr/.config/moltbook/credentials.json` was missing. At 10:57:13 the supervisor received SIGTERM; the scheduler and decoder stopped and NEX reported a clean STANDBY exit. This means a Moltbook loop was instantiated in the host runtime at that time, despite no loop startup being found in the inspected GitHub PR65 snapshot's `run.py` or `gui/server.py`.

The same log material identifies the runtime data path under `/home/rr/Desktop/Desktop/nex5`, while shell commands refer to the separate audit checkout `/home/rr/Desktop/NEX_AUDIT/Nex_v5.0-main`. It contains no `git status --short`, branch name or `git rev-parse HEAD` for both checkouts. Therefore the active host checkout and the GitHub snapshot used for this audit are **not proven identical**. The 16 Nov missing-credentials observation is historical, not a current credentials/status claim; no successful Moltbook post or DM is evidenced by that log excerpt. Current process/standby state remains UNKNOWN.

This qualifies DRAFT-006: the GitHub snapshot has no inspected startup wiring, but the host log confirms a locally instantiated loop in a potentially divergent checkout. Manus must compare both checkout identities and the current startup path before any activation claim or code correction.



## 3.37 TaggingBeliefWriter and IntakeResonance — default-on belief-write path

The beliefs writer is wrapped in both run.py and gui/server.py. Eligible belief inserts without caller-supplied tags are rewritten with tags from tag_ops.generate(). Before the underlying insert, the wrapper also calls IntakeResonance unless NEX5_INTAKE_RESONANCE_OFF=1. This is a default-on measurement path, not just a passive read: it embeds incoming content, compares it with standing beliefs and writes an intake_resonance_log row containing up to 500 characters of content, score, top-match belief ID and timestamp.

The T6 reserve selection has focused tests; tag injection has tag-protocol tests. No direct test covers resonance logging/retention or a failed underlying belief insert after the probe. init_db.py creates the log table, but the inspected DB reaper does not target it; no cleanup path was found. The incoming belief ID is not part of the log row, so it is not directly linked to the subsequent insert.

NEX_TAG_FEEDBACK_ON is a separate, default-off prompt path that reads user tags from fountain_events.tag; do not confuse it with auto-generated beliefs.tags. This entry maps the actual writer/probe path and leaves retention/cost policy unresolved.

## 3.38 WorldBridge — active prompt injection despite Phase-A-only module docs

WorldBridgeSelector's module/class documentation describes Phase A as select+log only and Phase B as future prompt injection. In the inspected runtime snapshot, run.py constructs and passes the selector unconditionally, selector.py has ENABLED=True, and FountainGenerator calls select_and_log(mark_injected=True), then appends returned stream/body text to the prompt. It can inject up to five events, with 150 characters per event and a 1,500-character total budget. The registered NEX5_BRIDGE flag is not consulted by this path.

This is a source-confirmed documentation/implementation mismatch; whether the implementation is an approved Phase-B change is unresolved because the referenced World Bridge Design v0.2 and approval record were not located. world_bridge_log stores selected-event JSON and injection status. init_db.py creates it; the inspected DB reaper does not target it and no cleanup path was found. Runtime selection frequency and log growth remain unknown.



## 3.39 Phase-0 causal trace sample and verified scope

PR65 exact-head CI passed at `cffbbc94b5a494247d127abf2720886a08f7a567` (run `45273123963`). The resulting metadata/digest-only sample is committed as `NEX_CAUSAL_TRACE_SAMPLE.json` in the evidence branch.

The sample contains a 14-record Fountain cycle and an 11-record Chat turn. Every non-root record has explicit earlier parentage; the Fountain prompt-block-manifest write is linked to the model-input and workspace-selection records. Overlay ON/OFF equivalence passed for the tested outputs, model requests, DB rows and SQL read sequences.

Scope limitations: Chat retrieval returned no belief context; Fountain's speech gate returned HOLD, so no queue/playback/audibility is demonstrated. The artifact is from isolated fixtures, not the live host. A populated-retrieval Chat trace, speech-consumer chain, and live-host capture remain open.



### Host-state timestamp qualification (19 Nov snapshot; current state unknown)

A separate `NEX_R77_diagnostics.txt` snapshot reports `NEX5 is currently OFF` (19 Nov 2026). The 16 Nov runtime log shows a clean SIGTERM/STANDBY transition, followed by keepalive/power-switch supervisor activity. These are historical observations only; they do not establish the process or standby-marker state on 23 Nov. The keepalive/power-switch may control relaunch, so Manus must inspect the current marker, process tree and supervisor before any host-side work.



## Stage World source-to-sink addendum — prediction, calibration and expectation ledger (24 Nov 2026)

Revision basis: PR #65 integrated source head `cffbbc94b5a494247d127abf2720886a08f7a567`.

| Mechanism | Construction / activation | Source-confirmed sink | Evidence level / limit |
|---|---|---|---|
| WorldPredictionLoop | Constructed and started by `run.py` only under `NEX5_WORLD_PRED=1` (default OFF). | Voice direction and random control are persisted in `world_predictions`; resolver stamps outcomes against a later independent price fetch; ScorecardLoop reads the scorecard to refresh its fixed-source self-belief. | [L1] source path plus isolated producer tests; host flag/runtime activity UNKNOWN. |
| SelfPredictionLoop | Constructed and started only under `NEX5_SELF_PRED=1` (default OFF). | Fire/no-fire target; authored-belief count target; self-description novelty target; optional owned-belief expectations, commitment scan and reconciler. | [L1] source path; several producer/reconciler fixture tests exist; integrated loop execution UNKNOWN. |
| Calibration consult | Called after the voice direction is generated and before its prediction row is fully recorded. Reads the fixed-source self-belief and current voice/random scorecards; stamps trust level on the voice row. | Trust metadata is persisted on `world_predictions`; it does not change the current prediction. | [L1]; no dedicated consult test; unavailable-scorecard branch currently records `none` rather than `unknown`. |
| Expectations reconciler | Called from SelfPredictionLoop only under `NEX5_RECONCILER=1` (default OFF). | Headers frozen producer rows, adjudicates due evidence, writes terminal ledger states and event valence; optional learning/mood are separate gates. | [L1]; `tests/test_expectations.py` covers pure math, guardrails, producer/reconciler fixture paths and canaries; no live activation claim. |
| Learning guards | Reconciler records guard ticks; subtraction paths are separately gated by `NEX5_LEARN_RATIO_SUBTRACT` and `NEX5_LEARN_ATTRIBUTION_SUBTRACT`; cap is gated by `NEX5_LEARN_CAP`. | Read-only diagnostics, reversible learning-subtraction records and cap blocks, depending on the specific flag/path. | [L1]; `tests/test_learning_guards.py` covers bounded fixture cases; host flag values UNKNOWN. |

### Crosswalk qualifications

- The SelfPredictionLoop's actual tick is broader than the fire/no-fire startup log: it also resolves/makes `authored_30m` and `selfdesc_novel` rows, then conditionally runs owned-belief, commitments and expectations. Keep these as distinct producers and gates rather than describing the loop as a single fire predictor.
- The market voice/random comparison is not guaranteed to share one baseline/time observation: the voice prompt takes an initial price read, and each subsequent producer insert performs another independent price fetch. Each row receives its own timestamp. A failed second/third fetch can also leave one leg missing while the wrapper returns a non-error dictionary. See DRAFT-009 in the Reality Report.
- Calibration consult distinguishes missing self-belief (`unknown`) from a present self-belief plus unavailable live scorecard (`none`), even though the latter has no fresh evidence for a negative judgement. Its returned level is stamped onto the voice row. See DRAFT-010 in the Reality Report.
- Existing `test_frozen_at_made.py` verifies direct producer persistence and frozen-field immutability, not the generator's paired baseline or partial-pair contract. Self-prediction and expectations have separate fixture coverage; these tests do not prove the environment-gated loops run on the target host.
- No host environment values, network activity, live prediction rows, actual voice calibration, or statistical skill have been measured here. [L1] is not [L2]–[L4].

No source/runtime behaviour, experiment, flags, schema, database or host state changed.


## Predictive surprise consumer qualification — empty-window sentinel (24 Nov 2026)

At PR #65 source head `cffbbc94b5a494247d127abf2720886a08f7a567`, the producer emits an empty-window sentinel as `surprise_score=1.0`, `actual_content=NULL`, `surprise_flag=1`, `big_surprise=1`. Consumers differ:

- Stage 2 `SurpriseLoop` filters out rows without actual content before belief promotion.
- The expectations ledger treats score 1.0 plus absent actual content as `empty_window` and no evidence.
- `surprise_weighting.confidence_for_fire()`, called by FountainCrystallizer under the source-default-enabled `NEX5_SURPRISE_WEIGHT` setting, uses the latest score alone and does not check `actual_content`, `surprise_flag` or `big_surprise`. A recent empty-window sentinel can therefore supply the maximum confidence boost to an unrelated subsequent crystallization. See DRAFT-011 in the Reality Report.

This is a source-level producer/consumer mismatch; the runtime flag value, occurrence and downstream impact are UNKNOWN. The existing producer and ledger tests exercise the sentinel separately, but no test exercises its handling by the confidence consumer. No behaviour or test change was made.


## Fountain emphasis instrumentation — source-to-sink qualification (24 Nov 2026)

`FountainGenerator` constructs `PredictionTracker` and `EmphasisEngine` internally. It scores each candidate thought **before** inserting that thought into `fountain_events`, so the 20-fire novelty window contains prior fires rather than the candidate itself. The result is persisted to `dynamic.db.emphasis_log` after the Fountain event ID is available.

The composite is the equal-weight mean of goal relevance, locked-keystone self relevance and recent-entity novelty. Drive resonance is computed/logged but excluded from the composite and dominant-signal selection; the source cites a prior null test (p=0.190) as the reason. The underlying historical experiment record was not re-verified in this pass.

The inspected path is observation-only: the score does not alter the thought, branch, crystallization or belief confidence. No downstream consumer of `emphasis_log` was identified in this bounded pass. Treat this as [L1] instrumentation, not [L3] operational influence or [L4] validated improvement. No dedicated EmphasisEngine/PredictionTracker test module was found in the inspected tree.


## Chat provenance — accepted retry and measurement boundary (24 Nov 2026)

The admin-scoped provenance path snapshots pre-turn context, logs a mirror score for the first composed reply, and may issue one cue-driven retry. The retry is evaluated with `log=False`; if accepted, it becomes the delivered response, but no final-response provenance row is written to `/tmp/nex5_provenance.log`. Thus the file represents initial drafts for retry-accepted turns, not exclusively delivered replies. The trace overlay may record the retry output/selection separately. See DRAFT-012 in the Reality Report.

Existing module tests cover the mirror metric, cue and snapshot, not the `api_chat` retry branch or final-log identity. This is a conditional measurement limitation; feature activation and retry incidence on the target host are UNKNOWN.


## CounterfactualNode — open-problem LRU rotation qualification (24 Nov 2026)

The boot path starts CounterfactualNode without an environment gate. Each 300-second tick selects the oldest `open_problems.last_touched_at` row. It inserts accepted Tier-3 beliefs but does not update that problem's `last_touched_at`; TimeFetch's called `fetch_from_beliefs()` is read-only, and the node does not call `ProblemMemory.touch()`. Automatic promotion is disabled, so it does not remove the selected problem from the open pool. If no other subsystem touches/closes the oldest problem, it can be selected repeatedly and starve newer problems. The risk is conditional on external updates; no live incidence is established. Existing tests do not exercise multi-problem rotation. See DRAFT-013 in the Reality Report.


## PredictiveSubstrate — external-input population parity (24 Nov 2026)

The external-input producer takes up to 10 non-internal sense rows plus up to 10 user messages, concatenates sense first, then truncates to 10; it does not merge by timestamp. A full 10-row sense sample excludes chat entirely. The verifier then queries all sense events in the window without excluding `internal.*`, so internal events omitted from the prediction population can influence the score. The forecast and verification populations therefore differ. This can affect the surprise score and its downstream consumers (including DRAFT-011). Live incidence and score impact are UNKNOWN; current fixture tests do not exercise mixed-source chronological selection or producer/verifier filter parity. See DRAFT-014 in the Reality Report.


## Stage Capability — public Chat / Python execution security boundary (24 Nov 2026)

The normal `run.py` boot path constructs `ToolRegistry` and `ToolCaller` and injects them into `AppState`. The public `api_chat` route passes the raw prompt to the heuristic selector; a “calculate”/“compute”/“math” match can route to `python_exec`. `build_tool_kwargs()` forwards the raw query as code. `ToolRegistry._python_exec()` uses regex checks for literal import statements, then executes the text with `python3 -c` under the NEX process account. This is not a sandbox; Python built-ins and indirect imports bypass the blacklist.

The central mutation gate explicitly exempts `api_chat` as public, so no admin session is required for this tool path. The default bind is `127.0.0.1`, but `NEX5_HOST` can change the interface. If reachable by untrusted clients, the path permits conditional unauthenticated arbitrary code execution. No exploit was run; no live exposure or compromise is claimed. The tool tests cover only literal blocked imports and raw-query handoff, not indirect import bypass or isolation. See DRAFT-015 in the Reality Report.

**Security disposition:** do not expose this service beyond a trusted local boundary until the Python tool is disabled or safely isolated and independently verified. Runtime changes remain outside this documentation-only pass.


### Web fetch destination validation — conditional SSRF path

`ToolRegistry._web_fetch()` uses `parsed.netloc.lstrip("www.")` for allowlist normalization, which strips a character set rather than an exact prefix; certain lookalike hostnames can be normalized to an allowed name. It then uses default `urllib.request.urlopen()` redirect handling without validating the final destination. A permitted origin redirecting to an internal/private address can therefore bypass the initial host check. This is a conditional SSRF risk; no request was made and no internal target is asserted reachable. Existing tests cover only a direct unknown-domain rejection. See DRAFT-016 in the Reality Report.


## Throw-Net — threshold activation and failed-session accounting (24 Nov 2026)

- Gate REJECT and Chat gap-deflection callers invoke the TriggerDetector record methods but ignore their threshold booleans. Each method still inserts an unfired trigger row. `pending_triggers()` returns every unfired row, and `run_pending()` processes all of them. Therefore the documented four-reject/three-deflection thresholds do not gate session execution in the inspected chain. The monitor starts only with `NEX5_THROWNET=1` (default OFF). See DRAFT-017.
- If an outer ThrowNetEngine cycle raises, the DB session is written as `failed`, but the function later returns `status="complete"` and marks the trigger fired, so it is not retried by the pending query. Per-candidate gate errors are separately caught and do not exercise this outer failure path. The retry policy is unresolved; the returned/persisted status mismatch is source-confirmed. See DRAFT-018.
- Existing tests cover threshold booleans and pending-row mechanics independently, but do not enforce the cross-component threshold gate or outer-cycle failure status/retry contract.


## Chat attention and working-memory integration — session scope (24 Nov 2026)

The Chat module constructs one process-global FocalSet and a process-global dictionary of per-session WorkingMemory objects. On each chat request, FocalSet is updated from that request's retrieved beliefs; its focal IDs are then added to the current session's WorkingMemory. Later in the same request, active WorkingMemory items are appended to the prompt for Conversational turns with at least two retrieved beliefs. The source comment calling FocalSet “log-only” is therefore inaccurate for this conditional path: the selected items can influence the current-turn prompt.

FocalSet has no internal lock and is shared across sessions; overlapping candidate IDs can inherit cross-session priority influence, and concurrent requests can interleave between update and focal-ID read. The current request's content is filtered against its own retrieval set, so no direct arbitrary cross-session text transfer was identified. The WorkingMemory objects have per-instance locks and seven-item capacity, but the global session registry has no lock or cleanup/eviction and can grow with session count. Existing tests are component-level; no chat integration/multi-session concurrency test was identified. See DRAFT-020 in the Reality Report.


## Memory continuity — shutdown snapshot and resumption recovery

The boot sequence records downtime before running ResumptionSeeder because both read the same snapshot and the seeder consumes it; that ordering is correct. The SnapshotWriter is passed into Fountain and writes on every Fountain scheduler tick. However, SnapshotWriter's constructor-installed SIGTERM handler is later replaced by run.py's graceful-standby handler. That handler calls `os._exit(0)` without invoking `snapshot_writer.write_snapshot()`; `os._exit` also bypasses the registered atexit callback. Thus the normal SIGTERM path does not produce the advertised final snapshot; recovery relies on the latest periodic tick. See DRAFT-021.

For a valid non-stale snapshot, ResumptionSeeder calls promotion/reissue helpers that swallow database errors and return zero/partial counts, then consumes the snapshot unconditionally. A transient write failure can therefore discard the recovery manifest and prevent retry on the next boot. Existing tests do not cover this recovery failure contract. See DRAFT-022.


## Phase 0 findings backlog companion (24 Nov 2026)

The source-to-sink findings in this Crosswalk are consolidated in `NEX_VERIFIED_DEFECT_BACKLOG.md` for Gate 0 review. That file separates source-confirmed defects, conditional risks, documentation/implementation mismatches and unresolved host/approval questions; its priority ordering is provisional, not an approved severity scheme. The top five doc-vs-code discrepancies are recorded there. No remediation is authorized by the backlog.


## Explicit 30-node MIND_MAP → source/runtime evidence crosswalk (24 Nov 2026)

Source basis:
- mind_map/MIND_MAP.yaml SHA cb7e54052b0c5c8bee8b257fd196630093dbe567 (meta declares 30 nodes; 30 node entries reconciled below).
- sentience_dag.json SHA 687cd854913714193622468bd64a6f872f5b7854.
- ARCHITECTURE.md SHA e60f7b9c60081a3f8b24a32484ecd4a0adc0ca1a.
- SENTIENCE_PROGRAM.md SHA 3c5a82f1bed3d814c3b63b9557ae588cb8042016.
- Runtime source basis: PR #65 integrated source head cffbbc94b5a494247d127abf2720886a08f7a567; run.py SHA 73a2c58a4f5f0348135a46eb83d6cdd61db874e7.

**Important distinction:** MIND_MAP's own evidence values (implemented/measured/static/inferred/unknown) and dark/blocked modifiers are not the roadmap L-levels. The L-level below is a separate assessment of construction, trace and consumption evidence. Historical live observations recorded in MIND_MAP (mostly dated 2026-11-15) are marked “reported L2”; they are not independently revalidated against the PR #65 source checkout because the target host checkout identity is still unresolved (see DRAFT-006). Do not silently promote these historical host observations to current-host truth.

| MIND_MAP node | Principal source / actual route | Declared MIND_MAP state | Strict L-level in this evidence set | Qualification |
|---|---|---|---:|---|
| **amoha** — discernment / non-delusion | stage_tom/amoha_detector.py; Fountain prompt formatting | measured; dark | L1 | Built/tested, NEX5_AMOHA default OFF. MIND_MAP's 50-thought probe found max clouded salience 0.191 vs 0.30 threshold; this is a manual corpus probe, not an active runtime loop. |
| **karuna** — compassion | stage_affect/compassion.py; admin Chat prompt block | measured; dark | L1 | Unit-tested, but NEX5_COMPASSION=1 and admin session are both required. MIND_MAP says live uptake is not established. |
| **upeksa** — equanimity | stage_affect/upekkha.py; admin Chat prompt block | measured; not dark | L2 reported | MIND_MAP reports live/falsifier pass. Source path is gated by NEX5_EQUANIMITY=1 and admin session; current host flag is not reverified. |
| **apramada** — conscientiousness | stage_affect/apramada.py; admin Chat prompt block | measured; not dark | L2 reported | MIND_MAP reports live/falsifier pass. Source path is gated by NEX5_APRAMADA=1 and admin session; current host flag is not reverified. |
| **alobha** — non-attachment | stage6_fountain/generator.py _alobha_context/_alobha_penalty | implemented; dark | L1 | Code/test exists; NEX5_ALOBHA defaults OFF. No default-on behavioural influence established. |
| **vedana** — feeling-tone | stage_affect/affect_state.py; Fountain reads affect state | measured; not dark | L2 reported | run.py constructs and starts AffectState. MIND_MAP reports 35 live samples and 12 distinct valence deltas from /tmp/nex5_affect_state.log; host checkout identity pending. |
| **mana** — self-conceit | stage_tom/mana_detector.py via self_binding.py affliction cluster | static; dark | L1 | MIND_MAP reports no live call: both caller and helper are gated by NEX5_AFFLICTIONS; no standalone watcher found. |
| **vicikitsa** — doubt / within-moment refusal | No matching implementation | unknown; absent | L0 | NEX5_ABSTAIN_CLOSE closes a persistent problem after repeated doubt-language; it is not a within-moment candidate-pricing refusal. |
| **drsti** — fixed view | keystone.py; stage_world/expectations.py locked-row filters | implemented; not dark | L1 | Locked Tier-1 beliefs are excluded from ordinary reconciliation; MIND_MAP reports 90 live locked beliefs with static confidence. This is a live-state probe, not an ID-linked execution trace; the protective/narrow scope caveat remains. |
| **smrti** — retention | stage6_fountain/generator.py retrieval manifest → crystallizer.py retained candidate | implemented; dark | L1 | Implemented as observational retention attribution and tested; it does not itself change selection or belief confidence. |
| **virya** — joyous effort | stage_affect/virya.py; admin Chat prompt block | implemented; dark | L1 | Built and deliberately disarmed; NEX5_VIRYA is required. |
| **prasrabdhi** — pliancy | stage_affect/prasrabdhi.py; admin Chat prompt block | implemented; dark | L1 | Built and deliberately disarmed; NEX5_PRASRABDHI is required. |
| **sraddha** — warranted confidence | stage_affect/sraddha.py; admin Chat prompt block | implemented; dark | L1 | Built and deliberately disarmed; NEX5_SRADDHA is required. |
| **p5_second_order** — second-order monitoring | stage9_metacognition/metacognition.py; run.py and Chat/Fountain injection | static; not dark | L2 reported | run.py constructs Metacognition and passes it to Fountain/Chat. MIND_MAP reports real live writes; the specific “reports itself being wrong” falsifier remains unrun. |
| **kaukratya** — regret / repricing | stage3_world_model/harmonizer.py tension repricing methods | implemented; dark | L1 | Built/tested, but the newer repricing method is not established as a live consumer path. Do not conflate it with the separate always-live retire/synthesize path. |
| **p6_unified_present** — unified present | stage_tom/global_workspace.py; Chat budget assembly; Fountain workspace | static; not dark | L3 fixture path | The isolated Fountain trace records GlobalWorkspace.arbitrate as workspace_selection, and that record is an explicit parent of model_input. This proves simulated downstream prompt consumption in the fixture, not live-host operation; the Chat-specific arbiter path is not separately represented in that trace. |
| **vitarka** — applied thought | stage6_fountain/generator.py wide-mode focal item selection | implemented; not dark | L2 reported | MIND_MAP reports NEX5_WIDE_MODES=1 and 2,821 real [WIDE MODE] markers. Current host flag/log not reverified. |
| **vicara** — sustained thought | stage6_fountain/generator.py associative recall using prior focal item | implemented; not dark | L2 reported | MIND_MAP reports NEX5_ASSOC_RECALL=1 and caller condition own_n > 1; current host flag/log not reverified. |
| **p1_continuity** — continuity of self | nex_keepalive.sh; substrate/writer.py; substrate/db.py | static; not dark | L1 | Persistence/keepalive code exists, but MIND_MAP's own falsifier says the cited anchor does not establish the intended continuity-of-self directive. |
| **p2_train** — train across restart | memory/resumption.py; snapshot_writer.py; downtime.py | static; not dark | L2 reported | MIND_MAP reports five real boots with five beliefs promoted per boot. This is historical host evidence; DRAFT-021/022 add current source-level recovery caveats. |
| **p3_stakes** — stakes | stage_tom/stakes_appraisal.py; stage_world/frozen_at_made.py; stage6_fountain/readiness.py | static; not dark | L2 reported | MIND_MAP reports live frozen stake snapshots. The readiness penalty is separately gated by NEX5_STAKES and was absent in its observed process; frozen-value downstream consumption remains unproven. |
| **p4_interoception** — honest interoception | stage1_sense/internal/interoception.py; SenseScheduler | static; not dark | L2 reported | Internal adapter is in the boot scheduler. MIND_MAP reports five polls in the live log; current host log/checkout not reverified. |
| **p7_valence** — intentional valence | Inferred from vedana; no independent faculty | inferred; not dark | L0 | Concept is inferred from the parent affect signal; no independent source mechanism is identified. Parent vedana has separate L2-reported evidence. |
| **p10_thickness** — temporal thickness | No graded temporal-distance reader | static; absent | L0 | Timestamp cutoffs and downtime narration do not provide a graded temporal-distance reader. |
| **p11_agency** — agency/authorship | No action-point self/world authorship signal | static; absent | L0 | source_kind labels content provenance; recursion_attribution measures an experiment. Neither records deliberate action vs received event. |
| **p12_selfreport** — unflattering self-report | stage_tom/apatrapya_channel.py; hri_apatrapya_prototype.py | implemented; dark; blocked | L1 | Read-only verdict path and 29 fixture tests exist. Blocked on ledger-pricing conflict and absence of real rating data; no live self-lowering result. |
| **p13_finitude** — finitude/budget cap | stage_finitude/budget_shadow.py; stage_tom/global_workspace.py; Chat budget assembly | implemented; dark | L1 | A fixed 1,400-character selector cap is source-active, but BudgetShadow's per-moment Balance/spend ledger is not wired to the live caller. |
| **p9_dissonance** — held contradiction | stage3_world_model/harmonizer.py; dynamic.sql held_tensions | implemented; dark | L1 | NEX5_HELD_TENSION default OFF and MIND_MAP reports zero live held-tension calls. The separate always-live retire/synthesize path is not equivalent to keeping and resurfacing both sides. |
| **hri_apatrapya** — shame/dread of blame | stage_tom/apatrapya_channel.py; hri_apatrapya_prototype.py | implemented; dark; blocked | L1 | 29 fixture-based tests; flag default OFF. Blocked on ledger-pricing type conflict and no real rating corpus. |
| **p8_episodic** — episodic/autobiographical memory | memory/episodic.py | implemented; dark | L1 | Code/tests exist; NEX5_EPISODIC default OFF and MIND_MAP reports zero live calls. |

**Level summary:** 4 nodes at L0, 16 at L1, 9 at L2 (all historical MIND_MAP host claims pending checkout reconciliation), 1 at L3 (isolated Fountain fixture path only), and 0 at L4. No node is L4-validated. No L2 historical host claim should be treated as current PR #65 runtime truth until the host checkout identity and environment are reconciled.

**MIND_MAP discrepancies retained, not silently edited:** (a) the map's dark:false for upeksa/apramada is based on historical live observations, while source shows explicit admin-scoped environment gates; (b) p13_finitude's live fixed selector cap is not the same as wiring BudgetShadow's spend ledger; (c) p9_dissonance's active retire/synthesize path is not the same as the dark held-tension behaviour; (d) p12_selfreport and hri_apatrapya are built but blocked; (e) p7_valence is inferred, not independently implemented. These distinctions require Founder review before any status or code change.


## ExecutiveControl faculty — constructed but not consumed by active Chat routing

The GUI constructs and registers one ExecutiveControl instance, but the active api_chat route does not call its select() method. Instead, unless the client supplies an explicit register, the route selects Philosophical. The module docstring says ExecutiveControl replaces the voice.registers.classify() stub, while that function remains a Conversational stub and default_register() returns Conversational. A dated code comment identifies the Philosophical default as an intentional edit and says the classifier branch should be restored later; whether that temporary override remains approved is unresolved. Unit tests cover the classifier itself, not route-level consumption. See DRAFT-023 in the Reality Report.

Secondary qualification if the classifier is restored: its continuity-bias read is outside the lock despite the thread-safe claim, and its process-lifetime session map has no expiry/cleanup.


### M0.3/M0.4 progress update (24 Nov 2026)

Completed in this documentation pass:
- Explicit L0–L4 mapping for all 30 declared MIND_MAP nodes, preserving the map's own evidence/dark/blocked modifiers separately.
- Broad forward/backward source-to-sink audits for boot stages, Chat, Fountain, WorldModel, predictive/counterfactual, provenance, gate/reshape, warrant, affect, memory, attention/working memory, and optional faculties.
- Exact source/test boundaries and conditional activation notes for DRAFT-001 through DRAFT-023, consolidated in NEX_VERIFIED_DEFECT_BACKLOG.md.
- A current exact-head CI reconciliation in ADR-001 and the defect backlog.

Still open:
- Exhaustive closure of every module's direct/dynamic import, event, shared-state, SQL read/write and downstream-consumer edges; the current crosswalk is broad but not yet a complete all-file call graph.
- Exact host checkout identity, process environment and live trace capture; historical MIND_MAP host observations remain unverified against PR #65 source.
- Target-host M0.1/M0.2 measurements and full pytest/known-failure baseline.
- Frozen V2.1 and Founder Sign-Off reconciliation and approval.


### ToolCaller belief-context handoff

api_chat calls ToolCaller.should_use_tool(prompt, []) even after the normal retrieval branch has assembled local belief context. ToolCaller’s “no beliefs + factual phrasing” fallback is therefore always eligible for those patterns. This may be a deliberate freshness policy, but it does not match the method's documented condition and has no route-level test. It can increase web_fetch calls and therefore the reachable surface of DRAFT-016. See DRAFT-024.


### Manus advisory reconciliation — 24 Nov 2026

The following points are independent technical recommendations, not governing requirements or Founder decisions. The reviewed PR tree did not contain the canonical Master Roadmap or Frozen V2.1 specification; exact acceptance wording must be checked against those authoritative documents.

1. **Asynchronous parentage.** Require an explicit parent edge for an in-scope asynchronous handoff when the producer record exists and consumer identity can be joined to it. Do not infer parentage from timestamps or ordering. The controlled speech-queue commit-before-registration test demonstrates a real unlinked-trace race and a useful partial result, not complete producer-to-consumer lineage. Preserve missing-parent observations as explicit gaps. Additional isolated coverage is recommended for registration failure, trace-registry loss/restart and overlapping consumers. No race-frequency claim is made.

2. **Operation-stage evidence.** Distinguish a pre-call attempt marker, observed callee entry, successful return or exception, persisted outcome, and physical completion. A pre-call marker does not prove callee entry; a returned player call does not prove audio completed or was audible. A queue row marked spoken is software-state evidence only. Persistence claims should be tied to Writer success and, where material, independent read-back. Physical completion remains unobserved without a device/backend acknowledgement.

3. **Observer overhead.** Treat behavioural neutrality and latency neutrality as separate properties. Synchronous JSONL serialization, filesystem writes and shared-lock contention necessarily may add elapsed time. Do not assert zero added delay. Before an acceptance benchmark, agree the representative host/workload and a bounded latency budget; report repeated p50/p95/p99, including concurrency and lock contention. The existing benchmark remains diagnostic and non-gating until its workload and threshold are approved.

4. **L5 classification.** Provisionally treat L5 as a separate generalisation classification and keep the Phase 0 faculty audit at L0–L4 if that is what the canonical roadmap's Phase 0 text specifies. Record L5 separately as exploratory/out of scope unless the canonical roadmap explicitly requires it. The apparent global L0–L5 versus Phase 0 L0–L4 distinction still requires exact-document reconciliation.

These recommendations do not resolve the roadmap's acceptance criteria, approve a latency threshold, certify causal-trace completeness, or authorise runtime, schema, queue, flag, host, experiment, merge or deployment changes. Gate 0 remains unestablished.



### Speech operation-stage test addendum — 24 Nov 2026

A test-only follow-on on PR #74 now exercises the ordering boundary between the speech consumer's pre-call markers and the actual callee bodies. Instrumented fake synthesis and player methods inspect the trace at their own entry: `synthesis_started` and `player_invocation_started` are already present, while the corresponding completion/failure events are not. After return, the distinct completion/return events appear.

This establishes the source/test distinction between attempt markers and observed call outcomes for the isolated fixture. It does not add a runtime callee-entry event, establish physical audio completion, or verify deployed behaviour. The same test file already verifies independent SQLite read-back of the resulting `spoken` queue status in its real-Writer/Reader fixture; that is persisted software state, not audibility evidence.

PR #74 remains draft and unmerged. Latest test-only commit: `ec551aac4c634aa21d9b827421dc89f24c0246f2`. Exact-head CI result is pending; no pass is claimed.



### Watcher host-evidence request CI update — 24 Nov 2026

PR #73 exact head `e917f3704647c3431d2f2a86b4abf8ab40818aef` completed workflow run `45283644024` successfully, including the full repository test/baseline gate and MIND_MAP sourcing check. This validates the Watcher request-template coverage and its isolated tests at that commit only. It does not mean any target-host probe was executed: OS/model/runtime measurements, artifact hashes, live checkout identity and performance remain uncollected. PR #73 remains open, draft and unmerged.



### MIND_MAP source-pointer integrity spot audit — 24 Nov 2026

A repository-tree check against the PR #49 evidence branch found 30 declared MIND_MAP nodes. The nine distinct file-typed source references currently present in `mind_map/MIND_MAP.yaml` all resolve to tracked repository files, and each stated line range is within the current file length. This is a pointer-integrity check only: it does not validate the semantic sufficiency of each cited source, re-run the probes, or establish live activation.

The same pass inspected all nine `sentience_dag.json` nodes carrying a `module` field. Seven values resolve as repository paths; two values — `bonsai.py decay_pass (recency penalty)` and `bonsai.py decay_pass (starvation bonus)` — are descriptive function labels, not literal paths. They are therefore not counted as missing source files, but remain less directly navigable than path-qualified module references. The DAG and MIND_MAP are distinct artifacts with different node sets/roles; this check does not assert they should be one-to-one.

The repository tree contains 311 Python files under `theory_x/`. This bounded check does not close the required faculty-by-faculty forward/backward dependency audit, dynamic imports, event/shared-state edges, SQL readers/writers, or downstream consumers. Those remain open for M0.3.



### Boot-orchestrator forward-path audit slice — 24 Nov 2026

Static inspection of `run.py` on this branch confirms a concrete boot construction path, distinct from mere module presence:

- Core factories imported and called from `main()`: `build_scheduler` (stage1), `build_dynamic` (stage2), `build_world_model` (stage3), `build_membrane` (stage4), and `build_fountain` (stage6); supporting construction includes self-location commitment, mode/voice state, drives, memory/resumption, and WorldBridge selection.
- Additional faculties are imported/constructed in the boot body rather than through those five factories: SelfNarrative; CoherenceGate/HoldingZone/Resolver/TriggerDetector; ProblemMemory; GoalManager; Metacognition; NovelAssociation; ThrowNet; SubstrateHarmonic; GeniusTagger; CounterfactualNode; DriveEmergence; CompetingDrives; VoiceEngine; and affect-related components.
- Activation is not uniform. Several constructors/loops are guarded by broad `try/except` blocks and can fail non-fatally. Throw-Net's monitor is constructed, but its autonomous loop is started only when `NEX5_THROWNET=1`; otherwise trigger telemetry remains. WarrantRecorder is only constructed/started when `NEX5_WARRANT_RECORD=1`. The code comments identify some subsystems as log-only.
- This is a source-level boot-path observation, not proof that the target host is running this checkout, that all optional constructors succeeded, or that every constructed component is registered, consumed, or behaviourally influential.

Source anchor: `run.py` at the PR #49 evidence branch (boot setup and faculty wiring, approximately lines 100–420). This slice strengthens the forward boot map but does not close backward-consumer, dynamic-import, shared-state, event, or SQL edge closure across the 311 Python files under `theory_x/`.


### Stage 1 internal self-observation and status semantics — 24 Nov 2026

A bounded source-to-sink slice of the two always-on internal adapters adds these qualifications:

- `Interoception.poll()` reads aggregate belief counts/tier counts/locked count and maximum `created_at` through the supplied beliefs Reader, then emits one `internal.interoception` SenseEvent for submission to `sense.db`. It also appends a separate best-effort JSONL line to `/tmp/nex5_interoception.log`; failure of that auxiliary append is swallowed and does not prevent the SenseEvent path. Its first `beliefs_since_last_poll` value is `null`, because no prior in-process total exists.
- `MetaAwareness.poll()` samples Writer queue depths, recent error-channel length (up to 500 returned events), and scheduler status, then emits `internal.meta_awareness`. Its `sense_active_external_count` is derived from each adapter's `enabled` boolean, not a fresh poll-success/health signal.
- Scheduler `enable()` sets `enabled=True` before a successful poll is observed. A poll that returns an empty list without raising is still recorded as a successful scheduler iteration with event count zero and `last_error=None`. Therefore the MetaAwareness active count is control-state/enablement telemetry, not proof that an external source is reachable, producing events, or recently polled successfully.
- The scheduler module docstring still describes external feeds as paused until GUI activation, while its constructor calls `start_all()` unconditionally. This corroborates the already-recorded source-comment/actual-startup discrepancy; it does not establish target-host runtime activation.

This slice maps production and semantics of these two internal streams only. No downstream consumer of `internal.interoception` or `internal.meta_awareness` was established in this bounded pass; that is an open backward-consumer question, not evidence of no consumer. Source anchors: `theory_x/stage1_sense/scheduler.py`, `internal/interoception.py`, `internal/meta_awareness.py` on repository `main` at the inspected revision. No runtime changes or tests were made.

### Stage 1 sense-stream persistence and read-consistency audit — 24 Nov 2026

A bounded source-to-sink inspection of `stage1_sense/base.py`, `substrate/writer.py`, `substrate/reader.py` and `substrate/schema/sense.sql` clarifies the persistence boundary:

- Every adapter event is inserted into `sense_events` through `Adapter.submit()` and the shared `Writer`; the table stores stream, JSON payload, provenance and integer timestamp. The inspected schema has stream and timestamp indexes, but no explicit producer/trace identity or parent-link columns.
- `Adapter.submit()` calls synchronous `Writer.write()` separately for each event. Each call is its own transaction/commit in the Writer worker. It increments the returned count only after the write future returns successfully; a failed row is recorded to the error channel and swallowed, and iteration continues. Therefore one poll's event list is not an atomic batch: partial persistence is possible. If every insert fails, `submit()` can return zero without raising to the scheduler.
- The scheduler wraps both `poll()` and `submit()` in one try block. Since `submit()` absorbs per-row failures, a persistence failure can still lead to `last_poll_at` being updated, `last_event_count=0` (or a partial count), and `last_error=None`. The scheduler's “successful iteration” fields therefore do not prove that all emitted events were durably persisted.
- `Reader.read()` and `read_one()` each open and close a fresh read-only connection. Interoception performs separate Reader calls for tier counts, locked count, total count and maximum creation timestamp. These are separate read operations, not one explicit read transaction/snapshot; concurrent belief writes could make the aggregate fields describe slightly different database moments. No observed inconsistency is claimed.
- The schema's absence of explicit trace/parent columns is only a statement about this table's current shape; it does not rule out correlation in payloads or other stores. Downstream readers/consumers remain unverified in this slice.

Source anchors: `theory_x/stage1_sense/base.py`, `theory_x/stage1_sense/scheduler.py`, `theory_x/stage1_sense/internal/interoception.py`, `substrate/writer.py`, `substrate/reader.py`, and `substrate/schema/sense.sql` on `main` at the inspected source revision. This is source-level evidence only; no host DB or live adapter output was inspected. No runtime or test changes were made.

### Stage 1 adapter inventory and remaining internal feeds — 24 Nov 2026

Inspection of `theory_x/stage1_sense/__init__.py` closes another bounded forward-path slice:

- `build_scheduler(writers, readers, mode_state)` wires 28 adapter instances to the single `writers["sense"]` destination and supplies `readers["beliefs"]` to Interoception. MetaAwareness receives the Writer map and a late-bound scheduler reference.
- The four internal streams are Proprioception (CPU/memory/load/available thermal readings), Temporal (local/UTC clock fields), Interoception (belief-store aggregates) and MetaAwareness (Writer queue/error/scheduler telemetry). All four are constructed in the factory.
- The factory docstring says external feeds start paused, while the instantiated `SenseScheduler` constructor calls `start_all()` unconditionally. On this source path, the scheduler sets the global run event and enables each non-internal adapter; the docstring does not describe the implemented constructor behaviour.
- The factory imports/constructs the listed active external adapters, while Reuters, APNews, PhilPapers and PapersWithCode are explicitly commented out of this factory. Their files remain in the tree but are not part of this factory's adapter list.
- The source count is 28 constructed adapters in this factory. It is not evidence that all polls succeed, all rows persist, or the target host is running this version.

This complements the scheduler and persistence slices; it does not close the backward-consumer audit for `sense_events` or prove live external-feed activity.

### Stage 1 backward-consumer audit — verified source paths — 24 Nov 2026

A backward trace from sense_events now establishes several concrete consumers; the earlier “consumer unverified” statement applies only to the two internal streams individually until this pass:

- Stage 4 SelfModel.snapshot() queries the latest row by id DESC for internal.proprioception, internal.temporal, internal.interoception and internal.meta_awareness. It maps the first three payloads into CPU/memory/load/thermal, clock and belief-graph fields. It fetches the MetaAwareness payload, but the inspected snapshot code does not use that payload to populate its meta_awareness result; those values are instead read from the supplied DynamicState when available. Thus “row fetched” and “payload relied upon” differ.
- Stage 6 FountainGenerator reads non-internal sense_events directly. The quiescent branch (every fifth fire under the inspected counter condition) selects the latest non-internal event and can surface its truncated payload as the thought. _recent_sense_sample() separately reads a recent multi-source window, skips internal streams and selected noise streams, extracts summaries, and returns up to the requested number of distinct streams for drift context.
- Stage 6 also writes its own internal.fountain row to sense_events; that is a producer path, not evidence that its own internal row is consumed by the above non-internal readers.
- Tests corroborate portions of these paths: tests/test_interoception_fixes.py seeds an internal.interoception row and verifies SelfModel field mapping; tests/test_sense_extract.py covers Fountain extraction and the external/internal filtering contract. These are isolated test fixtures, not live-host evidence.

This establishes source-level consumers for three internal payloads and a fetch-but-not-use path for MetaAwareness, plus external-stream consumption in Fountain. It does not establish how often those paths execute on the target host, which rows were present, or whether any particular row changed a final decision/output.


### Stage 1 → Stage 2 ingestion and cursor semantics — 24 Nov 2026

A further source-to-sink pass traced the shared `sense_events` table into Stage 2 Dynamic formation:

- `substrate/schema/sense.sql` defines `sense_events` with an autoincrement row id plus stream, payload, provenance and timestamp. It does not encode a consumer-processing status or retry/dead-letter state.
- Stage 2 `_sense_poll_loop()` reads all streams in ascending id order, in batches of at most 100, beginning after its persisted `dynamic_cursor.last_sense_id`. Unlike the distillation loop and Fountain readers, this general A–F attention path does not filter out `internal.%` rows.
- The poller calls `run_pipeline()`, then advances its in-memory cursor and increments `_pipeline_runs` regardless of the integer returned. `run_pipeline()` catches its own exceptions, records an error and returns 0; zero is also a normal result when no branch matches. Therefore a pipeline exception is not propagated to the cursor loop and the affected row is treated as consumed in that process. Cursor persistence occurs every 50 rows and on shutdown. A failure before the next cursor save may be replayed after restart; after a later save advances beyond it, there is no source-level retry path for that row. This is a source-confirmed retry/accounting gap, not a measured live loss rate.
- Pipeline effects are not one atomic transaction: pipeline-stage rows are written through separate Writer calls, while `step_F()` mutates the in-memory tree and membrane accumulator before writing its F-stage event. If a later write fails, earlier log rows and/or in-memory effects may already exist; the outer handler records the error and returns 0. Exact partial-effect outcomes depend on the failure point and were not experimentally induced.
- The separate sense-distillation loop reads non-internal rows (excluding `external.other_mind`) in id order, but advances its cursor to the maximum row id seen. It permits at most five new belief writes per pass; after the cap is reached it does not extract/promote later rows in that fetched batch, while still advancing past them. The source comment explicitly says the cap limits writes, not cursor. This is an intentional-looking throughput/drop boundary in code, but whether this matches the approved acceptance contract remains unresolved.

This distinguishes three different Stage 1 downstream policies: all-stream attention processing, non-internal/non-persona belief distillation, and Fountain's separately filtered external-sense context. Retrieval from the shared table is not equivalent to belief promotion or prompt influence. All findings are source-level; no live sense.db rows, dynamic cursor values, host loop health or row-level causal effects were inspected.

Source anchors at the inspected PR #49 branch: `substrate/schema/sense.sql`, `theory_x/stage2_dynamic/__init__.py` (`_sense_poll_loop` and `_sense_distillation_loop`), and `theory_x/stage2_dynamic/pipeline.py`. No runtime, test, schema, flag or host changes were made.


### Stage 1 external-feed failure semantics and expanded Fountain consumers — 24 Nov 2026

A further source pass distinguishes feed-level partial success from adapter-level failure and expands the Stage 1-to-Stage 6 input map:

- The shared `parse_rss()` helper converts up to `max_entries` feed entries into SenseEvents, assigns the same poll-time timestamp to every entry in that batch, and preserves title/link/summary/published/authors/tags. It does not itself persist rows, record per-item source identity beyond payload fields, or deduplicate entries across polls. This is a parser contract observation, not evidence that duplicate rows were observed in the target database.
- `ExchangePrices.poll()` catches each Binance, Coinbase and Kraken request/parse exception independently and silently continues. It can return zero, one or two exchange events while the scheduler sees a normal return and clears `last_error`; the event count reflects successful exchange groups, not completeness across all three sources.
- `CryptoNews.poll()` similarly catches each of its three RSS-source exceptions independently and continues. It can return a partial list or an empty list without surfacing those per-source failures to the scheduler. By contrast, the inspected `ArxivAI.poll()` lets fetch/parse exceptions propagate to the scheduler, where they populate `last_error`. These are materially different observability semantics within the same adapter family.
- Fountain has more than one read path over `sense_events`: (a) the periodic quiescent/latest-external-row path; (b) `_recent_sense_sample()`, which reads the latest `limit * 6` non-internal rows, filters configured noise streams, extracts a summary and keeps at most one row per distinct stream; (c) the optional OVERWHELM prompt block, enabled only when `NEX5_SENSE_OVERWHELM_N` is greater than zero, which inserts the latest N external rows with payloads truncated to 120 characters; and (d) the optional SELF layer, enabled only when `NEX5_SELF_LAYER_N` is greater than zero, which inserts the latest N `internal.%` rows. The latter corrects any broad reading that Fountain never consumes internal streams: its default configured value is zero, but the source path exists.
- A separate optional SOCIAL prompt lane reads the latest `external.other_mind` rows when `NEX5_SOCIAL_N` is greater than zero. This stream is not one of the 28 adapters assembled by the Stage 1 factory; its producer/writer path is not established by this slice. It must not be attributed to a Stage 1 factory adapter.
- The inspected Fountain read queries are ordered by timestamp but do not apply an explicit age/freshness cutoff in these paths. Thus “latest” means latest available row(s), not necessarily recent in wall-clock terms when a stream has stopped producing. No stale-row use on the target host is asserted.

Source anchors at PR #49 evidence branch head `23e327e84b6b26b6e22eb27808514100c2802855`: `theory_x/stage1_sense/feeds/_helpers.py`, `feeds/exchange_prices.py`, `feeds/crypto_news.py`, `feeds/arxiv_ai.py`, and `theory_x/stage6_fountain/generator.py` (constructor defaults around lines 1058–1074; sense sampling around 2626–2650; OVERWHELM/SELF blocks around 3624–3685; SOCIAL block around 3731–3765). The inspected `tests/test_sense_extract.py` covers payload-title extraction and filtering helpers, but is not an adapter-level test of per-source partial failures, RSS repeat ingestion, freshness bounds, or live prompt inclusion. No test was run as part of this source-only pass.

These are source-level control-flow and test-boundary findings. They do not establish which environment flags are set on the target host, which external sources currently respond, whether repeated items are persisted, or whether any particular row changes a generated thought. No runtime, schema, test, flag, host, experiment, merge or deployment change was made.


### Stage 2 internal-stream effect qualification — 24 Nov 2026

The Stage 2 attention mapping was inspected to avoid equating row ingestion with branch influence. The general poller does fetch internal streams, and `_match_branches()` has direct mappings for the four internal stream names to the `systems` branch. However, `_magnitude_for()` returns 0.0 immediately for any `internal.*` stream. The pipeline can therefore emit B, D and E diagnostic `pipeline_events` rows for those internal observations, but Stage F skips magnitudes below 0.001; the inspected path does not apply internal rows to Bonsai focus or the membrane accumulator. This is an important distinction between row retrieval, diagnostic pipeline traversal and behavioural state influence.

For non-internal text streams, matching combines stream-name and selected payload tokens against branch hint sets; direct stream-prefix mappings can force a branch proximity of 1.0. The magnitude function then applies a direct-stream base and keyword-overlap bonus. This is source-level routing/weighting logic, not evidence that a specific live row matched a branch or changed a later decision.


### Stage 2 test-coverage boundary — 24 Nov 2026

The inspected tests cover basic A–F pipeline operation and cursor save/load, but do not establish the failure semantics above. `tests/test_dynamic.py::TestCursorPersistence` verifies a stored cursor can be loaded; it does not exercise a `run_pipeline()` exception followed by cursor advancement, replay before/after a save, partial Stage F side effects, or the distillation write-cap/cursor interaction. Its `test_internal_event_matches_systems_branch` only asserts the returned hit count is non-negative; it does not assert that internal telemetry leaves tree focus and membrane accumulation unchanged. `tests/test_sense.py` verifies successful adapter writes and a mock scheduler hand-off, but the inspected cases do not inject a per-event Writer failure into the real `Adapter.submit()` implementation. These are gaps in the inspected test slices, not a claim that no other tests anywhere exercise related behaviour.


### Stage 1 repeated-feed rows and Stage 2 consumer asymmetry — 24 Nov 2026

The Stage 1 feed audit was cross-checked against the Stage 2 loops to avoid treating the two downstream paths as one:

- The inspected RSS adapter path has no cross-poll item deduplication in `parse_rss()`; the `sense_events` schema has no uniqueness constraint on source item identity. Repeated feed entries can therefore become separate rows with distinct database IDs even when their payload title/link repeats. This is a code-path possibility, not a measured duplicate rate.
- Stage 2 `_sense_poll_loop` reads every new `sense_events` row by increasing database ID, without excluding internal or repeated external items, and calls `run_pipeline()` for each row. The pipeline's A–F steps operate on each row; no content-level deduplication appears in this path. Repeated rows may therefore receive repeated pipeline processing when their stream/value matches branches. Whether repeated processing materially changes live tree/membrane state is unverified.
- The separate `_sense_distillation_loop` excludes `internal.%` and `external.other_mind`, extracts titles, applies exact/near-duplicate belief checks within its time window, and limits new belief writes per pass. That deduplication is local to belief promotion; it does not make the general Stage 2 A–F pipeline idempotent.
- `run_pipeline()` catches its own exceptions, records an error and returns zero. The caller then advances its in-memory row cursor after the call returns, so a failed pipeline row is not distinguished from a no-match/zero-hit row by the caller. The separate source audit already records cursor persistence cadence and restart uncertainty; this addendum connects that boundary to the repeated-feed path without asserting a live loss or duplicate effect.

Source anchors at current PR #49 branch head `5dc5f8b13e18a716901a5b0296a50c7463156ebe`: `theory_x/stage1_sense/feeds/_helpers.py`, `theory_x/stage1_sense/feeds/arxiv_ai.py`, `substrate/schema/sense.sql`, `theory_x/stage2_dynamic/__init__.py` (`_sense_poll_loop`, `_sense_distillation_loop`) and `theory_x/stage2_dynamic/pipeline.py` (`run_pipeline`, steps A–F). No tests were run in this pass.

This is a conditional cross-stage risk map, not a finding that duplicate feed rows, repeated state changes, or cursor-loss incidents occurred on the target host. No runtime, schema, test, flag, host, experiment, merge or deployment change was made.


### Additional Stage 2 sense-table consumers — 24 Nov 2026

The Stage 2 backward scan found two further direct readers of `sense_events` beyond the A–F poller, distiller and Fountain paths:

- `BonsaiTree.refresh_cadence()` reads the previous 24 hours of non-internal sense rows, groups timestamps by stream, clusters bursts, computes median inter-burst gaps and maps recognised stream prefixes to branches. The minimum interval among mapped streams becomes that branch's cached cadence factor input. This is a separate influence path: event frequency can affect later decay timing even where an individual event did not produce a Step-F attention hit. It is read-only against sense.db and refreshes on the first accumulator tick and then every 60 ticks (about 30 minutes at the 30-second loop cadence).
- `consolidation._external_quiet()` reads the latest `internal.temporal` payload and expects `seconds_since_last_user_message`; when the value exceeds 300 seconds, the consolidation loop runs an additional tree decay/prune pass. The inspected built-in `Temporal.poll()` producer emits clock fields (unix/local/UTC time, hour, weekday, etc.) but does not emit this expected key. The tests for consolidation manually seed `internal.temporal` rows containing the key rather than invoking the actual Temporal adapter. This is a producer/consumer contract discrepancy on the inspected factory path. Whether another writer supplies the field was not established, so target-host impact and global absence remain UNKNOWN.
- Stage 2 Crystallizer reads `pipeline_events`, not `sense_events`, and selects recent high-magnitude events for a branch when constructing a precipitated belief. This is a second-order consumer of the Stage 2 pipeline log, not a direct sense-table reader. The provenance stream can be carried into the resulting belief when the selected pipeline metadata contains a sensed title.

These paths add three distinct mechanisms to the crosswalk: frequency-derived decay cadence, quiet-triggered decay/pruning based on a temporal payload field, and pipeline-log-driven belief crystallization. No runtime activity or causal effect is claimed from source inspection alone.


### RSS parser identity and malformed-feed qualification — 24 Nov 2026

A closer read of `feeds/_helpers.py::parse_rss()` adds two qualifications to the feed audit:

- The helper does not inspect Feedparser's `bozo` / parse-warning status before accepting `feed.entries`. A malformed or partially parsed response may still yield entries and be treated as an ordinary poll result; no malformed response was supplied or observed in this audit.
- The stored payload contains title, link, summary, published, authors and tags, but omits the RSS/Atom entry's stable `id`/`guid` field. The table therefore receives no dedicated item identity from this helper. Title/link may help downstream matching, but they are not guaranteed unique or stable identifiers.
- Together with the absence of cross-poll deduplication and a unique source-item key in the inspected schema, this means the current source path cannot itself distinguish a repeated item from a newly observed item with the same content. This is a structural limitation, not a measured duplicate-ingestion incident.

Source anchor: `theory_x/stage1_sense/feeds/_helpers.py` at PR #49 source revision `23e327e84b6b26b6e22eb27808514100c2802855`. No malformed-feed test or live feed response was run. No runtime or test behaviour changed.


### Stage 1 scheduler shutdown and Writer-close ordering — 24 Nov 2026

A bounded lifecycle trace from the Stage 1 adapter threads through application shutdown found a possible in-flight write race:

- `_AdapterThread` starts a daemon thread but does not retain the `threading.Thread` handle on the object. Its `stop()` method only sets a stop event; it does not join or otherwise wait for the worker to exit.
- If shutdown begins while an adapter is inside `poll()`, the worker continues through `submit(events)` and updates status before its next loop condition observes the stop event. The stop event shortens the subsequent wait but does not cancel or synchronously drain the in-flight poll/submit.
- `SenseScheduler.shutdown()` calls `stop()` for each adapter thread and returns without joining them.
- `AppState.close()` calls `scheduler.shutdown()` and then immediately calls `close()` on each Writer. `Writer.close()` enqueues its sentinel and joins its worker with a timeout. A Stage 1 adapter that reaches `Writer.write()` after the Writer sentinel has been enqueued could enqueue behind the sentinel, after the Writer worker has exited; its synchronous future wait may then remain unresolved. The exact interleaving depends on shutdown timing and Writer queue state.
- This is a source-confirmed race possibility, not an observed shutdown failure. No thread interleaving was induced, no shutdown test was run, and no target-host impact is claimed.

Source anchors at current PR #49 source head: `theory_x/stage1_sense/scheduler.py` (`_AdapterThread.__init__`, `_run`, `stop`, `SenseScheduler.shutdown`); `gui/server.py` (`AppState.close`); and `substrate/writer.py` (`Writer.close`, synchronous `write`, worker sentinel handling). This lifecycle edge belongs in the Stage 1 forward dependency/termination map and remains an open Phase 0 defect/risk candidate pending authoritative acceptance criteria. No remediation is authorised by this finding.

No runtime, test, schema, flag, host, experiment, merge or deployment change was made.


### Stage 2 → Stage 3 pipeline-hook influence path — 24 Nov 2026

The WorldModel factory constructs `PipelineHooks` and registers the live `DynamicState`, which injects `on_pipeline_event` as the optional callback used by Stage 2 `run_pipeline()`. The callback is reached only after Step F has at least one qualifying branch hit; Stage 2 invokes it for each valenced branch with magnitude at least 0.001. The hook itself ignores magnitudes below 0.6, then tokenises `sensation_source` (the provenance string when present, otherwise the stream name) together with the branch id. It reads up to the 50 newest beliefs with tier <= 7 that are unpaused and unlocked, and calls the promoter's corroboration path when overlap divided by the hook query-token count is at least 0.7. With `NEX5_TIER_CLIMB=1`, it additionally considers up to 500 T6 beliefs.

This means the inspected cross-stage feedback is not a direct semantic comparison between the full sensed payload and belief content: the hook's comparison input is provenance/stream plus branch identity. It is also conditional on a Step-F hit and a high enough magnitude. Internal streams do not reach Step F in the inspected mapper because their magnitude is forced to zero. The hook is a real source-level connection from Stage 2 attention to Stage 3 belief corroboration, but no live invocation or specific belief promotion is established.

The inspected `tests/test_world_model.py` covers the promoter's corroboration threshold and stage labels; the reviewed test slice does not exercise the full DynamicState → Step-F → PipelineHooks integration or verify which source tokens drive corroboration.


### Stage 2/3 startup ordering qualification — 24 Nov 2026

A source-level startup ordering window exists around the pipeline hook. `build_dynamic()` starts its daemon loops, including `_sense_poll_loop()`, before returning. In `run.py`, `build_dynamic()` is called before VoiceClient construction/health check and before `build_world_model()`. The WorldModel factory creates `PipelineHooks` and only then calls `hooks.register(dynamic_state)`, which sets `dynamic_state._pipeline_hook`. The Stage 2 poller uses `getattr(state, "_pipeline_hook", None)` each batch, so rows processed before registration have no Stage 3 corroboration callback. This is a possible startup race/window, not evidence that a qualifying external row was actually processed in that interval; internal rows are magnitude-zero in the inspected mapper. No synchronization or startup barrier was identified in these inspected paths.


### Stage 1 scheduler test-coverage reconciliation — 24 Nov 2026

The existing `tests/test_sense.py` suite explicitly asserts that external adapters are running/enabled immediately after scheduler construction (`test_starts_running_for_external`), matching the constructor's auto-start call and dated inline comment. This makes the paused-by-default package/scheduler docstrings a stale documentation discrepancy; the inspected test suite encodes the auto-start behaviour. The same test file's teardown calls `scheduler.shutdown()`, and its direct `_AdapterThread` test calls `stop()`, but neither asserts that worker threads have terminated before Writers are closed. Thus the shutdown/join risk remains untested by the inspected cases; this is not a claim that the auto-start behaviour itself is untested.


### Additional sense_events consumers: WorldBridge and probe/strike context snapshots — 24 Nov 2026

A wider backward search from the Stage 1 sense table identified two additional consumer families beyond the previously mapped Stage 2 loops, SelfModel and Fountain's direct sampling helpers:

- `run.py` constructs `WorldBridgeSelector` with the sense DB path and passes it into `build_fountain()`. The active Fountain prompt builder calls `select_and_log(mark_injected=True)`; when selections are returned, it appends their formatted text under “What's happening in the world right now”. This is an actual source-level prompt-injection path, not merely a selection log.
- The selector's own module/class docstrings still describe “Phase A: select + log only, no prompt modification” and “Phase B (future): inject”. That prose is stale relative to the inspected caller. The selector is enabled by a module constant, identifies streams with events inside cadence-scaled freshness windows, excludes crypto/market noise and selected internal noise, includes the four qualitative internal streams as eligible candidates, selects at most five streams (with at most two internal), takes the latest row per selected stream, formats within a character budget, applies process-local fingerprint deduplication, and logs the result. The generator passes `mark_injected=True` and then actually appends returned items to its prompt.
- This qualifies the earlier narrower observation that Fountain's quiescent and recent-sample readers exclude `internal.%`: those particular SQL paths do, but WorldBridge's distinct prompt path can include `internal.temporal`, `internal.meta_awareness`, `internal.proprioception` and `internal.interoception` when the selector's freshness/selection conditions admit them. The optional SELF layer is another distinct path.
- `theory_x/probes/context_snapshot.py` reads `sense_events` for a grouped `feed_activity` summary over a configurable time window (default 600 seconds), storing stream counts and latest timestamps. `ProbeRunner.run_probe()` captures this snapshot before sending a probe and persists the fields into `probe_context`. `StrikeProtocol._capture_snapshot()` uses the same function and stores the JSON snapshot in the strike record. These are measurement/context-capture consumers, not evidence that the snapshot itself is fed into the Chat or Fountain cognition prompt.
- The inspected `tests/test_strikes.py` verifies that a wired sense Reader produces the required `feed_activity` snapshot key and that failures can be represented. That test does not exercise WorldBridge's selector-to-Fountain-prompt integration. No claim is made that a dedicated WorldBridge integration test is absent globally; the test search was bounded to the paths inspected here.

Source anchors at PR #49 source revision `e0ab228728094eacc22e3e51f10d5174523c6e18`: `run.py`; `theory_x/world_bridge/selector.py` (active stream selection, cadence/freshness, qualitative internal eligibility and formatting); `theory_x/stage6_fountain/generator.py` (selector invocation and prompt append around lines 4085–4105); `theory_x/probes/context_snapshot.py`; `theory_x/probes/probe_runner.py`; `strikes/protocols.py`; and `tests/test_strikes.py`.

This closes another bounded consumer slice but does not establish target-host activation, which exact rows were selected, whether the resulting text changed a model response, or complete global reader closure. No runtime, test, schema, flag, host, experiment, merge or deployment change was made.


### WorldBridge internal-payload reliance qualification — 24 Nov 2026

The selector formatter confirms that eligible internal rows are not merely counted or logged before prompt assembly:

- `internal.temporal` is reduced to its local ISO timestamp.
- `internal.meta_awareness` is reduced to adapter count plus a running/idle label derived from `sense_adapter_count` and `sense_global_running`. Those source fields ultimately reflect scheduler/control-state telemetry, not verified feed health or successful persistence; WorldBridge can therefore present that narrower control-state signal in Fountain's prompt.
- `internal.interoception` is reduced to total/locked belief counts, dominant tier and non-zero delta.
- `internal.proprioception` has no dedicated formatter branch in the inspected selector. It falls through generic JSON handling; absent title/body/url fields, the payload's first 80 characters can be used as the prompt snippet.
- Consequently, the earlier Stage 4 SelfModel finding that its fetched MetaAwareness payload is not used in the returned SelfModel snapshot must not be generalized to “MetaAwareness is unused”: WorldBridge is a separate, conditional prompt consumer of that stream. Eligibility remains dependent on recent-row freshness, selection cap and formatting.

Source anchor: `theory_x/world_bridge/selector.py` at source revision `e0ab228728094eacc22e3e51f10d5174523c6e18`, `QUALITATIVE_INTERNAL_STREAMS`, `_pick_events()` and `_parse_payload()`. No target-host prompt or selected row was observed.


### Consolidated Stage 1 sense-table consumer index — 24 Nov 2026

The following index consolidates the source paths identified so far. It is a navigational synthesis of inspected paths, **not** a claim that every repository reader has been found.

| Consumer | Input scope | What the code does | Evidence boundary |
|---|---|---|---|
| Stage 2 sense poll loop → A–F pipeline | Every new row by id, including internal and external | Runs branch matching, magnitude/aperture, valence, tree attention, membrane accumulation and pipeline logging | Source path; row-level live effects and retry outcomes UNKNOWN |
| Stage 2 sense distillation loop | Non-internal rows except external.other_mind | Extracts titles; exact/near-duplicate checks; up to five new belief writes per pass; cursor advances across fetched batch | Separate belief-promotion path; does not make A–F processing idempotent |
| Stage 2 BonsaiTree cadence refresh | Previous 24 hours of non-internal rows | Derives per-stream burst/cadence measures that feed branch decay timing | Frequency influence can occur without a Step-F hit; target-host cadence values UNKNOWN |
| Stage 2 consolidation quiet check | Latest internal.temporal row | Looks for seconds_since_last_user_message to trigger extra quiet-period decay/pruning | Inspected Temporal factory producer does not emit that key; another writer/live payload not ruled out |
| Stage 4 SelfModel snapshot | Latest rows for four internal streams | Uses Proprioception, Temporal and Interoception fields; fetches but does not use MetaAwareness payload in that snapshot | Retrieval is not equivalent to reliance |
| Stage 6 Fountain direct sampling | Latest non-internal row, recent distinct-stream sample, optional OVERWHELM and SELF lanes, optional external.other_mind SOCIAL lane | Several separate prompt-context paths with different filters and default-off flags | Target-host flags and exact included rows UNKNOWN |
| WorldBridge selector called by Fountain | Fresh external plus eligible qualitative internal streams | Selects/formats up to five rows (at most two internal) and returned text is appended to the Fountain prompt | Actual source-level prompt contributor; host activation and model reliance UNKNOWN |
| ProbeRunner / StrikeProtocol context snapshot | Grouped feed_activity within configurable window | Captures stream counts/latest timestamps into probe/strike records | Observational record, not direct Chat/Fountain prompt input |

The index reconciles several apparent contradictions: “Fountain excludes internal streams” is true only for its specific non-internal SQL readers, not for WorldBridge or the optional SELF layer; “MetaAwareness is unused” is true only of the inspected SelfModel snapshot mapping, not of WorldBridge's conditional prompt formatting; and Stage 2 attention, belief distillation and cadence derivation are separate consumers with different inclusion and persistence rules.

Remaining closure work: verify the complete repository-wide reader/writer census (including dynamic imports, direct SQLite connections, helpers and non-obvious table aliases), reconcile every faculty edge against the governing architecture documents, and distinguish source presence from target-host activation and causal influence. The current map remains bounded and provisional.


### WorldBridge write-path / One-Pen Rule reconciliation — 24 Nov 2026

A further check against the repository's governing technical specification found a concrete storage-boundary discrepancy:

- SPECIFICATION.md §8 states that each database has exactly one writer thread, all writes submit to the single writer queue, and no code acquires a write lock directly. Its “non-negotiable” rules section further states that every write goes through the queue and direct DB writes are bugs.
- WorldBridgeSelector imports substrate.connect and uses a fresh ordinary connection to the beliefs database inside _log_selection(), executing an INSERT into world_bridge_log directly. It is not passed the beliefs Writer. This is not a read-only connection and does not route the insert through the Writer queue.
- The boot path constructs WorldBridgeSelector and passes it into Fountain; Fountain invokes select_and_log() in prompt construction. Therefore the direct-write method is reachable on the inspected source path, subject to the selector and Fountain path executing.
- The existing test_sense.py one-pen ratchet searches for the literal “import sqlite3” outside substrate. A module using “from substrate import connect” and issuing INSERT is outside the coverage of that specific grep assertion; this observation does not establish that no other guard or test covers it.
- This is source-confirmed divergence from the inspected SPECIFICATION.md contract. Whether there is a later approved exception or superseding authority has not been established. No contention event or live impact is claimed, and no remediation is authorised by this audit.

Source anchors at current PR #49 source revision: SPECIFICATION.md §8 and the non-negotiable rules; theory_x/world_bridge/selector.py (_log_selection); run.py (selector construction); theory_x/stage6_fountain/generator.py (selector call and prompt assembly); tests/test_sense.py (literal import scan). This should be reconciled with the Frozen V2.1 authority before any implementation change.


### Stage 3 retrieval, graph activation and chat-route use — 24 Nov 2026

The source-to-sink trace confirms the production chat route uses Stage 3 belief retrieval through Stage 4 QueryRouter when both membrane and WorldModel are present:

- INSIDE queries take the self-model snapshot plus belief retrieval with `side_filter="INSIDE"`, branch hint `systems`, limit 5; the returned belief block is appended to the reply prompt. OUTSIDE queries use active Dynamic branch hints and limit 8. The fallback path when no membrane is present uses limit 3 plus a chat-only two-token overlap filter and an approximately 800-character cap. These are materially different retrieval policies, not one uniform WorldModel retrieval contract.
- `BeliefRetriever.retrieve()` first constructs keyword-scored candidates. It seeds spreading activation from the top five keyword matches and blends keyword and activation scores (0.4/0.6 when activation exists). However, after activation, it only emits IDs found in the original `row_map` of keyword-scored candidates. A belief reached through graph edges but with zero query-token overlap is therefore not added to the result set. Graph activation reranks/adjusts the keyword candidate pool in this path; it does not expand retrieval recall to graph-only neighbours. Edge traversal timestamps are stamped best-effort on this chat/query path when the retriever has an edges Writer.
- The separate FocalSet path in `gui/server.py` retrieves up to 10 raw beliefs and updates FocalSet plus per-session Working Memory, but its enclosing comment calls this log-only attention tracking and the inspected code does not append those focal items to `belief_text` at this location. Do not conflate this tracking path with the explicit routed belief prompt block.
- The GUI stats path also constructs a separate read-only ActivationEngine for epistemic-temperature reporting, seeding it with the five highest-confidence Tier <=4 beliefs. That dashboard calculation is distinct from the chat retriever's query-seeded activation and does not establish that the dashboard metric affects responses.

Harmonizer coverage requires a separate qualification. Its initial conflict scan is hard-limited to 200 eligible beliefs ordered by ascending tier. The module's own dated comment reports a 3,700+ pool, 600+ Tier 3 beliefs, and that Tiers 5–7 were not reached by the capped scan in the measured state described there. The optional `NEX5_HARMONIZER_PARADOX_FIX` pass rechecks already-open paradox pairs by ID for escalation; it does not broaden initial conflict discovery beyond the 200-row scan. Thus the flag can address escalation of already-known pairs without establishing complete conflict-detection coverage. The historical live counts are source comments, not freshly verified current DB measurements.


### Stage 3 test-boundary review — 24 Nov 2026

The reviewed `tests/test_world_model.py` covers small-population keyword retrieval, basic activation-adjacent retrieval, promotion/decay and a two-belief Harmonizer conflict example. It does not test graph-connected zero-keyword-overlap beliefs being returned, the 200-row/tier-order starvation boundary, or the distinction between initial conflict discovery and the optional direct escalation pass. The chat injection test only asserts that a request does not crash and that the system prompt contains the generic NEX marker; it does not assert the exact routed belief set, INSIDE/OUTSIDE policy, or provenance of the injected belief block. These are bounded observations about the inspected test file, not repository-wide absence claims.


### WorldBridge test-tree spot check — 24 Nov 2026

The recursive tracked-tree inventory at PR #49 source head 90b4ee4cd4dbee06abfdb54fc8f8111264259831 contains no dedicated tests/test_world_bridge*.py module. The inspected tests/test_fountain.py does not reference WorldBridgeSelector, select_and_log or world_bridge_log. By contrast, tests/test_probe_snapshot.py explicitly tests feed_activity grouping by stream and snapshot-window behavior. This narrows the test evidence: the probe/strike snapshot consumer has direct fixture coverage, while the selector-to-Fountain prompt and direct beliefs.db logging paths were not covered by the specific test modules inspected. This is not a claim that no assertion about WorldBridge exists anywhere in the entire suite.


### Stage 4 SelfModel payload-use audit — 24 Nov 2026

The SelfModel reads the latest rows for four Stage 1 streams using four independent `SELECT ... ORDER BY id DESC LIMIT 1` operations. It does not use one shared read snapshot, so the assembled self-state can combine different event times. This is a source-level consistency limitation, not a measured stale-data incident.

The payload-use distinction is narrower than the snapshot field names suggest:

- Proprioception payload fields populate CPU, memory, load and a selected thermal value. The prompt formatter surfaces CPU, memory and load, but not thermal.
- Temporal contributes hour, weekday and local ISO time to the snapshot; the formatter surfaces local time/period, but not weekday.
- Interoception contributes total belief count, tier distribution and locked count; the formatter surfaces total and locked counts, but not the tier distribution.
- The latest `internal.meta_awareness` payload is fetched into `meta_p` but never read. The snapshot's `meta_awareness` fields are instead populated from `DynamicState.status()`. Those fields are returned in the snapshot object but `format_self_state()` does not render them into the INSIDE prompt block.
- The inside-belief query selects at most 30 candidates from an explicit source allowlist, then scores by confidence × tier weight and returns five; the prompt formatter renders at most the first three.

Thus “read”, “mapped into snapshot”, and “surfaced to the model” are separate stages. The inspected router calls `self_model.snapshot()` directly for each INSIDE route; the 30-second cache belongs to `tick()`/state reporting and is not used by that direct route call. No live snapshot contents or prompt payload were captured.


### Stage 4 BehaviouralSelfModel measurement-to-prompt path — 24 Nov 2026

The BehaviouralSelfModel reads the latest 100 `messages` rows with role `nex` and computes hedge/position phrase rates, dominant register, average word count, and a `belief_usage_rate`. The latter increments when the stored NEX response text contains the literal phrase `her current beliefs` or `[tier`. However, `gui/server.py` stores the sanitized generated reply text in role `nex`; the retrieved belief block is assembled earlier into the system prompt. The metric therefore inspects the model's response wording, not the actual prompt's retrieved-belief inclusion or the separately captured `_retrieved_belief_text` provenance. It can undercount genuine prompt injection and may count incidental wording. The metric is subsequently compared to a keystone expectation and can create a Tier 6 `behavioural_observation` belief when it falls below threshold.

This is a measurement-target mismatch in the inspected source path. Whether the metric is used as an intended proxy rather than a literal injection measure requires the governing acceptance language; no behaviour change is proposed. The BehaviouralSelfModel's own metric calculation, its 4-hour belief-writing loop, and its INSIDE-only prompt formatter are separate stages. The formatter uses cached observations from the last 100 responses and surfaces response length, dominant register, hedge rate and a coarse belief-usage statement; it does not render every calculated metric.


### Stage 4 test-coverage boundary — 24 Nov 2026

The inspected `tests/test_behavioural.py` seeds role=`nex` message text directly and checks hedge metrics / that belief-writing does not raise; it does not compare `belief_usage_rate` against the actual per-turn system prompt or `_retrieved_belief_text`. The reviewed `tests/test_self_model.py` and `tests/test_membrane.py` verify snapshot keys, caching, basic sensor payload mapping and route outputs, but do not assert which snapshot fields survive `format_self_state()` into the model prompt, nor that the fetched MetaAwareness payload is unused. These are bounded gaps in the inspected test files, not claims that no other test covers adjacent behaviour.


### Stage 5 → Stage 6 identity-continuity path — 24 Nov 2026

Stage 5 is a boot-time commitment write in the inspected runtime, not a continuously running self-location process. `run.py` calls `SelfLocationCommitment.commit()` after database initialisation and Writer/Reader construction, before Kokoro preload and before later worker/faculty startup. The method writes one locked Tier 1 belief (confidence 0.98, branch `systems`, source `self_location`) with the fixed “I am inside / vantage point” content. The beliefs schema's partial unique index on locked Tier 1 content makes the fixed-content `INSERT OR IGNORE` idempotent against concurrent identical inserts; the method then reads back the source-qualified row. The isolated self-location tests cover the write, repeated-call idempotency and resistance to decisive contradiction. This establishes the intended boot call in source and tests, not that the target host has executed it.

Stage 6's separate `NEX5_IDENTITY_BLOCK` is default-OFF. The generator checks the environment flag directly while building the Fountain prompt; the module's `enabled()` helper is not the call-site gate. When enabled, the block selects one floor claim on every eligible fire: a random authored `identity` claim if present, otherwise a `self_location` claim. It can append up to two further self-model claims with affinity >= 0.40 (configurable), and records each selected belief in the Fountain retrieval manifest. Thus the boot commitment supplies a fallback floor; it does not mean the standing identity block is active by default. The dedicated tests exercise flag-off absence, flag-on floor presence, affinity-controlled extras, self-location fallback and a normal/treatment-arm ablation case.

A treatment-isolation uncertainty remains: `identity_block._ablation_defers()` catches any import or condition-read exception and returns False, which permits the identity block rather than suppressing it. The reviewed tests cover a readable treatment configuration, not a missing/unreadable experiment module or condition lookup failure. Whether fail-open is acceptable must be resolved against the experiment protocol; no treatment state or host flag was inspected. This is recorded as a failure-mode/acceptance question, not a prescribed code change.

The Stage 6 readiness evaluator is a separate gate from identity continuity. The loop is started by `build_fountain()`; each check evaluates Dynamic branch focus/consolidation, total belief count and elapsed time, with optional genius-rate modulation when a conversations Reader is supplied. The generator independently checks readiness >= 0.7 before composing. Mode-level Fountain suppression is checked in the loop. Neither a committed Stage 5 belief nor an assembled identity prompt block alone establishes a Fountain fire or spoken output.


### Stage 6 → Stage 7 sustained-problem feedback path — 24 Nov 2026

The runtime constructs one `ProblemMemory` instance before the later faculty wiring and passes that shared instance into the Fountain builder. The same object is also supplied to other faculties (including CoherenceGate and CounterfactualNode), so its state is not exclusively owned by Fountain.

The Fountain problem-feedback path is conditional, not a general always-on reminder. During prompt construction it is considered only in the existing input-gap/drift branch (`_wb_events` empty); it also requires a 40-minute global cooldown. `ProblemMemory.select_for_injection()` then considers non-template, anchor-passing problems created in the prior 14 days, including closed states, excludes entries with a `problem_injection` observation in the prior eight hours, and refuses to select anything unless at least three candidates survive. It chooses the never/least-recently injected candidate. The prompt carries its title and up to 400 description characters. After a normal LLM output, the generator appends a `problem_injection` observation; it deliberately does not credit the candidate when an earlier alternate-emission path supplied the thought. This separates prompt inclusion from observed follow-through.

The inspected tests `tests/test_problem_memory.py`, `tests/test_fountain.py` and `tests/test_problem_self_gate.py` do not exercise the new `select_for_injection()` pool rules, the full input-gap → Fountain prompt injection → source-tagged observation cycle, the two cooldowns, or the no-credit alternate-emission boundary. This is a bounded test-file observation, not a claim that no other repository test exists. No live candidate pool, prompt, injection, observation or runtime state was captured.


### Stage 8 GoalManager activation and chat influence — 24 Nov 2026

The GoalManager is constructed during boot, registered in the process-lifetime Theory X node registry, and attached to AppState. Its API exposes open/list/resume/priority/complete/cancel operations. The registry module defines a node protocol and `all_nodes()` accessor, but the inspected boot and chat call paths do not show a generic registry dispatcher invoking every registered node. In particular, `GoalManager.tick()` is not called by the inspected chat route; its implementation only refreshes the open-goal cache and returns a summary, while `decay()` is a separate method.

On each chat turn, `gui/server.py` calls `get_active()` and writes the selected goal id/title to `/tmp/nex5_goal_manager.log`. The source comment explicitly records that the prior goal prompt injection was removed (SEAM 3) because a Fountain-internal target bled into chat voice. The selected goal is not appended to the chat `belief_text` at this location. Thus the highest-priority goal is retrieved and logged, not used as a chat instruction in this route. The goal manager remains user/API-manageable and its state is visible in the GUI; its method name `get_active` and docstring “for belief_text injection” should not be mistaken for an active prompt injection path.

The class exposes stale-goal `decay()` (60-day cutoff), but `tick()` does not call it. The inspected `run.py` and chat route construct/use the manager without invoking `decay()`; whether an external maintenance caller invokes it elsewhere was not established. The unit tests exercise CRUD, priority selection, prompt formatting and direct `tick()` calls, but do not assert the production chat route's deliberate non-injection or a boot-time decay schedule. These are source/call-path observations, not evidence of current live goal counts or behaviour.


### Stage 9 GrooveSpotter → Metacognition repeat-ingestion path — 24 Nov 2026

The inspected Stage 9 groove consumer has no consume/acknowledge step. `_detect_groove()` selects up to three `groove_alerts` detected in the last 600 seconds where `acknowledged_at IS NULL`. `tick()` writes each selected row as a new `meta_cognition_events` row, but neither `_detect_groove()` nor `_write_event()` updates the source alert's `acknowledged_at`, and the reviewed `theory_x/diversity/groove.py` producer inserts alerts without any acknowledgement operation. The in-memory `_last_groove_at` field is initialised but has no other reference in the inspected module. Therefore the same still-unacknowledged source alert can be re-ingested on successive chat turns throughout its 600-second lookback window.

This has a second-order consequence: when any groove rows are returned, `tick()` calls `_maybe_engage_stillness()`; that function counts `meta_cognition_events` of type `groove` in the preceding 1,800 seconds and engages a 60-second stillness row once the count reaches three. Re-ingestion of one persistent source alert could therefore satisfy a threshold described as three groove events without three distinct source alerts. This is a source-level repeat-ingestion/threshold-coupling risk, not evidence that it has occurred on the target host. The separate GrooveSpotter producer has an in-memory fingerprint guard against inserting unchanged alert patterns again, but that does not acknowledge an already persisted alert for the Metacognition consumer.

The inspected `tests/test_metacognition.py` verifies one alert produces an event, already-acknowledged alerts are ignored, and old alerts are ignored. It does not tick twice against the same unacknowledged alert, assert source-alert acknowledgement, or prove that one source alert cannot trigger the three-event stillness threshold. The test confirms filtering of pre-acknowledged input, not consumption after processing. No runtime correction or test addition is made in Phase 0.


### Stage 9 Metacognition execution cadence and event lifecycle — 24 Nov 2026

Metacognition is constructed and registered during boot, but the inspected live invocation is explicit: the chat route calls `state.metacognition.tick()` immediately before `format_for_prompt()`. No independent Metacognition worker/daemon is started by the inspected `run.py` or module. “Always-on” in the chat comment therefore means on chat turns, not continuous wall-clock monitoring. The node registry provides registration and enumeration, but no dispatcher was found in the inspected runtime paths that would make registration itself invoke `tick()` or `decay()`.

The 14-day `decay()` method auto-resolves stale `meta_cognition_events`, but the inspected boot/chat wiring does not call it. The live chat call invokes `tick()` only. Consequently, the stale-event cleanup guarantee is not established by the inspected normal runtime path; a separate external maintenance caller remains unverified.

A second repeated-event risk exists beyond GrooveSpotter ingestion. `tick()` calls the Phase 40 history detectors and Phase 41 value-drift detector on each chat turn. The reviewed value-drift contradiction and abandonment branches have no per-event-type cooldown or “same condition already open” guard before `_write_event()`; persistent qualifying windows can therefore generate repeated unresolved rows on successive chat turns. The distance detector has an in-memory eight-sample history, but the other two do not share that same gating. The inspected tests verify individual detector thresholds and event formatting, not repeated ticks under a persistent qualifying condition or an operational decay schedule.

These findings describe event-production cadence and cleanup wiring, not observed production event volume. The detector windows and thresholds retain their own source comments describing some calibration values as provisional; this audit does not validate their live calibration.


### Stage 10 Imagination, WorldBridge prompt path, Counterfactual and Throw-Net — 24 Nov 2026

**NovelAssociation (Stage 10).** The primary `run.py` boot path constructs and starts `NovelAssociation.start_loop()`, then passes that same instance into `AppState`. Its scan reads unpaused beliefs with confidence >=0.15, samples each branch (fully if small, capped at the configured batch size for large branches), embeds cross-branch pairs and writes `synthesises` edges plus `novel_association_log` rows above the similarity threshold. The chat route calls `format_for_prompt()`, which selects the newest fresh unannotated association, marks it annotated, and appends a one-line self-observation to `belief_text`. Thus the Stage 10 result has a direct chat-prompt path; the module's own test file verifies scanning and one-time annotation, but the inspected tests do not assert the full production boot → scan → chat prompt assembly path. The separate `gui.server.build_state()` construction creates a NovelAssociation instance but does not call `start_loop()`; callers using that alternate builder do not receive autonomous association production unless they start it separately. This is a boot-path distinction, not a claim that the main `run.py` path is inactive.

**WorldBridge.** The selector's module/class documentation describes Phase A as selection-and-log only and Phase B as future prompt injection. The actual Fountain generator calls `select_and_log(mark_injected=True)` and, when a non-empty list returns, appends the formatted events under a “What's happening in the world right now” prompt section. `ENABLED=True` in the selector. Therefore the inspected main Fountain path does inject WorldBridge selections into the composition prompt; the Phase A / Phase B comments are stale relative to the callsite. The `mark_injected=True` log flag matches the current append path. This establishes prompt assembly, not that the model attended to or acted on the information. The prior “prompt influence unverified” uncertainty is resolved at the source assembly level.

**CounterfactualNode.** Both the main `run.py` path and alternate `build_state()` path start a daemon loop (default 300 seconds). Each tick selects the single open problem with oldest `last_touched_at`, retrieves up to ten belief candidates via TimeFetch, refines them, and submits buildable candidates to CoherenceGate. ACCEPT decisions are inserted as Tier 3, confidence 0.65 beliefs linked to the problem. The implementation's `_maybe_promote()` returns immediately; the historical three-accept auto-promotion to `review_queue` is explicitly disabled, despite the class docstring still describing promotion. This is deliberate according to the source's dated rationale: the automatic move had hidden still-open problems from the user's focus. No claim is made about live queue contents or acceptance frequency.

**Throw-Net trigger/monitor contract.** CoherenceGate records a trigger for each eligible REJECT and ignores the boolean returned by `record_gate_reject()`. The chat gap-deflection path likewise calls `record_gap_deflection()` without using its threshold boolean. Those methods calculate the documented thresholds (four same-topic gate rejects in 15 minutes; three same-topic gap deflections in 30 minutes) but insert a trigger row for every event. `pending_triggers()` selects every unfired row, with no threshold-state predicate or age cutoff. If `NEX5_THROWNET=1`, the 300-second monitor processes all such rows, including sub-threshold rows; if the flag is unset, the monitor is not started and trigger telemetry accumulates. The primary boot comments explicitly identify the monitor as retired by default and retain the flag as the opt-in restore path. This is a concrete producer/consumer threshold-contract mismatch, but runtime impact is conditional on the flag and current queue contents. A session-row INSERT failure returns before `mark_fired()`, leaving that trigger pending for a later retry; this is a separate persistence/retry edge, not proof of repeated live failure.


### Stage 27 / 29 / 35 affect, drive and prediction causal path — 24 Nov 2026

**PredictiveSubstrate (Phase 35).** The main `run.py` path starts a 300-second background loop. Each tick first verifies due predictions, then may write one `internal_belief` prediction from a centroid of recent beliefs, open-problem titles and the current DriveEmergence topic embedding; it separately may write one `external_input` prediction from recent non-internal sense events and user messages. Verification writes `surprise_events` in dynamic.db and marks the prediction verified. These are persisted prediction/surprise records, not by themselves a belief or a prompt block.

**Surprise promotion boundary.** `theory_x/life/surprise_loop.py` is the separate consumer that converts qualifying surprise rows into Tier 6 `source='surprise'` beliefs for Fountain retrieval. It uses a persisted last-promoted timestamp and requires a flagged event with non-empty predicted and actual content. The inspected main `run.py` contains no import, constructor or start call for this loop. Fountain separately queries beliefs with `source='surprise'` and a six-hour lookback. Therefore the main boot path starts prediction and writes raw surprise rows, but does not demonstrate the promotion step that supplies Fountain's surprise-belief prompt section. A separately managed external caller/process is not ruled out; target-host process inventory was not obtained. AffectState is a separate consumer of raw `surprise_events`, so the absence of the belief-promotion loop does not mean the arousal input is disconnected.

**Prediction verification population mismatch.** External prediction construction explicitly excludes `internal.%` sense streams. Its verification path, however, gathers every `sense_events` row in the prediction window without the same stream exclusion, then combines those rows with user messages when computing nearest actual input. Consequently, internal telemetry can enter the observed comparison set for an `external_input` prediction even though internal streams were excluded from the prediction centroid. Existing `tests/test_predictive_substrate.py` covers creation, verification, flags and idempotency, but the inspected verification cases do not seed an internal sense event alongside external inputs to assert the intended population boundary. Whether the broader verification set is intentional remains unresolved.

**AffectState (Phase 27).** The main boot path starts its 300-second daemon. It integrates belief-count arousal, confidence-weighted lexical valence from high-tier beliefs, recent genius-tag striking rate, stability signals from gate/holding state, and flagged prediction-surprise events. The optional expectations-to-valence mood nudge is gated by `NEX5_EXPECT_MOOD=1` and an eligibility check requiring organic valence evidence of both signs. Its persisted mood/valence line is appended to the normal GUI chat `belief_text` whenever the state row exists. Fountain's separate compositional-emotion mood line is explicitly gated by `NEX5_MOOD=1`; do not conflate the chat route with the Fountain route.

**DriveEmergence (Phase 29).** The main boot path starts its 600-second daemon. It clusters recent eligible beliefs, persists one current drive row, decays or deletes a drive that no longer qualifies, and exposes the topic both to Fountain focus construction and GUI chat `belief_text`. The topic embedding also contributes to the next internal-belief prediction centroid. Thus this mechanism has at least three distinct consumers: Fountain prompt, chat prompt, and predictive centroid.

**CompetingDrives (Phase 29b).** The main boot path starts its 600-second background loop, and Fountain independently calls `compute_now()` immediately before each eligible fire to refresh weights and persist a per-fire `drive_activations` row. The Fountain prompt formatter emits a tension-resolution block only when the set of detected conflict pairs changes; unchanged tension is suppressed. The generator later backfills the activation row with the Fountain event ID. This is an explicit prompt-influence path, but the tests inspected primarily verify component calculations, persistence, and formatter change suppression rather than the complete fire → activation row → attached Fountain event → prompt sequence.


### Stage 26 SelfNarrative and Stage 30 VoiceEngine activation — 24 Nov 2026

**SelfNarrative.** The main `run.py` path constructs and passes SelfNarrative into AppState. Its write API is called by CoherenceGate on qualifying problem-connected ACCEPTs and by NovelAssociation on strong cross-branch pairs; Metacognition also receives it as a write target. The chat route reads recent narrative rows and appends them to `belief_text`, topic-filtered by the first 100 characters of the current prompt. However, the self-rut detector lives in `SelfNarrative.tick()`, and the inspected main boot/chat paths do not call that method or start a SelfNarrative loop. Thus narrative accumulation and prompt retrieval are wired, but the independent rut-notice producer is not demonstrated as active. The module test explicitly verifies that `tick()` is a no-op in the tested call; it does not establish a production caller.

**VoiceEngine.** The main boot path constructs VoiceEngine and AppState defaults `voice_mode` to `use_substrate`. For ordinary non-probe, non-instruction chat, the route calls `query_reply()` in that mode. A candidate scoring >=0.6 is returned directly as the reply (except admin operator-composition mode, where it becomes grounding). The engine records a `user_query` trigger row for every query: successful substrate replies are inserted with `fired=1`; misses are inserted with `fired=0`. This is an additional trigger producer beyond gate rejects and gap deflections. If Throw-Net monitoring is enabled, the current pending query treats every such unfired user-query miss as a pending session candidate, because it filters only `fired=0` and not trigger type/threshold.

There is also a source-comment/call-path discrepancy: the chat handler comment says a substrate miss suppresses LLM fallback in `use_substrate` mode, but after `query_reply()` returns None, `text` remains None and the ordinary `if text is None` composition branch proceeds to call `state.voice.speak()`. In the inspected path, a miss therefore falls through to LLM composition rather than a demonstrated substrate-only deflection. Probe and instruction requests bypass VoiceEngine intentionally. The current source establishes a hybrid retrieval-first/fallback path, not a strict substrate-only mode on misses.



## Chat provenance retry — current-branch source revalidation (24 Nov 2026)

Rechecked against current PR #49 head `6eb6598ba8eae5a6bd0138e54ecd946276490437`. The admin-scoped path still logs the initial reply through `read_provenance()`, evaluates a cue-driven retry with `log=False`, and may deliver that retry if its mirror score is lower. No provenance-log entry is written for the accepted retry. Thus the log is not a delivered-reply sample for retry-accepted turns. This is conditional on `NEX5_PROVENANCE=1`, admin scope and retry acceptance; target-host activation and incidence remain UNKNOWN.

The cue can cause one retry, so this is a conditional generation influence, not merely passive measurement. The module still refuses a self-grounded/authenticity verdict; its grounding hint remains explicitly unproven. Module tests do not cover the route-level retry/log identity.

Current source hashes: `gui/server.py` `5ee8b167f386466c383090445c63a84810bbae52`; `theory_x/stage_provenance/provenance.py` `92671a3e120a1935fab33f6d659ab806f1eb4cc6`; `tests/test_provenance.py` `fcefbeccb6bedc3e20798142814d7b96b4e6dca5`. See DRAFT-012 and the current-branch revalidation in the Reality Report.



## Stage 7 Moltbook — optional activation and external-action boundary (24 Nov 2026)

The main `run.py` path does not construct/start the Moltbook DM listener, DM responder or post loop. The GUI activity endpoint reads optional Moltbook tables only; its tests cover absent/present table handling, not the action loops. External process/manual activation is not ruled out.

If separately launched, the listener can auto-approve profile-filtered DM requests and persist inbound message text to `sense_events` and a pending-reply queue. The responder sanitizes selected inbound/thread text, adds optional belief context, calls the local LLM and sends a reply. The post loop selects recent `fountain_insight` beliefs and can publish them. These are potential external I/O paths, not evidence of host activation.

Two source-level contract discrepancies are recorded in the Reality Report:
- **DRAFT-041:** client dry-run returns a marker without making the external write, but listener/responder/poster callers treat the normal return as approval/sent/posted success in local state.
- **DRAFT-042:** poster's stated priority is word-count first, recency second; implementation sorts recency first, word-count second.

No external request or account access was performed. No runtime changes authorised.



## Stage 37 / Stage 38 / Stage 45 source-to-runtime crosswalk (24 Nov 2026)

**Stage 37 PersonaResponder.** Main boot path starts the sending loop only with `NEX5_PERSONA_RESPONDER=1`; Fountain's receiving SOCIAL block is independently controlled by `NEX5_SOCIAL_N`. The responder uses the same configured voice endpoint/model defaults as NEX, but a distinct persona prompt; it reads recent Fountain thoughts, bouncer-checks its generated reply, and writes accepted text to `sense_events` as `external.other_mind`. If both flags are enabled, Fountain can read this synthetic interlocutor output on later fires. The module explicitly disclaims a second conscious being. The stream name is not evidence of a human, independently operated model or external service. Target-host flags/processes are UNKNOWN. No end-to-end responder→sense→Fountain test was found in the inspected test tree.

**Stage 38 SocialPresence.** Not active in inspected main boot: `_social_presence=None`, and Metacognition consumers are guarded for None. The module/test suite exists, but no production snapshot consumer is demonstrated. This agrees with the explicit cut comment in `run.py`.

**Stage 45 EmphasisEngine / PredictionTracker.** Constructed inside Fountain generator initialization. For each generated thought, score is computed before inserting the current `fountain_events` row, preventing self-inclusion in the 20-fire novelty window. Result is persisted after the fire in `emphasis_log` with the event ID. The three combined signals are goal relevance, locked-keystone self relevance and recent-fire entity novelty; drive resonance is still recorded but excluded from the combined mean after a documented null/negative ground-truth result. Source says observation-only; inspected callsite does not feed score into prompt, generation, branch or selection. Other three signals remain unvalidated.

**Self-maintenance / Warrant boundary.** SelfMaintainShadow is an env-gated log-only would-regulator; its table has no demonstrated reader. WarrantRecorder (default off) records use-day and survival evidence; it is distinct from the Warrant scoring pass. Main `run.py` constructs only the recorder under `NEX5_WARRANT_RECORD=1`, not `WarrantPass`; the scorer has its own `NEX5_WARRANT` gate. Do not conflate evidence accrual with scoring/consumption.

See the Reality Report section “Stage 37 social interlocutor and Stage 45 emphasis” for source hashes, test boundaries and activation qualifications. No runtime changes authorised.
