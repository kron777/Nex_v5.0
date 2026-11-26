# NEX Architecture Crosswalk v2
## Source-to-boot-to-consumer reconciliation — 27 November 2026

**Pinned source snapshot:** main at 49b1d6c0b247b5694259e1225d077fc60e5c3706.
**Evidence boundary:** cloud/source and completed CI only. Host/runtime state is not observed.
**Purpose:** reconcile declared architecture with actual source wiring and the paths that consume its outputs. This is not a new architecture proposal and does not modify the frozen specification/register.

## 1. The three inventories

### Mind map

mind_map/MIND_MAP.yaml contains 30 descriptive nodes across five arms:

- Prices: amoha, karuna, upeksa, apramada, alobha, vedana, mana, vicikitsa, drsti.
- Writes: smrti, virya, prasrabdhi, sraddha.
- Readers: p5_second_order, kaukratya.
- Consumers: p6_unified_present, vitarka, vicara.
- Scope: p1_continuity, p2_train, p3_stakes, p4_interoception, p7_valence, p10_thickness, p11_agency, p12_selfreport, p13_finitude, p9_dissonance, hri_apatrapya, p8_episodic.

The map declares itself descriptive only: a node may not gate, score, block or veto an action. It is a ledger-role diagram, not a runtime registry or boot plan.

The evidence classes in its metadata are measured, implemented, static, inferred and unknown. The dark modifier means a path may exist and be tested without invocation in the live loop. The blocked modifier means an intentional refusal, not merely unfinished work. These modifiers must not be collapsed into an ordinary active/inactive flag.

The file metadata says it was built on 2026-11-09. Node last_verified dates range from 2026-11-09 to 2026-11-20. They are the dates recorded in the map, not a claim that all nodes were re-verified on 2026-11-27.

### DAG

sentience_dag.json contains 15 build/dependency nodes. It serves a different purpose from the mind map: it represents the build frontier and prerequisite relationships. nex_next_dev.py defines a prerequisite as satisfied for buildability when its status is built, live_unproven or terminal. live_unproven and terminal dependencies remain explicit caveats; they are not proof of operational success.

### Python source inventory

The complete recursive Git tree contains 273 Python files beneath theory_x/. Many subpackages have empty __init__.py files or expose only helpers. A directory or source class is not automatically a distinct booted faculty. For each subsystem, this crosswalk therefore distinguishes:

1. Declared: concept or package is present.
2. Constructed: run.py or another builder creates an instance.
3. Started: source calls a thread/loop start method.
4. Emitting: an event/row/result is produced.
5. Consumed: a downstream function uses that result.
6. Runtime-observed: the host has been seen doing it.

Only the first five can be established from source and tests here. The sixth remains UNKNOWN.

## 2. Mind-map policy enforcement

mind_map/mind_map.py implements check_descriptive_only(). It checks node metadata for forbidden action-authority fields and scans configured runtime Python roots using the AST to reject runtime imports/references to mind_map and references to MIND_MAP.yaml outside docstrings. The main CI workflow invokes:

- ci/test-sandbox/probe.py
- scripts/check_test_baseline.py
- mind_map/mind_map.py --check --verify

This is a static source guard plus CI execution. It is not a formal proof against every dynamically constructed import, reflection path or indirect authority influence. The accurate claim is “static AST policy guard is implemented and invoked by CI”, not “all possible authority paths are dynamically proven impossible”.

### Doctrine references that do not resolve

The mind-map metadata lists four doctrine files. The full recursive repository tree contains SENTIENCE_SYNTHESIS.md, but does not contain:

- VIRTUE_SLATE.md
- mental_factors_inventory_alobha_spec.txt

These two references are unresolved repository documentation links. This finding does not establish that the documents never existed elsewhere; it establishes that the pinned main tree does not contain either filename.

## 3. Forward audit: declaration → construction → start → emission → consumer

