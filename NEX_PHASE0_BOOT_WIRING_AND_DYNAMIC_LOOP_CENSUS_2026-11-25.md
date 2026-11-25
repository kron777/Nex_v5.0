# NEX Phase 0 — Boot Wiring and Dynamic Loop Census
**Date:** 2026-11-25  
**Source baseline:** `de93134f34adac07a3a41c2a05b33720510a2bfc`  
**Status:** Static source audit only; no runtime, service, database, network, or launcher execution.

## 1. Purpose and limits

This increment follows Producer/Consumer Trace §8 item 5: identify what normal boot constructs and starts, what is conditional, what is merely constructed/on-demand, what is retired, and what shutdown actually stops.

Inspected source includes `run.py`, `gui/server.py`, Stage 1 SenseScheduler, Stage 2 Dynamic builder and life loops, Stage 3 WorldModel builder, Stage 4 Membrane builder, Stage 6 Fountain builder, Stage 7 Moltbook loops, supporting `start_loop()` classes, `substrate/writer.py`, `nex_keepalive.sh`, and the tracked systemd README.

This is not a live host inspection. The repository contains a tracked supervisor script, but the README says the active user systemd units live under `~/.config/systemd/user` and are not tracked. Therefore the script's environment is verified as a declared launch configuration, not proven to be the current process environment. Credentials, installed optional dependencies, actual service invocation, and live thread health remain unknown.

## 2. Startup topology

The normal `run.py` path constructs and starts multiple subsystems before the HTTP server is fully serving:

1. Shared database Writers/Readers and mode/voice state are created.
2. `build_scheduler()` constructs `SenseScheduler`; its constructor starts adapter threads and calls `start_all()`.
3. `build_dynamic()` starts its daemon-loop list.
4. `build_world_model()` starts six daemon threads; one is internally environment-gated.
5. `build_membrane()` starts the BehaviouralSelfModel daemon loop.
6. `build_fountain()` starts a separate daemon thread whose loop is `while True`.
7. `run.py` starts additional faculty loops (resolver, NovelAssociation, SubstrateHarmonic, GeniusTagger, CounterfactualNode, DriveEmergence, CompetingDrives, AffectState, PredictiveSubstrate, SelfMindView, SignalLoop, DiversityLoop, EdgeGeneratorLoop, SpeechQueueConsumer, decoder).
8. Optional loops are started according to environment flags.

This means background work can begin during boot, before the HTTP app is fully available. No runtime execution was performed to observe actual ordering or first-tick timing.

## 3. Stage 1 — SenseScheduler and external feeds

`run.py` constructs the scheduler from the adapter registry. The scheduler source reports 23 adapters. `_AdapterThread` creates daemon threads; internal adapters have their local run event set, while external adapters are enabled when `start_all()` sets the global and per-adapter run events.

There is a source-documentation contradiction:

