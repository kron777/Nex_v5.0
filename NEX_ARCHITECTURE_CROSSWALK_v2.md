# NEX v5.0 — Architecture Crosswalk v2 (Output Paths)
 
## 0. Current branch and boot-wiring first pass (25 November 2026)

**Repository snapshot:** active host checkout at de93134f34adac07a3a41c2a05b33720510a2bfc. This branch is 4 commits ahead and 205 behind main; do not treat main as the active host source or merge it wholesale.

**Inventory distinctions:**
- The active branch has 42 top-level theory_x package directories. Package directories are not a count of cognitive faculties, MIND_MAP nodes or running loops.
- mind_map/MIND_MAP.yaml is absent from this active branch but present on main. The main file contains 34 node entries plus five arm entries; its own bootstrap comment and older roadmap references still say 30.
- The MIND_MAP metadata declares the map descriptive-only. Main's mind_map/mind_map.py --check --verify checks map structure, source references, freshness and declared absence claims; it does not inspect runtime callsites to prove that represented faculties cannot gate or veto decisions.
- sentience_dag.json and nex_next_dev.py form a separate development/buildability graph. nex_next_dev.py treats both built and live_unproven as satisfied for buildability. Do not conflate that rule with MIND_MAP authority or the roadmap's evidence ladder.
- This crosswalk's L0–L4 labels use the Watcher evidence_class vocabulary. They are not the Master Roadmap's separate L0–L5 capability ladder.

### Boot sequence and main producer/consumer paths

| Stage | Source wiring | Producer / consumer relationship | Evidence status |
|---|---|---|---|
| Substrate | run.py:60–70; substrate/paths.py:23–31 | Initializes six DBs: beliefs, sense, dynamic, intel, conversations, probes; creates Readers/Writers; beliefs Writer is wrapped by TaggingBeliefWriter | Static source |
| Sense | run.py:108–111; stage1_sense/__init__.py; scheduler.py:149 | 28 adapters (4 internal, 24 external) write sense_events. External feeds auto-start because SenseScheduler.__init__ calls start_all(); internal sensors run from boot | Static source; no current live run observed |
| Dynamic | stage2_dynamic/__init__.py | Reads sense_events into pipeline/tree state; cursor in dynamic.db; separate distillation loop promotes selected sense titles into beliefs; crystallization/consolidation/snapshot loops consume tree state | Static source; detailed per-loop DAG outstanding |
| World model | stage3_world_model/__init__.py | Belief retrieval, promotion/decay, harmonization, provenance erosion, synergizer and optional world consolidation | Static source; downstream effect not measured |
| Membrane | stage4_membrane/__init__.py | Classifies inside/outside and starts behavioural self-model loop when conversations reader is available | Static source |
| Coherence / holding / reshape | run.py:124–171; stage_gate/coherence_gate.py | Evaluates ThoughtPackets into ACCEPT/REJECT/HOLD/RESHAPE, records gate decisions, routes HOLD/RESHAPE and eligible REJECT events to separate mechanisms | Static source; full upstream producers/consumer outcomes outstanding |
| Fountain | run.py:538–584; stage6_fountain | Consumes sense, dynamic, belief, mode, drive and other state; generator produces a thought; output is consumed by sense/dynamic/belief writers and downstream snapshot/tag/decoder paths | Detailed output-path audit in §1; live L4 unknown |
| Chat | gui/server.py:api_chat | Receives prompt, assembles faculty context, optional workspace selection, invokes voice/tool path, persists conversation messages and returns reply | Detailed output-path audit in §2; live L4 unknown |
| Speech | run.py:611–629; speech/queue_consumer.py; beliefs.sql | If speech is enabled, SpeechQueueConsumer reads and updates speech_queue in beliefs.db and sends speakable items to the TTS backend | Static source; runtime enabled state unknown |
| Ancillary loops | run.py:242–741 | Additional loops include gate resolver, harmonic, genius tagger, counterfactual, drive emergence, affect, predictive substrate, signals, diversity, edge generation and decoder; several write derived/diagnostic state | Static source; each downstream consumer still needs mapping |

