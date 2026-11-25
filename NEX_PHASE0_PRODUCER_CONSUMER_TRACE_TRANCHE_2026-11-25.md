# NEX Phase 0 — Producer/Consumer Trace Tranche (25 November 2026)

## Scope and evidence boundary

This is a bounded source-level continuation of M0.3–M0.4, grounded against the active host source branch `claude/nex-continuity-wire` at `de93134f34adac07a3a41c2a05b33720510a2bfc`. It traces the first connected chain:

`SenseScheduler → sense_events → Dynamic A–F pipeline / sense distillation → beliefs and dynamic state → World Model / CoherenceGate / Holding Zone → Fountain and prompt-facing self-model`.

It is **not** the complete producer/consumer DAG. It does not establish which threads are currently running, what the live DB contains, whether any optional environment flag is set, or whether a component has a measurable behavioural effect. All conclusions below are static source observations unless explicitly marked otherwise. Do not infer L3/L4 from source presence.

No source/runtime behaviour was changed in this tranche. The Gate's documented perception exception and direct-write paths are recorded as evidence questions, not silently classified as spec violations: the exact Frozen V2.1 specification and founder approval record remain unavailable.

## 1. Sense intake

- `run.py:108–111` constructs the scheduler from shared substrate writers/readers.
- `theory_x/stage1_sense/scheduler.py:136–153`: `SenseScheduler.__init__()` builds one `_AdapterThread` per supplied adapter and calls `start_all()`. The source comment explicitly says external feeds auto-start on boot per Jon's 2026-05-09 request. `start_all()` enables external adapters; internal sensors are not controlled by the external-feed switch.
- Current branch inventory: 28 adapters (4 internal, 24 external), as reconciled in the Phase 0 crosswalk. Their output sink is `sense_events` in `sense.db`.

**Evidence limit:** source wiring establishes the configured startup action, not whether any particular adapter successfully connected or emitted events during the current host session.

## 2. Sense events have two distinct downstream paths

### 2.1 Dynamic attention pipeline

- `theory_x/stage2_dynamic/__init__.py:274–300`: `_sense_poll_loop` reads `sense_events` in ascending ID order, using a cursor stored in `dynamic_cursor` in `dynamic.db`; it passes each row to `run_pipeline()`.
- `theory_x/stage2_dynamic/pipeline.py:20–33, 39–116`: the A–F path logs intermediate `pipeline_events` to `dynamic.db`. It unpacks stream/value/provenance, matches branches, computes magnitude, applies membrane aperture, computes valence, then attends the Bonsai tree and adds to the membrane accumulator. The optional hook runs after step F only when hits are positive.
- The dynamic loop set begins with nine fixed loops in `stage2_dynamic/__init__.py:459–520` (sense poll, aperture, accumulator, crystallization, consolidation, sense distillation, snapshot, health, emergent drives). Further loops are conditionally imported/appended; the exact set is import-dependent. The factory starts each collected function in a daemon thread near the end of the factory.
- This path changes in-memory attention/tree/accumulator state and writes dynamic event/cursor/snapshot records. The A–F pipeline itself does **not** write a belief for every sense event.

### 2.2 Sense distillation directly writes beliefs

- `theory_x/stage2_dynamic/__init__.py:170–272`: `_sense_distillation_loop` independently reads external `sense_events`, advances a separate cursor, extracts one title per eligible event, deduplicates against recent `precipitated_from_sense` beliefs, and caps new writes per pass.
- The query excludes `internal.%` and `external.other_mind`.
- On a new title it directly inserts a Tier 7 belief with source `precipitated_from_sense` through the beliefs writer. This path does **not** call `CoherenceGate.check()`.
- The source comment explains the intended distinction: external perceptions are treated as substrate content rather than internally generated thoughts.

**Unresolved governing question:** the gate module describes a universal gate with no generative bypass, while this perception-to-belief path explicitly bypasses it. The design rationale is visible in source, but whether this is an authorised scope exception cannot be decided without Frozen V2.1 and the founder's acceptance record.

