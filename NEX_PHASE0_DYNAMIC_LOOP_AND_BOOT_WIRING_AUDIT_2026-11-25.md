# NEX Phase 0 — Dynamic Loop and Boot-Wiring Audit (25 November 2026)

## Scope and evidence boundary

Static source audit against host source baseline `de93134f34adac07a3a41c2a05b33720510a2bfc`, following Producer/Consumer Trace Tranche §8 item 5. This increment inventories:

- the dynamically imported Stage 2 loop registrations in `theory_x/stage2_dynamic/__init__.py`;
- the six World Model loops and the Membrane behavioural loop;
- the principal startup-wired loops/faculties in `run.py`;
- environment, import, service, and mode gates visible in those paths;
- shutdown coordination visible in `AppState.close()` and the SIGTERM handler.

This is not a live process inspection. It does not establish current environment-variable values, which imports succeeded on the host, which threads are alive, external service status, or actual database activity. No runtime state, code, tests, flags, DBs, or deployment settings were changed.

## 1. Stage 2 factory: 26 registered daemon loops

`build_dynamic()` constructs the tree/state, assembles a list of loop callables, and then starts each collected callable in its own daemon thread. The nine core registrations are unconditional. The additional life/faculty registrations are attempted through guarded imports; if an import fails, the exception is logged and that loop is omitted, while the rest of the factory continues.

### 1.1 Nine core loops

| Loop | Source cadence / action | Principal effect |
|---|---|---|
| `dynamic.sense_poll` | 2.5 s | Reads sense events in cursor order and runs the A–F attention pipeline; writes pipeline/cursor telemetry and updates in-memory tree/membrane state |
| `dynamic.aperture` | 5 s | Recalculates membrane aperture from tree texture |
| `dynamic.accumulator` | 30 s | Decays tree/membrane accumulation, refreshes cadence periodically, flushes accumulator entries |
| `dynamic.crystallization` | 60 s | Checks branches for crystallization; the crystallizer has its own gate path |
| `dynamic.consolidation` | 60 s | Runs quiet-triggered tree consolidation |
| `dynamic.sense_distillation` | 60 s | Extracts eligible external sense titles and directly inserts Tier 7 `precipitated_from_sense` beliefs; this is the previously documented gate-bypass path |
| `dynamic.snapshot` | 60 s | Writes tree snapshots and tier-count history |
| `dynamic.health` | 30 s | Emits DynamicState health telemetry |
| `dynamic.emergent_drives` | 12 h initial wait, then scans/applies proposals | Scans drive pressure and applies approved proposals; normal factory passes the CoherenceGate reference |

The module-level docstring still enumerates only eight loops and omits `_emergent_drives_loop`; the executable registration list contains nine. This is a documentation drift, not a runtime defect by itself.

### 1.2 Fourteen additional life/faculty registrations

| Loop | Import registration | Source cadence / behaviour |
|---|---|---|
| `life.witness_loop` | guarded import | 30 min tick; composes blind-spot observations from prior patterns; source describes a 24 h decision rhythm |
| `life.pattern_loop` | guarded import | 10 min tick; composition restricted to local hours 03 and 15 |
| `life.identity_loop` | guarded import | 5 min tick; composition restricted to local hours 00, 06, 12 and 18 |
| `life.affinity_loop` | guarded import | 30 min tick; recalculates and updates existing belief affinity |
| `life.scorecard_loop` | guarded import | Runs once immediately, then hourly; invokes `ground_self_belief.refresh_self_belief()` |
| `life.surprise_loop` | guarded import | 5 min tick; promotes eligible prediction-surprise events into beliefs |
| `life.remember_loop` | dynamic `__import__` | 10 min tick; selects an older and a recent belief and composes a connection |
| `life.wonder_loop` | dynamic `__import__` | 15 min tick; selects a recent entity and composes a question |
| `life.fetch_loop` | dynamic `__import__` | 30 min tick; fetches an eligible URL from a recent sense event and composes a response |
| `life.daily_life` | guarded import | 60 s tick; fires scheduled local-time activities once per date |
| `sustained.focus_loop` | guarded import | 60 s tick; updates current focus, appends relevant Fountain observations, and can surface a stuck-problem message into conversations |
| `signals.signal_to_problem` | guarded import | 120 s tick; converts eligible signal rows into open problems under its internal confidence/quality controls |
| `diversity.edge_builder` | guarded import | 60 s tick; heuristic edge proposals |
| `stage_gate.retention` | guarded import | Daily wait; prunes old gate-decision and empty throw-net-session rows in batches |

