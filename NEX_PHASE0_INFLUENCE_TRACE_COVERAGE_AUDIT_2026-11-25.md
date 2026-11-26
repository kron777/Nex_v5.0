# NEX Phase 0 — InfluenceRecord M0.5 Causal Trace Coverage Audit (25 November 2026)

## Scope and evidence boundary

Static-source review of `influence_record.py`, the actual Fountain and Chat call sites, the JSONL fixture and unit tests against source baseline `de93134f34adac07a3a41c2a05b33720510a2bfc`.

The current reconciliation records a roadmap extract that names `NEX5_TRACE_OVERLAY=0` and asks for `trace_id` / `parent_ids` across Input Arrival → Candidate Generation → Salience/Workspace Selection → Gate → SQLite Writer Delta → Output. The exact governing Frozen V2.1 and approval record remain absent. This audit compares actual implementation with that recorded extract, but does not invent missing field-level requirements or authorise implementation.

No live trace file, host flags, Fountain fire, Chat turn, substrate DB, or runtime process was inspected. No trace flag was enabled and no trace record was generated during this audit.

## 1. Actual integration points

There are two runtime call sites in the inspected source:

1. **Fountain:** `theory_x/stage6_fountain/__init__.py:fountain_loop` calls `generator.generate()`, then calls `InfluenceTracer.record_fountain_fire()` if a thought exists and the tracer is enabled.
2. **Chat:** `gui/server.py:api_chat()` calls `InfluenceTracer.record_chat_turn()` after it has selected/sanitized the final reply and attempted to persist it in `conversations.messages`.

No other call to `record_fountain_fire()` or `record_chat_turn()` was found in the inspected normal runtime path. The unit tests use faithful seam harnesses; they do not invoke the actual Fountain loop or Flask Chat route end-to-end.

## 2. What the records actually contain

### Fountain record

The live call passes only:

- final returned thought;
- mode name;
- readiness score computed immediately before generation;
- last-fire timestamp;
- total-fire count.

The record emits those as output + three input entries (mode, readiness, timing). The module's own `unresolved` field explicitly says belief-level attribution (which stored beliefs the generator retrieved) requires a deeper hook inside `FountainGenerator.generate()`.

The actual call does not pass `extra_inputs`. It does not capture the retrieved belief IDs/content, retrieval manifest, WorldBridge events, focus/workspace winner, current drive, selected mode prompt, Gate decision, crystallizer candidate, or SQLite writer delta.

### Chat record

The live call passes only:

- incoming user prompt;
- final reply text;
- register name;
- session ID;
- `voice_ok`;
- successful tool name (or None).

The record's own `unresolved` field says faculty-block attribution (which of the approximately 13 assembled blocks shaped the reply) requires a deeper hook in `_assemble_chat_blocks()`.

The actual call does not pass `extra_inputs`. It does not capture Membrane route, retrieved belief IDs/content, later context augmentations, exact faculty-block set/order/budget, tool-result content, VoiceEngine hit/miss candidate, voice mode, model request identity/parameters, CoherenceGate decision, or Writer delta.

The `tool_used` value means a tool returned success and its name is stored. It does not prove the tool result was consumed by the final reply; the separate Chat route audit records VoiceEngine-hit and early-gap paths where execution and prompt consumption can diverge.

## 3. Trace identity and causal lineage

The schema contains `cycle_id`, but no `trace_id` or `parent_ids` fields.

- Fountain defaults to `fire:<total_fires>`. This identifies a process-local fire counter, not a parent/child chain through candidate generation, selection, Gate, write and output. The record has no explicit boot/process identifier.
- Chat defaults to `chat:<session_id>`. Every turn in the same session receives the same cycle ID; it is not a unique per-turn identifier.
- No shared identifier links a Fountain fire to a later belief/crystallization row, a Chat turn to a tool invocation or VoiceEngine candidate, or either output to a Writer delta.
- The record stores a flat list of observable inputs, not a directed parent-child graph.

The implementation is therefore an output-seam side-channel capture with explicit unknowns, not an end-to-end causal trace through the requested intermediate stages.

## 4. Evidence-level integrity

The tracer maps directly observed inputs to L3 in fixture context and L4 when `NEX5_INFLUENCE_TRACE_CONTEXT=runtime`. The module documentation says L4 is asserted only when the live process declares runtime context and requires founder authorisation.

The implementation does not independently authenticate that the process is the live NEX host. `_env_context()` trusts the environment string `runtime`; the constructor also accepts `context="runtime"`. The unit test `test_runtime_context_is_L4_fixture_is_L3` deliberately creates an ordinary test tracer with `context="runtime"` and asserts that it emits L4.