| Subsystem | Source wiring / construction | Start or activation | Downstream consumer | Evidence boundary |
|---|---|---|---|---|
| Substrate | init_all() and Writer/Reader construction in run.py | Writers start worker threads in construction | All database-backed faculties | STATIC; schema and host DB contents UNKNOWN |
| Self-location | SelfLocationCommitment constructed and commit invoked during boot | Commit is a startup write | Locked self-location belief can be read by belief/world model | Source path VERIFIED; live host state UNKNOWN |
| Modes / voice state | build_mode_state() and build_voice_state() | State objects constructed | Fountain and Chat request generation | STATIC; model endpoint health UNKNOWN |
| Stage 1 Sense | build_scheduler() wires 28 adapters: 4 internal, 24 external | SenseScheduler constructor calls start_all(); external feeds auto-start in normal construction | sense_events consumers in dynamic/Fountain/world-model paths | 28 wired is STATIC; successful feed polling is UNKNOWN |
| Stage 2 Dynamic | build_dynamic() constructs core dynamic state and loop set | Nine unconditional core loops; optional loop groups are added through guarded imports/configuration | Stage 3, readiness, attention, world bridge and Fountain read dynamic status/events | Source wiring VERIFIED; per-loop host activity UNKNOWN |
| Stage 3 World Model | build_world_model() constructs retrieval/world state | Factory starts six worker loops | Chat membrane routing, world bridge, belief consumers and consolidation paths | Source wiring VERIFIED; semantic effect/runtime consumption requires host evidence |
| Coherence Gate | Gate, HoldingZone, resolver and TriggerDetector constructed in run.py | Resolver loop started; Gate is called inline at configured belief-write paths | Fountain crystallization and other configured belief-write producers | Source call path VERIFIED; decision counts and runtime effects UNKNOWN |
| Stage 4 Membrane | build_membrane() constructs classifier, self-model and router | Behavioural loop thread starts when conversations reader is available | Chat route classifies inside/outside and selects the appropriate retrieval route | Inline Chat consumption STATIC; actual live requests UNKNOWN |
| Stage 7 Sustained / Problem Memory | ProblemMemory constructed | Used by Fountain and API; not an independent cognitive loop by itself | Problem injections and problem API operations | Constructed/consumed in source; live state UNKNOWN |
| Stage 8 Goal Manager | GoalManager constructed in run.py | Used by Gate, Chat and related paths | Gate checks and problem/goal context | Source wiring STATIC; active consumer volume UNKNOWN |
| Stage 9 Metacognition | Metacognition constructed | Its worker/maintenance paths are source-wired where called | Stillness/attention and related downstream records | Source wiring STATIC; live emission UNKNOWN |
| Stage 10 Imagination | NovelAssociation constructed and start_loop() called under guarded import | Thread starts if import/construction succeeds | Association outputs and downstream belief/goal consumers | Source start call VERIFIED; runtime output UNKNOWN |
| Throw-Net monitor | TimeFetch, RefinementEngine, ThrowNetEngine and monitor constructed in guarded block | ThrowNetMonitor starts only when NEX5_THROWNET=1; default retired/disabled path is documented | Monitor diagnostics/trigger path | Optional source wiring; host flag and execution UNKNOWN |
| Substrate Harmonic / Genius Tagger | Components constructed in guarded blocks | Their log/tag loops are started by run.py | Diagnostic and tagging consumers; not equivalent to cognitive authority | Source wiring only; output and consumption unobserved |
| Counterfactual Node | CounterfactualNode constructed with dependencies | start_loop() invoked | Counterfactual and review/learning paths | Source start call; output/runtime UNKNOWN |
| Drive Emergence / Competing Drives | Both constructed | start_loop() invoked for the relevant instances | Fountain mode/activation and drive-related context | Source wiring; useful behavioural effect UNKNOWN |
| Warrant Recorder | Constructed only when NEX5_WARRANT_RECORD=1 | Optional loop start | Warrant evidence records | Optional; current host flag UNKNOWN |
| VoiceEngine | Constructed in run.py | Not an independent daemon in this boot path; called inline from Chat | Chat stored-answer shortcut, retrieval trigger and response selection | Inline source consumer; request frequency/runtime UNKNOWN |
| Affect State | AffectState constructed | start_loop() invoked | Chat faculty blocks, state readers and related consumers | Source wiring; live state UNKNOWN |
| Predictive Substrate | Constructed | start_loop() invoked | Surprise/readiness/confidence-related paths | Source wiring; actual predictions/consumption UNKNOWN |
| Persona Responder | Constructed only when configured | Optional loop start | Chat or social response surfaces | Optional; current flag UNKNOWN |
| SelfMindView | Constructed | start_loop() invoked | Self-model and Chat context | Source wiring; output consumption UNKNOWN |
| World / Self Prediction | Loop objects constructed only under their respective flags | NEX5_WORLD_PRED and NEX5_SELF_PRED gate start | World/self expectations and downstream prediction checks | Optional; current host flags UNKNOWN |
| Self-maintenance shadow | Constructed only under NEX5_SELF_MAINTAIN_SHADOW | Optional loop start | Self-maintenance diagnostics | Optional and observational; host flag UNKNOWN |
| Fountain | build_fountain() constructs generator/crystallizer state | Fountain loop starts on its scheduler path | sense_events, fountain_events, retrieval logs, T6 beliefs, crystallization links and optional speech queue | Source wiring and tests; complete host cycle UNKNOWN |
| Speech | SpeechQueueConsumer constructed if SpeechConfig.enabled | Consumer daemon starts if enabled | speech_queue rows created by crystallizer, then synthesises/plays and records status | Source wiring; voice device/output UNKNOWN |
| Signals | build_signal_loop() | Loop starts | Signal-to-problem and diagnostic consumers | Source wiring; actual signal volume UNKNOWN |
| Diversity | build_diversity_loop() | Loop starts; Fountain calls notify_fire() | Belief diversity/maintenance and related APIs | Source wiring; live efficacy UNKNOWN |
| Edge generator | build_edge_generator_loop() | Loop starts | belief_edges / world graph readers | Source wiring; edge production UNKNOWN |
| Probes | ProbeRunner constructed | Runs only when explicitly invoked/scheduled by its caller | Probe records and test/assessment paths | Static source; no live probes were run in this audit |
| Coincidence decoder | decoder_loop wrapped in a daemon Thread in run.py | Thread starts | Context/tag retrieval and coincidence decoding | Source start; useful output UNKNOWN |
| Arc reader | ArcLoop implementation exists and package exports builder | run.py explicitly treats it as retired/None in this snapshot | No active boot consumer established | Declared/implemented; no active loop wiring in run.py |

