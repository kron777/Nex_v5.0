# NEX v5.0 — Architecture Crosswalk v2 (Mainline Evidence Snapshot)

**Snapshot:** `main` at `66a97964f0531c16d60637dc8291b42e0b73f00b`  
**Evidence date:** 27 November 2026  
**Boundary:** source-level map and controlled tests; not a live runtime audit.

## 1. Inventory and authority boundary

- `mind_map/MIND_MAP.yaml` is a descriptive index, not a runtime authority.
- Current YAML inventory: 39 `nodes:` entries and 5 `arms:` entries. The bootstrap comment and older roadmap references still say 30 nodes. Preserve the discrepancy for owner reconciliation; do not remove/merge entries to force the old count.
- `sentience_dag.json` and `nex_next_dev.py` are a separate development/buildability graph. The executable satisfaction set is `built`, `live_unproven`, and `terminal`. The latter two are surfaced as caveats, not proof of operation.
- `mind_map/mind_map.py` performs schema/source/freshness checks and a static AST guard. The guard enforces the descriptive-only constraint, rejects specified action-authority fields, and scans configured runtime source roots for direct imports/references to `MIND_MAP.yaml`. It does not constitute a proof against all dynamic/indirect/external authority paths.

## 2. Static boot and substrate path

The current `run.py` boot sequence initializes the six substrate databases via `substrate.init_db.init_all()`, constructs Readers/Writers, builds mode/voice state, then builds the sense scheduler, dynamic layer, world model, membrane and Fountain before wiring the GUI/AppState. Speech is conditionally started according to its speech configuration.

The six database identities come from `substrate.paths.db_paths()`: beliefs, sense, dynamic, intel, conversations and probes. Each database has its own Reader/Writer path. A Writer's `write()` commits one statement in one database; `write_many()` is atomic inside one database only. There is no cross-database transaction across sense/dynamic/beliefs/conversations.

### Sense

`theory_x/stage1_sense/__init__.py:build_scheduler()` wires 28 adapters: 4 internal sensors and 24 external feeds. `SenseScheduler.__init__()` calls `start_all()`; external feeds therefore auto-start during normal construction/boot. The internal sensors are not controlled by the external-feed global run-event. Adapter wiring is static source evidence; it does not prove that every external feed successfully polls or produces events.

### Dynamic and world-model layers

`theory_x/stage2_dynamic/__init__.py` constructs dynamic state and registers its core worker loops. Additional loops are guarded by optional imports/configuration. Successfully registered loops are started as daemon threads by the builder. This is static boot wiring, not proof that each thread is alive or has downstream effect on the host.

`theory_x/stage3_world_model` provides belief retrieval and associated world-model services consumed by Chat and Fountain. Static construction does not establish retrieval quality or live model performance.

### Membrane, Coherence Gate and consumers

`theory_x/stage4_membrane` classifies queries as INSIDE/OUTSIDE and routes to the corresponding retrieval surface. It may also start a behavioural self-model loop when the conversations reader is present.

`theory_x/stage_gate/coherence_gate.py` evaluates ThoughtPackets into ACCEPT/REJECT/HOLD/RESHAPE, persists decisions in `beliefs.db:gate_decisions`, and has optional downstream handling for REJECT/HOLD/RESHAPE/ACCEPT. Its current evaluation exception policy is fail-open: an evaluation exception is recorded and returned as ACCEPT with reason `gate_error_fallback`. This report documents the code; it does not endorse or change that policy.

## 3. Theory-X source-package inventory and boot distinction

The Git tree at the audited snapshot contains 43 immediate subdirectories under
`theory_x/`, including 27 directories whose names begin `stage`. This is a
filesystem inventory only. It does not mean that 43 faculties are declared,
that 27 stages are instantiated, or that any worker is alive.

| Inventory class | Packages present at this snapshot |
|---|---|
| Stage-named packages (27) | `stage1_sense`, `stage2_dynamic`, `stage3_world_model`, `stage4_membrane`, `stage5_self_location`, `stage6_fountain`, `stage7_moltbook`, `stage7_sustained`, `stage8_goal_manager`, `stage9_metacognition`, `stage10_imagination`, `stage_affect`, `stage_capability`, `stage_counterfactual`, `stage_drives`, `stage_emphasis`, `stage_finitude`, `stage_gate`, `stage_prediction`, `stage_provenance`, `stage_self_maintain`, `stage_self_narrative`, `stage_social`, `stage_throw_net`, `stage_tom`, `stage_warrant`, `stage_world` |
| Ancillary packages (16) | `arcs`, `auto_probe`, `coincidence`, `diversity`, `genius`, `harmonic`, `life`, `memory`, `modes`, `probes`, `signals`, `snapshots`, `substrate`, `sustained`, `tag_protocol`, `world_bridge` |
| Top-level Python modules | `__init__.py`, `conversation_memory.py`, `executive_control.py`, `focal_set.py`, `working_memory.py` |

### Directly visible boot wiring

