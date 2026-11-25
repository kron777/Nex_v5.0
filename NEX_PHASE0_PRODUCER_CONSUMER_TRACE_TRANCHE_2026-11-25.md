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


## 14. Further gated producers and non-belief consumers

Two more candidate-generation faculties were traced:

- **CounterfactualNode** is a gated belief producer as described above. Its acceptance decision is followed by its own `_insert_belief()` helper; the helper writes Tier 3 `counterfactual_node` content. The gate decision and the writer call are adjacent in the same processing loop.
- **ThrowNetEngine** is a gate consumer but not, in the inspected `run_session()` loop, a direct belief producer. It submits refined candidates to CoherenceGate and records outcome counts. This prevents an inaccurate edge in the DAG that would show every gate caller as automatically creating a belief.

A separate review of the self-location bootstrap confirmed that its locked Tier 1 anchor is created before the rest of the runtime faculties are constructed. It should therefore appear in the graph as a boot-seeded substrate invariant/anchor, not as a normal runtime thought or an output of the gate.

### Bounded negative findings

The following inspected files contained no direct `INSERT INTO beliefs`, `UPDATE beliefs`, or obvious `beliefs_writer.write` call in the fetched source:

- `theory_x/stage_warrant/warrant.py`
- `theory_x/stage_provenance/provenance.py`
- `theory_x/stage_self_narrative/self_narrative.py`
- `theory_x/stage_world/prediction_generator.py`
- `theory_x/stage_drives/competing_drives.py`
- `theory_x/stage7_moltbook/poster.py`
- `theory_x/stage7_moltbook/listener.py`
- `theory_x/stage_affect/compassion.py`
- `theory_x/stage_prediction/predictive_substrate.py`

These are only file-local negative observations. They do not prove the faculties are write-free: a module may delegate to another helper, write another table, or be invoked by a different component. They are not evidence of absence for the whole repository.

### Updated census status

Verified gated candidate producers in this tranche: Dynamic crystallization, World Model synergizer, Fountain crystallization, CounterfactualNode. Verified gate consumers with no direct belief insert in their inspected main loop: ThrowNetEngine and Fountain drive probe. Verified direct producer/seed/promotion paths: sense distillation, Fountain rut mirror, self-location boot seed, and resolver-mediated Holding Zone promotion. Additional callsites and indirect writers remain unverified.


## 15. Stage 2 life-loop belief writers — additional direct paths

A targeted pass over the optional life-loop modules found additional belief producers that were not in the earlier direct-writer subset. These functions open the beliefs database directly with `connect(BELIEFS_DB)` and issue SQL themselves; they do not use the shared `TaggingBeliefWriter` instance, and the inspected write functions contain no `CoherenceGate.check()` call.

The modules are imported and appended to the `build_dynamic()` loop list in `theory_x/stage2_dynamic/__init__.py:526–628`; the factory starts every collected loop in daemon threads at approximately lines 665–667. This establishes source-level startup wiring when `build_dynamic()` runs and the imports succeed. It does not establish current live thread state or successful execution.

Verified direct belief inserts:

1. **Pattern loop** — `theory_x/life/pattern_loop.py:85–120`: composes a pattern statement from recent self-descriptions, writes `pattern_log` in `dynamic.db`, then directly inserts a Tier 6 belief at confidence 0.85 with the `self_pattern` tag. The loop is wired in `stage2_dynamic/__init__.py:546–554`.
2. **Witness loop** — `theory_x/life/witness_loop.py:100–128`: composes a blind-spot observation from prior patterns, writes `witness_log`, then directly inserts a Tier 6 belief at confidence 0.85 with the `blind_spot` tag. Wired at `stage2_dynamic/__init__.py:526–534`.
3. **Identity loop** — `theory_x/life/identity_loop.py:245–275`: composes a periodic identity statement, persists it to `identity_log`, then directly inserts a Tier 6 belief at confidence 0.90 with the `identity` tag. Wired at `stage2_dynamic/__init__.py:566–574`.
4. **Surprise loop** — `theory_x/life/surprise_loop.py:85–124`: reads flagged surprise events with non-empty predicted and actual content, converts each event into a statement, and directly inserts Tier 6 beliefs at confidence 0.75 with `surprise` / `big_surprise` tags. It advances its promotion cursor after processing the batch. Wired at `stage2_dynamic/__init__.py:584–592`.
5. **Remember loop** — `theory_x/life/remember_loop.py:94–126`: selects an older and a recent belief, asks the voice model to compose a link, enforces a daily cap, then directly inserts a Tier 6 belief at confidence 0.70. Wired by the dynamic factory's import loop at `stage2_dynamic/__init__.py:600–609`.
6. **Wonder loop** — `theory_x/life/wonder_loop.py:120–166`: selects an entity, builds context and composes a question, checks for a question mark and a daily cap, then directly inserts a Tier 6 belief at confidence 0.60. Wired at `stage2_dynamic/__init__.py:600–609`.
7. **Fetch loop** — `theory_x/life/fetch_loop.py:145–183`: fetches an eligible URL, checks for duplicate URLs and minimum body length, composes a response, then directly inserts a Tier 6 belief at confidence 0.65. Wired at `stage2_dynamic/__init__.py:600–609`.

These are seven additional source-verified direct belief producers. They are distinct from the previously documented sense-distillation path, Fountain rut mirror, self-location bootstrap and resolver-mediated Holding Zone promotion. Their content is generated from self-history, prediction error, questions, or fetched external material; do not collapse them into one semantic class. In particular, the Fetch loop's content is model-composed from retrieved external material, while the Surprise loop converts already-recorded prediction events.

### Related life-loop maintenance path

- **Affinity loop** — `theory_x/life/affinity_loop.py:313–365` updates `beliefs.affinity` and `affinity_updated_at` for existing beliefs. It is a belief-state mutation, not a new belief producer. Its shadow mode logs deltas separately. It is wired in `stage2_dynamic/__init__.py:586–594`.
- The checked `scorecard_loop.py` contains no direct belief insert/update match in the fetched file. That bounded observation is not a whole-module proof that it cannot cause writes through a helper.

### Implication for the producer/gate crosswalk

The earlier statement that only two direct producer bypasses had been verified is superseded by this expanded subset. At least nine direct runtime producer paths are now source-verified across the traced modules: sense distillation, Fountain rut mirror, and the seven life-loop writers above. This count excludes the self-location boot seed and the resolver-mediated Holding Zone promotion because they have different bootstrap/promotion semantics.

The life-loop writes are not proof of an architectural defect by themselves. Their authority, intended gate scope, and relationship to any doctrine that prohibits faculty-level belief writes must be reconciled against the unavailable Frozen V2.1 specification and founder approval record. No behaviour has been changed, and no live loop state has been inferred.

## 16. Emergent-drive proposal application is conditionally gated

A further source check distinguishes emergent-drive proposals from the direct life-loop writers:

- `theory_x/stage2_dynamic/__init__.py:430–455` calls `drive_detector.apply_approved(..., coherence_gate=state.coherence_gate)`.
- `theory_x/stage2_dynamic/emergent_drives.py:149–214` reads proposals whose status is `approved`, adds the proposed branch to the Bonsai tree, constructs a natural-language drive statement, and—when a gate object is present—submits a ThoughtPacket with source `emergent_drives`. It inserts a Tier 5 belief only when the gate outcome is ACCEPT.
- If `coherence_gate` is absent, the source explicitly permits the belief insert without a gate. The normal factory wiring passes `state.coherence_gate`, but the no-gate fallback remains part of the component's callable contract.
- A non-ACCEPT decision still allows the proposal to be marked `applied`; the source comment says it is not retried. A gate exception is recorded and does not satisfy the ACCEPT condition for the write.

This is a conditionally gated producer, not an unconditional bypass. The current runtime value of the gate reference and the existence/status of any approved proposals are UNKNOWN.

## 17. Existing-belief mutations are a separate graph edge class

The wider scan also confirmed several mutation-only components that should not be drawn as new belief producers:

- `theory_x/stage3_world_model/promotion.py:74–299` writes belief edges and updates existing belief tiers, corroboration counters, promotion/demotion timestamps and logs. It does not create a new belief row in the inspected methods.
- `theory_x/stage3_world_model/harmonizer.py:219–276` pauses, retires and changes tiers/content of existing beliefs while recording harmonizer events and edges; its inspected resolution path selects an existing synthesis belief rather than inserting a new one.
- `theory_x/stage3_world_model/erosion.py:47–132` updates use/reinforcement counts and provenance erosion stage on existing beliefs.
- `theory_x/life/affinity_loop.py:363–365` updates affinity fields on existing belief rows.
- `theory_x/stage6_fountain/crystallizer.py:600–632` contains an optional best-of-cluster path that replaces content in an existing belief row and its crystallization record. It is an update-in-place path, not a new belief insert; the feature is environment-gated in source.

This separation matters for the DAG: distinguish (a) candidate-to-new-belief production, (b) controlled promotion of held content, (c) boot-time anchor seeding, and (d) maintenance or replacement of existing belief state. A single generic “writes beliefs” edge would hide materially different control and provenance semantics.

### Updated status

The producer/consumer trace remains partial. This increment expands the source-verified direct writer subset and records conditional gating and mutation-only paths. It does not complete the 256-file `theory_x` inventory, prove the absence of helper-mediated writes, or establish any runtime-active/operational/behavioural evidence level. Frozen V2.1 and founder approval evidence remain blocking inputs for adjudicating the gate-scope questions.


## 18. Behavioural Self-Model is a gated belief producer

The Membrane path contains a further belief-producing loop, distinct from the prompt-only metrics path:

- `run.py:180–188` calls `build_membrane(..., coherence_gate=coherence_gate)`.
- `theory_x/stage4_membrane/__init__.py:20–39` runs the behavioural loop; the loop calls `write_behavioural_beliefs(..., coherence_gate=state.coherence_gate)` when the BehaviouralSelfModel and shared writers/readers are present.
- `stage4_membrane/__init__.py:55–95` constructs the BehaviouralSelfModel when the conversations reader is available, stores the shared writer/reader dictionaries and starts its daemon loop.
- `theory_x/stage4_membrane/behavioural_self_model.py:150–215` compares observed response metrics against seeds, deduplicates existing `behavioural_observation` content, constructs a ThoughtPacket with source `bsm`, and inserts a Tier 6 belief only when the supplied CoherenceGate returns ACCEPT.
- The write itself uses the shared beliefs writer. Under normal `run.py` wiring the gate is supplied; the callable method still accepts `coherence_gate=None`, in which case the source skips the gate and writes. This is a component-level fallback, not evidence that the normal boot path omits the gate.

This adds a fifth verified gated producer family in the inspected source set (Dynamic crystallizer, World Model synergizer, Fountain crystallizer, CounterfactualNode, Behavioural Self-Model), alongside EmergentDrive's conditionally gated path. It is not a direct bypass under the normal boot wiring.

The BehaviouralSelfModel also formats recent-response metrics for the Membrane INSIDE route; that prompt-consumption role and its separate belief-production role must be represented as two edges, not conflated.

## 19. Boot-time resumption mutates existing state, not new belief content

The `run.py` boot sequence constructs and runs `ResumptionSeeder` once after the World/ToM loops are wired and before Fountain construction:

- `run.py` Phase B resumption block constructs `ResumptionSeeder` using the beliefs DB, probes DB and `state_snapshot.json`, then calls `seeder.run()`.
- `theory_x/memory/resumption.py:65–106` reads a prior snapshot, checks its age against a three-day threshold, and if recent promotes up to five listed belief IDs and reissues up to three pending probes.
- `resumption.py:137–162` updates the existing beliefs' `created_at` values to `now - 1`; it does not insert new belief rows.
- `resumption.py:164–191` updates existing probe rows to re-issue them.
- `resumption.py:193–200` renames the snapshot to a `.consumed` path after processing (or stale-snapshot handling).

This is a boot-time recency/replay mutation with a filesystem side effect, not a belief producer and not a CoherenceGate path. Whether it executes on a given boot depends on the snapshot's existence, parseability and age. Current host snapshot state and whether this path has run are UNKNOWN; no host snapshot was read or altered for this audit.

## 20. Startup and loop-state distinctions reinforced

The boot source makes several different activation classes explicit; they should not be flattened into “all faculties run”:

- **Constructed and loop-started in the normal boot path:** World Model's six daemon loops; Membrane behavioural loop (when conversations reader is available); NovelAssociation loop; SubstrateHarmonic; GeniusTagger; CounterfactualNode; DriveEmergence; SelfMindView; Fountain; Signal loop; Diversity loop; EdgeGenerator loop; Decoder daemon; plus Dynamic's collected loop list.
- **Constructed but not started in the shown boot path:** ProbeRunner is instantiated and passed into AppState, but this code does not call `start_loop()`; ArcLoop is explicitly `None` following a documented cut; SocialPresence is explicitly `None` following a documented cut.
- **Environment-gated in source:** ThrowNetMonitor loop (`NEX5_THROWNET=1`); PersonaResponder (`NEX5_PERSONA_RESPONDER=1`); WorldPredictionLoop (`NEX5_WORLD_PRED=1`); SelfPredictionLoop (`NEX5_SELF_PRED=1`); SelfMaintainShadow (`NEX5_SELF_MAINTAIN_SHADOW=1`); World Model consolidation (`NEX5_WORLD_CONSOLIDATE`); optional Moltbook posting behaviour (`MOLTBOOK_DRY_RUN=0`).
- **Feature/consumer flags do not equal service activation:** e.g. the Phase 1 continuity consumer is default-OFF; speech consumer depends on SpeechConfig; no effective host environment values are inferred here.

These are source-code activation categories only. They do not replace host process/service evidence and do not establish which optional flags are currently set.

### Updated gated producer inventory

Verified gated producers in the inspected paths: Dynamic crystallization, World Model synergizer, Fountain crystallization, CounterfactualNode and Behavioural Self-Model. EmergentDrive is conditionally gated by the gate object passed from normal boot wiring, with an explicit no-gate fallback in its callable method. The seven Stage 2 life-loop producers, sense distillation and Fountain rut mirror remain direct insert paths without a gate call in the inspected write functions. The self-location Tier 1 row remains a separate boot seed; Holding Zone promotion remains a resolver-controlled promotion.

This is still not a complete repository-wide producer census. In particular, all helper-mediated writes and all remaining source modules have not been exhaustively examined.