## 3. Dynamic crystallization is a separate gated belief path

- `theory_x/stage2_dynamic/crystallization.py:45–91` samples each Bonsai branch's focus history and calls `_crystallize()` when the cumulative threshold and cooldown conditions are met.
- `crystallization.py:170–218`: `_write_belief()` creates a `ThoughtPacket` with source `stage2_crystallization`, confidence 0.15, and branch ID. If the gate outcome is not ACCEPT, the write is withheld. On ACCEPT, it inserts a Tier 7 belief with source `precipitated_from_dynamic`.
- This is distinct from sense distillation: one path promotes extracted external event titles directly; the other crystallizes accumulated branch attention and consults the gate.

## 4. World Model: belief maintenance, synthesis, and graph relations

`theory_x/stage3_world_model/__init__.py:245–310` wires the following components and starts six daemon loops:

- **Decay** — hourly calls `BeliefPromoter.decay_pass()`, which demotes eligible idle Tier 5–7 unlocked beliefs. `promotion.py:198+`. Environment flags alter some eligibility rules; their live values are unknown.
- **Harmonizer** — every two hours scans belief conflicts, records first detections as paradoxes, and escalates after the incubation interval. `harmonizer.py:335–370`. It can set a temporary disturbance on the WorldModelState.
- **Cross-domain** — every six hours scans a bounded set of Tier 3–7 beliefs and writes `cross_domain` edges for qualifying cross-branch keyword overlap. `harmonizer.py:372–435`.
- **Provenance erosion** — every six hours checks reinforcement counts and advances eligible beliefs through `external → nex_absorbed → nex_integrated → nex_core`, with protected sources and locked beliefs excluded. `erosion.py:1–180`.
- **Synergizer** — timer-triggered every 25 minutes (the retired quiet trigger is not used). It synthesizes from belief pairs; `synergizer.py:90–110` sends the candidate through CoherenceGate and only proceeds to the Tier 6 `synergized` belief insert at approximately line 131 on ACCEPT. It then records parent lineage.
- **World consolidation** — the thread is constructed, but its loop returns immediately unless `NEX5_WORLD_CONSOLIDATE` is non-empty; if armed it wakes every 30 minutes. Its live flag state is unknown.

### Retrieval and prompt consumption

- `theory_x/stage3_world_model/retrieval.py:1–160` implements a belief retriever: it reads eligible unpaused beliefs with `tier <= 6`, scores keyword overlap and confidence, can apply membrane-side filtering, and optionally blends spreading activation. It returns selected beliefs for prompt injection; retrieval/formatting alone does not prove the resulting reply used or was changed by those beliefs.
- Exact per-caller retrieval mapping (Fountain, Chat, tools, strikes and other callers) remains part of the outstanding crosswalk.

## 5. CoherenceGate, Holding Zone and Reshape

### Gate evaluation and side effects

