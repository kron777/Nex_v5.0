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