Thus L4 is a caller-declared label, not independently verified runtime evidence. The checked-in fixture uses `capture_context="fixture"` and L3, and is not itself a live trace. No L4 live record was inspected.

This does not make the fixture invalid; it means the current L4 label needs an explicit provenance/authorization contract before it can be treated as proof of live-host observation.

## 5. Side-channel privacy and retention

The overlay is default-OFF and writes to a dedicated JSONL path, not a substrate database. When enabled:

- `record_chat_turn()` stores a digest and a raw preview (up to 160 characters) of the user's prompt and final reply.
- `record_fountain_fire()` stores a digest and raw preview of the generated thought.
- The default sink is `<repo>/logs/influence_trace.jsonl`; an environment variable can redirect it.
- The module appends records and creates the parent directory. No rotation, retention cap, redaction policy, encryption or access-control mechanism is implemented in this module.

The digest does not remove the raw preview. Enabling the overlay can therefore persist conversation/output snippets in a file outside the substrate DBs. No live file or permissions were inspected. The default-off contract is intact in source, but an activation decision needs to account for preview sensitivity and file lifecycle.

## 6. Tests and fixture

`tests/test_influence_record.py` covers:

- default-off no-op and no file;
- faithful Fountain/Chat seam harnesses with identical output and simulated DB writes off/on;
- record shape, digest and preview fields;
- append-only JSONL;
- side-channel sink path outside substrate DBs;
- fail-safe sink errors;
- fixture L3 versus explicitly declared runtime L4;
- singleton reset and evidence-class mapping.

These are useful module/seam tests, but they do not prove end-to-end runtime lineage. The fixture `docs/phase0_influence_capture_fixture.jsonl` contains two hand-authored/example records (one Fountain, one Chat) with explicit unresolved fields. It is not a record captured from a live NEX process.

The faithful seam tests compare small harnesses; they do not test actual generator retrieval, Chat block assembly, Gate outcomes, Writer deltas or process-level parent/child linkage.

## 7. Reconciliation against the recorded roadmap extract

| Recorded requirement from current reconciliation | Actual source state |
|---|---|
| Default-off overlay | Implemented under `NEX5_INFLUENCE_TRACE`; different name from recorded `NEX5_TRACE_OVERLAY` |
| `trace_id` | Not present |
| `parent_ids` | Not present |
| Input Arrival | Chat prompt only; no full sense/input event identity |
| Candidate Generation | Not captured |
| Salience / Workspace Selection | Not captured |
| Gate | Not captured |
| SQLite Writer Delta | Not captured |
| Output | Final Fountain thought / Chat reply digest + preview |
| Fixture evidence | Present as static JSONL examples, L3/fixture |
| Live L4 evidence | No live record inspected; source trusts a caller-declared environment string |

The exact Frozen V2.1 and approval record are still needed to determine whether this is an intentionally reduced Phase 0 seam or an incomplete implementation of the approved requirement. Do not replace or expand the implementation based on an absent spec.

## 8. Phase 0 disposition

### Confirmed source facts

- The overlay is default-OFF and side-channel-only in source; actual call sites are Fountain after generation and Chat after reply persistence.
- The record is limited to a small set of scalar/output inputs and explicitly marks belief/faculty attribution unresolved.
- There are no `trace_id` or `parent_ids`; Chat cycle ID is session-scoped rather than turn-unique.
- No Gate outcome or SQLite writer delta is captured.
- L4 is controlled by a caller-declared context string and can be produced in a unit test; it is not authenticated by the module.
- When enabled, the trace file includes raw text previews; no retention/redaction/access policy is implemented in this module.
- Tests exercise the module and faithful seams, not full actual runtime causality. The checked-in fixture is not live evidence.

### Unverified / authority-dependent

- Whether the recorded roadmap extract is still authoritative or superseded by Frozen V2.1.
- Whether M0.5 requires full stage-by-stage causal lineage or only the two output seams as a preliminary capture.
- Required identity scope: per fire, per Chat turn, per session, per process, or parent/child graph.
- Which exact candidate, retrieval, workspace, Gate and writer fields are required and which can be captured without adding reads.
- Whether L4 should be authenticated by host/process evidence rather than environment declaration.
- Required trace file privacy, access, retention and redaction policy.
- Whether the default-off flag is enabled anywhere; no host state was inspected.

### Boundary

No trace field, flag, call site, runtime context, sink, privacy policy or capture behavior was changed. Do not add deeper hooks, new reads, trace IDs, host assertions or runtime activation until the exact governing requirement and Gate 0 founder decision are recovered or explicitly re-established.