## 21. Gate decision scope, exception handling and pre-gate side effects

A closer read of the producer callsites shows that “gated” is not one uniform control contract. The following distinctions are visible in source:

1. **Dynamic crystallizer — gate rejection blocks the insert; gate-call exception does not.** In `theory_x/stage2_dynamic/crystallization.py:177–218`, a returned non-ACCEPT outcome returns before the belief write. However, the `except Exception` branch logs the error and then falls through to the INSERT. This is a callsite-level fail-open fallback distinct from CoherenceGate's own internal `gate_error_fallback` ACCEPT behaviour.
2. **Behavioural Self-Model — gate rejection blocks the insert; gate-call exception does not.** In `theory_x/stage4_membrane/behavioural_self_model.py:165–215`, a non-ACCEPT outcome continues to the next divergence, but an exception is logged and execution falls through to the belief insert.
3. **EmergentDrive — gate rejection blocks the belief insert, but not the branch side effect or proposal completion.** In `theory_x/stage2_dynamic/emergent_drives.py:165–214`, the Bonsai branch is added before the gate check. A non-ACCEPT outcome still allows the proposal to be marked `applied`; a gate exception also prevents the belief insert because the gate object is non-null and the decision remains None. Thus the gate controls the associated belief row, not the earlier attention-tree mutation or proposal lifecycle.
4. **CounterfactualNode — gate exception blocks the candidate insert.** In `theory_x/stage_counterfactual/counterfactual_node.py:145–181`, exceptions from `check()` are caught and the candidate loop continues without calling `_insert_belief()`.
5. **CoherenceGate — internal evaluation exceptions return ACCEPT.** In `theory_x/stage_gate/coherence_gate.py:208–288`, the gate itself catches `_evaluate()` errors and returns ACCEPT with reason `gate_error_fallback`. Therefore, the caller-specific exception branches above concern exceptions escaping the gate call, not the internal evaluation fallback already represented as an ACCEPT decision.

These differences should be represented as separate evidence fields in the eventual producer/gate crosswalk: returned REJECT/HOLD/RESHAPE handling; exceptions escaping the gate call; pre-gate state changes; and post-decision lifecycle effects. A single binary “gate yes/no” column would conceal the actual control semantics.

**Founder/spec question, not a change request:** does the governing gate obligation apply only to persistence of a belief candidate, or must it also govern upstream state changes that make the candidate consequential (such as adding a Bonsai branch)? What exception policy is required for each producer? The source establishes current behaviour but cannot answer the normative question without Frozen V2.1 and founder approval evidence. No code changes were made.

## 22. Operator-invoked identity/self-belief seed utilities (outside normal boot)

Two additional source paths can create or refresh Tier 1 locked beliefs, but neither appears in the normal `run.py` boot sequence inspected here:

1. **Identity YAML seeder** — `scripts/seed_identity_beliefs.py:1–145` is an explicit CLI utility. It reads `seeds/identity.yaml`, supports `--dry-run`, and otherwise uses a standalone `Writer` to `INSERT OR IGNORE` Tier 1, confidence 1.0, source `identity`, locked beliefs. Its own documentation describes manual invocation and idempotence. It is not a normal runtime loop and does not call CoherenceGate.
2. **Grounded scorecard self-belief** — `ground_self_belief.py:1–30, 105–145, 220–260` is an explicit CLI utility with `--dry-run` and `--remove`; its `refresh_self_belief()` entry point computes a sentence from the scorecard and `_write_self_belief()` inserts a Tier 1 locked belief if absent or updates the existing row in place. `_get_writer()` constructs a raw substrate Writer. No CoherenceGate call appears in the utility. Its own docstring mentions possible non-CLI callers, but no caller is established by the normal `run.py` boot path inspected in this tranche.

These are operator/tooling pathways, not counted among the nine direct runtime producer paths. They should be represented separately as controlled seed/calibration operations with explicit operator intent, dry-run support and a different authority boundary. Their existence reinforces why a repository-wide census must distinguish boot seeds, runtime loops, manual tools and migration scripts rather than counting every `INSERT INTO beliefs` as one type of producer.

Other checked utility paths include `nex_affinity_backfill.py`, which updates existing affinity fields under an explicit `--apply` plus environment guard, and the selected reporting/replay scripts, which use read-only connections. These are maintenance/analysis paths, not new runtime belief producers.

## 23. TaggingBeliefWriter is not a universal belief-write chokepoint

The wrapper's own source comment overstates its coverage:

- `run.py:68–71` wraps the shared `writers["beliefs"]` object in `TaggingBeliefWriter` and passes that wrapped object through the normal boot dependency dictionary.
- `theory_x/tag_protocol/writer_wrapper.py:1–16, 90–175` documents interception of explicit-column-list `INSERT [OR IGNORE] INTO beliefs` statements sent through that wrapper. It also describes its intake-resonance probe as a “UNIVERSAL chokepoint” through which “every belief from every writer passes here.”
- The seven Stage 2 life-loop writers listed in §15 instead open the beliefs DB with `connect(BELIEFS_DB)` and execute `INSERT INTO beliefs` directly. They do not call the shared wrapper.
- The operator utilities `scripts/seed_identity_beliefs.py` and `ground_self_belief.py` construct standalone `Writer` instances rather than obtaining `writers["beliefs"]` from `run.py`; they are also outside this wrapper instance.

Therefore, the wrapper is a chokepoint only for eligible writes routed through the wrapped shared Writer. It does not intercept direct SQLite connections or independent Writer instances. The seven life-loop paths are sufficient source counterexamples to the universal claim. The operator tools are further separate counterexamples.

**Consequences to represent accurately:**
- Auto-tag generation is not universal across all belief inserts. Some direct paths supply their own tags; others rely on schema defaults or omit tags. Do not assume every stored belief passed through `tag_protocol.generate()`.
- The wrapper's embedded `IntakeResonance.compute()` call is likewise not universal across every belief insert. Some modules call IntakeResonance separately; others do not. The exact set of producers covered by the wrapper and the separately invoked resonance hooks needs its own census.
- CoherenceGate, TaggingBeliefWriter and IntakeResonance are three different mechanisms. Passing through one does not prove passage through either of the others.

This is a source/documentation discrepancy, not a recommendation to route every writer through the wrapper. Whether the current coverage is intentional and what should be universal must be settled against the governing design. No runtime behaviour was changed.

## 24. Belief-graph edge producers and the NovelAssociation prompt consumer

Two active boot paths grow `belief_edges` without creating new belief rows:

- **EdgeGeneratorLoop:** `run.py` constructs and starts it through `build_edge_generator_loop(...)`; `theory_x/stage3_world_model/edge_generator.py:175–220` persists `belief_edges` from existing belief candidates. Its loop declares a 60-second boot delay and a 30-minute tick. It is a graph-topology producer, not a belief producer and does not call CoherenceGate for each edge.
- **NovelAssociation:** `run.py` constructs `NovelAssociation` and calls `start_loop()` in the Phase 17 block. `theory_x/stage10_imagination/novel_association.py:165–279` starts a daemon loop that sleeps 30 minutes before each scan, pulls beliefs with non-null branch IDs, computes cross-branch semantic similarity and writes `synthesises` edges plus `novel_association_log` rows. It does not insert a new belief row. `format_for_prompt()` selects one recent unannotated association, marks it annotated, and returns a templated self-observation.

The GUI consumes that result: `gui/server.py:1445–1453` calls `state.novel_association.format_for_prompt()` during chat-context assembly and appends the returned text to `belief_text`. This is a verified source-level producer → graph/log persistence → prompt-injection path. It does not establish that the text changed a final reply.

Graph topology is a distinct state channel from belief content. The EdgeGenerator and NovelAssociation write edges; the World Model's retrieval/activation mechanisms can consume belief graph structure; NovelAssociation additionally exposes a one-shot prompt annotation. Do not draw an edge write as if it were a new belief or assume that every graph edge is used by every retrieval route.

**Evidence boundary:** source shows these components are wired and their loops are started in the normal boot path. Their 60-second / 30-minute delays mean construction is not equivalent to an immediate first output. Current host thread state and downstream causal effect remain UNKNOWN.

## 25. DailyLife produces internal conversation messages and feeds the behavioural observer

`daily_life` is wired into the Stage 2 loop list and started by the same dynamic daemon-thread factory. It is not a belief writer, but it is a conversation-message producer with a downstream self-observation relationship:

- `theory_x/stage2_dynamic/__init__.py` imports `daily_loop` and appends it to the loop list in the Daily life block; the factory starts the collected loop.
- `theory_x/life/daily_life.py:1–35` declares six local-time activities (morning, two reading sessions, two outreach slots and journal), a once-per-day activity ledger, and a claimed 23:00–06:00 sleep behaviour.
- `daily_life.py:70–100` creates/uses the fixed `internal_daily_life` conversation session and inserts its generated text into `conversations.messages` with `role='nex'`.
- `daily_life.py:160–240` shows the activity implementations. Reading selects a recent external sense event and writes a templated internal message. Outreach selects an approved Moltbook conversation but the inspected implementation explicitly says it only records the intent; it does not send the DM. Morning and journal entries write status summaries.
- `daily_life.py:240–302` runs scheduled activities once their hour has passed, records them in `dynamic.db:daily_activities`, and ticks every 60 seconds. On boot it can catch up activities whose scheduled hour has already passed.

### Behavioural Self-Model measurement overlap

`theory_x/stage4_membrane/behavioural_self_model.py:67–75` observes the last 100 rows with `role='nex'` from `conversations.messages`, without filtering by `session_id`, register or whether the row is a reply to a user. The `internal_daily_life` messages therefore fall inside the source query's eligible population. This creates a possible measurement-mix issue: templated internal diary/reading/outreach messages can influence response-style metrics that are described as observations of recent responses.

This is a verified source-level overlap, not proof that it has materially changed any metric in the live database. The current trace has not inspected live message composition or calculated the contribution of the `internal_daily_life` session. It remains a candidate measurement-validity question: should behavioural self-observation include all NEX-authored messages, or only user-facing responses?

### DailyLife doc/source discrepancies

- The module header says outreach activities send one Moltbook DM; the inspected implementation only records a proposed outreach message and explicitly says actual sending is wired separately.
- The module header claims 23:00–06:00 sleep mode doubles the Fountain interval and reduces fires. `daily_tick()` returns a `sleep` boolean, but `daily_loop()` only logs activities and does not consume that value or change ModeState. `ModeState` persists explicit mode changes; no time-based sleep transition is shown in the inspected path. Treat the scheduled sleep effect as unverified/not implemented in this module, not as an active runtime behaviour.

These findings add a separate internal-message producer and a cross-faculty measurement dependency. They do not establish that the daily activities have fired on the current host or that the BehaviouralSelfModel has consumed any such messages.

## 26. DailyLife messages also enter Metacognition's goal-drift sample

A second downstream observer uses the same broad `role='nex'` population:

- `theory_x/stage9_metacognition/metacognition.py:284–335` selects the highest-priority open/active goal, then reads the latest five `messages` rows with `role='nex'` ordered by ID. It does not filter by session, register or user-facing route.
- It embeds the goal title/description and those latest NEX messages, averages the message embeddings, and compares semantic distance to the goal. A sufficiently large distance produces a `goal_drift` event in `meta_cognition_events`.
- Since DailyLife writes into the same `messages` table as role `nex`, its internal activity entries are eligible to enter this five-message sample as well as the BehaviouralSelfModel's 100-message sample.

This expands G-09 from a single observer to a shared input-population issue affecting at least two distinct consumers: response-style measurement and goal-drift detection. Whether this is intentional (all NEX-authored language is relevant) or a confound (only user-facing responses should represent response behaviour) is a design question, not settled by source. No live rows were read and no metric was recomputed.

## 27. Dynamic crystallization appears to double-record IntakeResonance

A concrete duplicate-measurement path is visible across the Dynamic crystallizer and TaggingBeliefWriter:

1. `run.py:68–71` wraps the shared beliefs Writer in `TaggingBeliefWriter` before `build_dynamic()` receives it.
2. `theory_x/stage2_dynamic/__init__.py:470–490` constructs an `IntakeResonance` instance and passes it into the Dynamic `Crystallizer` as `intake_resonance`.
3. `theory_x/stage2_dynamic/crystallization.py:198–212` calls `self._intake_resonance.compute(content)` before writing the new belief.
4. The same belief INSERT has an explicit column list but does not include `tags`. The shared writer is the TaggingBeliefWriter wrapper, whose `write()` path parses that INSERT, and—because `tags` is absent—runs its own lazy `_intake_probe.compute(content)` before injecting tags.
5. `theory_x/stage2_dynamic/intake_resonance.py:108–178` writes a new `intake_resonance_log` row on each successful `compute()` call. The table schema in `substrate/init_db.py:422–430` has an autoincrement ID and timestamp index but no content uniqueness or deduplication constraint.

Therefore, when the path is active and `NEX5_INTAKE_RESONANCE_OFF` is not `1`, one Dynamic crystallization can invoke two separate IntakeResonance instances and create two log rows for the same content. The two calls may use separate cached standing-point/embedding state; no deduplication is present in the inspected compute path. This is a source-level duplicate-measurement finding. It is not evidence that the host has generated duplicate rows, because live DB state and effective environment flags were not inspected.

### Contrast with other traced producers

- FountainCrystallizer explicitly calls its own IntakeResonance before INSERT, but its INSERT includes a `tags` column (`_attr_tags`, defaulting to `[]`). TaggingBeliefWriter returns early when the caller already supplies `tags`, so its embedded probe does not run for that write; the explicit Fountain call is the observed measurement path.
- The World Model synergizer also includes `tags` in its INSERT, so the wrapper's early `tags` pass-through prevents its embedded probe from running; no separate IntakeResonance call was observed in the inspected synthesize path.
- The seven direct-SQL life loops bypass TaggingBeliefWriter altogether and do not call IntakeResonance in their inspected insert functions.

This demonstrates that the wrapper's embedded resonance probe is not a uniform single call per belief. The eventual coverage map must record each producer's explicit resonance call, whether it routes through the wrapper, whether the INSERT already includes `tags`, and the number of resulting log writes.

## 28. Producer coverage matrix — gate, writer wrapper, tags and resonance

The following matrix consolidates the source-verified subset. “Wrapper” means the normal boot `TaggingBeliefWriter` instance is called; “auto-tag” and “wrapper resonance” apply only when the INSERT is routed through that wrapper and its column list does not already include `tags`.