This table intentionally says “source start call” rather than “running”. A call to Thread.start() in run.py is not proof that the thread survives on the host, that its first iteration succeeds, that it emits a row or that a consumer reads it.

## 4. Backward audit: outputs → upstream producers

### Chat reply

Observed source path in gui/server.py:

1. Validate incoming prompt.
2. Create/find conversations session and persist user message through conversations Writer.
3. Route the query through Membrane when Membrane and WorldModel are present; otherwise use the fallback WorldModel retrieval path.
4. Query VoiceEngine for a stored answer candidate where configured. A qualifying stored answer can be returned verbatim; otherwise it may become grounding for the composition path.
5. Assemble faculty blocks in the current order (operator, operator_anchor, compassion, compass, equanimity, apramada, virya, sraddha, prasrabdhi, affect_carry, convo, spectrum and tag). Default assembly concatenates all in order; NEX5_CHAT_WORKSPACE enables budgeted selection. NEX5_SELF_PRESENT is a separate optional salience carry path.
6. Execute an eligible tool if selected and configured.
7. If no earlier stored-answer return exists, call VoiceClient.speak(); retries are bounded and conditional.
8. Sanitize final text, persist assistant message, then return JSON to the client.

Chat response text is not itself a Tier-6 belief write. The Coherence Gate's Fountain crystallization decision is therefore NOT_APPLICABLE to an ordinary Chat reply. A tool result, a stored VoiceEngine answer and a newly generated LLM reply are different source kinds and must remain distinguishable.

### Fountain thought and belief

1. ReadinessEvaluator.score() checks dynamic status, branch focus, consolidation, belief count, elapsed time and optional modulation.
2. The generator can exit early through substrate-voice replay, quiescent mode, duplicate-retrieval stillness or voice fallback. These paths do not all produce a new model candidate or pass through crystallization.
3. The normal path builds a prompt using existing belief retrieval, recent sense, mode, problem/world context and prompt blocks; it retains a retrieval_manifest with candidate IDs/slots/rank.
4. It may use an existing substrate-emission or reconcile branch; otherwise VoiceClient.speak() returns a candidate. Language and frame filters may keep, retry or drop the candidate.
5. Generator writes an internal.fountain sense_events row and a dynamic.fountain_events row via separate Writers/transactions.
6. Retrieval manifest and prompt-block manifest may be persisted in additional dynamic.db write_many transactions.
7. FountainCrystallizer performs its quality checks and optional best-of-cluster upgrade; then CoherenceGate.check() if a gate instance was supplied. Non-ACCEPT outcomes return without a new Tier-6 belief insert.
8. On acceptance, FountainCrystallizer writes a Tier-6 row to beliefs.db and a separate fountain_crystallizations link row. These are separate committed writes, not a cross-database transaction.
9. If the source category is speakable, speech is enabled, text length fits, and SpeechGovernor says SPEAK, a speech_queue row may be inserted. SpeechQueueConsumer later marks it speaking, spoken, failed or suppressed.