- `run.py:124–171` constructs one `CoherenceGate`, one `HoldingZone`, and one `HoldingZoneResolver`, connects them, then starts the resolver loop after the voice client is available.
- `theory_x/stage_gate/coherence_gate.py:208–288`: `check()` evaluates a `ThoughtPacket`, records the decision in `gate_decisions`, and applies outcome side effects:
  - REJECT: optionally records a trigger for the throw-net detector (excluding throw-net's own resubmissions).
  - HOLD: persists the candidate in `held_thoughts`.
  - RESHAPE: persists a `reshape_pending` row.
  - ACCEPT: calls `resolver.on_gate_accept()`.
- `coherence_gate.py:291+` evaluates against locked anchors, recent beliefs, active goals and problems, with redundancy/contradiction/HOLD/connection/RESHAPE logic.
- **Fail-open behaviour:** if `_evaluate()` raises, `check()` records the error and returns ACCEPT with reason `gate_error_fallback`. This is an availability policy, not fail-closed rejection. It is a material property to retain in the reality report; whether it is acceptable is a founder/spec question.

### Holding and resolution

- `theory_x/stage_gate/holding_zone.py:59–86` persists HOLD candidates; corroboration/contradiction scans operate over active held rows.
- `holding_zone.py:170–199` can promote a held candidate to a belief directly. This is invoked by the resolver after three corroborating ACCEPT events, then the held row is marked accepted; contradictory ACCEPT events mark held rows rejected. See `resolver.py:60–115`.
- `resolver.py:117–142` starts a five-minute daemon loop. `tick()` fades stale held rows and processes reshape-pending rows when transformer and gate are wired.
- `resolver.py:163–205`: up to ten pending rows are transformed and resubmitted through the gate. The original row is marked `reshaped` when a transformed packet is returned, regardless of the new packet's gate outcome; that outcome is represented by the new gate decision/side effects, not by the old row's terminal status.
- The CoherenceGate module header's statement that HOLD/RESHAPE are only logged is stale: the above persistence/processing calls are present in executable code.

### Gate producer paths verified in this tranche

The following concrete callers have been read and verified; this is **not yet an exhaustive caller census**:

1. Dynamic crystallizer → gate → Tier 7 `precipitated_from_dynamic` belief on ACCEPT.
2. World Model synergizer → gate → Tier 6 `synergized` belief on ACCEPT.
3. Fountain generated thought → quality checks → `FountainCrystallizer` gate (source `fountain`) → Tier 6 belief insert on ACCEPT; see `stage6_fountain/crystallizer.py:383–400, 447–454`.
4. Fountain drive probe → gate (source `drive_probe`); the probe itself is delivered to gate/holding/resolution rather than directly inserted by that function.
5. Reshape resolver → transforms held candidate → re-submits through gate.

The sense-distillation path is a verified direct-to-beliefs bypass. Additional direct belief writers and gate callers across the remaining faculties still need inventory.

## 6. Membrane self-model and prompt-facing state

- `theory_x/stage4_membrane/__init__.py:78–112` constructs a `SelfModel`, a `QueryRouter`, and (when conversations reader exists) a `BehaviouralSelfModel`; it starts the behavioural loop.
- `stage4_membrane/self_model.py:47–190`: SelfModel reads the latest internal proprioception, temporal and interoception sense streams; reads DynamicState status for pipeline/attention data; and selects inside beliefs from `beliefs.db`. It caches the snapshot for 30 seconds. `format_self_state()` is a formatting helper; its exact route-by-route injection points are not established in this tranche.
- `stage4_membrane/behavioural_self_model.py:66–115, 209–260`: BehaviouralSelfModel reads the last 100 NEX messages from `conversations.db` and derives response-style metrics; `format_for_prompt()` exposes those metrics as text.
- The full route-by-route mapping of these formatted blocks into Voice/Chat prompt assembly, and whether each is present on each route, remains outstanding.

## 7. Additional direct-write path discovered

While tracing Fountain source, `theory_x/stage6_fountain/generator.py:2910–2935` was found to write a Tier 6 `self_rut_notice` belief directly when its internal governor detects a low STRIKING-tag rate and the two-hour throttle permits. This code path does not pass the candidate through CoherenceGate in the shown implementation. It is a distinct source from the Fountain's normal generated thought and from the drive-probe gate path.

This is recorded as a source fact and an additional gate-scope question, not labelled a defect until the governing spec and full producer inventory are reconciled.

## 8. Evidence gaps / next bounded increment

1. Complete gate caller census and direct `INSERT/UPDATE beliefs` writer census across the active branch, separating perception ingestion, internal synthesis, self-observation, and controlled promotion paths.
2. Trace exact Fountain input selection/retrieval → generated thought → each writer/consumer, including residue, snapshots, probes and tag/decoder paths.
3. Trace GUI Chat assembly through each route (RAG-first, HYBRID/operator, voice fallback, tool path) and connect SelfModel/BehaviouralSelfModel formatted blocks to actual inclusion points.
4. Map SpeechQueue producers to `beliefs.db:speech_queue` and verify which routes enqueue, what the consumer updates, and which voice modes bypass it.
5. Trace each dynamically imported Stage 2 loop and all remaining boot-wired faculties; distinguish constructed, thread-started, env-gated, retired and externally gated states.
6. Reconcile all gate bypasses and fail-open semantics against the missing Frozen V2.1 source and founder approval record before any behavioural modification.

**Status:** partial source trace only. No live runtime observation, no L4 claims, no Gate 0 sign-off, no Phase 1 authorisation.


## 9. Chat retrieval, self-model injection and reply persistence

- `gui/server.py:1207–1255` routes a chat prompt through `state.membrane.route()` when both Membrane and World Model are present. Without Membrane it calls the retriever directly, filters to beliefs sharing at least two content tokens with the prompt, and caps the rendered belief block at about 800 characters.
- `theory_x/stage4_membrane/router.py:28–95` separates INSIDE and OUTSIDE:
  - INSIDE: snapshots SelfModel, formats its proprioception/temporal/interoception/attention/inside-belief content, and retrieves INSIDE-filtered beliefs (limit 5).
  - OUTSIDE: retrieves ordinary relevant beliefs (limit 8) using active Dynamic branches as hints.
- `gui/server.py:1268–1288` adds BehaviouralSelfModel metrics to the prompt-facing `belief_text` on INSIDE routes only. The metrics are derived from the last 100 NEX messages in `conversations.db`.
- `gui/server.py:1291–1310` records SelfModel injection observability; the actual SelfModel text has already been added by the router's INSIDE route.
- `gui/server.py:1900–2045` builds 13 named faculty/context blocks and passes them through `_assemble_chat_blocks()`. By default the blocks concatenate; `NEX5_CHAT_WORKSPACE=1` enables budgeted salience selection. Several blocks are independently flag- and admin-scoped. The final `voice_prompt` combines these blocks with the routed belief/self-model context and the user prompt.
- `gui/server.py:2061–2130` sends the composed prompt through `state.voice.speak(VoiceRequest(...))`, with retry/regeneration and provenance handling on some paths. This is a direct chat voice path, not the persistent speech queue.
- `gui/server.py:2163–2180` sanitizes the final reply, inserts the NEX message into `conversations.messages`, and then records the default-OFF InfluenceRecord chat-turn sidecar. The trace hook does not mutate the reply.

**Route caveat:** the source establishes the two principal Membrane routes and the prompt assembly shown above. It does not yet establish every fallback/tool/repeat path's exact block inclusion or causal contribution to the final answer.

## 10. Speech queue producer/consumer path

- `theory_x/stage6_fountain/crystallizer.py:383–400` gates the generated Fountain thought after its quality checks and before the belief insert. On ACCEPT, it writes the belief and a `fountain_crystallizations` row at approximately lines 447–454.
- `crystallizer.py:459–494` is a verified speech-queue producer. It checks `SpeechConfig`, limits eligible source categories to `fountain_insight`, `synergized`, `koan`, and `voice_fallback`, applies the `SpeechGovernor`, avoids duplicate queue rows for the belief, then inserts `speech_queue` with belief ID, content, voice and queued timestamp.
- `run.py:611–629` constructs and starts `SpeechQueueConsumer` only when `SpeechConfig.enabled` is true. `speech/config.py:1–35` reads `NEX5_SPEECH_ENABLED` (default true in source); the current host's effective environment is not established here.
- `speech/queue_consumer.py:79–160` reads the oldest pending row and updates its state through `speaking` then `spoken`, or `suppressed` / `failed`; it synthesizes with Kokoro and plays through `Player`. Quiet hours and pause state can defer consumption.
- `gui/server.py:2557+` exposes `/api/speech/say` for immediate read-aloud through the consumer's backend/player. Its docstring explicitly says this on-demand path does not touch `speech_queue`.
- Chat's `state.voice.speak()` path is also separate from this queue/consumer path.

**Evidence gap:** FountainCrystallizer is a verified queue producer, but an exhaustive repository-wide `INSERT INTO speech_queue` census is still required before claiming it is the only producer. Live consumer activation and actual audio output remain UNKNOWN.


## 11. Belief-writer wrapper and direct-write distinction

The active boot path wraps the base beliefs writer in `TaggingBeliefWriter` at `run.py:70` before passing the writers dictionary to the faculties. The wrapper intercepts eligible explicit-column-list `INSERT INTO beliefs` statements, generates tags, and delegates to the underlying writer. This is a persistence/tagging wrapper, not a CoherenceGate call and not evidence that a candidate was coherence-evaluated.

Consequently, a direct insertion can still receive tags while bypassing CoherenceGate. These are separate mechanisms and must not be conflated in the crosswalk.

## 12. Additional direct belief paths verified

The following source paths have now been verified against the active host source commit `de93134f34adac07a3a41c2a05b33720510a2bfc`:

1. **Sense distillation:** `theory_x/stage2_dynamic/__init__.py:170–272` inserts eligible external-event titles as Tier 7 `precipitated_from_sense` beliefs without a gate call. The source explicitly frames this as perception ingestion.
2. **Fountain rut mirror:** `theory_x/stage6_fountain/generator.py:2899–2935` inserts a Tier 6 `self_rut_notice` belief when the governor's recent STRIKING rate is at or below 5% (with at least four observations) and the two-hour throttle allows it. No CoherenceGate call appears in this insertion path. It is an internally generated self-observation, unlike external sense ingestion.
3. **Holding-zone promotion:** `theory_x/stage_gate/holding_zone.py:170–199` inserts a held candidate as a belief when `promote_to_belief()` is invoked. The resolver's corroboration path invokes it after three corroborating ACCEPT events (`resolver.py:60–115`). This is a controlled resolution path with prior gate-derived corroboration, not a raw unreviewed producer insertion; retain it as a separate promotion mechanism.
4. **Gated synthesis paths:** Dynamic crystallization, World Model synergizer, and normal Fountain crystallization each construct a ThoughtPacket, call CoherenceGate, and only insert the resulting belief on ACCEPT in the inspected path.

The distinction is material: “all beliefs are written through the TaggingBeliefWriter” (boot wiring) does **not** imply “all belief candidates pass CoherenceGate.” The source currently demonstrates at least two direct producer bypasses (sense distillation and Fountain rut mirror), plus a separately controlled held-thought promotion route.

### Census completeness

This is a verified subset, not a repository-wide exhaustive direct-writer census. The remaining faculties and utility modules still require inspection for direct `INSERT INTO beliefs`, update-in-place paths, alternate writer instances, and gate calls. No claim is made that the two direct producer bypasses listed above are the only ones.



## 13. Additional gate callers and boot-time belief seed

A further bounded caller check verified two additional gate consumers:

- **CounterfactualNode:** `theory_x/stage_counterfactual/counterfactual_node.py:145–181` builds a ThoughtPacket for each buildable candidate, calls `CoherenceGate.check()`, and inserts the candidate as a Tier 3 `counterfactual_node` belief only on ACCEPT. This is a gated producer path.
- **ThrowNetEngine:** `theory_x/stage_throw_net/throw_net_engine.py:125–175` refines candidates, submits each as a ThoughtPacket to CoherenceGate, and records outcome counts in the session metadata. In the inspected engine loop, it does not itself insert each candidate into `beliefs`; the gate's own ACCEPT side effects and any linked holding-zone corroboration are separate.

A distinct boot-time write is also verified:

- **Self-location commitment:** `run.py:70–75` wraps the beliefs writer, then calls `SelfLocationCommitment.commit()`. `theory_x/stage5_self_location/commitment.py:1–55` idempotently seeds the locked Tier 1 `self_location` belief if absent. This is a deliberate bootstrap anchor, not a generated thought candidate. It is not routed through CoherenceGate; its locked/axiomatic status must be interpreted under the governing doctrine rather than lumped together with runtime producer bypasses.

These additions expand the verified caller/producer subset; they do not complete the census. In particular, modules that update existing beliefs, write through helper functions, or use alternate Writer instances still require inspection.