The seven direct life-loop belief writers already identified in the earlier producer audit (witness, pattern, identity, surprise, remember, wonder, fetch) are among these registrations. Affinity mutates existing beliefs; it is not a new-belief producer. Scorecard calls a helper that refreshes the tested self-belief. Daily life, focus, signal-to-problem and edge-builder have their own distinct tables/side effects and should not be collapsed into the belief-producer category.

### 1.3 Three Moltbook registrations

If `theory_x.stage7_moltbook` imports successfully, `get_moltbook_loops()` appends three more loop callables:

- `moltbook.poster` — wakes every 60 s; queues eligible Fountain insights and checks the post interval.
- `moltbook.listener` — polls every 300 s; reads remote activity and can write inbound messages to `sense_events` and `moltbook_pending_replies`.
- `moltbook.responder` — polls every 300 s; composes replies to pending DMs and calls the remote DM-send endpoint.

These threads are registered without a dedicated NEX5 enable flag in the inspected factory. Their work is service-gated by `_ensure_client()`: credentials must load and the remote status must report `claimed`. The client defaults `MOLTBOOK_DRY_RUN` to `1`; in dry-run mode non-GET requests are logged/mocked, while GET status/read calls still reach the external service. Setting `MOLTBOOK_DRY_RUN=0` permits non-GET external requests. The effective credential, service and dry-run state on the host are UNKNOWN.

**Total:** 9 core + 14 additional life/faculty + 3 Moltbook = **26 loop registrations** in the executable factory list, conditional on the corresponding imports succeeding. The source does not prove all 26 threads actually started on the live host.

## 2. World Model and Membrane loops

### World Model

`build_world_model()` unconditionally starts six daemon threads:

1. `world_model.decay` — hourly belief decay/demotion pass.
2. `world_model.harmonizer` — every two hours conflict detection/resolution.
3. `world_model.cross_domain` — every six hours cross-domain edge work.
4. `world_model.erosion` — every six hours provenance-stage updates.
5. `world_model.synergizer` — checks on a 60 s loop and synthesizes on its 25 min timer; candidate goes through CoherenceGate.
6. `world_model.world_consolidation` — thread is started, but immediately returns if `NEX5_WORLD_CONSOLIDATE` is empty. Any non-empty value arms its 30 min loop; the source comment distinguishes dry reports from `=1` arming. The host value is unknown.

Thus “six threads started” is not the same as “six active periodic workloads.”

### Membrane

`build_membrane()` constructs SelfModel and QueryRouter. When a conversations reader is present, it also constructs BehaviouralSelfModel and starts `membrane.behavioural`. The loop waits four hours before its first write attempt, then calls `write_behavioural_beliefs(..., coherence_gate=...)`. Normal startup provides the conversations reader, but whether the loop has reached a tick on the live host is unknown.

## 3. Remaining boot-wired faculties and their activation classes

The following separates actual thread-start calls from construction/wiring. “Unconditional” means the startup code attempts it without a dedicated environment gate; guarded imports and runtime dependencies can still prevent successful operation.

### 3.1 Startup loops attempted without a dedicated environment gate