The scheduler documentation mismatch found during this audit is corrected in this PR: six DBs, 28 adapters and external-feed auto-start are now stated consistently in run.py, stage1_sense, scheduler.py and the GUI API description. No scheduler or feed startup behaviour was changed.

**Gate scope discrepancy discovered during this pass:**
- The coherence_gate.py module header still says HOLD and RESHAPE are only logged and not acted on. Current check() code calls HoldingZone.hold() for HOLD and put_reshape_pending() for RESHAPE. The header is stale.
- check() returns ACCEPT if _evaluate() raises an exception (reason gate_error_fallback). This is a fail-open availability policy and must be described explicitly; it is not equivalent to a fail-closed safety gate.
- stage2_dynamic._sense_distillation_loop explicitly bypasses CoherenceGate for precipitated_from_sense beliefs, on the stated basis that external perceptions are substrate content rather than internally generated thoughts. The gate module's “Universal: no generative path bypasses the gate” design commitment therefore needs a precise scope definition; do not silently treat the perception path as either a violation or an exception without reconciling the governing spec.




**Expanded boot/loop inventory:** The full Stage 2 registration list (26 conditional registrations), World Model/Membrane worker details, environment/service gates, request-driven versus autonomous faculty classification, and shutdown coordination are now traced in [NEX_PHASE0_DYNAMIC_LOOP_AND_BOOT_WIRING_AUDIT_2026-11-25.md](NEX_PHASE0_DYNAMIC_LOOP_AND_BOOT_WIRING_AUDIT_2026-11-25.md). This remains static L2 source evidence; the live thread set and effective flags are UNKNOWN.



**Prediction/surprise path:** [NEX_PHASE0_PREDICTION_SURPRISE_CROSS_FACULTY_AUDIT_2026-11-25.md](NEX_PHASE0_PREDICTION_SURPRISE_CROSS_FACULTY_AUDIT_2026-11-25.md) now maps Stage 35 prediction/surprise events and their four consumers, and separates them from the optional market and self-prediction systems. The findings remain static-source evidence; no live prediction or DB state was inspected.



**Problem/goal lifecycle:** [NEX_PHASE0_OPEN_PROBLEM_AND_GOAL_LIFECYCLE_AUDIT_2026-11-25.md](NEX_PHASE0_OPEN_PROBLEM_AND_GOAL_LIFECYCLE_AUDIT_2026-11-25.md) maps problem producers, state transitions and consumers; separates the GoalManager state vocabulary from CoherenceGate's query; and checks whether SentienceNode tick/decay methods are actually orchestrated. Findings are source-only, with live rows and host state UNKNOWN.



**Signals/patterns/retention:** [NEX_PHASE0_SIGNAL_PIPELINE_RETENTION_AND_PATTERN_AUDIT_2026-11-25.md](NEX_PHASE0_SIGNAL_PIPELINE_RETENTION_AND_PATTERN_AUDIT_2026-11-25.md) traces the detector and direct Fountain signal producers, current-tick pattern matching, SignalToProblem promotion, reaper allowlist drift, cross-database commit boundary, and bounded readers. No live signal data was inspected.



**Self-continuity Phase 1 seam:** [NEX_PHASE0_SELF_CONTINUITY_SEMANTICS_AUDIT_2026-11-25.md](NEX_PHASE0_SELF_CONTINUITY_SEMANTICS_AUDIT_2026-11-25.md) checks the default-OFF helper's tuple query, phrase semantics, tie ordering, resource cleanup and tests. The flag remains untouched; no live host state was inspected.