- The SenseScheduler class docstring says external feeds start paused and only run when enabled through the GUI.
- A `run.py` comment also labels external feeds “PAUSED”.
- The constructor actually calls `start_all()` on boot. A nearby source comment records this as an intentional auto-start change (“per Jon's request”, 2026-05-09), and `run.py` logs “External feeds auto-start”.

**Verified source behavior:** external adapter threads are started by normal boot; this is not behind a separate `NEX5_*` environment flag. Per-adapter enable/weight settings can still affect whether a poll produces data. The active host's adapter credentials and per-mode weights were not inspected.

`SenseScheduler.shutdown()` sets adapter stop events but does not join the adapter threads. The scheduler is the only major subsystem explicitly shut down by `AppState.close()`.

## 4. Stage 2 — Dynamic loop inventory

`build_dynamic()` assembles a shared list of loop functions and starts each in a daemon thread, using a shared stop event. Optional imports are caught and logged; the builder does not expose a complete per-loop health/liveness manifest. The list contains 26 loop functions when all listed imports succeed.

### 4.1 Core Dynamic loops (9)

| Loop | Source cadence | Function / state effect | Belief admission |
|---|---:|---|---|
| `sense_poll_loop` | 2.5 s | Reads new sense events and runs the A–F pipeline | No direct belief insert |
| `aperture_loop` | 5 s | Recalculates membrane aperture | No direct belief insert |
| `accumulator_loop` | 30 s | Decay and flush of dynamic focus state | No direct belief insert |
| `crystallization_loop` | 60 s | Tests sustained focus and invokes Dynamic Crystallizer | New belief path calls CoherenceGate |
| `consolidation_loop` | 60 s | Quiet-triggered Dynamic consolidation | No direct belief insert in the loop wrapper |
| `sense_distillation_loop` | 60 s | Distils titled sense events into `precipitated_from_sense` beliefs | Direct Tier 7 insertion through the shared beliefs Writer; no CoherenceGate, explicitly treated as external perception |
| `snapshot_loop` | 60 s | Writes tree/state snapshots | No belief insert |
| `health_loop` | 30 s | Reports health to the error channel | No belief insert |
| `emergent_drives_loop` | 30 min | Evaluates emergent drives | New Tier 5 belief path calls CoherenceGate |

### 4.2 Life loops (9)

All nine are dynamically imported and appended to the same loop list; there is no per-loop environment flag in the builder.

| Loop | Poll / schedule | Source-level role | Belief effect |
|---|---:|---|---|
| Witness | 30 min poll; daily eligibility | Reflects on blind spots | Direct Tier 6 belief insert; no Gate |
| Pattern | 10 min poll; scheduled twice daily | Synthesises recurring identity/pattern material | Direct Tier 6 belief insert; no Gate |
| Identity | 5 min poll; scheduled four times daily | Builds identity statements from substrate state | Direct Tier 6 belief insert; no Gate |
| Surprise | 5 min | Converts prediction surprise into reflection | Direct Tier 6 belief insert; no Gate |
| Remember | 10 min | Reflective memory loop | Direct Tier 6 belief insert; no Gate |
| Wonder | 15 min | Generates questions from recent experience | Direct Tier 6 belief insert; no Gate |
| Fetch | 30 min | Fetches external material and reflects on it | Direct Tier 6 belief insert; no Gate |
| Affinity | 30 min | Recalculates belief affinity | Updates existing belief rows; not a new-belief producer |
| Scorecard | 1 hour | Refreshes grounded self-scorecard belief | Updates the existing grounded self-belief; not a new generative thought |

The seven direct Tier 6 writers are internal reflective/generative paths, not the external-perception exception used by SenseDistillation. They remain a material part of the Gate 0 admission-contract review.

### 4.3 Additional Dynamic loops (8)

| Loop | Source cadence | Role / effect |
|---|---:|---|
| DailyLife | 60 s | Schedules daily activities; the “outreach” activity logs “would reach out” and does not itself send a Moltbook DM |
| Focus | 60 s | Maintains focus on open problems; cooldowns constrain repeat pings |
| SignalToProblem | 120 s | Converts signal evidence into `open_problems`; not a beliefs-table writer |
| EdgeBuilder | 60 s | Builds `belief_edges`; uses direct SQLite connection in this path, not a new belief insert |
| Retention | 24 h | Reaps retention-scoped records such as gate/throw-net logs |
| Moltbook poster | 60 s enqueue/post tick | Queues candidate thoughts; real posting cadence is separately throttled |
| Moltbook listener | 300 s | Polls external DM/request endpoints and ingests inbound material |
| Moltbook responder | 300 s | Processes pending replies and may send outbound DMs |

The three Moltbook loops are included when the module imports successfully. The Stage 2 builder does not have a separate `NEX5_MOLTBOOK_ENABLED` gate.

## 5. Stage 3 — WorldModel loops (6)

`build_world_model()` starts six daemon threads with a shared state stop event:

| Loop | First delay / cadence | Role | Gate / activation |
|---|---:|---|---|
| BeliefPromoter / decay | 1 h cadence | Corroboration and idle-decay tier movement | Always started; no CoherenceGate |
| Harmonizer | 2 h cadence | Conflict detection and pause/retirement actions | Always started; no CoherenceGate |
| Erosion | 6 h cadence | Erosion state updates | Always started; no CoherenceGate |
| Cross-domain | 6 h cadence | Cross-domain graph work | Always started |
| Synergizer | 25 min cadence | Generates synthesis candidates | New belief path calls CoherenceGate |
| WorldConsolidation | 30 min cadence | Clusters Tier 7 world-beliefs and asks BeliefPromoter to corroborate/promote up to three | Thread wrapper exits if flag is unset; `NEX5_WORLD_CONSOLIDATE=1` arms it |

WorldConsolidation reads unlocked Tier 7 rows with `erosion_stage != 'retired'`, but its candidate query does not exclude paused rows. `BeliefPromoter.corroborate()` also reads by ID without a paused predicate. The normal BeliefPromoter decay query and the `NEX5_TIER_CLIMB` query likewise omit a paused predicate. These are tier/status mutations, not new-belief admissions; they do not call CoherenceGate.

The tracked `nex_keepalive.sh` sets both `NEX5_WORLD_CONSOLIDATE=1` and `NEX5_TIER_CLIMB=1`. If that launcher is active, WorldConsolidation is armed and the Tier 6 extended idle-decay rule is enabled. The actual active service unit was not inspected.

## 6. Stage 4 — Membrane

`build_membrane()` constructs BehaviouralSelfModel with the shared Writer and CoherenceGate, then starts a daemon loop. The first write cycle waits four hours; subsequent cycles use the same four-hour wait. The loop has a local stop event stored on the returned membrane state, but no thread handle is retained for joining. `AppState.close()` does not set that stop event.

The BSM's Gate exception-fallthrough is recorded in the Gate/Writer census and backlog D-39.

## 7. Stage 5–7 and other always-started faculties

### 7.1 Fountain

`build_fountain()` starts a daemon `fountain_loop` with a local `while True` loop. It waits the configured interval (source default 30 seconds), checks mode/fountain state, and calls `FountainGenerator.generate()`. There is no stop event, no stored thread handle and no stop method exposed by the returned Fountain state. The loop is not stopped by `AppState.close()`.

### 7.2 Other `run.py` starts

| Faculty | Startup state | Role / note |
|---|---|---|
| HoldingZoneResolver | Always started | Periodic held-candidate resolution; has a stop mechanism, but `AppState.close()` does not call it |
| NovelAssociation | Always started | Periodic association/edge work; its loop is `while True` and has no stop event |
| SubstrateHarmonic | Always started | Conversation/substrate harmonic logging; not a belief writer |
| GeniusTagger | Always started | Tags recent conversation quality; no Gate admission |
| CounterfactualNode | Always started | Periodic counterfactual work; new belief path calls Gate |
| DriveEmergence | Always started | Updates drive state; content synthesis is separately controlled by `NEX5_DRIVE_CONTENT` |
| CompetingDrives | Always started | Tracks competing drives; no direct beliefs-table insert |
| AffectState | Always started | Updates affect-state records; not a belief writer |
| PredictiveSubstrate | Always started | Prediction/substrate records; not a beliefs-table writer |
| SelfMindView | Always started | Periodic self-state snapshots; not a belief writer |
| SignalLoop | Builder starts its own loop | Signal/pattern records; not a beliefs-table writer |
| DiversityLoop | Always started | CrossbreedGrader, GrooveSpotter, DormancyScanner and ClockRunner |
| EdgeGeneratorLoop | Always started | Separate Stage 3 edge generator, 30 min cadence after initial delay; distinct from Stage 2 EdgeBuilder |
| SpeechQueueConsumer | Started when SpeechConfig.enabled | Source default is enabled; polls pending speech queue and performs playback/status updates |
| Decoder loop | Always started | Separate daemon thread; the only loop with an explicit stop event set by the SIGTERM/atexit path |

There are two distinct edge-building loops: Stage 2 `EdgeBuilder` wakes every minute and creates cross-domain edges through direct SQLite access; Stage 3 `EdgeGeneratorLoop` wakes every 30 minutes after an initial delay and uses the shared Writer for broader typed-edge generation. Their scopes differ, so this audit does not assume they are redundant; both are started.

### 7.3 Optional or conditionally started faculties

| Faculty | Start condition in source | Tracked launcher value | Meaning |
|---|---|---|---|
| WarrantRecorder | `NEX5_WARRANT_RECORD=1` | `1` | Records survival/use evidence in side tables; does not change beliefs |
| PersonaResponder | `NEX5_PERSONA_RESPONDER=1` | `1` | Generates a separate synthetic-interlocutor LLM reply and writes `external.other_mind` sense events; it is not a second conscious entity |
| WorldPredictionLoop | `NEX5_WORLD_PRED=1` | `1` | External-world prediction/scorecard loop |
| SelfPredictionLoop | `NEX5_SELF_PRED=1` | `1` | Self-behaviour prediction/scorecard loop |
| SelfMaintainShadow | `NEX5_SELF_MAINTAIN_SHADOW=1` | `1` | Log-only shadow regulator; its own spec says it does not change beliefs or retrieval |
| WorldConsolidation | Non-empty flag starts wrapper; exactly `1` arms | `1` | Tier 7 clustering and corroboration promotion |
| ThrowNetMonitor | `NEX5_THROWNET=1` | Not set | Source comments call this retired; default is off |
| HotObserver | `NEX5_HOT_OBSERVER=1` inside Fountain | `1` | Conditional direct Tier 3 belief writer |
| Substrate emission | `NEX5_SUBSTRATE_EMIT=1` inside Fountain | Not set | Separate emission path; source default off |
| Fountain social read | `NEX5_SOCIAL_N` | `1` | Reads `external.other_mind` events when present |
| Speech queue | `SpeechConfig.enabled` | Not explicitly set | Launcher removed the old speech-disable assignment; source default remains enabled |

`NEX5_GOVERNOR_OFF=1` is set in the tracked launcher. In the inspected FountainGenerator it disables the adaptive reanimation-cadence branch and its self-rut mirror; it does **not** disable SpeechQueue or the speech governor. The launcher also sets `NEX5_RECONCILE=1`, `NEX5_RECONCILE_WB=1`, `NEX5_ANTILOOP=1`, and `NEX5_DELIVER_N=10`: this disables the substrate-as-voice branch and enables the open-problem reconciliation fallback, prior-work context, anti-repeat prompt material and deliverable forcing after the configured observation count.

## 8. Moltbook external I/O boundary

The Stage 2 builder includes listener, responder and poster loops. Source comments say the integration was rearmed on 2026-09-18. The client defaults `MOLTBOOK_DRY_RUN` to true, but dry-run only suppresses non-GET requests:

- GET requests still reach the external API. The listener can read requests/conversations and write inbound DM material to local sense records even in dry-run.
- In dry-run, the client returns a synthetic success object for POST. Listener, responder and poster callers do not consistently distinguish that object from a real remote success: local DM approval, reply-sent and post-published state can be recorded even though no remote POST occurred.
- The tracked launcher explicitly sets `MOLTBOOK_DRY_RUN=0`. If that launcher is active and credentials are available, real DM approvals, DM replies and thought posts are enabled. This is an external side effect, not a dry-run.
- The actual credential file, service invocation and remote account state were not inspected.

The separate PersonaResponder is local LLM-generated synthetic-interlocutor material written to `sense_events`; `NEX5_SOCIAL_N=1` lets Fountain read it. Its source documentation explicitly distinguishes this from a second conscious being.

## 9. Constructed, on-demand, retired or not started

- `VoiceEngine`, `GoalManager`, `Metacognition`, `SelfNarrative`, `ToolRegistry`, `ToolCaller`, `ProbeRunner`, `StrikeProtocol`, `WorldBridgeSelector` and `StateSnapshotWriter` are constructed or used on demand/event-driven; they are not all independent background loops.
- `WarrantPass` is not started by the inspected `run.py` path; WarrantRecorder is the optional recorder actually started.
- `SocialPresence` is explicitly set to `None` (cut).
- `ArcLoop` is explicitly retired/not started.
- `DriveHistory` is removed from the boot path.
- `ThrowNetMonitor` is source-marked retired and default-off, but the flag can still start it if explicitly set.
- `DailyLifeLoop` has an “outreach” activity description, but its implementation records “would reach out”; it does not itself send a Moltbook DM.

## 10. Shutdown ownership and race

The shutdown path does not quiesce the complete loop set before closing Writers.

- `gui/server.py::AppState.close()` calls `scheduler.shutdown()`, then closes each Writer. It does not set the DynamicState, WorldModelState or Membrane stop events and does not call stop methods for SignalLoop, DiversityLoop, EdgeGeneratorLoop, SpeechQueueConsumer, Resolver, NovelAssociation or the other `run.py` loops.
- `run.py` SIGTERM handling sets the decoder stop event, waits 1.5 seconds, calls `state.close()`, then calls `os._exit(0)`. The atexit path likewise does not stop the full loop set.
- The Fountain loop is an uninterruptible `while True` daemon. NovelAssociation and several other faculty loops also have no stop event. Other loops do have local stop events/methods, but the shutdown path does not invoke them.
- `SenseScheduler.shutdown()` sets adapter stop events but does not join adapter threads.
- `substrate/writer.py::Writer.close()` puts a sentinel on the queue and joins the worker for up to 10 seconds. `submit()` has no closed-state guard; a write submitted after the sentinel/worker exit can leave its Future waiting indefinitely. `AppState.close()` closes Writers sequentially.
- The tracked `nex_keepalive.sh` supervisor waits up to 15 seconds after SIGTERM, then sends SIGKILL if the child remains alive. The application may be closing several Writers sequentially, each with a 10-second join timeout.

**Confirmed source-level risk:** background producers are not stopped/joined before Writer shutdown; a late write can race with the sentinel/closed worker, and the supervisor's 15-second kill deadline may expire before sequential Writer close calls complete. This is not evidence that a particular live shutdown failed; no shutdown was executed.

## 11. Phase 0 findings and decision boundaries

### Confirmed source facts

1. Stage 2 starts up to 26 daemon loops; seven life loops directly insert Tier 6 beliefs without CoherenceGate.
2. Stage 2 SenseDistillation directly inserts Tier 7 beliefs from external sense events without Gate, as an explicit perception path.
3. Stage 3 starts six threads; the tracked launcher arms WorldConsolidation and Tier 6 extended idle-decay behavior.
4. Stage 4 starts a four-hour BehaviouralSelfModel loop; its Gate exception-fallthrough is documented separately.
5. Fountain starts a daemon loop with no stop path.
6. The tracked launcher enables multiple optional loops and sets `MOLTBOOK_DRY_RUN=0`; actual host use remains unverified.
7. The tracked launcher enables HotObserver, WorldConsolidation, WarrantRecorder, PersonaResponder, WorldPrediction, SelfPrediction, SelfMaintainShadow, and external Moltbook POSTs.
8. AppState shutdown does not stop the complete background loop set before closing Writers.

### Unverified

- Whether the tracked `nex_keepalive.sh` is the exact script invoked by the active user systemd unit.
- Which optional packages, API credentials, and external endpoints are available on the live host.
- Whether the active service has the exact environment assignments in the tracked script.
- Whether any of the identified loops have actually run, written rows, or produced external posts/DMs in the current runtime.
- Whether the documented loop cadence and host clock align in the live deployment.
- Whether paused-state exclusion is intended for all promotion/decay paths.
- Whether the external I/O and synthetic-interlocutor behavior remain authorized in the current Frozen V2.1 design.

### No action taken

No source/runtime code, flags, database rows, services, systemd units, tests, experiments, probes, baselines, or deployments were changed or run in this increment. This document records static source evidence only.