| Component | Startup evidence | Classification |
|---|---|---|
| SenseScheduler | `build_scheduler()` called; factory starts adapter threads | External/internal sense intake; per-adapter connectivity is runtime-dependent |
| HoldingZoneResolver | `start_loop()` called after transformer wiring | 300 s resolver/fade/reshape worker |
| NovelAssociation | constructed, then `start_loop()` | 30 min association scan and prompt annotation |
| SubstrateHarmonic | constructed, then `start_loop()` | 300 s log/metric worker; source describes log-only phase |
| GeniusTagger | constructed, then `start_loop()` | 60 s tag scoring plus initial backfill |
| CounterfactualNode | constructed, then `start_loop()` | Autonomous 300 s candidate cycle; gate supplied |
| DriveEmergence | constructed, then `start_loop()` | 600 s background tick |
| CompetingDrives | constructed, then `start_loop()` | 600 s background tick |
| AffectState | constructed, then `start_loop()` | 300 s background tick |
| PredictiveSubstrate | constructed, then `start_loop()` | 300 s autonomous cycle |
| SelfMindView | constructed, then `start_loop()` | 300 s autonomous cycle |
| Fountain | `build_fountain()` starts daemon `fountain_loop` | Repeated mode-aware readiness checks and generation; interval/mode can suppress fires |
| SpeechQueueConsumer | starts only when `SpeechConfig.enabled` | Config default is enabled; Kokoro preload failure sets backend to None, so effective playback still depends on backend availability |
| SignalLoop | `build_signal_loop()` constructs and starts it | 60 s signal detection and pattern matching |
| DiversityLoop | constructed, then `.start()` | 60 s groove/dormancy/clock processing |
| EdgeGeneratorLoop | constructed, then `.start()` | 30 min belief-edge generation (builder source/log) |
| Decoder loop | daemon thread explicitly started after AppState construction | 30 s Fountain-output tokenization |

The scheduler's source comments and startup log describe external feeds as auto-starting; the current process's adapter connection state is not established here.

### 3.2 Explicit environment-gated startup

| Component | Gate in source | Default source behaviour |
|---|---|---|
| ThrowNetMonitor | `NEX5_THROWNET=1` | Constructed but autonomous monitor loop not started unless set |
| WarrantRecorder | `NEX5_WARRANT_RECORD=1` | Not imported/constructed/started unless set |
| PersonaResponder | `NEX5_PERSONA_RESPONDER=1` | Not imported/constructed/started unless set; interval override `NEX5_PERSONA_INTERVAL`, default 600 s |
| WorldPredictionLoop | `NEX5_WORLD_PRED=1` | Off unless set |
| SelfPredictionLoop | `NEX5_SELF_PRED=1` | Off unless set; interval override `NEX5_SELF_PRED_INTERVAL`, default 900 s |
| SelfMaintainShadow | `NEX5_SELF_MAINTAIN_SHADOW=1` | Off unless set; source describes log-only shadow behaviour |
| WorldConsolidation loop body | non-empty `NEX5_WORLD_CONSOLIDATE` | Thread exists but body returns immediately when empty |

Additional subfeature controls do not gate the containing faculty's startup: examples include `NEX_TAG_FEEDBACK_ON` inside identity composition, `NEX5_DRIVE_CONTENT` inside DriveEmergence, and `NEX5_SOCIAL_N` on the Fountain social input path. Their effective values are unknown.

### 3.3 Constructed/wired but not started as background loops in the inspected startup path

- SelfNarrative, ProblemMemory, GoalManager and Metacognition are constructed and passed to dependent faculties/Chat; no own `.start_loop()` call appears in the inspected `run.py` path.
- VoiceEngine is constructed and supplied to AppState; it is invoked by the Chat route rather than started as a daemon loop.
- ToolRegistry/ToolCaller, StrikeCatalogue/StrikeProtocol and ProbeRunner are constructed/wired as request- or caller-driven services; no autonomous loop start appears in this path.
- ResumptionSeeder runs once during boot. StateSnapshotWriter and WorldBridgeSelector are constructed and supplied to Fountain; they are not separately started as their own daemon loops.
- SocialPresence is explicitly assigned `None`; its historical loop is described as cut/removed.
- ArcLoop is explicitly `None`; its historical loop is described as cut/removed.
- GrooveBreaker instantiation is removed; its module is described as disabled/no-op in the startup comments.
- DriveHistory is described as removed from startup because its output had no consumer.