**M0.5 causal-trace coverage:** [NEX_PHASE0_INFLUENCE_TRACE_COVERAGE_AUDIT_2026-11-25.md](NEX_PHASE0_INFLUENCE_TRACE_COVERAGE_AUDIT_2026-11-25.md) checks the two actual output seams, missing trace/parent IDs and intermediate stages, L4 context declaration, fixture status and raw-preview retention boundary. The trace remains default-OFF; no runtime capture occurred.



**Main-only MIND_MAP reconciliation:** [NEX_PHASE0_MAIN_BRANCH_MIND_MAP_RECONCILIATION_2026-11-25.md](NEX_PHASE0_MAIN_BRANCH_MIND_MAP_RECONCILIATION_2026-11-25.md) confirms the main/active-host divergence, 12 map source references absent from the active-host base, the descriptive-only constraint, and the separation from sentience_dag build order. No files were imported.



**Moltbook external I/O:** [NEX_PHASE0_MOLTBOOK_EXTERNAL_IO_AND_DRY_RUN_AUDIT_2026-11-25.md](NEX_PHASE0_MOLTBOOK_EXTERNAL_IO_AND_DRY_RUN_AUDIT_2026-11-25.md) maps listener/responder/poster side effects, GET versus non-GET dry-run behavior, synthetic local success states, outbound belief filtering and inbound DM handling. No credentials or remote endpoints were accessed.

**Important:** this boot inventory is a forward wiring map, not a complete producer/consumer DAG. It does not prove that every declared faculty is operationally consumed, nor does it establish L3/L4 runtime evidence. The two detailed paths below remain the only end-to-end output-path audits in this document.


> **Current branch status (25 Nov 2026).** This crosswalk is refreshed against the active host branch claude/nex-continuity-wire at de93134f34adac07a3a41c2a05b33720510a2bfc. It contains a first-pass boot inventory plus the two detailed output-path audits below. It is still a partial M0.3–M0.4 crosswalk: the complete producer/consumer DAG across every theory_x faculty, substrate, speech and GUI remains outstanding. See [NEX_PHASE0_CURRENT_RECONCILIATION_2026-11-25.md](NEX_PHASE0_CURRENT_RECONCILIATION_2026-11-25.md) and [NEX_PHASE0_VERIFIED_DEFECT_BACKLOG_2026-11-25.md](NEX_PHASE0_VERIFIED_DEFECT_BACKLOG_2026-11-25.md) for current branch, runtime and defect evidence.


**Master Roadmap v3.0 Phase 0 — deliverables M0.3–M0.4 (seed scope).**

- **Branch:** `claude/nex-continuity-wire` · **Head:** `de93134f34adac07a3a41c2a05b33720510a2bfc`
- **Scope decision (Optimal Functional Tension).** A full producer/consumer DAG
  across the active branch's 42 top-level theory_x package directories is a
  multi-increment effort and is **OUTSTANDING** (see §5). This v2 crosswalk is grounded end-to-end for exactly the **two output
  paths the Phase-0 causal trace instruments** — the Fountain cycle and the Chat
  turn — because an audit of the paths we hook is worth more than a speculative
  whole-system diagram. Every node cites a file:line read from the tree.
- **Governing note.** The L0–L4 ladder is defined here (§3) by grounding it in the
  repository's **existing Watcher `evidence_class` vocabulary**, not by reproducing
  a governing PDF that is not in the workspace.

---

## 1. Fountain cycle — producer / consumer crosswalk

**Driver:** `theory_x/stage6_fountain/__init__.py:fountain_loop` (daemon thread,
interval from `mode_state.current().fountain_interval_seconds`).

**Single producer call:**
`FountainGenerator.generate(dynamic_state, beliefs_reader) -> Optional[str]`
(`theory_x/stage6_fountain/generator.py:1356`).