| Producer / path | Belief write route | CoherenceGate | TaggingBeliefWriter | Tag value path | IntakeResonance path |
|---|---|---|---|---|---|
| Sense distillation | Shared beliefs Writer | No | Yes | Wrapper auto-generates | Wrapper probe once (unless disabled) |
| Fountain rut mirror | Shared beliefs Writer | No | Yes | Wrapper auto-generates | Wrapper probe once (unless disabled) |
| Dynamic crystallization | Shared beliefs Writer | Yes; escaping exception falls through | Yes | Wrapper auto-generates | Explicit Crystallizer call plus wrapper probe; potential double row |
| Fountain crystallization | Shared beliefs Writer | Yes; non-ACCEPT blocks insert | Yes, but tags already supplied | Explicit `_attr_tags` (`[]` or attribution marker) | Explicit FountainCrystallizer call; wrapper early pass-through |
| World Model synergizer | Shared beliefs Writer | Yes; non-ACCEPT blocks insert | Yes, but tags already supplied | Explicit `_attr_tags` (`[]` or attribution marker) | No explicit call observed; wrapper early pass-through |
| Behavioural Self-Model | Shared beliefs Writer | Yes under normal boot wiring; method has no-gate fallback; escaping exception falls through | Yes | Wrapper auto-generates | Wrapper probe once (unless disabled) |
| CounterfactualNode | Shared beliefs Writer | Yes; exception blocks insert | Yes | Wrapper auto-generates | Wrapper probe once (unless disabled) |
| EmergentDrive | Shared beliefs Writer | Conditional on gate object; branch is added before gate | Yes | Wrapper auto-generates | Wrapper probe once (unless disabled) |
| Holding Zone promotion | Shared beliefs Writer | Resolver-mediated after corroborating ACCEPTs | Yes | Wrapper auto-generates | Wrapper probe once (unless disabled) |
| Database-init keystone + koan/Tao/don't-know seeds | Raw Writers inside `init_all()` before wrapper construction | No; Tier 1 seed authority | No | Schema migration default `[]` | No call observed |
| Self-location boot seed | Shared beliefs Writer after wrapper construction | No; bootstrap anchor | Yes | Wrapper auto-generates | Wrapper probe once (unless disabled) |
| Pattern / Witness / Identity / Surprise / Remember / Wonder / Fetch | Direct SQLite connections | No in inspected insert functions | No | Explicit semantic tags or explicit `[]` | No call observed |
| HotObserver (env-gated `NEX5_HOT_OBSERVER=1`) | Direct SQLite connection | No | No | Omits tags; schema migration default `[]` | No call observed |
| Identity YAML seeder (operator CLI) | Independent Writer | No | No | Omits tags; schema migration default `[]` | No call observed |
| Spectrum loaders/batch (operator CLI) | Direct `sqlite3` | No | No | Copies existing tags or schema migration default `[]` | No call observed |
| Grounded scorecard self-belief (operator CLI/API) | Independent Writer | No | No | Omits tags; schema migration default `[]` | No call observed |

**Interpretation limits:**
- This matrix is a verified subset, not a complete repository census. It does not claim that every caller, alternate writer or helper has been found.
- A row marked “Yes” under TaggingBeliefWriter does not imply generated tags: if the caller includes a `tags` column, the wrapper returns before tag generation and before its embedded IntakeResonance probe.
- A non-empty explicit tag such as `identity` or `self_pattern` is not equivalent to generated semantic tags. An explicit `[]` is also a caller-supplied value, not a wrapper-generated result.
- `NEX5_INTAKE_RESONANCE_OFF=1` disables the compute operation in the inspected implementation. Effective host state is UNKNOWN.
- CoherenceGate, TaggingBeliefWriter/tag generation and IntakeResonance are independent controls/observations. Evidence for one must never be used as evidence for another.

This matrix provides the next useful unit for completing M0.3–M0.4: each remaining candidate producer should be added with these same independent dimensions, then linked forward to its actual consumers.

## 29. DailyLife catch-up can create a burst of internal messages at boot

`daily_loop()` calls `daily_tick()` immediately on entering its loop, before its first 60-second wait. `daily_tick()` iterates every scheduled activity whose hour has already passed and fires any activity not yet recorded for the current local date. The module header explicitly describes this as boot catch-up.

Consequently, a late-day boot can create several `role='nex'` internal messages in one initial tick (up to all six scheduled activities if the boot occurs after the final scheduled hour and none has fired that day). Those rows are ordered as recent messages and can therefore enter both the BehaviouralSelfModel's latest-100 sample and Metacognition's latest-five sample before ordinary user-facing replies have accumulated.

This is a source-derived possibility, not an assertion about the current host's boot time, daily_activities ledger or message table. It makes the G-09 measurement question more consequential and should be included in any isolated fixture that tests observer input selection.


**Invocation timing:** `Metacognition` has a `tick()` method but no `start_loop()` in the inspected module, and `run.py` constructs it without starting a daemon loop. `gui/server.py:1418–1424` calls `state.metacognition.tick()` during chat-context assembly. Thus the goal-drift comparison is evaluated on the chat path, using the latest five NEX-authored messages available at that time; it is not established as a continuously running background detector in this branch.

## 30. Conditional best-of-cluster content replacement precedes CoherenceGate

`FountainCrystallizer.crystallize()` has a separate existing-belief mutation path before the normal CoherenceGate call:

- The method first runs `_quality_check()`. A semantic near-duplicate can return `ok=False, reason='semantic_repeat'` and populate `_last_semantic_match`.
- If `NEX5_BESTOFCLUSTER=1`, the branch at `theory_x/stage6_fountain/crystallizer.py:319–357` calls `_maybe_bestofcluster_upgrade()` before the normal `if not ok` rejection and before the CoherenceGate block.
- `_maybe_bestofcluster_upgrade()` at `crystallizer.py:591–638` loads genius-v2 weights, scores the new thought against the matched existing belief, and if the new thought scores strictly higher performs an in-place `UPDATE beliefs SET content = ? WHERE id = ?` plus an update to `fountain_crystallizations.content` using `write_many()`. It retains the belief ID so graph references remain intact.
- When the upgrade succeeds, `crystallize()` returns the existing belief ID immediately. The normal CoherenceGate check (which is later in the method) is not reached for this mutation.

This is not a new belief INSERT; it is a generation-triggered replacement of existing belief content. It is explicitly environment-gated and default OFF in source. The current host flag value is UNKNOWN.

**Gate-scope question:** if CoherenceGate is required for every newly generated candidate that changes durable belief content, this path is a conditional bypass; if the intended contract only gates new belief-row insertion, it may be an authorised maintenance/upgrade path. The available source cannot adjudicate that. No runtime flag or code was changed.

## 31. Fountain end-to-end output path and the actual scope of its gate

### Generation and pre-gate persistence

1. **Readiness:** `theory_x/stage6_fountain/__init__.py` runs the Fountain loop after its configured interval; it checks `mode_state.current().fountain_enabled` and calls `generator.generate()` only when the mode allows it. `FountainGenerator.generate()` scores readiness and returns `None` when not ready.
2. **Pre-generation state:** on an eligible fire it computes competing-drive activation, checks the optional substrate-voice branch, and applies the every-fifth-fire quiescent branch. Quiescent fires write a `fountain_events` row and return before the normal voice/crystallizer path.
3. **Prompt/retrieval:** `_build_prompt()` assembles context from `_retrieve_context_beliefs()` (own-source beliefs, seed sources, optional associative recall, residue, periodic reanimation, a dedicated recent `hot_observer` slot), plus mode/focus blocks, world-bridge material or an input-gap problem injection, standing spectrum beliefs, and optional env-gated self/social/continuity/affect/metacognition blocks. The retrieval manifest records the belief IDs and slots selected for the fire. The `own_sense` and seed blocks render by default; the separate distilled-own-content render is gated by `NEX5_OWN_CONTENT_RENDER=1`.
4. **Voice:** the normal path calls `VoiceClient.speak()` with the assembled prompt. The optional language guard can retry or drop a non-English output. If voice fails, the generator selects the latest external sense event (or a bare tick), writes a `voice_fallback` `fountain_events` row and returns without condenser, crystallizer or speech queue.
5. **Pre-gate event writes:** on the normal path the generated thought is written to `sense_events` as `internal.fountain`; the condenser may derive a droplet; EmphasisEngine scores it; then the main `fountain_events` row is written. Retrieval manifest, prompt-block manifest, snapshots, emphasis and other telemetry are written as best-effort side channels. Optional duplicate-fire suppression can prevent crystallization while leaving the already-generated/persisted fire intact.

### Quality, CoherenceGate, belief and speech

6. **Quality filter:** `FountainCrystallizer.crystallize()` applies its quality checks (length/on-subject, engagement, repetition/template and related checks) and records rejects. An active Stillness row can also suppress crystallization.
7. **CoherenceGate:** after a candidate passes the quality filter, the normal path constructs a ThoughtPacket with source `fountain` and confidence `0.70`, calls CoherenceGate, and returns without inserting a new belief if the outcome is not ACCEPT.
8. **Intake resonance and belief:** on the normal accepted path it explicitly computes IntakeResonance, derives confidence (surprise weighting is enabled by default in source unless disabled), applies optional attribution stamping, inserts a Tier 6 belief with explicit `tags`, and writes the matching `fountain_crystallizations` row.
9. **Speech decision:** only after the belief exists does the SpeechGovernor decide whether to enqueue it. The category must be in the speakable source set, SpeechConfig must be enabled, length must be within configured bounds, and the governor must return `speak=True`; the code also checks for an existing queue row. `run.py` starts SpeechQueueConsumer only when `SpeechConfig.enabled` is true.

### What CoherenceGate does and does not govern in this path

- The gate is **not** a gate on generating the Fountain thought. It runs after the LLM has produced the thought and after the normal path has already written the internal sense event, condenser result (if any), emphasis score and `fountain_events` row.
- A gate rejection prevents the normal new-belief INSERT and therefore prevents the downstream speech-queue step, but it does not erase or suppress the already-persisted Fountain event or its pre-gate telemetry.
- The optional `NEX5_BESTOFCLUSTER=1` semantic-repeat upgrade can update an existing belief before the normal gate check; see §30.
- Quiescent and voice-fallback paths return before normal crystallization. They are separate output classes, not gate rejections.

This establishes a source-level distinction between generated thought/event persistence, durable belief crystallization and spoken delivery. The gate's current scope is belief admission in the normal Fountain path, not universal control over all prior output side effects. Runtime flags, live path frequency and causal influence remain UNKNOWN.

## 32. Chat replies are composed and persisted outside CoherenceGate

The GUI chat route has a separate output contract from Fountain belief crystallization:

- `gui/server.py:2027–2065` builds the pre-turn provenance snapshot when enabled, writes a diagnostic prompt log, calls `state.voice.speak()` and obtains the reply text.
- `gui/server.py:2067–2130` may regenerate once for same-opening repetition or provenance-mirror dominance; these are bounded prompt/reply checks, not CoherenceGate calls.
- `gui/server.py:2160–2175` sanitizes the final reply and inserts it into `conversations.messages` with role `nex` for the session.
- A source-wide scan of `gui/server.py` found CoherenceGate construction and dependency wiring in `build_state()`, but no `coherence_gate.check()`, `ThoughtPacket` or `GateOutcome` in the chat response path. The gate is passed to Dynamic, World Model, Membrane, Fountain, ThrowNet and Counterfactual components; it is not applied to the final user-facing chat reply.

Therefore, a normal Chat reply can be generated and stored in conversation history without a CoherenceGate decision. That is distinct from Fountain's normal new-belief admission path. Chat replies are conversation records, not new rows in `beliefs`; the source does not establish that every chat reply should be a belief candidate.

**Founder/spec question:** does “universal gate” mean all generated cognitive belief candidates, all autonomous outputs, or also every user-facing Chat reply? The code currently implements different boundaries for chat messages, Fountain events, and durable beliefs. Do not infer a violation or change the chat path until Frozen V2.1 and founder approval evidence resolve the intended scope.

## 33. Database initialisation seeds are a separate Tier 1 boot authority path

`run.py` calls `substrate.init_db.init_all()` before constructing the normal shared Writers and before wrapping `writers['beliefs']` in TaggingBeliefWriter. `init_all()` creates its own raw Writers, applies schema/migrations, and then performs three seed operations:

1. **Keystone seeds:** `substrate/init_db.py:691–702` calls `keystone.reseed(writers['beliefs'])`. `keystone.py:60–101` uses `write_many()` with `INSERT OR IGNORE` to seed the core and extended Tier 1 locked keystone rows. The normal boot seed uses the raw Writer created inside `init_all()`, not the later TaggingBeliefWriter wrapper.
2. **Koan/Tao/don't-know seeds:** `substrate/init_db.py:706–708` calls `seed_koans(writers['beliefs'])`. `substrate/koan_seeds.py:712–750` inserts Tier 1 locked rows with sources `koan`, `tao` and `dont_know` through that same raw Writer. These are idempotent inserts in the normal boot path.
3. **Blacklist seeds:** `init_all()` also seeds the belief contamination blacklist; this writes blacklist state, not new belief rows.

Because `init_all()` completes before `run.py` creates and wraps the shared Writer, the keystone and koan seed inserts do not pass through TaggingBeliefWriter, do not receive wrapper-generated tags, do not invoke its embedded IntakeResonance probe and do not call CoherenceGate. The `tags` migration default is `[]`. These are explicit boot-time Tier 1 seed operations, distinct from runtime-generated beliefs and from the later SelfLocationCommitment insertion.

`keystone.reseed(force=True)` additionally exposes an explicit destructive re-seed ceremony that deletes Tier 1 locked rows before inserting them again. The normal boot call does not pass `force=True`; no destructive reseed was performed during this audit.

### Seed authority classes now distinguished

- **Database-init seeds:** keystone and koan/Tao/don't-know rows, raw Writer, Tier 1 locked, idempotent, normal `init_all()` boot operation.
- **Post-init boot anchor:** SelfLocationCommitment, after TaggingBeliefWriter is installed; idempotent Tier 1 locked row through the wrapped Writer, no CoherenceGate.
- **Operator-invoked seed utilities:** identity YAML and grounded scorecard self-belief tools from §22; independent Writers and explicit CLI/API invocation.

