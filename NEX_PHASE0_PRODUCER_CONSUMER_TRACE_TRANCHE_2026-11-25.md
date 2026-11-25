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
| Identity YAML seeder (operator CLI) | Independent Writer | No | No | Omits tags; schema migration default `[]` | No call observed |\n| Spectrum loaders/batch (operator CLI) | Direct `sqlite3` | No | No | Copies existing tags or schema migration default `[]` | No call observed |
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