| Role | Component | Source |
|---|---|---|
| **Inputs (read)** | `dynamic_state`; `beliefs` reader; `sense` reader; `conversations` reader; `mode_state`; `problem_memory`; `drive_emergence`; `competing_drives`; `coherence_gate`; `erosion`; `metacognition` | `build_fountain(...)` wiring, `__init__.py:108–127` |
| **Readiness gate** | `ReadinessEvaluator.score() / is_ready()` | `readiness.py`; `__init__.py:162–167` |
| **Producer** | `generator.generate(...)` → `thought` | `generator.py:1356` |
| **Consumers (write)** | `sense_writer` → `sense.sense_events`; `dynamic_writer` → `dynamic.fountain_events` / `fountain_crystallizations`; `beliefs_writer` via `FountainCrystallizer` → `beliefs.*` | `generator.py:891–892`, `crystallizer.py` |
| **Downstream** | `StateSnapshotWriter.write_snapshot()`; drive-probe spawn; genius tagger; decoder daemon | `__init__.py:182–193`, `run.py` |

**Causal-trace hook (this increment):** immediately after the producer call
(`__init__.py`, after `thought = generator.generate(...)`), a **default-OFF**,
fail-safe `influence_record.tracer().record_fountain_fire(...)`. It reads only
values already in scope (`thought`, `mode_state.current_name()`,
`generator.last_fire_ts()`, `generator.total_fires()`), performs no new reader
traversal, and never mutates `thought`.

**Honest gap:** belief-level attribution (which stored beliefs the generator
retrieved for a given fire) lives *inside* `generate()` and is **not** hooked in
this minimal increment — recorded as `L0/UNKNOWN` in the `unresolved` field.

---

## 2. Chat turn — producer / consumer crosswalk

**Entry:** `gui/server.py:api_chat()` (`POST /api/chat`, line 1145).

| Role | Component | Source |
|---|---|---|
| **Input** | `prompt` (user message), `register`, admin/session context | `api_chat()` body |
| **Assembly** | `_assemble_chat_blocks()` — ~13 faculty blocks | `gui/server.py:198` |
| **Routing** | RAG-first verbatim; or HYBRID operator composition for admin (`_use_operator_composition`); chat memory (`_chat_memory_active`) | `gui/server.py:255–281` |
| **Producer** | voice calls `VoiceRequest(...)` at `:2061 / :2083 / :2119`; repeat/mirror regeneration guards | `gui/server.py`, `voice/llm.py` |
| **Finalise** | `text = _sanitize_reply(_strip_question_parrot(text, prompt))` | `gui/server.py:2163` |
| **Consumer (write)** | `writer.write("INSERT INTO messages ...")` → `conversations.messages` | `gui/server.py:2168` |
| **Return** | `jsonify({"text": text, "register": …, "voice_ok": …})` | `gui/server.py:2180` |

**Current-branch continuity addition (Phase 1 source, default-OFF):** `run.py:473` constructs `SelfMindView`, `run.py:720` passes it into `AppState`, and `gui/server.py:1512` appends `current_summary()` to `belief_text` for this chat-composition path. The summary is implemented at `theory_x/stage_tom/self_mind_view.py:434` and calls `continuity_for_prompt()` in `self_binding.py:345`. It is enabled only by `NEX5_SELF_CONTINUITY=1`; default is OFF. This is a source-level Phase 1 context modification, not part of the InfluenceRecord trace hook. No live activation or behavioural effect is verified; do not arm it before Gate 0 and explicit approval.

**Causal-trace hook (this increment):** between the `messages` insert and the
`return jsonify(...)` (`gui/server.py:2180`), a **default-OFF**, fail-safe
`influence_record.tracer().record_chat_turn(...)` reading `prompt`, final `text`,
`register.name`, `session_id`, `voice_ok`, `tool_used`. Never mutates `text`.

**Honest gap:** faculty-block attribution (which of the ~13 assembled blocks
shaped the reply) is **not** hooked — recorded as `L0/UNKNOWN`.

---

## 3. L0–L4 evidence ladder (grounded in the Watcher vocabulary)