These are intentional-looking authority classes in source, but the exact Frozen V2.1 doctrine governing Tier 1 seeding, tags and resonance remains unavailable. No seed was added, removed or refreshed on the host.

## 34. Additional operator-invoked spectrum seed utilities

Two further source paths can populate `beliefs` with `source='spectrum'`, but neither is called from the inspected `run.py` or `init_all()` boot path:

- **Outward spectrum loader:** `substrate/seed/load_spectrum.py:1–81` is an explicit CLI script. It reads `substrate/seed/outward_spectrum.txt`, samples an existing spectrum row's tier/confidence/branch/tags, and inserts new rows with direct `sqlite3` calls. It bypasses TaggingBeliefWriter, IntakeResonance and CoherenceGate. It copies the sample's `tags` value rather than generating new tags.
- **Process spectrum batch:** `substrate/spectrumizer_process.py:1–255` is a one-time batch script that inserts 100 Tier 1 locked `spectrum` variants with direct `sqlite3` calls, after checking schema columns and aborting if the `parent_belief_id=-2` cluster already exists. Its INSERT omits `tags`, so the schema migration default applies. It bypasses TaggingBeliefWriter, IntakeResonance and CoherenceGate.

These are manual/one-time seed operations, not normal runtime producers. Whether either script has previously been run on the host is UNKNOWN; no live beliefs DB was inspected. They extend the operator-seed class in §22 and the producer matrix in §28, but do not change the runtime direct-producer count.


**Downstream Fountain use:** the seed sources from `keystone.reseed()` and `seed_koans()` are members of `_SEED_SOURCES` in `generator.py`; `_retrieve_context_beliefs()` samples them as seed-reference material. `source='spectrum'` is handled in a separate standing-point block in `_build_prompt()`, which attempts one inward row (`id < 23000`) and one outward row (`id >= 23000`) per normal fire, with a random fallback if either pool is missing. Thus operator spectrum seeding is a prompt-input operation, not merely archival storage. Whether the manually seeded process/outward variants are present on the current host is UNKNOWN.


**Chat consumption:** `gui/server.py:1670–1703` also samples `source='spectrum'` rows for the Chat prompt (up to six random standing-points in the main composition block, and a further up-to-four sample in the thin-belief Philosophical path). The source comment describes the block as always present when spectrum rows exist. Thus spectrum seed content is a shared prompt input to both autonomous Fountain generation and user-facing Chat composition. This does not apply CoherenceGate to the Chat reply; see §32.

## 35. Environment-gated HotObserver is an additional direct belief producer

`FountainGenerator.generate()` contains a separately gated self-observation write:

- The callsite in `theory_x/stage6_fountain/generator.py:2004–2024` invokes `theory_x.stage_tom.hot_observer.observe()` only when `NEX5_HOT_OBSERVER=1`. The flag is not enabled by default in this source path.
- `theory_x/stage_tom/hot_observer.py:1–90` classifies each eligible fire, increments an in-process counter, and writes on every third call. It opens the beliefs database directly with `connect()` and inserts a Tier 3, confidence 0.6 belief with source `hot_observer`, branch ID, and explicit state/provenance fields.
- This direct SQL insert does not use the shared TaggingBeliefWriter, does not invoke its IntakeResonance probe, and does not call CoherenceGate.
- The Fountain retrieval path has a dedicated `hot_observer` slot: `_retrieve_context_beliefs()` reads up to 300 `hot_observer` rows from the prior 72 hours, deduplicates near-identical first sentences, and randomly selects one to prepend to the next fire's context. This is separate from the main own-content and seed slots.

This adds one environment-gated direct runtime belief producer to the census. When armed, it creates a feedback path: Fountain fire → HotObserver meta-belief (one per three calls) → dedicated retrieval slot on a later fire. It is a source-level possibility only; the host flag and live rows are UNKNOWN.

## 36. “Global Workspace” has two different route-specific mechanisms

The same module exposes two distinct attention helpers, and the two output routes use them differently:

### Fountain: single leading-frame arbitration

- `FountainGenerator._build_prompt()` invokes `global_workspace.arbitrate()` when `NEX5_GLOBAL_WORKSPACE` is unset or `1` (source default ON).
- `global_workspace.arbitrate()` competes five candidate classes: recent surprise, active L4 stakes, live momentum, hottest Bonsai branch and dominant drive. It selects the highest weighted candidate and returns one `[WORKSPACE]` framing line.
- That line is prepended to Fountain's `focus_block`. Other faculty blocks are still appended below; the function does not suppress the losing faculties or send a control signal back into them.

### Chat: optional budgeted block selection

- `gui/server.py` assembles approximately thirteen faculty/context blocks. `_assemble_chat_blocks()` concatenates all blocks unchanged unless `NEX5_CHAT_WORKSPACE=1` (source default OFF).
- When enabled, it calls `global_workspace.select_within_budget()` with per-block salience and a configurable character budget (default 1400). Exempt safety blocks are always retained; remaining blocks are admitted by descending salience until the budget is reached, but returned in their original assembly order.
- Optional `NEX5_SELF_PRESENT=1` updates the salience vector across turns. This is a block-budget selector, not the Fountain's single-winner framing mechanism.

### Architectural distinction

The source therefore does not show one unified global-workspace arbiter controlling every NEX route. Fountain has a default-on single-frame prompt prefix over five candidates; Chat has a separate default-off budgeted selector over faculty blocks. Neither mechanism, as inspected, directly gates belief writes or user-facing output. The module's “broadcast” terminology refers to prompt framing, not a demonstrated cross-faculty control broadcast or causal change in module execution.

Host-effective flags and the actual composition of either route's prompts remain UNKNOWN.

## 37. Residue retention is implemented in the reaper; the residue module's status note is stale

A fresh source comparison corrects an earlier assumption that residue was absent from the database reaper:

- `nex_db_reaper.py` currently includes `("beliefs.db", "residue", "created_at", 2)` in `TARGETS`. The accompanying comment explicitly assigns residue a 2-day TTL because `pop_residue()` now orders by `created_at DESC` and older unconsumed rows become unreachable.
- `deploy/systemd/nex5-db-reaper.timer` is configured for a persistent nightly trigger around 04:00. The service reference file still contains the old `/home/rr/Desktop/Desktop/nex5` checkout path; the host's loaded user unit was separately corrected to the actual `/mnt/games/storage/Desktop/Desktop/nex5` path, but the last host evidence showed the reaper service failed with `MainPID=0`. Whether the timer has since run successfully is UNKNOWN.
- `theory_x/diversity/residue.py`'s module docstring still says residue is not in `nex_db_reaper.TARGETS`, calls the backlog unbounded, and proposes adding an external retention pass. That statement is contradicted by the current `nex_db_reaper.py` source.
- The local `_reap()` inside `residue.py` removes only consumed rows older than 7 days. The external reaper's 2-day `created_at` cutoff is broader: if it runs, it deletes all residue rows older than 2 days, consumed or not. Thus the local 7-day consumed-row cleanup is a fallback/secondary path, not the effective maximum retention while the external reaper is operating.
- `tests/test_retention_reaper.py` currently tests the 30-day and 90-day log targets but does not assert the residue target or exercise its 2-day cutoff.

The module's historical figures (~709k unconsumed rows, ~623k stranded backlog, and earlier daily growth rates) are dated 2026-09-18 source comments, not current host measurements. No live DB row counts, reaper logs, service runs or data were inspected/changed in this audit.

**Disposition:** correct the stale residue module documentation and add isolated temp-DB coverage for the 2-day target. Do not manually run the reaper, delete live rows, alter the retention window, or activate the timer without explicit approval.

## 38. HotObserver retrieval can reintroduce Tier 8 retired beliefs

A source-level filter mismatch exists between the main Fountain retrieval query and the dedicated HotObserver slot:

- `FountainGenerator._retrieve_context_beliefs()` explicitly filters the main own-content query with `b.tier < 8`, and `fetch_residue_beliefs()` also filters `tier < 8`.
- The dedicated `hot_observer` query fetches rows where `source='hot_observer'` and `created_at` is within 72 hours, but it has no `tier < 8`, `paused=0` or `locked=0` predicate. The randomly selected row is appended directly to the context result.
- `hot_observer.observe()` inserts Tier 3 rows with `locked=0` and `paused=0`.
- `Harmonizer.scan_for_conflicts()` scans beliefs with `tier BETWEEN 3 AND 7 AND locked=0 AND paused=0`, without excluding `source='hot_observer'`. Its escalation path can update selected originals to Tier 8 and prefix their content with `[RETIRED]`.

Therefore, if a HotObserver belief is selected in a Harmonizer conflict pair and retired, it remains eligible for the dedicated Fountain slot until it ages beyond the 72-hour cutoff. This is a conditional source-level retrieval defect candidate: a tombstoned belief can be reintroduced through a special slot even though the main retrieval path explicitly excludes Tier 8.

Additional flag nuance: `NEX5_HOT_OBSERVER` gates new HotObserver writes, but the 72-hour retrieval query itself is not gated by that flag. If the writer flag is turned off after prior rows exist, those rows remain eligible for prompt injection until they age out or are otherwise excluded.

No live HotObserver rows, Harmonizer events or host flag values were inspected. No code or flag was changed.

## 39. Optional substrate-emission path also lacks a retired-belief filter

A second Fountain retrieval path can surface activated beliefs independently of the normal own/seed query:

- `theory_x/substrate/activation.py:get_top_activated()` joins `belief_activation` to `beliefs`, orders by effective activation and returns the top N rows, but its SQL has no `tier < 8`, `paused=0` or `locked=0` filter.
- `FountainGenerator.generate()` calls `get_top_activated(..., n=4)` only when `NEX5_SUBSTRATE_EMIT=1`; source comments identify this flag as default OFF. It then formats the selected beliefs (including their tiers and activation values) into a `[substrate emit]` thought instead of calling the normal LLM for that fire.
- The resulting thought continues through the normal Fountain event path and, when a crystallizer is present, reaches quality checks and CoherenceGate before a new belief can be inserted. The retrieval itself can nevertheless include a belief already retired to Tier 8.
- Harmonizer can retire unlocked Tier 3–7 beliefs to Tier 8. Fountain retrieval also bumps activation for beliefs selected into context, so a recently retired belief may retain a decaying activation record for this helper to read.

This is another conditional retired-row retrieval gap, distinct from the unconditional dedicated HotObserver slot. It is relevant only if substrate emission is armed and a retired belief remains above the activation threshold. The host flag and live activation rows are UNKNOWN.

## 40. NovelAssociation candidate scan does not exclude Tier 8 retired beliefs

`NovelAssociation._pull_candidates()` reads belief rows with `confidence >= 0.15`, `branch_id IS NOT NULL` and `paused = 0`, ordered by branch and recency. It does not filter `tier < 8` or `locked=0`.

`Harmonizer.scan_for_conflicts()` can retire unlocked Tier 3–7 beliefs by setting `tier=8`, `locked=0`, `paused=0` and prefixing `[RETIRED]`. Such rows still satisfy NovelAssociation's candidate query while they remain above the confidence threshold and have a branch ID.

The loop runs every 30 minutes from normal boot wiring. It can therefore compute cross-branch similarity for retired rows and write `synthesises` edges plus `novel_association_log` entries. At similarity above the narrative threshold it also calls `SelfNarrative.write_narrative()` with the branch-pair observation. The GUI's `format_for_prompt()` later injects the branch-pair annotation into `belief_text` without exposing the underlying belief content.

A nearby comment in `FountainGenerator._retrieve_context_beliefs()` says `novel_association.py` is among the paths that bound tiers to 5/6/7 and exclude retired beliefs. That statement does not match the current `_pull_candidates()` SQL.

This is a source-level retired-row graph-ingestion candidate. Unlike the HotObserver and substrate-emission retrieval gaps, the NovelAssociation loop is started in the normal boot path; the extent depends on retired rows satisfying its confidence/branch/paused filters and on semantic similarity. The resulting edges may also affect the optional edge-weighted Fountain ranking. No live retired rows or edge history were inspected.

## 41. Diversity EdgeBuilder also permits Tier 8 rows into belief_edges

`theory_x/diversity/edge_builder.py:47–78` selects source candidates with fewer than the minimum outgoing-edge count, `paused=0`, `locked=0` and sufficient content length—but no tier bound. Its comparison pool selects sufficient-length beliefs with `paused=0`, also without a tier or locked filter. The loop then embeds candidates/pool members and inserts `cross_domain` edges in `belief_edges`.

The Stage 2 dynamic factory includes `edge_builder_loop` in its loop list and starts it through the daemon-thread factory. Thus the path is normal source wiring, not an environment-gated optional path.

Harmonizer retirement sets `tier=8`, `locked=0`, `paused=0`; retired rows therefore remain eligible both as EdgeBuilder source candidates and as comparison-pool targets. Locked Tier 1 beliefs are excluded as source candidates but may still be comparison targets because the pool has no `locked=0` condition.

This is a separate graph-ingestion path from NovelAssociation (§40). It can create edges involving retired rows even though the Fountain main retrieval and World Model EdgeGenerator use tier bounds. Such edges may affect later graph consumers, including the optional edge-weighted Fountain ranking. No live edge table or retired belief population was inspected.

## 42. Stage 3 spreading activation can traverse retired nodes even when final results exclude them

`BeliefRetriever.retrieve()` first builds `row_map` from beliefs satisfying `tier <= 6`, `paused=0`, and `(locked=1 OR confidence >= 0.15)`. Its final result assembly only emits IDs found in that active candidate `row_map`, so a Tier 8 row is not returned directly by this retriever.

However, `ActivationEngine.activate()` traverses `belief_edges` by source ID for up to three hops without joining or checking the current status of source/target belief rows. It can therefore pass activation through Tier 8 retired nodes and onward to other IDs. Those retired IDs are omitted at final assembly because they are absent from `row_map`, but their outgoing edges can still contribute activation to active candidates reachable through them. The engine also stamps every traversed edge's `last_traversed_at`.

Combined with the NovelAssociation and EdgeBuilder paths above—and with historical edges remaining after Harmonizer retires a belief—this means retired nodes may remain part of the graph's effective propagation topology even when retrieval excludes them from direct result content.

This may be intentional graph-history semantics or an unintended stale-node influence. The source does not define whether retirement should remove a node from graph propagation, preserve it as a historical bridge, or merely hide it from direct retrieval. This is a specification question; no edges were deleted and no activation code was changed.


