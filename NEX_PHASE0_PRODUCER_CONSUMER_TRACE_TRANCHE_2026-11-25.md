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
3. Fountain drive probe → gate (source `drive_probe`); the probe itself is delivered to gate/holding/resolution rather than directly inserted by that function.
4. Reshape resolver → transforms held candidate → re-submits through gate.

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