Defined in `influence_record.py` (`L_TO_EVIDENCE_CLASS`), test-guarded by
`test_evidence_ladder_maps_to_watcher_vocabulary`:

| Level | Meaning | Watcher `evidence_class` |
|---|---|---|
| **L0 UNKNOWN** | no evidence | `unknown` |
| **L1 INFERRED** | indirect / heuristic | `inferred` |
| **L2 STATIC** | present in source/state, not observed acting | `static` |
| **L3 OBSERVED** | observed in an instrumented/controlled path (test/fixture) | `implemented` |
| **L4 RUNTIME** | observed in the **live** runtime | `measured` |

**Gating rule:** the overlay asserts **L4 only** when the live process declares
`NEX5_INFLUENCE_TRACE_CONTEXT=runtime` (founder-authorised live run). Until then
every captured value is at most **L3**, and **L4 is explicitly UNKNOWN** — matching
"keep unknown runtime evidence explicitly UNKNOWN." The committed fixture capture
(`docs/phase0_influence_capture_fixture.jsonl`) is L3 throughout.

---

## 4. Current evidence state of the two paths

| Path | Source present (L2) | Instrumented/tested (L3) | Live runtime (L4) |
|---|---|---|---|
| Fountain fire | ✅ `generator.py:1356` + seam | ✅ fixture capture + 16 tests | **UNKNOWN** (host-gated) |
| Chat turn | ✅ `gui/server.py:2163` + seam | ✅ fixture capture + 16 tests | **UNKNOWN** (host-gated, also needs `flask` + voice endpoint) |

---

## 5. OUTSTANDING (not done in this increment — honest scope)

1. **Full-system producer/consumer DAG** across `theory_x/` (~40 stages),
   `substrate`, `speech`, `gui` — the complete M0.3–M0.4 crosswalk. This v2 covers
   only the two output paths.
2. **Belief-level and faculty-block attribution** (the `L0/UNKNOWN` gaps in §1–§2)
   — requires deeper hooks inside `generate()` and `_assemble_chat_blocks()`.
3. **Live L4 capture** of one real Fountain cycle and one real Chat turn — requires
   the running NEX (voice endpoint, `flask`) and founder authorisation to enable
   the flag on the live process.
4. **RDO v1.3 Stage 1 Watcher** reconciliation vs Watcher v3.0 — on the RDO branch
   family, not this tree.


## 6. Additional source-trace tranche (25 November 2026)

A bounded continuation of the first-pass boot inventory now traces Sense intake through the Dynamic A–F pipeline, separate sense-to-belief distillation, Dynamic crystallization, World Model maintenance/synthesis, CoherenceGate/Holding Zone/Reshape, and Membrane self-model inputs. It also records two direct belief-write/gate-scope questions and the current evidence limits. See [NEX_PHASE0_PRODUCER_CONSUMER_TRACE_TRANCHE_2026-11-25.md](NEX_PHASE0_PRODUCER_CONSUMER_TRACE_TRANCHE_2026-11-25.md).

This tranche remains static-source evidence only. It does not complete the full faculty DAG, establish current thread/service activity, or resolve gate scope against Frozen V2.1. No runtime or behavioural changes were made.


**Belief-writer census update (25 November 2026):** the linked tranche distinguishes the `TaggingBeliefWriter` (tag injection/persistence wrapper) from CoherenceGate. The expanded source-verified subset now includes at least nine direct runtime producer paths: sense distillation, Fountain `self_rut_notice`, and seven Stage 2 life-loop writers (Pattern, Witness, Identity, Surprise, Remember, Wonder and Fetch). It separately records the locked self-location boot seed, resolver-mediated Holding Zone promotion, and conditionally gated EmergentDrive proposal application. Mutation-only paths (promotion/demotion, harmonizer retirement, erosion, affinity and optional best-of-cluster replacement) are classified separately from new belief inserts.