**Log consumption and retention:** `scripts/intake_resonance_cli.py` is the only additional source consumer found in the inspected tree; its `show` command counts every row in `intake_resonance_log`, and `recent`/`top`/`bottom` read the full log by timestamp or score. `nex_db_reaper.py` has no `intake_resonance_log` target, and the table has no content uniqueness constraint. No retention policy was found in the inspected source. Whether indefinite retention is intentional for longitudinal analysis is UNKNOWN; duplicate rows from §27 would be counted as separate intake events by the CLI.

## 43. Fountain retrieval telemetry has two different persistence/retention contracts

`FountainGenerator` creates and writes two dynamic-database telemetry tables:

- **`fountain_retrieval_log`:** records `(fire_id, belief_id, slot, rank, boost_value, ts)` for the belief IDs actually retrieved. `_associative_recall()` reads the last three fires from this table to avoid re-serving the same own-content IDs in a short burst. The schema creation checks `PRAGMA foreign_key_list` and drops the table only if a legacy cross-database FK to `beliefs` is found; it then recreates it without that FK. The comment in the prompt-block section saying the retrieval log is destroyed on every restart is therefore stale after the no-FK migration has taken effect.
- **`fountain_prompt_blocks`:** records each prompt block's name, hash, character count, prefix and fire ID. The code prunes rows older than 30 days during Fountain schema setup.

`fountain_retrieval_log` is not in `nex_db_reaper.TARGETS`, and no other pruning was found in the inspected Fountain code. Its behavior only needs the last three fires for associative-recall dedup, but the table retains older rows unless the legacy-FK migration drops it. This creates a separate retention-policy question from the prompt-block table's explicit 30-day prune.

The log is not merely diagnostic: it is read by associative recall to maintain the six-hour per-thread already-shown set across recent fires. The actual `_assoc_shown` cache is in memory; the last-three-fire DB history is a second short-window dedup mechanism.

No live table sizes or restart history were inspected. Do not drop or prune the table without confirming the intended continuity semantics and any other consumers.

## 44. Retired-belief handling matrix across retrieval and graph paths

| Path | Tier 8 handling in source | Activation / graph effect |
|---|---|---|
| Fountain main own-content query | `tier < 8` only; no paused/locked predicate | Excludes Tier 8 but can surface paused Tier<8 rows |
| Fountain associative recall | `tier < 8` only; no paused/locked predicate | Can select paused Tier<8 own-source rows |
| Fountain residue fetch | `tier < 8` only; no paused/locked predicate | Rechecks retirement, but can still return paused rows |
| Fountain seed-source slot | No tier predicate; source allowlist is intended for locked Tier 1 seed families | Expected protected seed content; status not independently enforced by query |
| Fountain HotObserver slot | No tier/paused/locked predicate; 72-hour source/time filter only | Can directly inject retired HotObserver content |
| Fountain substrate emission | `get_top_activated()` has no tier/status predicate; flag default OFF | Can format retired activated beliefs into a generated thought |
| Fountain Favorites block | `affinity > 0.40` only; no tier/paused/locked filter | Can render retired content while affinity remains high |
| Fountain recent Surprise block | `source='surprise'` and six-hour time window only | Can render recently retired surprise beliefs |
| Stage 3 World Model BeliefRetriever | `tier <= 6`, `paused=0`, locked or confidence floor | Final result map excludes Tier 8 direct results |
| Stage 3 ActivationEngine | No belief-status check while traversing `belief_edges` | Retired nodes can be intermediate propagation bridges; final retriever output still filters to its active row map |
| Stage 3 EdgeGenerator | Source selection has no tier/status filter; target candidates have `tier <= 7` but no paused/locked filter | Can create edges from retired sources to tier<=7 targets, including paused/locked targets |
| Diversity EdgeBuilder | No tier predicate; source excludes locked but not Tier 8; pool excludes only paused | Can create edges involving retired rows |
| NovelAssociation | No tier or locked predicate; confidence/branch/paused filters only | Can create edges and branch annotations involving retired rows |
| Chat spectrum standing points | Source `spectrum` allowlist, no tier predicate | Expected locked Tier 1 spectrum seed content |

This matrix shows that Tier 8 is consistently excluded from some direct retrieval pools but not from every special slot, graph producer or graph traversal. The policy cannot be inferred from one main query. Sections 38–42 and backlog D-21–D-24/G-14 capture the specific candidate gaps; the matrix is a source inventory, not a normative judgement.

## 45. DormancyScanner's “incremental” scan does not advance beyond the oldest 50 rows

`DormancyScanner.scan_incremental()` in `theory_x/diversity/dormancy.py` selects:

- sources limited to `fountain_insight`, `synergized` and `behavioural_observation`;
- ordered by `created_at ASC LIMIT 50`;
- with no tier, paused, locked, `dormant_beliefs` membership or cursor predicate.

For each qualifying row it upserts `dormant_beliefs` with `ON CONFLICT(belief_id) DO UPDATE`, refreshing `last_active_at`, `dormancy_score` and `flagged_at`. It does not advance a cursor, exclude already-flagged/reanimated rows, or remove rows after reanimation. The same oldest 50 therefore remain the first 50 candidates on each scan as long as they remain in `beliefs`.

The normal `DiversityLoop._run()` calls `self.dormancy.scan_incremental()` every 60 seconds. The separate `ClockRunner._run_fast()` also constructs a new DormancyScanner and calls `scan_incremental()` every 20 Fountain fires. These are two scan callsites against the same tables; at some times they can repeat the same first-50 scan.

This is a source-level progress defect candidate: despite its name, the scanner has no visible mechanism to advance through the source population. It may repeatedly refresh the same oldest rows and fail to discover newer dormant beliefs. No live dormant_beliefs table or scan logs were inspected.

## 46. Dormancy reanimation can surface retired or paused beliefs

The dormancy/reanimation chain has no active-belief status guard at any of its three stages:

1. `DormancyScanner.scan_incremental()` selects the three source families without `tier`, `paused` or `locked` predicates.
2. `reanimate.wake_one()` selects the highest dormancy-score row where `reanimated_at IS NULL`, joins the belief by ID, and marks it reanimated. It does not check belief tier, paused or locked state.
3. `FountainGenerator._retrieve_context_beliefs()` calls `pop_reanimated()` on its periodic cadence and re-reads the returned belief using `SELECT ... FROM beliefs WHERE id=?`, again without checking tier, paused or locked state.

Because Harmonizer can retire unlocked source-family beliefs to Tier 8 with `paused=0`, those rows remain eligible for dormancy scanning, reanimation and Fountain prompt injection. Paused rows are also not excluded. The residue path explicitly rechecks `tier < 8`; the reanimation path does not.

This is a further normal-wiring retired/paused content path, separate from HotObserver, substrate emission, NovelAssociation and EdgeBuilder. It is conditional on a matching row being flagged, selected by `wake_one()` and consumed on a Fountain cadence. No live dormant row, pending reanimation or Fountain prompt was inspected.

## 47. Fountain pre-gate output also updates open-problem state

When a Fountain prompt contains a pending problem injection, the generated output is fed back into `ProblemMemory.observe()` before the normal crystallizer/gate stage:

- `FountainGenerator.generate()` checks `_pending_problem_injection` and, when present, calls `self._problem_memory.observe(problem_id, thought, source='problem_injection')` before the later `FountainCrystallizer.crystallize()` call.
- `ProblemMemory.observe()` in `theory_x/stage7_sustained/problem_memory.py:138–180` appends a timestamped observation to `open_problems.observations` and updates `last_touched_at`, deduplicating only if the new observation is byte-identical to the last entry.
- This write is to the conversations DB's `open_problems` state, not to `beliefs`; it is not guarded by CoherenceGate and occurs even if the later crystallizer rejects the thought.
- If `NEX5_HOT_OBSERVER=1`, the same pre-crystallizer region also calls HotObserver, which can insert a Tier 3 belief directly (see §35).

These are additional pre-gate state effects from the same generated output: open-problem feedback is persisted regardless of belief admission, and the optional HotObserver can persist a separate belief outside the normal gate. The gate is therefore a specific belief-admission control, not a transaction boundary around all consequences of a Fountain fire.

## 48. VoiceEngine is a separate substrate-first Chat reply path

The Phase 30 VoiceEngine is constructed in `run.py` and passed into AppState. `AppState.voice_mode` defaults to `use_substrate`; `/api/voice_mode` can switch the in-memory state between `use_substrate` and `use_llm`.

On a normal non-probe, non-instruction Chat turn, `gui/server.py:1735–1768` calls `VoiceEngine.query_reply()` when the mode is `use_substrate`:

- If a candidate is returned and operator composition is not active, the GUI sets `text` to the candidate's stored content verbatim and `voice_ok=True`; the normal LLM composition path is skipped.
- If operator composition is active, the hit is prepended as grounding and the reply is still composed by the LLM.
- If no candidate is returned, `text` remains `None` and the code continues into `state.voice.speak()` at the normal Chat output block.

`VoiceEngine.query_reply()` itself is read-only with respect to the belief graph, but records a `throw_net_triggers` user-query row. It uses `TimeFetch.run()` across beliefs, novel-association pairs, arcs and open problems; it scores candidates and returns the highest one above `min_score=0.6`. It does not call CoherenceGate.

### TimeFetch status filters

- `TimeFetch.fetch_from_beliefs()` filters only `confidence > 0.4`, `LENGTH(content) > 30` and keyword match. It has no `tier`, `paused` or `locked` predicate.
- `fetch_from_novel_associations()` joins `novel_association_log` to both belief rows and matches keywords in either content, with no belief-status filter.
- `fetch_from_arcs()` excludes `return_transformation` arcs and requires quality/theme fields, but does not validate the current status of the beliefs from which an arc may have been derived.
- `fetch_from_problems()` uses ProblemMemory's open-problem matching path.

Consequently, Tier 8 retired, paused or locked belief content can be returned by the direct VoiceEngine route if it meets the confidence/length/semantic score conditions. The T8 score penalty is not an exclusion: `VoiceEngine._score_candidate()` assigns T8 a tier score of 0.5, and a strong semantic/confidence/recency candidate can still exceed 0.6. `tests/test_voice_engine.py` tests that T4 scores higher than T8 but does not test that T8 is excluded; no TimeFetch test file was found.

### Substrate-miss fallback comment/source discrepancy

The comment at `gui/server.py:2057–2058` says that in `use_substrate` mode the LLM fallback is suppressed and a substrate miss returns NEX's own deflection. The inspected control flow does not implement that claim: after a miss, `text` is still `None`, and the same route calls `state.voice.speak()` with the assembled Chat prompt. `VoiceClient.speak()` calls its configured LLM request function. This is a source/comment discrepancy; the actual miss behaviour is LLM composition, not a VoiceEngine-provided substrate deflection.

This route is distinct from Fountain crystallization and the main Chat prompt path. It can serve a stored belief or novel-association pair verbatim without CoherenceGate, and it has a broader candidate status filter than the main World Model retriever. Whether this is intended Phase 30 behaviour or a retired-content leakage path requires founder/spec review. No mode, query, prompt or live belief state was changed.

## 49. VoiceEngine misses can feed the optional ThrowNet monitor

`VoiceEngine._record_query_trigger()` writes a `throw_net_triggers` row with `trigger_type='user_query'`. It sets `fired=1` when a substrate candidate is used and `fired=0` on a miss; the miss row has no `session_id` yet but preserves the session/turn string in `source_event_id`.

`TriggerDetector.pending_triggers()` selects all rows with `fired=0` without filtering by trigger type. If `NEX5_THROWNET=1`, the normal boot path starts `ThrowNetMonitor`, which polls every 300 seconds and passes pending triggers to `ThrowNetEngine`. The engine calls TimeFetch for the trigger topic, runs its refiner, and sends each refined ThoughtPacket through CoherenceGate; it records the session/outcomes but does not itself insert each candidate as a belief in the inspected loop.

Thus a VoiceEngine substrate miss can become an autonomous ThrowNet session when the monitor flag is enabled. A VoiceEngine hit is recorded as already fired and is not pending. This is a separate downstream path from the LLM fallback discrepancy in §48; it does not mean the direct VoiceEngine reply itself is gated.


**Mode persistence:** `/api/voice_mode` changes only `AppState.voice_mode` in memory; no persistent settings write is made by the endpoint or the inspected front-end toggle. A process restart therefore returns to the dataclass source default `use_substrate` unless another caller changes it after boot. The host's current in-memory mode and any UI action history are UNKNOWN.


**Additional TimeFetch detail:** the novel-association candidate query has no `detected_at` lookback and does not filter `annotated_at`; it can return any matching association-log row, regardless of age. These candidates have no belief `tier` or `confidence` fields, so VoiceEngine applies its non-belief defaults (tier score 0.7, confidence 0.5, recency 0.3, genius 0.5). With a perfect semantic match, the source weights yield approximately 0.762 before drive alignment—above the 0.6 threshold. Thus old/retired pair content can be eligible for a verbatim reply without any retired-tier penalty.

## 50. VoiceEngine hit and miss paths have different Chat post-processing

On a VoiceEngine hit, `gui/server.py` sets `text` before entering the `if text is None` LLM-composition block. The hit therefore bypasses the composed faculty prompt, LLM anti-repeat regeneration, and provenance-cue regeneration. The common final `_sanitize_reply(_strip_question_parrot(text, prompt))` still runs for both hit and LLM paths before the reply is persisted and returned.

On a VoiceEngine miss, the route enters the LLM-composition block and executes the ordinary `VoiceClient.speak()` call. The miss also leaves an unfired `user_query` trigger for the optional ThrowNet monitor (§49).

The VoiceEngine mode toggle is admin-visible in the GUI and changes only in-memory AppState; the app's initial state remains `use_substrate` on each process start unless changed. The front-end's initial `use_llm` string is only a display placeholder until `/api/system/status` refreshes it.

This means the default source route attempts substrate-first replies, but actual host mode remains UNKNOWN. A direct hit is a distinct verbatim response path; a miss is not a substrate-only deflection in the current source.

## 51. Fountain's always-on Favorites and Surprise prompt blocks bypass the main Tier 8 filter

Two additional prompt blocks query belief content directly, outside `_retrieve_context_beliefs()`:

- **Favorites:** `FountainGenerator._build_prompt()` selects the top 10 rows where `affinity IS NOT NULL AND affinity > 0.40`, then randomly renders up to two. The query has no `tier < 8`, `paused=0` or `locked` predicate. Harmonizer's retirement UPDATE changes tier/locked/paused/content but does not clear `affinity`, so a retired belief can remain eligible for this prompt block.
- **Recent surprise:** the prompt selects the latest belief with `source='surprise'` created in the last six hours, without a tier/paused/locked predicate. `theory_x/life/surprise_loop.py` writes these as Tier 6 unlocked beliefs directly through SQLite, with source `surprise`; Harmonizer can later retire them to Tier 8 while leaving them within the six-hour prompt window.

These blocks are separate from the main own-content query, which filters `tier < 8`. Therefore the main query's retired-row exclusion does not protect all Fountain prompt content. The Favorites block can select a retired row for as long as its affinity remains above 0.40; the Surprise block can select a recently retired surprise for the remainder of its six-hour window.

No live affinity values, retired surprise rows or prompt manifests were inspected. These are source-level retrieval filter gaps, not proof that retired content has appeared in a live prompt.

## 52. Fountain's main own-belief retrieval is not prompt rendering by default

The `_retrieve_context_beliefs()` own-content pool and the prompt text are separate stages:

- The retrieval function selects the configured own-source beliefs (default allocation around seven in the current mode), records their IDs in `fountain_retrieval_log`, and applies retrieval-side activation/erosion updates.
- The dedicated `own_content` prompt block in `_build_prompt()` is added only when `NEX5_OWN_CONTENT_RENDER=1`; source default is OFF. The optional associative-recall block is separately gated by `NEX5_ASSOC_RECALL=1` (default OFF), and wide-focus selection is separately gated by `NEX5_WIDE_MODES=1` (default OFF).
- The always-present `own_sense` block is built from recent sense events; it is not the same thing as the own-belief pool.
- Other belief-derived prompt blocks (Favorites, recent Surprise, spectrum standing points and optional HotObserver/reanimation paths) are separate queries with their own filters, as recorded in §§35, 38, 44 and 51.

Therefore the source comment that own lived content dominates the retrieval allocation does not establish that own-belief text dominates the actual Fountain prompt. With source defaults and absent environment overrides, the main own-belief pool is retrieved and statefully used but its dedicated text block is not rendered. Whether that separation is intentional is UNKNOWN; host-effective flags and actual prompt manifests were not inspected.

## 53. World Model EdgeGenerator filters target candidates but not source rows

The earlier summary of EdgeGenerator's tier bound needs a source/target distinction:

- `EdgeGeneratorLoop._tick()` selects source IDs from `beliefs` where `source IN ('fountain_insight','synergized')` and the ID appears in neither the `source_id` nor `target_id` columns of `belief_edges`. This source-selection query has no tier, paused or locked predicate.
- `EdgeGenerator.propose_edges_for_belief()` re-reads the source row by ID without a status predicate. Its *candidate target* query filters `tier <= 7` and a seven-day creation window, but does not filter `paused` or `locked`.
- The loop runs after a 60-second boot delay and then every 30 minutes in normal Stage 3 boot wiring.

Therefore, a Tier 8 retired `fountain_insight` or `synergized` belief that has no existing incoming/outgoing edge can still be selected as an EdgeGenerator source and connected to a tier<=7 target. Paused or locked tier<=7 rows can also be selected as targets. The earlier statement that EdgeGenerator excludes Tier 8 applies only to its target-candidate query, not its source selection.

This adds another normal-wiring path for retired rows to enter graph topology and broadens the paused/locked graph-status question. It does not directly return retired content from the Stage 3 retriever, but the graph can influence later spreading activation. No live graph state was inspected.

## 54. Harmonizer synthesis branch retires both rows, then demotes one back to Tier 7

A high-confidence control-flow defect is present in the successful-synthesis branch of `Harmonizer.resolve()`:

1. When a bridging belief is found, the method updates both original conflict rows to `tier=8`, `locked=0`, `paused=0`, and prefixes both contents with `[RETIRED]`.
2. It records the synthesis event and writes `synthesises` edges from both retired originals to the surviving bridge belief.
3. It then calls `self._promoter.decisive_contradiction(belief_id_b)` on the second original row.
4. `BeliefPromoter.decisive_contradiction()` reads the current tier and computes `new_tier = min(7, current + 2)`. Given the just-written Tier 8 value, it sets that row back to Tier 7, leaving the `[RETIRED]` content prefix in place. The method's docstring says “or discard if already at Tier 7”, but its implementation also leaves Tier 7 at Tier 7 rather than discarding it.

Therefore, when the synthesis branch is taken, the two originals do not both remain retired: `belief_id_a` stays Tier 8, but `belief_id_b` is moved back to Tier 7 immediately after retirement. Because the update also leaves `paused=0` and `locked=0`, the Tier 7 `[RETIRED]` row passes main retrieval filters such as `tier < 8` and can be treated as active content.

The current `tests/test_harmonizer_fixes.py::test_escalation_fires_after_incubation` checks only `row_a` after escalation, and its fixture does not establish a third bridging belief. It therefore does not exercise the successful-synthesis branch or assert that both originals remain Tier 8.

This is a source-level defect, not a policy ambiguity: the method's own resolution contract says both originals are retired, but the subsequent demotion reverses that state for one of them. No code was changed and no live Harmonizer event was inspected.

## 55. Harmonizer conflict scan is capped to the first 200 rows by tier

`Harmonizer.scan_for_conflicts()` selects `tier BETWEEN 3 AND 7 AND locked=0 AND paused=0 ORDER BY tier ASC LIMIT 200`. It has no created-at ordering, cursor, offset, rotation or sampling strategy.

If the eligible working-belief population exceeds 200, the scan repeatedly prioritises the same lowest-tier rows. If more than 200 eligible Tier 3 rows exist, Tier 4–7 rows are not examined at all; more generally, later rows at a given tier can be starved by earlier rows. Rows that are successfully resolved/retired leave the scan population, but rows with no detected conflict remain eligible on every two-hour scan.

This may be an intentional compute cap, but the current source does not show a fairness/progress mechanism for the remainder of the working-belief population. Live eligible row counts and actual scan coverage are UNKNOWN.

## 56. TaggingBeliefWriter intercepts `.write()`, not `.write_many()`

`theory_x/tag_protocol/writer_wrapper.py` implements tag injection and the IntakeResonance probe only in `TaggingBeliefWriter.write()`. Its `write_many()` method delegates the complete statement batch directly to `self._inner.write_many(statements)` without parsing or intercepting any contained SQL.

This is another boundary on the wrapper's coverage: even a belief INSERT routed through the wrapped Writer's batch API would bypass tag generation and the embedded resonance probe. The current scanned runtime `write_many()` callsites on the wrapped beliefs Writer are primarily updates/edge writes rather than new belief-row INSERTs; database-init keystone/koan seeding uses raw Writers before the wrapper is constructed. No current normal-runtime belief INSERT through the wrapped `write_many()` path was established.

The comment inside `write()` calling this a “UNIVERSAL chokepoint” is therefore too broad. The accurate claim is: it intercepts eligible explicit-column-list belief INSERTs routed through the wrapper's single-statement `.write()` method. Direct SQLite, independent Writers, pre-wrapper boot seeding, positional/no-content SQL, caller-supplied tags and `.write_many()` all bypass its tag/resonance logic.

## 57. CounterfactualNode reuses the broad TimeFetch pool before its gate

`CounterfactualNode` also consumes the shared `TimeFetch` retrieval layer:

- For each selected open problem it calls `TimeFetch.fetch_from_beliefs(constraint, limit=10)`, then passes those candidates through its refinement engine.
- `TimeFetch.fetch_from_beliefs()` has the same confidence/length/keyword filters described in §48, but no tier, paused or locked predicate. A retired/paused/locked belief can therefore become a counterfactual input.
- Buildable refinements are wrapped in ThoughtPackets and sent through CoherenceGate. Only ACCEPT results call `_insert_belief()`; that INSERT is routed through the shared TaggingBeliefWriter without an explicit tags column, so the wrapper auto-tags and runs its single resonance probe.

This differs from VoiceEngine: the VoiceEngine can return a TimeFetch candidate verbatim without a gate, whereas CounterfactualNode refines the candidate and requires CoherenceGate ACCEPT before creating a new Tier 3 belief. However, the gate evaluates the refined packet, not the active/retired status of the source candidate. Retired content can therefore be transformed into a new active candidate if the refinement passes the gate.

ThrowNetEngine also uses TimeFetch candidates but gates/refines them and, in the inspected loop, records outcomes without inserting each candidate as a belief. The shared TimeFetch status policy is therefore an upstream dependency for three distinct consumers with different downstream controls.

## 58. IntakeResonance coverage differs by belief producer

Following the call chain through the main gate-approved producers shows that the wrapper's “universal” comment does not describe actual measurement coverage:

| Producer | Gate before new belief? | Tags path | IntakeResonance calls in source |
|---|---|---|---|
| DynamicCrystallizer | Yes | INSERT omits `tags`; wrapped `.write()` injects tags | **Two**: explicit `_intake_resonance.compute()` before insert, then wrapper probe on the same `.write()` |
| FountainCrystallizer | Yes | INSERT explicitly includes `tags` | **One**: explicit compute; wrapper returns early because caller supplied tags |
| WorldModel Synergizer | Yes | INSERT explicitly includes `tags` (attribution tags or `[]`) | **Zero**: no explicit compute; wrapper skips because `tags` is present |
| CounterfactualNode | Yes | INSERT omits `tags` | **One**: wrapper probe |
| HoldingZone promotion | Prior three corroborating ACCEPT events | INSERT omits `tags` | **One**: wrapper probe |
| SelfLocationCommitment | No; boot anchor | INSERT omits `tags` | **One**: wrapper probe |
| Fountain rut mirror | No; threshold/telemetry mirror | INSERT omits `tags` | **One**: wrapper probe |
| HotObserver | No; env-gated direct SQLite | Direct SQL | **Zero** |
| Seven Stage 2 life loops | No; direct SQLite | Explicit tags in the inspected loops | **Zero** |
| init_db keystone/koan seeds | No; boot seed authority | Raw Writer before wrapper | **Zero** |

All rows assume `NEX5_INTAKE_RESONANCE_OFF` is not set to `1`; host-effective state is UNKNOWN. The dynamic duplicate is documented in §27. The Synergizer omission is the converse: it is a gated new-belief INSERT with explicit attribution tags, but no resonance measurement. Direct SQL/seed paths have their own tag/resonance contracts.

This is not yet adjudicated as a defect because the Frozen V2.1 requirement for IntakeResonance coverage is unavailable. It does establish that the current source does not provide one uniform measurement per belief admission.

## 59. Repository contains a Phase 0 Locked constitution, but it is not identified as Frozen V2.1

`SPECIFICATION.md` exists in the active repository. Its header identifies it as “NEX 5.0 — SPECIFICATION”, author Jon Kron with Claude, dated April 2026, status “Phase 0 Locked”. Its preamble calls it the Constitution of NEX 5.0, states that it is the written ground against which later decisions are checked, and says it wins over later engineering until explicitly revised. Its closing says it is revised only through explicit amendment logged in the repository.

Git history for this path shows one commit (`f10ac308`, 2026-04-23, “Phase 1: bones…”); no later amendment to this file was found in the path history. However, the file is not labelled V2.1 and is not identified by the handover as the exact Frozen V2.1 artifact. It cannot safely be assumed to be the same document.

### Material conflicts between this constitution and current source

- **Tier 8 meaning:** the specification defines Tier 8 as raw OBSERVATIONS, data rather than belief, stored in SenseDB/IntelDB and separate from the belief graph. Current code uses `beliefs.tier=8` as a `[RETIRED]` tombstone state. The handover/roadmap terminology also treats Tier 8 as retired. These are incompatible meanings unless a later spec explicitly amended the constitution.
- **Harmonizer resolution:** the specification says common ground produces a *new synthesized belief* and retires both originals; if no common ground exists, both beliefs are deleted. Current source searches for an existing third bridging belief, links both originals to it, and does not create a new synthesis belief. The no-bridge branch labels its event `both_deleted` but updates both rows to Tier 8 with `[RETIRED]` content rather than deleting them.
- **Harmonizer tier scope:** the specification describes conflict detection at Tier 4 or above; current query scans Tier 3–7. The intended ordering interpretation and any later amendment are UNKNOWN.
- **One-pen rule:** the specification says every write must go through the per-database writer queue and direct DB writes are bugs. Current source contains direct SQLite belief writes in HotObserver, Stage 2 dynamic perception/life loops and other paths, as well as direct non-belief writes. This is a source-level conformance conflict if the constitution remains governing.
- **Database inventory:** the specification lists five DBs (beliefs, sense, dynamic, intel, conversations); current `substrate/paths.py` defines six, adding probes.db. This may be a later approved extension, but no amendment to `SPECIFICATION.md` was found.

These conflicts make the missing Frozen V2.1 document material, not administrative. The April `SPECIFICATION.md` is clearly a governing artifact by its own terms, but it may have been superseded by a later founder-approved V2.1 spec that is not present in the searched archive/Library. Do not reconcile these meanings by assumption, edit the constitution, or implement behavior changes until the founder identifies the canonical governing version.


## 60. Fountain's tier-only retrieval guards do not exclude paused rows

The main own-content query, associative-recall pool and residue re-read all use `tier < 8` as their status guard, but none of those queries checks `paused=0` (or `locked`). A Tier 3–7 belief temporarily paused by Harmonizer, or paused through another path, can therefore remain eligible for these Fountain paths. This differs from Stage 3 BeliefRetriever, NovelAssociation and EdgeBuilder, which explicitly filter paused rows in their candidate queries.

This may be intentional if `paused` is only a Harmonizer transaction marker rather than a general retrieval exclusion; the source does not establish that policy. No live paused rows or prompt manifests were inspected.

## 61. Multiple normal-wired loops write directly through substrate.connect(), outside the One-Pen Writer queue

The repository Phase 0 Locked constitution, SPECIFICATION.md §3, says each database has exactly one writer thread, all writes from all code paths submit to one writer queue per database, and no code acquires a write lock directly. substrate.connect() is the canonical SQLite connection factory, but it is not a Writer and does not submit statements to the Writer worker queue. A caller that executes UPDATE/INSERT and commits on a connection returned by connect() is therefore outside that queue.