`run.py` explicitly imports/builds the core staged sequence: Sense
(`build_scheduler`), Dynamic (`build_dynamic`), World Model
(`build_world_model`), Membrane (`build_membrane`), Self-Location
(`SelfLocationCommitment`) and Fountain (`build_fountain`). It also
constructs/wires supporting capabilities including Coherence Gate, Holding
Zone/Resolver, ProblemMemory, GoalManager, Metacognition, NovelAssociation,
Throw-Net components, Drive Emergence, Warrant, AffectState, Predictive
Substrate, PersonaResponder/SelfMindView, World/Self Prediction loops,
Self-Maintain shadow and ToolRegistry/ToolCaller. Several constructions are
inside guarded `try` blocks or depend on flags, readers, optional modules or
external configuration; presence of an import line is not proof of successful
construction.

Separate workers started elsewhere include speech, signals, diversity,
edge-generation and decoder paths. Stage 2 and Stage 3 factories also register
and start loops internally. Exact per-loop liveness, poll success, event
production and downstream consumption remain UNKNOWN without host/runtime
evidence.

The complete forward/backward audit remains open: this inventory is a search
map to the code, not a declaration that every package has been traced from
declaration through emission to a verified consumer.

### Writer and Coherence Gate scope boundaries

The repository's own `SPECIFICATION.md §8` and `substrate/writer.py` define
one Writer queue/thread per database as a non-negotiable one-pen rule. The
current RememberLoop, Diversity EdgeBuilder and Sustained FocusLoop instead
open raw SQLite connections and commit writes directly (G-61). These paths
need an intentional migration and concurrency tests; they have not been
changed in this Phase 0 audit.

The Coherence Gate source declares universal coverage for thoughts generated
by faculty nodes. The current RememberLoop temporal-link belief and Fountain
`self_rut_notice` reflective belief are inserted directly without Gate checks;
Stage-2 `precipitated_from_sense` writes are explicitly classified by their
producer as external perception rather than thought (G-62). This is a Gate
scope/specification reconciliation item, not permission to change policy.


### Problem/Goal lifecycle scheduler boundary

`ProblemMemory.decay()` (30-day stale close) and `GoalManager.decay()`
(60-day stale cancel) exist and both objects are constructed/registered during
normal boot. The registry itself has no orchestration loop. In the reviewed
`run.py` and `gui/server.py` paths no call to these two nodes' `tick()` or
`decay()` was found; Chat uses matching/active-goal retrieval and the GUI uses
CRUD/list operations. Existing tests invoke decay manually, not through a
process scheduler. This is a bounded source audit, not proof that no operator
or auxiliary entry point can invoke the methods. See G-60 in the backlog.

## 4. Backward/forward path crosswalk

| Path | Producer → selection/gate → persistence → consumer | Evidence |
|---|---|---|
| Sense | 28 wired adapters → `sense_events` → Stage 2 dynamic consumers | Static source; host polling not observed |
| Fountain | readiness → retrieval manifest → prompt/workspace → voice/reconcile candidates and filters → `sense_events` + `dynamic.fountain_events` → quality gate → Coherence Gate → `beliefs.beliefs` and `fountain_crystallizations` → optional speech queue | Static source plus L3 paired fixture tests |
| Chat | `/api/chat` input/session/message → membrane/fallback retrieval → 13 faculty blocks/workspace → voice/tool path → sanitization → conversation message and response | Static source plus L3 paired fixture tests |
| Speech | selected speakable crystallized beliefs → governor → `beliefs.speech_queue` → asynchronous consumer/TTS backend | Static source; host enabled state unknown |
| DAG tooling | `sentience_dag.json` prerequisites → `nex_next_dev.py` satisfaction rule | Static source |

This is not yet a complete producer/consumer DAG for every faculty under `theory_x/`. Faculties without a traced downstream consumer, or whose live effect is not measured, remain open work rather than being marked complete.

## 5. M0.5 causal trace

Roadmap v3.0 Phase 0 M0.5 is implemented in `influence_trace.py` and integrated into Fountain and Chat. The switch is `NEX5_TRACE_OVERLAY`; unset/zero is OFF. When enabled, the overlay appends parent-linked JSONL events to a sidecar (default `logs/nex_causal_trace.jsonl`), never to a substrate database. It hashes text-bearing data and stores UTF-8 byte lengths rather than raw prompts, beliefs or outputs.

The trace includes explicit `trace_id`, `event_id` and `parent_ids`. An event only has causal parents supplied by the producer; mere chronological proximity does not infer a parent edge. The collector does not read substrate databases or participate in decisions. The Gate decision's persisted `gate_decisions` row is recorded as a Writer delta and linked to the upstream quality-gate event.

### Fountain

Observed stages include readiness, retrieved candidate identifiers/source kinds, workspace selection, prompt context/assembly, output filters and retries, quality/Gate outcomes, `sense_events`, `fountain_events`, belief insert, crystallization link and speech-queue outcome. Substrate-voice, quiescent, voice-fallback and stillness paths are distinguished because they bypass different portions of the normal generation/crystallization path.