The life-loop modules are appended to the `build_dynamic()` loop list and started by its daemon-thread factory in source. This is static wiring evidence, not proof that any of those loops are active on the host. The new direct-write paths use their own SQLite connections and do not call CoherenceGate in the inspected insert functions. Their intended authority and gate scope remain unresolved pending Frozen V2.1 and founder approval evidence.

The census remains partial: helper-mediated writes, alternate writers, and the remaining `theory_x` modules have not all been inspected. See sections 15–17 of the linked tranche. No architectural defect is declared solely from these source observations.


**Further boot-path reconciliation (25 November 2026):** the linked trace now also records the Membrane Behavioural Self-Model as a gated belief producer under normal `run.py` wiring, and the boot-time ResumptionSeeder as an existing-belief/probe mutation path rather than a new producer. The trace separates normal-start loops, constructed-but-not-started components, and environment-gated loops. These are source wiring categories only; effective host flags and live thread state remain UNKNOWN. See sections 18–20 of the trace tranche.


**Persistence-wrapper boundary:** the linked trace also establishes that `TaggingBeliefWriter` is only a chokepoint for eligible inserts routed through the wrapped shared Writer. Direct SQLite life-loop inserts and independent operator Writers bypass it. The wrapper's “universal chokepoint” comment therefore overstates source coverage; auto-tagging and its embedded IntakeResonance probe must not be assumed universal. CoherenceGate, tag generation and IntakeResonance remain distinct mechanisms. See trace §23 and backlog D-12/G-08.


**Belief-graph topology path:** the source trace now distinguishes EdgeGeneratorLoop and NovelAssociation as `belief_edges` producers, not belief-content producers. NovelAssociation also has a verified GUI prompt consumer (`gui/server.py` calls `format_for_prompt()` and appends its one-shot annotation to `belief_text`). Both loop outputs remain source-level evidence; runtime activation and causal effect are UNKNOWN. See trace §24.


**DailyLife / behavioural observation path:** the source trace now maps the Stage 2 DailyLife loop as a producer of internal `role='nex'` conversation messages, not beliefs. BehaviouralSelfModel's latest-100-NEX-message query and Metacognition's latest-five-NEX-message goal-drift query have no session/register filter, so these internal entries are eligible inputs to both observers. This is a verified source overlap, not a measured live effect. The DailyLife header also overstates Moltbook sending and scheduled sleep-mode effects; see trace §§25–26 and backlog D-13/G-09.


**Fountain control boundary:** the expanded trace follows readiness → retrieval/prompt assembly → voice → pre-gate sense/Fountain event persistence → quality filter → CoherenceGate → belief insertion → optional speech enqueue. The gate does not govern initial thought generation or the already-persisted Fountain event; it governs normal belief admission and therefore the downstream speech-queue path. Quiescent/voice-fallback outputs bypass crystallization, and the optional best-of-cluster update can mutate an existing belief before the normal gate. See trace §§30–31 and backlog D-15.


## 2026-11-25 source-trace expansion

The producer/consumer trace now covers Fountain generation and pre-gate persistence, Chat composition and the separate VoiceEngine substrate-first route, database-init and operator seed paths, HotObserver, dormant reanimation, graph producers/traversal, IntakeResonance coverage, DailyLife feedback, and retention telemetry. See `NEX_PHASE0_PRODUCER_CONSUMER_TRACE_TRANCHE_2026-11-25.md` §§29–58 and the expanded verified defect backlog.

Highest-priority source finding: Harmonizer's successful-synthesis branch retires both originals to Tier 8 and then calls `BeliefPromoter.decisive_contradiction(belief_id_b)`; that method clamps the tier to 7, reactivating one just-retired row while retaining its `[RETIRED]` prefix (backlog D-32). The current test checks only row A and does not exercise a bridge-belief synthesis branch.