The following source-level paths were verified:

| Module/path | Direct write observed | Database | Normal dynamic-builder wiring |
|---|---|---|---|
| theory_x/life/affinity_loop.py::affinity_tick | UPDATE beliefs SET affinity / affinity_updated_at | beliefs.db | appended and thread-started |
| theory_x/life/witness_loop.py | INSERT Tier-6 witness belief; INSERT OR REPLACE witness_log | beliefs.db; dynamic.db | appended and thread-started |
| theory_x/life/remember_loop.py | INSERT Tier-6 remember belief | beliefs.db | appended and thread-started |
| theory_x/life/surprise_loop.py | INSERT Tier-6 surprise belief; daemon_kv writes | beliefs.db; dynamic.db | appended and thread-started |
| theory_x/life/wonder_loop.py | INSERT Tier-6 wonder belief | beliefs.db | appended and thread-started |
| theory_x/life/identity_loop.py | INSERT Tier-6 identity belief; identity_log writes | beliefs.db; dynamic.db | appended and thread-started |
| theory_x/life/pattern_loop.py | INSERT Tier-6 pattern belief; pattern_log writes | beliefs.db; dynamic.db | appended and thread-started |
| theory_x/life/fetch_loop.py | INSERT Tier-6 fetch belief | beliefs.db | appended and thread-started |
| theory_x/sustained/focus_loop.py | current_focus INSERT; open_problems UPDATE; internal sessions/messages INSERT | dynamic.db; conversations.db | appended and thread-started |
| theory_x/life/daily_life.py | daily_activities INSERT; internal sessions/messages INSERT | dynamic.db; conversations.db | appended and thread-started |
| theory_x/signals/signal_to_problem.py | signals UPDATE; open_problems INSERT | beliefs.db; conversations.db | appended and thread-started |

These modules import substrate.connect and execute/commit SQL directly on the returned connections. The Stage 2 builder appends the listed life, focus, daily-life and signal-to-problem loops and starts each in its daemon-thread loop factory. This proves normal source wiring when build_dynamic() is invoked and the imports succeed; it does not prove the threads are currently active on the host.

HotObserver is another direct beliefs.db writer: theory_x/stage_tom/hot_observer.py::observe() opens a connection with substrate.connect(), inserts a Tier-3 belief and commits. Its call in stage6_fountain/generator.py is explicitly gated by NEX5_HOT_OBSERVER=1 (default OFF), so it is an optional direct-connection path rather than a normal-default active producer.

Contrast: life.scorecard_loop delegates to ground_self_belief.refresh_self_belief(), whose belief insert/update uses substrate.Writer.write(), so that path is not included in the direct-connection list. Stage 2 DynamicCrystallizer and EmergentDrive belief inserts also use their injected Writer objects.

Effects on the evidence map:

- These are source-level departures from the literal One-Pen rule in SPECIFICATION.md. The exact Frozen V2.1 spec and founder amendment record remain unavailable, so normative classification is unresolved.
- The direct belief INSERT paths also bypass TaggingBeliefWriter, its auto-tag injection and its embedded IntakeResonance probe. Some insert statements explicitly supply hard-coded tags; others rely on the schema default. This adds to the producer-dependent measurement boundary in §§56 and 58.
- These direct paths do not call CoherenceGate in the inspected insert functions. That is a separate gate-scope question; the source trace does not assume every authored life-loop observation is necessarily intended to be a generated ThoughtPacket.
- Direct connections may contend with the per-database Writer thread, but no live lock contention, lost write or current thread activity is inferred from source alone.

No code was changed. Do not migrate these paths, alter loop activation, or route their beliefs through CoherenceGate before Gate 0 and explicit founder approval. Evidence: SPECIFICATION.md §3; theory_x/stage2_dynamic/__init__.py loop registration/thread-start block; the module callsites listed in the table; ground_self_belief.py for the compliant scorecard contrast.
## 61. Later Doctrine and Faculty Model documents add another authority layer

Two later architecture documents are present in the repository:

- `theory_x/DOCTRINE.md` is dated May 9, 2026 and its header says “DRAFT — awaiting Jon's review and approval”. Its §7 amendment states that belief-graph modification from inside nodes is governed by the Faculty Model + Coherence Gate, and generative nodes write thoughts through the gate.
- `theory_x/FACULTY_MODEL.md` is dated May 10, 2026 and calls itself foundational. It says every thought generated by a node passes through CoherenceGate, defines ThoughtPacket metadata, HoldingZone and recursive bounded reshape, and says it supersedes Doctrine §7's former prohibition on node-level belief writes. Its implementation order also says the initial Phase 22 gate was a read-only hook and existing Fountain/Synergizer paths remained unchanged in that phase, with faculty ports following later.

The repository path history shows the Doctrine amendment commit on May 9 and the Faculty Model commit on May 10. Neither document is labelled Frozen V2.1, and no founder sign-off record was found in the searched archive/Library. The April `SPECIFICATION.md`, May Doctrine and May Faculty Model therefore form a layered but incompletely reconciled authority stack; the later documents may amend parts of the earlier constitution, but an explicit amendment to `SPECIFICATION.md` was not found.

### Reshape implementation cross-check

The reshape path is present; it is not an unimplemented queue. `HoldingZone.put_reshape_pending()` persists the packet, `HoldingZoneResolver._process_reshape_pending()` retrieves up to 10 rows per tick, invokes the configured transformer, re-submits the new ThoughtPacket through CoherenceGate, and marks the original row `reshaped` or `reshape_failed`. `tests/test_reshape.py` covers the pending row, bounded resolver, transform failure and re-submit path. This is positive implementation evidence for Faculty Model §2.6.

### Authority consequence

The Faculty Model's universal gate statement is a design requirement, but the implementation-order note preserves legacy Fountain/Synergizer paths during the initial gate phase. The current source now calls the gate from several such producers, while other direct belief writers remain. These paths must be classified as generative thought, perception ingestion, bootstrap anchor or telemetry mirror against the canonical Frozen V2.1 and founder-approved Doctrine; do not declare every direct writer a gate violation solely from its SQL shape.

## 62. Additional direct-connection writes in Fountain, Moltbook and GUI action paths

A second source pass found additional direct writes outside the shared Writer queue. These are distinct from the normal-wired life-loop list in §61:

| Module/path | Direct write observed | Source activation category |
|---|---|---|
| theory_x/stage6_fountain/generator.py | INSERT OR REPLACE into dynamic.db recursion_attrib via substrate.connect() and commit | Inline in the Fountain fire path, inside a fail-safe try block |
| theory_x/stage7_moltbook/listener.py | INSERT/REPLACE into dynamic.db moltbook_dms and moltbook_pending_replies; INSERT into sense.db sense_events | Moltbook listener loop is returned by get_moltbook_loops() and appended/started by build_dynamic(); API/client readiness affects whether it reaches writes |
| theory_x/stage7_moltbook/responder.py | UPDATE dynamic.db moltbook_pending_replies status | Moltbook responder loop is returned and started in the same source wiring; client readiness affects execution |
| theory_x/stage7_moltbook/poster.py | INSERT/UPDATE dynamic.db moltbook_post_queue, daemon_kv and moltbook_posts | Moltbook poster loop is returned and started in the same source wiring; real external posting is separately gated by MOLTBOOK_DRY_RUN |
| gui/server.py /api/decoder/word_tag | DELETE or INSERT/UPSERT dynamic.db word_tags | Request-driven GUI/API action |
| gui/server.py /api/fountain/tag | UPDATE dynamic.db fountain_events and word_contexts | Request-driven GUI/API action |
| gui/server.py /api/ghost/flag and /unflag | INSERT/UPSERT or DELETE dynamic.db ghost_flags | Request-driven GUI/API action |
| gui/server.py /api/hypothesis create/update/autoscore | INSERT/UPDATE dynamic.db hypotheses | Request-driven GUI/API action, including autoscore invoked by the fountain-tag endpoint |

These are direct calls to substrate.connect() followed by SQL execution and commit; they do not use the shared Writer queue. The GUI's ordinary chat session/message persistence is a useful contrast: the inspected handlers use state.writers[conversations].write(). The drive-proposal approve/reject endpoints also use state.writers[dynamic].write().

Scope cautions:

- The Moltbook loop functions are in the normal build_dynamic() loop set, but client/auth readiness and external server state determine whether a given tick reaches these writes. No current host activity is asserted.
- The GUI writes require their respective endpoints to be invoked. Their presence is not evidence that a user invoked them.
- The Fountain recursion_attrib write is in the normal generation path, but is best-effort and exceptions are swallowed. Source presence does not prove every fire persisted a row.
- This is not an exhaustive audit of every GUI endpoint or every module in the repository. The One-Pen census remains open.
- The world_predictions module also uses its own connect() helper for world_predictions inserts/updates. Its WorldPredictionLoop is explicitly environment-gated by NEX5_WORLD_PRED=1 in run.py and defaults OFF; it is therefore an optional direct-connection path, not a normal-default active loop.

These additions strengthen the source-level mismatch with SPECIFICATION.md §3 if that document remains authoritative. They do not establish contention, data loss, or a need to funnel every administrative or observational write through a cognition gate. Queue serialization and CoherenceGate scope are separate contracts. No code or runtime state was changed.
## 63. ThoughtPacket arbitrary metadata is not persisted on accepted or held paths

`ThoughtPacket` defines an arbitrary `metadata` dictionary. The Faculty Model §3 says packet metadata gives the substrate queryable provenance and can support downstream filtering/weighting. The current persistence path retains the core fields (`source_node` as `beliefs.source`, `confidence`, `branch_id`, and creation time), but not the arbitrary dictionary:

- `beliefs.sql` has no metadata column or associated `belief_metadata` / `thought_packets` table.
- `gate_decisions` stores source_node, outcome, reason, latency, content preview, branch_id and confidence; it does not store packet metadata.
- `held_thoughts` schema has a `metadata TEXT` column, but `HoldingZone.hold()` and `put_reshape_pending()` omit that column from their INSERT statements.
- `HoldingZone.promote_to_belief()` inserts content, tier, confidence, source and branch_id; it does not copy metadata from the held row.
- Accepted producer INSERTs similarly persist the core belief fields but not `ThoughtPacket.metadata`. The gate currently consumes `reshape_hint` and `reshape_depth` transiently; the reshape path stores depth in its dedicated column and reconstructs those two keys, not the original arbitrary dictionary.

Thus basic provenance (who/source, when, confidence, branch) is persisted, but arbitrary packet metadata is not queryable after admission or while held. For example, a counterfactual scenario descriptor carried only in packet metadata would not survive as structured substrate metadata unless separately embedded in content or another producer-specific table.

This is a source-level gap against Faculty Model §3 if that document is governing. No live belief metadata or downstream consumer behavior was inspected.


**Doctrine phase-status cross-check:** the DOCTRINE §5 priority table still labels Counterfactual Simulation “UNBLOCKED” / queued for Phase 25+, and VoiceEngine “QUEUED (Phase 30)”, while the current branch contains `CounterfactualNode` and the substrate-first `VoiceEngine`. DOCTRINE §6 also requires five real-traffic HUD queries, route-class regression checks and Jon's quality greenlight for a node port. Code presence does not prove those acceptance criteria were completed; no founder quality approval or corresponding live-traffic evidence was established in this source audit. This may be stale status text or unrecorded approval, and requires founder clarification.

## 64. Database contract correction: distinguish the old queue-only constitution from the merged connection-factory model

PR #11, authored by the repository owner and merged 2026-10-17 (merge commit 64933125c5fabbdf8564a87d03f7b7a1a0c5f8b7), explicitly records that H4/H5 shipped a canonical substrate.connect() factory and a broad migration, with the one-pen ratchet retired. Its underlying implementation commit is 68bb3ec30b8f267cd0bdedca353116e8800e7010. The commit message says roughly 95 modules were migrated from raw sqlite3.connect() to substrate.connect(), which supplies WAL, busy_timeout and foreign_keys settings.

The current test tests/test_edges.py::TestNoDirectSqlite::test_no_direct_sqlite3_outside_substrate searches for 'import sqlite3' outside substrate/ and permits two named maintenance-tool exceptions. It does not inspect callsites to require Writer.write() or Writer.write_many(). The word 'one-pen' in that test therefore names the raw-sqlite import/factory ratchet, not a universal single-Writer queue.

This is positive evidence of deliberate owner acceptance of the connection-factory migration. It changes the interpretation of §§61–62: direct substrate.connect() calls are not automatically defects and must not be described as accidental bypasses of a current, enforced queue-only rule. The code inventory remains useful because substrate.connect() is a connection factory, not a queue; it applies consistent pragmas but does not serialize all callers through one worker.

The repository still contains contradictory artifacts: April SPECIFICATION.md §3 says every write must go through exactly one Writer queue; substrate/writer.py still says every write goes through Writer; and the merged October migration deliberately uses substrate.connect() directly in many modules. The merged PR body says the ratchet was retired, but it does not itself contain a visible amendment to SPECIFICATION.md §3. The exact current founder-approved transaction contract therefore remains UNKNOWN.

Revised classification: D-36 is a governing-document/architecture-contract divergence, not a confirmed code defect. G-24 is an inventory of direct-connection paths, not a defect list. No source path should be migrated back to Writer, and no direct-connect path should be assumed to provide serialized writes, until the founder-approved contract is identified.

This correction was prompted by actively seeking disconfirming evidence. It supersedes any earlier wording in this tranche or crosswalk that classified the direct-connection paths themselves as confirmed One-Pen violations.
## 65. Seven post-Phase-22 life-loop belief producers have no CoherenceGate or ThoughtPacket path

DOCTRINE.md records the Phase 22 amendment on 2026-05-10 as “universal thought gating” and says every thought from every generative path passes through one CoherenceGate instance. It lists the five paths wired at that time: Fountain crystallizer, World Model Synergizer, Stage 2 Dynamic crystallization, Behavioural Self Model and Emergent Drives. FACULTY_MODEL.md §2.3 separately states that every thought generated by a node passes through the gate.

Seven additional life-loop belief producers were introduced on 2026-05-16, after that Phase 22 record:

| Producer | First source commit | Belief output |
|---|---|---|
| RememberLoop | 6d26c353fcba, 2026-05-16 11:39 UTC | Tier 6, source=remember_loop |
| WonderLoop | 6d26c353fcba, 2026-05-16 11:39 UTC | Tier 6, source=wonder_loop |
| FetchLoop | 6d26c353fcba, 2026-05-16 11:39 UTC | Tier 6, source=fetch_loop |
| IdentityLoop | 5da76809b2bb, 2026-05-16 15:21 UTC | Tier 6, source=identity_loop |
| PatternLoop | 5da76809b2bb, 2026-05-16 15:21 UTC | Tier 6, source=pattern_loop |
| WitnessLoop | 5da76809b2bb, 2026-05-16 15:21 UTC | Tier 6, source=witness_loop |
| SurpriseLoop | 13895181ce99, 2026-05-16 15:21 UTC | Tier 6, source=surprise |

Current source checks on all seven modules found one direct INSERT INTO beliefs in each and no references to CoherenceGate, coherence_gate, ThoughtPacket or gate.check(). The Stage 2 builder imports/appends these loop functions and starts them in daemon threads. Their output therefore enters beliefs.db without the gate path used by the five Phase 22 producers.

Related life-loop distinctions:

- AffinityLoop updates existing belief affinity and is not a new-belief producer.
- ScorecardLoop delegates to ground_self_belief.refresh_self_belief(), which uses Writer.write(); it is not part of the seven direct belief producers.
- DailyLife writes conversation messages and activity bookkeeping, not new beliefs.
- FocusLoop and SignalToProblem mutate open-problem/signal state, not new beliefs.
- The life loops are separate background loops rather than explicit ThoughtPacket faculties. Whether they count as “generative paths” under the approved Faculty Model is the unresolved semantic boundary.

This is a candidate gate-coverage discrepancy, not yet a confirmed defect. The Doctrine header still says DRAFT awaiting Jon's approval; the exact Frozen V2.1 and founder sign-off are absent. The seven loops were added after the Phase 22 universal-gating record, so the Phase 22 list may have been a snapshot of then-existing paths, or the new loops may have been expected to adopt the gate. Current source does not answer which.

Do not retrofit gate calls, create packets, suppress these loops, or alter their belief outputs before Gate 0 and explicit founder approval. First establish whether background life-loop observations are thoughts subject to the universal gate, and whether their current behavior is an approved extension or an unrecorded exception.
## 66. Identity / Pattern / Witness life-loop beliefs are excluded from INSIDE self-inquiry retrieval

The three recursive self-model loops explicitly describe their outputs as internal self-description, pattern observation and blind-spot observation:

- IdentityLoop stores a Tier-6 belief with source=identity_loop; its module header says it writes NEX's own self-description.
- PatternLoop stores a Tier-6 belief with source=pattern_loop; its header describes a recursive self-model level that notices patterns in identity statements.
- WitnessLoop stores a Tier-6 belief with source=witness_loop; its header describes the third recursive self-model level that questions blind spots in PatternLoop.

However, Stage 4 membrane classification is source allowlist based. theory_x/stage4_membrane/classifier.py::_INSIDE_SOURCES includes the seed source identity but does not include identity_loop, pattern_loop or witness_loop. MembraneClassifier.classify_belief() returns INSIDE only when the belief's source is in that set.

SelfModel._get_inside_beliefs() queries only paused=0, tier<=6 beliefs whose source is in _INSIDE_SOURCES. MembraneRouter._inside_route() uses that snapshot and separately calls BeliefRetriever.retrieve(..., side_filter='INSIDE'); BeliefRetriever reclassifies candidate rows through the same MembraneClassifier before returning them. Both paths therefore exclude these three life-loop sources from the structured self-inquiry context under the current classifier.

Fountain's separate _OWN_CONTENT_SOURCES allowlist also contains fountain_insight, synergized, precipitated_from_dynamic, precipitated_from_sense, behavioural_observation and auto_probe, but not identity_loop, pattern_loop or witness_loop. These three belief rows are therefore absent from the dedicated own-content retrieval slots. Important exception: FountainGenerator separately reads the latest identity_log.statement and injects that text into its prompt (around generator.py:3471), so IdentityLoop's statement still has a direct Fountain input path independent of the belief row/allowlist. No equivalent direct pattern_log or witness_log injection was found. This does not prove the rows can never enter any broader retrieval slot; it establishes exclusion from the named inside and own-content paths.

This is a high-confidence source-level producer/consumer mismatch: the producers explicitly describe themselves as recursive self-model content, but the self-inquiry membrane and dedicated Fountain own-content allowlists do not recognise their source labels. Whether the omission is intentional or an oversight needs founder/design clarification; do not add sources to allowlists without approval because that changes what counts as NEX's INSIDE state and what Fountain treats as its own content. Additional source-history evidence: classifier.py was last changed for this source classification on 2026-10-10 by commit 397aa695c8 (“sync classifier to own-content sources”). That change explicitly added precipitated_from_dynamic, precipitated_from_sense and auto_probe, but not identity_loop, pattern_loop or witness_loop. The accompanying tests/test_membrane.py update enumerates identity as an inside source but still does not test the three loop-specific source labels. This shows the omission survived a later deliberate allowlist/test refresh; it does not establish whether the omission was intentional or simply a missed source-family update.
## 67. Life-loop belief inserts bypass the Tag Protocol; SurpriseLoop can persist duplicate tags

TAG_PROTOCOL.md identifies itself as a foundational specification with design decisions locked in a session with Jon (2026-05-11). It says tags are auto-generated from entity content and, in §6, that every path into a tags column flows through the helper module so normalization/deduplication is enforced.

The seven life-loop belief producers in §65 do not use TaggingBeliefWriter or the tag helper. Their direct INSERT statements specify:

| Producer | Stored tags expression | Source-level concern |
|---|---|---|
| IdentityLoop | hard-coded JSON [identity] | bypasses content-derived generation/helper |
| PatternLoop | hard-coded JSON [self_pattern] | bypasses content-derived generation/helper |
| WitnessLoop | hard-coded JSON [blind_spot] | bypasses content-derived generation/helper |
| RememberLoop | literal [] | no content-derived tags generated |
| WonderLoop | literal [] | no content-derived tags generated |
| FetchLoop | literal [] | no content-derived tags generated |
| SurpriseLoop | json.dumps([surprise, big_surprise if true else surprise]) | when big_surprise is false, the resulting JSON array contains duplicate surprise entries; helper normalization would deduplicate |

These are all Tier-6 belief admissions. They use substrate.connect() directly, so TaggingBeliefWriter cannot intercept them. Two additional source categories also bypass tag generation: boot-time keystone and koan seeds are written by raw Writers inside init_all() before the runtime wrapper is constructed and leave tags at the schema default []; optional HotObserver writes a Tier-3 belief through substrate.connect() and omits tags. Other explicit seed utilities also bypass tag generation: scripts/seed_identity_beliefs.py uses a raw Writer; substrate/seed/load_spectrum.py and substrate/spectrumizer_process.py use raw sqlite3 connections to seed source='spectrum' beliefs (the loader copies tags from an existing spectrum row). TaggingBeliefWriter's own docstring explicitly exempts seed scripts/admin tools, so these are separate bootstrap-policy cases; the seven post-spec life loops are ordinary background cognition loops, not seed/admin utilities. By contrast, SelfLocationCommitment and Stage 2 sense distillation call the wrapped beliefs_writer.write() and receive wrapper-generated tags. The issue is separate from the October database factory migration: the connection factory may be the intended write model, but it does not provide tag generation or normalization. The wrapper itself is deliberately conditional: it only matches INSERT and INSERT OR IGNORE statements with an explicit column list; it skips any INSERT whose column list already contains tags; and write_many() delegates unchanged. Its docstring also exempts seed scripts and admin tools. Therefore even routing these life-loop statements through the current wrapper would not normalize the three caller-supplied tag arrays unless the producer/helper contract changed.

This is a direct source-level divergence from TAG_PROTOCOL.md's entity-creation and normalization requirements, unless the life-loop producers have an approved exception or their explicit labels are intentionally treated as manually curated tags. Timeline strengthens the finding: TAG_PROTOCOL.md was committed 2026-05-11 19:52 UTC and tag_ops.py/writer_wrapper.py were implemented at 21:09 UTC that same day; the life-loop belief producers were introduced on 2026-05-16, after both the specification and its write-time integration existed. No later tag-protocol exception for these loops was found in the inspected docs. The SurpriseLoop duplicate is a concrete conditional data-quality defect independent of whether content-derived tags are required: on the non-big-surprise branch it constructs the same tag twice.

Boot-time keystone/koan seeds also bypass TaggingBeliefWriter (see §60), but they are authored/bootstrap anchors; whether they are in scope for the tag protocol is a separate policy question. Do not retrofit tag generation or alter producer inserts before Gate 0 / explicit approval. Isolated regression coverage can be prepared once the intended tag contract for generated beliefs and seed beliefs is confirmed.
## 68. The documented Identity → Pattern → Witness → Identity feedback loop is not closed in the inspected source

The three life-loop module docstrings describe a closed recursive self-model:

- PatternLoop says its belief enters retrieval and shapes the next IdentityLoop composition.
- WitnessLoop says its belief enters retrieval and modifies IdentityLoop's next composition, closing the L1→L2→L3→L1 loop.

The inspected implementation shows a narrower, mostly forward chain:

1. IdentityLoop reads identity_log for the previous identity statement and gathers metrics. _gather_metrics() reads total new-belief count, top-affinity belief, sense-precipitation count, current focus title, last big surprise, Fountain fire count, Moltbook post count and optional tag counts. It does not read pattern_log, witness_log, pattern_loop beliefs or witness_loop beliefs. _compose_statement() is deterministic and uses only these metrics plus the previous identity statement.
2. PatternLoop reads the last four identity_log statements, asks the LLM to name a pattern, writes pattern_log and inserts a Tier-6 pattern_loop belief.
3. WitnessLoop reads the last two pattern_log statements, asks the LLM to identify a blind spot, writes witness_log and inserts a Tier-6 witness_loop belief.
4. FountainGenerator separately reads the latest identity_log statement and injects it into the prompt (generator.py around line 3471). No equivalent direct pattern_log or witness_log prompt injection was found in the inspected generator source.
5. The Stage 4 INSIDE self-inquiry route excludes all three loop belief sources through its source allowlist (see §66). Fountain's dedicated own-content pool also excludes pattern_loop and witness_loop.

IdentityLoop's new_beliefs_6h metric does count all recent belief rows, so PatternLoop/WitnessLoop admissions can change the numeric count clause in a later identity statement. That is an indirect aggregate effect, not semantic feedback from the pattern or blind-spot content. The source does not show the documented text-level feedback edge from WitnessLoop output into IdentityLoop composition.

BeliefRetriever's unfiltered outside route may still retrieve these beliefs for ordinary queries, so this is not a claim that the rows are globally unreadable. The narrower verified result is that the explicitly described recursive self-model feedback into the next IdentityLoop composition and the explicit INSIDE self-inquiry context are not established by current source.

This is a source/documentation discrepancy and possible incomplete feedback edge, not an instruction to add a new dependency. The current design may intentionally use a feed-forward sequence plus an aggregate metric; if so, the module docstrings overstate the closed-loop semantics. Founder/design clarification is required before altering this architecture.
## 69. Active branch has not integrated the October 26 owner timezone decision present on main

Main contains commit c247c240f8 (2026-10-26), titled “clock: one timezone for NEX (NEX5_TZ, default Africa/Johannesburg)”. Its commit message records an owner decision for Africa/Johannesburg (SAST) and migrates four life loops plus decoder features, Fountain prompt time, temporal sense, downtime, quiet hours and GUI time bucketing to nex_config.local_tz/local_dt/local_utc_offset_seconds. It adds tests/test_local_tz.py, including a frozen-UTC test demonstrating the schedule difference between Johannesburg and Amsterdam.

The active development branch claude/nex-continuity-wire does not contain that migration:

- theory_x/life/identity_loop.py still imports ZoneInfo and sets TZ = ZoneInfo('Europe/Amsterdam').
- theory_x/life/pattern_loop.py still hardcodes Europe/Amsterdam.
- theory_x/life/witness_loop.py still hardcodes Europe/Amsterdam.
- theory_x/life/daily_life.py still hardcodes Europe/Amsterdam.
- The active-branch nex_config.py has no NEX5_TZ registry entry, DEFAULT_TZ, or local_tz helper. The main version has them, with Africa/Johannesburg as the default.

This is a branch-integration discrepancy with a later owner decision recorded in main, not a change to apply silently. The October 26 commit spans multiple files beyond the four life loops, so selectively copying only those four files would be an incomplete backport. The active branch is already known to be materially behind main; do not merge/rebase wholesale or cherry-pick this commit without explicit approval.

Operational consequence if the active checkout is run with its current source: the four scheduled loops use Europe/Amsterdam local time, not the main-branch NEX5_TZ/Africa-Johannesburg clock. This is source-level behavior only; no service was started and no current loop activity was observed. The timezone migration should be included in branch reconciliation after the founder confirms that the October 26 decision is intended for the active host branch.
## 70. SignalToProblem bypasses the Tag Protocol for open_problems, unlike ProblemMemory

TAG_PROTOCOL.md §4 explicitly defines content-derived tags for open_problems from title + description. theory_x/tag_protocol/tag_ops.py registers open_problems as a taggable table and provides generate()/normalize()/write() operations.

The normal ProblemMemory creation path follows the spec: theory_x/stage7_sustained/problem_memory.py combines title and description, calls tag_protocol.generate(), JSON-serializes the result and includes it in its Writer INSERT.

SignalToProblem is a different producer. theory_x/signals/signal_to_problem.py inserts open_problems directly through a SQLite connection and supplies tags as json.dumps(["auto", f"signal:{sig['signal_type']}"]). It does not call tag_protocol.generate(), normalize(), or tag_protocol.write(). The resulting stored values retain the source-style 'auto' and 'signal:<type>' labels rather than the content-derived tags required by §4; punctuation normalization would also change the latter label.

Because SignalToProblem is appended and thread-started by the normal Stage 2 dynamic builder, this is a normal-wired open_problem producer, not merely a seed/admin utility. It creates open_problems entities through a path distinct from the compliant ProblemMemory writer.

This is a source-level Tag Protocol divergence unless signal-created problems have an approved exception. It is separate from the seven life-loop belief paths and from the SurpriseLoop duplicate-tag defect. Do not change the producer or normalize existing rows before Gate 0 / explicit approval.