This classification is specific to the inspected `run.py` path; another entry point or manual invocation could differ.

## 4. Shutdown coordination boundary

`AppState.close()` explicitly shuts down the SenseScheduler and closes the shared Writers. It does not iterate through or stop the other loop/faculty objects in AppState.

The custom SIGTERM handler waits 1.5 seconds, sets the decoder stop event, calls `state.close()` (which drains Writers and shuts down the scheduler), then calls `os._exit(0)`. It does not signal the Stage 2, World Model, Membrane, Fountain, SpeechQueueConsumer, Signal, Diversity, EdgeGenerator, or the other started faculty loops before process exit.

The worker threads are predominantly daemon threads, so process exit terminates them. The code comment's intended guarantee is that in-flight work gets a short enqueue window and Writer queues are drained; it is not a coordinated per-faculty shutdown/join protocol. Whether this produces lost in-flight non-Writer work, partial external operations, or any practical incident is not established by static source.

## 5. Test coverage observations

The inspected tests cover substantial component-level behaviour:

- `tests/test_dynamic.py`: Bonsai, A–F pipeline, crystallization, consolidation, cursor persistence and GUI status; it does not verify the full 26-loop factory registration/startup set.
- `tests/test_world_model.py`: retrieval, prompt formatting, promotion, decay and harmonizer behaviour; it does not verify the six-thread boot lifecycle or environment gate on world consolidation.
- `tests/test_membrane.py`: classifier, SelfModel, router, retrieval side filtering and endpoints; it does not verify the delayed behavioural-loop lifecycle.
- `tests/test_signals.py`: detector/template logic and SignalLoop start/status/tick behaviour.
- `tests/test_diversity.py`: diversity component logic; no complete run.py startup/shutdown lifecycle.
- `tests/test_retention_reaper.py`: pruning behaviour; not dynamic factory registration or daily loop scheduling.
- The inspected tree has no single startup integration test that asserts all boot-wired loops, env-gated loops, service-gated loops, and shutdown coordination as one system.

These are test-scope observations, not a request to add tests or alter the startup architecture before Gate 0.

## 6. Phase 0 disposition

### Confirmed source facts

- Stage 2 executable factory registers 26 daemon loop callables when every guarded import succeeds; 9 are core, 14 are additional life/faculty loops, and 3 are Moltbook loops.
- Import failures omit individual optional loops and log warnings; the remaining dynamic loop list is still started.
- World Model starts six thread wrappers, one of which can return immediately based on `NEX5_WORLD_CONSOLIDATE`.
- Membrane starts a four-hour-delayed BehaviouralSelfModel writer when conversations are wired.
- `run.py` starts a broader set of loops and constructs several request-driven or passive faculties; source construction alone does not make a faculty an autonomous worker.
- Several explicitly environment-gated loops default off in source; host flag values are unknown.
- Moltbook loops are registered by default if import succeeds, but external work depends on credentials/claimed status; write requests are dry-run by default unless `MOLTBOOK_DRY_RUN=0`.
- Shutdown drains Writers and stops the scheduler/decoder only; other daemon loops are not individually stopped/joined before `os._exit(0)`.

### Unverified

- Actual host thread inventory, successful imports, active loop set, tick counts, and current state of each environment/service gate.
- Whether the host has Moltbook credentials, claimed status, or dry-run disabled.
- Whether any worker was mid-write or external request at shutdown.
- Whether the governing doctrine requires a unified lifecycle manager, all loops to be explicitly stopped, or particular faculties to be disabled by default.
- Whether any loop's actual functional influence is material; thread start is not proof of causal contribution.

### Boundary

No implementation changes proposed. Do not disable, re-enable, consolidate, retime, or refactor loops; do not change environment gates or shutdown behaviour until the governing Frozen V2.1 / roadmap authority and Gate 0 founder decision are recovered or explicitly re-established.