A Fountain tick, a produced thought, a fountain_events row, an accepted Tier-6 belief, a speech queue row and audible speech are six different states. The crosswalk must not equate them.

### Gate boundary

The Coherence Gate currently handles ACCEPT, REJECT, HOLD and RESHAPE in source. The current check() exception path records the failure and returns ACCEPT with reason gate_error_fallback. This is a fail-open availability policy. It has been documented in PR #149 but not changed here. Treat it as an explicit policy/risk item for founder review, not as evidence of cognitive quality.

## 5. Persistence and transaction boundary

substrate/writer.py documents the one-pen contract and performs explicit transactions. Writer.write() commits one statement; Writer.write_many() commits a multi-statement batch atomically within that one database. There is no cross-database atomicity between sense.db, dynamic.db, beliefs.db and conversations.db.

The Fountain path also contains direct substrate.connect() commits in recursion_attrib and the momentum helper. These are not Writer deltas and are not covered by the one-pen guarantee. They are a concrete source-level contract discrepancy requiring a bounded decision/fix; they must not be disguised as Writer-based persistence in traces.

## 6. Confirmed documentation/code discrepancies

1. Stage 2 Dynamic's module header describes fewer always-on loops than the current factory registers. The factory has nine unconditional core loops plus optional loop groups behind guarded imports/configuration.
2. Stage 3 World Model's header describes two workers while its current factory starts six worker loops.
3. ARCHITECTURE.md and SENTIENCE_PROGRAM.md are high-level summaries; some boot ordering, optionality and diagnostic/retired status differs from current run.py. PR #148 repaired the specific SenseScheduler 23-versus-28 and auto-start description drift.
4. Mind-map meta.doctrine references VIRTUE_SLATE.md and mental_factors_inventory_alobha_spec.txt, which do not occur anywhere in the complete main tree. SENTIENCE_SYNTHESIS.md is present.
5. The Fountain recursion_attrib/momentum paths write directly through substrate.connect(), while substrate/writer.py defines Writer as the sole write path. This is a source-level persistence-contract discrepancy.

The earlier stale DAG buildability wording was corrected by PR #150. The Coherence Gate outcome/fail-open module description was corrected by PR #149. These corrections are part of the pinned main snapshot.

## 7. L0–L4 evidence discipline

- L0 UNKNOWN: not established by the available evidence.
- L1 INFERRED: reasoned from related evidence; not direct observation.
- L2 STATIC: visible in source, documentation or configuration.
- L3 OBSERVED: executed in a controlled test or CI fixture.
- L4 RUNTIME: observed on the actual NEX host/runtime.

This crosswalk assigns L2 to source wiring and file inventories; L3 only to completed tests/CI. It assigns no L4 values because no host-origin Watcher collection or authorised runtime trace was available in this audit.

## 8. Phase boundary and next gate

The trace candidate in PR #151 is a separate M0.5 implementation candidate. This crosswalk is pinned to main before its merge. The trace branch has completed one full regression attempt but exposed five unit-test fixture mistakes; the corrected exact-head run is pending. It is not yet accepted as a completed M0.5 deliverable.

The Master Roadmap v3.0 Gate 0 exit condition requires founder review and approval of:
- NEX_REPOSITORY_REALITY_REPORT.md
- NEX_ARCHITECTURE_CROSSWALK_v2.md
- NEX_PHASE0_VERIFIED_DEFECT_BACKLOG.md

This crosswalk does not declare Gate 0 passed or authorise Phase 1. No live experiment, prompt, confidence, selection order, substrate database or runtime deployment was changed by this audit.