Other important conditional/source findings include unfiltered retired-row access through HotObserver, Favorites/Surprise, reanimation, substrate emission and VoiceEngine; unfiltered graph ingestion through NovelAssociation/EdgeBuilder/EdgeGenerator; retired-node spreading activation; DormancyScanner's fixed oldest-50 scan; and producer-dependent IntakeResonance measurement (Dynamic double, Synergizer zero).

Residue retention source truth is corrected: `nex_db_reaper.py` includes a 2-day `beliefs.db:residue` target; the old residue module note claiming otherwise was stale. An isolated temp-DB test now covers that override. No live reaper was run.

These are source-level findings only. No NEX DB, live flag, service, runtime behavior, experiment, baseline, tripwire or gate setting was changed. Gate 0 remains blocked pending founder review of the Reality Report, Crosswalk and verified defect backlog.


## Governing specification version ambiguity

A repository file `SPECIFICATION.md` has now been located. It is dated 2026-04-23, marked “Phase 0 Locked”, calls itself the NEX 5.0 Constitution, and states that it wins over later engineering until explicitly revised. Its path history contains one commit and no later amendment. It is not labelled Frozen V2.1 and is not identified by the handover as the exact Frozen V2.1 artifact.

The April constitution materially conflicts with current source and the handover's later vocabulary: it defines Tier 8 as raw observations separate from the belief graph, while current code uses Tier 8 as retired tombstones; it specifies a new synthesized belief or deletion of both conflict originals, while current Harmonizer reuses an existing bridge and retains Tier 8 tombstones; it makes the one-pen writer queue non-negotiable, while several current modules write directly through SQLite; and it lists five databases while runtime paths define six.

Do not assume this April constitution is the Frozen V2.1 spec or silently override it. The exact V2.1 spec and founder Gate 0 sign-off remain absent from the searched archive/Library. Founder must identify the canonical governing version and approved amendments before normative remediation.


**One-Pen direct-connection census (25 November 2026):** the latest source tranche now enumerates direct write-capable connections outside the shared Writer queue in the normal-wired life/focus/daily-life/signal loops, plus HotObserver. Belief paths include affinity UPDATE and seven life-loop INSERT producers (Witness, Remember, Surprise, Wonder, Identity, Pattern, Fetch); FocusLoop, DailyLife and SignalToProblem also mutate dynamic/conversation/signal tables directly. The scorecard loop is a contrast: it delegates belief mutations through substrate.Writer. This is a source-level mismatch with SPECIFICATION.md §3 if that April constitution remains authoritative; exact Frozen V2.1 authority and host thread activity remain UNKNOWN. The same belief INSERT paths bypass TaggingBeliefWriter/embedded IntakeResonance. No migration or runtime change was made. See trace §61 and backlog D-36.

## Later Doctrine / Faculty Model authority layer

