# NEX v5.0 — Architecture Crosswalk v2 (Output Paths)

> **Scope and branch note.** This remains a two-output-path seed at the earlier fb87e24 snapshot, not the full-system M0.3–M0.4 crosswalk. Current branch identity, missing MIND_MAP source, Phase 1 continuity wiring and outstanding trace lineage are recorded in [NEX_PHASE0_CURRENT_RECONCILIATION_2026-11-25.md](NEX_PHASE0_CURRENT_RECONCILIATION_2026-11-25.md).


**Master Roadmap v3.0 Phase 0 — deliverables M0.3–M0.4 (seed scope).**

- **Branch:** `claude/nex-v5-audit-review-53ouqv` · **Head:** `fb87e24`
- **Scope decision (Optimal Functional Tension).** A full producer/consumer DAG
  over 96,220 Python LOC is a multi-increment effort and is **OUTSTANDING**
  (see §5). This v2 crosswalk is grounded end-to-end for exactly the **two output
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