### Chat

Observed stages include input arrival, session/user-message writes, membrane classification and retrieval candidate identifiers (or fallback retrieval), faculty-block workspace selection, final prompt assembly, tool/voice path, assistant-message write and final reply. The Chat crystallization Gate is explicitly `NOT_APPLICABLE`: a Chat reply is a conversation output, not a belief-write request.

### Evidence and limits

`NEX_CAUSAL_TRACE_SAMPLE.json` contains one synthetic Fountain cycle and one synthetic Chat turn. Both are fixture captures, labelled L3. The complete paired tests prove semantic equivalence for the tested outputs, prompts/model requests, retrieved/selected candidates, confidence/belief state, Gate decisions and relevant database state with tracing off versus on. They do not prove identical timing; synchronous file I/O can add latency when explicitly enabled.

No live NEX process or runtime context was enabled. L4/runtime evidence remains UNKNOWN. The sample trace is not a live capture.

## 6. Additional bounded lifecycle and graph findings

The following source-level observations were rechecked against this mainline
snapshot after recovery from older audit drafts. They describe conditions and
coverage gaps, not verified live incidents:

- **Counterfactual progress:** `CounterfactualNode` selects the oldest open
  problem by `last_touched_at ASC`, but its own path does not call
  `ProblemMemory.touch()` after an empty retrieval, unbuildable set or Gate
  attempt. Current tests exercise one open problem, not multi-problem rotation.
  Whether persistent focus or LRU rotation is intended remains unresolved.
- **TimeFetch eligibility:** basic belief search filters confidence and content
  length but not tier/paused/locked/erosion status; novel-association and arc
  endpoints are not checked against those lifecycle states. Tests cover the
  documented basic filters, not those status exclusions. This is an eligibility
  policy question, not an automatic defect.
- **Warrant pagination:** lineage/arc use-day cursors use strict timestamp-only
  keysets with 20,000-row batches. Equal timestamps crossing a batch boundary
  could be skipped; no live population or skipped row was observed. Current
  tests do not include a tied-timestamp boundary fixture.
- **Warrant source coverage:** the scorer reads
  `dynamic.substrate_snapshots.walk_anchor_id`; the recorder's use-day scan
  does not. The only Fountain snapshot call found is in the substrate-voice
  path, gated by `NEX5_RECONCILE != '1'`; the tracked keepalive recipe sets
  `NEX5_RECONCILE=1` alongside `NEX5_WARRANT_RECORD=1`. These are source
  conditions only; effective host flags remain unknown.
- **RememberLoop lineage:** `theory_x/life/remember_loop.py` inserts a Tier-6
  temporal-link belief and returns the old/recent source IDs, but the inspected
  insert does not persist those parent IDs in `belief_lineage`. No direct
  `run.py` start call was found, and the associative-recall tests exercise a
  different Fountain method; live activation is not established.
- **EdgeBuilder metric:** `theory_x/diversity/edge_builder.py` tests
  connection-cumulative `cx.total_changes > 0` after `INSERT OR IGNORE`.
  Once a statement changes the connection, later ignored duplicates may still
  inflate the reported `wrote` count. This is a logging metric issue, not a
  persisted-edge mutation.
- **Graph admission:** Stage-2 Diversity EdgeBuilder writes generic
  `cross_domain` edges. Stage-3 EdgeGenerator only queues recent
  `fountain_insight`/`synergized` beliefs with no edge in either direction,
  so a generic edge can pre-empt later typed relation classification. Whether
  this is intended early saturation is unresolved; no live graph loss was
  measured.
- **Goal state contract:** GoalManager creates and lists `open` goals, while
  CoherenceGate's context query selects only `active`; the Gate fixture seeds
  `active` directly and therefore misses the normal GoalManager path.
- **Problem stuck-state contract:** FocusLoop moves pinged/cooldown-suppressed
  open problems to `stuck`, while ProblemMemory, CounterfactualNode and Gate
  context select only `open`. Whether this is intentional human handoff or an
  orphaned lifecycle state remains unresolved.

For precise source references, conditions, test coverage and dispositions, see
Section F of `NEX_PHASE0_VERIFIED_DEFECT_BACKLOG_2026-11-27.md`.

## 7. Discrepancies and next audit obligations

1. Host/runtime identity, process state, service health, live database hashes, model digest and local performance metrics have not been collected in this mainline pass.
2. The mind-map node-count convention (39 YAML nodes vs older “30” references; plus 5 arms) remains unresolved.
3. Two doctrine files referenced by map metadata are missing in the CI snapshot; node source-verification dates are stale, and `p13_finitude` carries a past-due unblock marker.
4. The full theory_x faculty-by-faculty forward and backward audit remains incomplete.
5. Coherence Gate fail-open behaviour is documented but not altered; any policy change is outside this observational increment.

No Phase 1 behavioural work or Gate 0 approval is implied by this crosswalk.