The repository also contains `theory_x/DOCTRINE.md` (May 9, header status DRAFT awaiting Jon's review/approval) and `theory_x/FACULTY_MODEL.md` (May 10, calls itself foundational). The Doctrine §7 amendment directs generative node writes through the Faculty Model + Coherence Gate; the Faculty Model says every node-generated thought passes the gate, while its implementation order preserves legacy Fountain/Synergizer paths during the initial gate phase.

The reshape path is implemented: HoldingZoneResolver retrieves up to 10 `reshape_pending` rows per tick, transforms and re-submits them through CoherenceGate; `tests/test_reshape.py` covers the path. These later documents are not labelled Frozen V2.1 and no founder sign-off record was found. Their relationship to the April Constitution and the handover's Frozen V2.1 authority hierarchy remains for founder clarification.


**Additional One-Pen source paths:** Fountain's fire path writes dynamic.db recursion_attrib through a direct connection; the normal-wired Moltbook listener/responder/poster loops write dynamic/sense tables directly; and GUI action endpoints write decoder tags, Fountain annotations, ghost flags and hypotheses through direct connections. Ordinary chat persistence and drive-proposal approval use Writer.write() as contrasts. Endpoint invocation, Moltbook client readiness and live activity remain UNKNOWN. The One-Pen census is still incomplete; see trace §62 and D-36.

**Correction to the One-Pen interpretation:** owner-authored PR #11 was merged 2026-10-17 and explicitly shipped the substrate.connect() factory migration while retiring the raw-sqlite import ratchet. The current test checks for raw sqlite3 imports outside substrate, not universal use of Writer.write(). Thus the direct-connection census is an intentional factory-migration inventory, not a confirmed runtime defect. April SPECIFICATION.md §3 and Writer docstrings still state a queue-only contract, so the exact current founder-approved transaction/serialization contract remains unresolved. See trace §64 and reclassified backlog D-36/G-24.

**Post-Phase-22 gate-coverage candidate:** seven life-loop belief producers (Remember, Wonder, Fetch, Identity, Pattern, Witness, Surprise) were added on 2026-05-16, after the May 10 universal-gating amendment. Each inserts a Tier-6 belief without a ThoughtPacket or CoherenceGate reference; build_dynamic() starts them. Whether background life-loop outputs count as “generative paths” under the approved Faculty Model remains unresolved. No behavior was changed. See trace §65 and backlog G-25.

**Self-model source classification candidate:** IdentityLoop, PatternLoop and WitnessLoop write Tier-6 first-person/self-reflective beliefs, but their source labels are absent from both Stage 4 `_INSIDE_SOURCES` and Fountain `_OWN_CONTENT_SOURCES`. SelfModel and MembraneRouter therefore exclude them from the explicit INSIDE self-inquiry context and Fountain's dedicated own-content slots. This may be intentional classification or a missed source registration; do not change allowlists without approval. See trace §66 and backlog G-26.

**Tag Protocol candidate:** the seven life-loop belief producers bypass TaggingBeliefWriter/tag_ops. Three supply hard-coded tags, three store `[]`, and SurpriseLoop can write duplicate `surprise` tags on its non-big-surprise branch. TAG_PROTOCOL.md says tags are content-derived and every tags-column path uses the helper. The connection-factory migration does not satisfy that separate semantic contract. Seed-belief scope and any approved life-loop exception remain unknown. See trace §67 and backlog G-27.

**Recursive self-model feedback candidate:** source shows IdentityLog → PatternLoop → PatternLog → WitnessLoop → WitnessLog, while IdentityLoop composes from metrics and its previous identity statement only. Its new-belief count is an aggregate metric; no semantic Pattern/Witness content feedback into the next IdentityLoop composition was found. Fountain separately injects the latest IdentityLog statement, not Pattern/Witness logs. The module docstrings claim a closed L1→L2→L3→L1 loop. See trace §68 and backlog G-28.

**Branch integration candidate — timezone:** main commit c247c240f8 (2026-10-26) records the owner decision for Africa/Johannesburg and centralizes time via NEX5_TZ/nex_config.local_tz. The active branch still hardcodes Europe/Amsterdam in IdentityLoop, PatternLoop, WitnessLoop and DailyLife, and its nex_config lacks the timezone helpers. The migration spans multiple modules and tests; do not cherry-pick only the four loops or merge main wholesale. See trace §69 and backlog D-38.

**Open-problem Tag Protocol candidate:** ProblemMemory uses tag_protocol.generate(title + description), but normal-wired SignalToProblem inserts open_problems with `['auto', 'signal:<type>']` directly and never calls the helper/normalizer. TAG_PROTOCOL.md §4 includes open_problems as content-derived taggable entities. See trace §70 and backlog G-29.

**review_queue status:** CounterfactualNode auto-promotion is explicitly disabled since 2026-05-16 because it removed active problems from FocusLoop/DailyLife too quickly; the source says Jon decides resolution rather than a three-ACCEPT counter. The two promotion tests are explicitly skipped. GUI GET/unflag endpoints remain, but the queue is intentionally dormant. Do not treat the missing enqueue path as a defect or re-enable it. See trace §71.