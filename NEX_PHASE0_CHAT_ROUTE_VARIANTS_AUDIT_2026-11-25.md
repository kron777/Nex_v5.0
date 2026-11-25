# NEX Phase 0 — Chat Route Variants and VoiceEngine Audit (25 November 2026)

## Scope and evidence boundary

Static-source audit against the active host source branch `claude/nex-continuity-wire` at `de93134f34adac07a3a41c2a05b33720510a2bfc`. This closes the route-specific portion of Producer/Consumer Trace §8 item 3, building on:

- `NEX_PHASE0_CHAT_COMPOSITION_ROUTE_TRACE_2026-11-25.md`
- `NEX_PHASE0_CHAT_BELIEF_CONTEXT_TRACE_2026-11-25.md`
- `NEX_PHASE0_MEMBRANE_PROVENANCE_COVERAGE_AUDIT_2026-11-25.md`
- `NEX_PHASE0_CHAT_BELIEF_COUNT_FORMATTER_AUDIT_2026-11-25.md)

No live host mode, database rows, flags, service state, or historical prompt was inspected. No runtime behaviour, code, tests, flags, schema, or deployment state was changed. Source facts below do not establish model attention or causal influence.

## 1. Chat route order

The current `POST /api/chat` path executes in this broad order:

1. Validate prompt; resolve register; persist the incoming user message.
2. Route through Membrane when Membrane and World Model exist; otherwise use the direct World Model fallback.
3. Capture `_retrieved_belief_text` immediately after the initial route/fallback result.
4. Apply route-dependent and optional context augmentations: BehaviouralSelfModel, SelfModel observability, Harmonizer tension, disturbance, ProblemMemory, Metacognition, NovelAssociation, SelfNarrative, AffectState, DriveEmergence, SelfMindView, optional SocialPresence, and successful tool output.
5. Finalise register; update FocalSet/WorkingMemory measurement state.
6. Calculate `belief_count` by counting literal `- [Tier` markers in the composite `belief_text`.
7. Apply the thin-context gap gate.
8. If the route continues, optionally query VoiceEngine; then either return a substrate candidate or assemble the 13 faculty blocks and compose through VoiceClient.
9. Sanitize and persist the NEX response in `conversations.messages`.

The initial Membrane retrieval and the VoiceEngine TimeFetch retrieval are separate searches. Tool selection/execution occurs before the thin-context gate and before VoiceEngine. A successful tool result is appended to `belief_text` before the marker count.

## 2. Self-model inclusion by route

### INSIDE

- `QueryRouter._inside_route()` snapshots SelfModel, formats `format_self_state()`, and appends that text to the returned belief block. It also retrieves up to five INSIDE-filtered beliefs.
- The SelfModel formatter adds up to three separate inside-belief rows as plain standing-point lines. These are additional belief-derived text, not necessarily the same rows as the router's later INSIDE retrieval.
- The GUI then ticks BehaviouralSelfModel and appends its formatted behavioural metrics. This is INSIDE-only.
- The GUI logs SelfModel injection metadata, but that log is not itself the prompt text.

### OUTSIDE

- QueryRouter retrieves up to eight ordinary relevant beliefs using active Dynamic branches as hints.
- The INSIDE-only SelfModel and BehaviouralSelfModel text additions are not applied through the explicit route guards.

### Other self-state blocks

- `run.py` constructs and starts SelfMindView, then passes it into AppState. The Chat handler appends its current summary to `belief_text` when present.
- The Chat handler has a SocialPresence injection branch, but the inspected normal `run.py` startup explicitly sets `_social_presence = None` and passes that value into AppState. Thus this branch exists but is not populated by the inspected normal startup path.
- Metacognition receives references to SelfMindView and SocialPresence, but that is distinct from the direct SocialPresence Chat injection.

The distinction is important: a formatter or injection branch existing in `gui/server.py` does not prove the normal startup path has supplied the component.

## 3. Thin-context gate precedes VoiceEngine

The Chat gap gate is evaluated before the VoiceEngine branch. Unless the turn is a probe, a social query, or uses an allowed-thin register, the handler returns the configured gap refusal when the marker count is below `CHAT_GAP_MIN_BELIEFS`.

Consequences visible in source:

- VoiceEngine is not consulted when the earlier Chat gap gate returns.
- A VoiceEngine candidate that might have matched through TimeFetch cannot rescue a turn rejected by the earlier marker-count gate.
- Probe calls bypass this gap gate and proceed to later routing.
- The marker count includes successful tool-result text because that text was appended before counting. It is not a structured count of belief rows.

## 4. VoiceEngine mode and route variants

### Mode default and control

- `AppState.voice_mode` defaults to `"use_substrate"` in `gui/server.py`.
- The inspected `run.py` constructs VoiceEngine and creates AppState without overriding `voice_mode`; therefore the source-default mode is `use_substrate`.
- `POST /api/voice_mode` can set the in-memory mode to `use_llm` or `use_substrate`. The handler only changes `state.voice_mode`; no persistence is performed in that route.
- The host-effective mode remains UNKNOWN because no live status endpoint or process state was inspected.

### VoiceEngine hit: non-admin or operator composition off

When not a probe, not an instruction query, VoiceEngine exists, and mode is `use_substrate`, the handler calls `VoiceEngine.query_reply()`.

If a candidate clears the threshold and operator composition is not active, the handler sets the response text directly to the stored candidate content and marks `voice_ok=True`. It does not build the normal 13 faculty blocks or call VoiceClient for that turn. The initial Membrane block and earlier augmentations may already have been computed, but they are not consumed as text by that reply.

This is the RAG-first-verbatim route.

### VoiceEngine hit: admin HYBRID

When operator composition is active for an admin session, a VoiceEngine hit is not returned verbatim. Its content is prepended to `belief_text` as grounding, and the normal LLM composition path proceeds with the 13 faculty blocks and user prompt.

### VoiceEngine miss

The code leaves `text` unset when VoiceEngine returns no candidate or a score below threshold. The normal LLM composition path then runs.

The comments in the VoiceEngine section say that a substrate miss should suppress LLM fallback and return a substrate deflection. The inspected executable control flow does not implement that claim: a miss leaves `text is None`, and the later branch calls `state.voice.speak()`. This comment/control-flow discrepancy is already noted in the broader trace and is confirmed here.

### use_llm, probes and instruction queries

- In `use_llm` mode, the VoiceEngine branch is skipped and normal LLM composition is used.
- `is_probe=True` bypasses both the thin-context gap refusal and VoiceEngine, but it does not bypass the initial Membrane route, ordinary context augmentations, or tool selection. It is therefore not a context-free or substrate-free probe.
- Instruction queries bypass VoiceEngine and continue through the normal LLM composition route, subject to the earlier gap-gate rules.

## 5. VoiceEngine candidate search has no active-belief status exclusion

VoiceEngine uses `TimeFetch.run()`, which combines four candidate sources:

1. Beliefs: `confidence > 0.4`, `LENGTH(content) > 30`, and keyword LIKE match.
2. Novel associations: joins the two belief rows in each association and matches keywords against either content.
3. Arcs: matches non-`return_transformation` arc summaries with a quality grade.
4. Open problems: calls ProblemMemory matching.

The belief query does not filter `tier`, `paused` or `locked`. The novel-association join does not filter the status of either linked belief. VoiceEngine subsequently enriches direct belief candidates with tier and reinforcement count, but that enrichment query is by ID and does not exclude retired or paused rows.

Scoring is not a status guard:

- Tiers 3–6 receive tier score 1.0.
- Every other tier, including Tier 8, receives tier score 0.5.
- The tier axis contributes a lower score for Tier 8; it does not reject the candidate.
- The default minimum reply score is 0.6.

Accordingly, a retired or paused belief is not structurally excluded from VoiceEngine's candidate pool. If its other scoring axes are sufficiently high, it may clear the threshold and be returned verbatim. This is a source-level exposure possibility, not evidence that any retired/paused row has been returned on the live host.

VoiceEngine's direct reply path does not call CoherenceGate. It is read-only with respect to beliefs, and the returned text is persisted as a conversation message rather than a new belief. Whether the universal Gate requirement is intended to cover user-facing verbatim retrieval replies is an authority question; this audit does not decide it.

## 6. Tool execution and attribution boundaries

Tool selection/execution happens before the gap gate and VoiceEngine:

- A successful tool result is formatted and appended to `belief_text`.
- The string-marker gap count can include Tier-shaped text from the tool result.
- On a normal LLM miss, probe, or admin HYBRID route, the successful tool injection is part of the composed prompt.
- On a non-admin VoiceEngine hit, the tool result may already have executed and been appended, but the handler returns the VoiceEngine candidate without composing from `belief_text`. The successful tool name is nevertheless stored in the NEX message's `tool_used` field and passed to the optional InfluenceRecord trace. That metadata therefore indicates tool execution/success, not necessarily that the tool result was consumed by the reply.
- If the thin-context gate returns early after a tool succeeded, the refusal path stores/returns `tool_used=None`. The tool may have executed, but the refusal record does not identify it.
- If VoiceClient raises and the static fallback is used, the final message may still record the successful tool name even though the fallback sentence did not consume the tool result.

These are measurement/attribution boundaries. No tool execution was performed during this audit.

## 7. LLM request failure and retry paths

When the normal LLM route is used, `VoiceClient.speak()` builds the system prompt and sends the assembled `voice_prompt` to the configured OpenAI-compatible endpoint. The default request uses a 120-second HTTP timeout and raises on an HTTP error.

If `state.voice.speak()` raises, the Chat handler catches the exception, returns the static text:

> I can't reach my voice right now. Still running, still watching, just can't compose a reply.

It sets `voice_ok=False` and persists the text as a NEX conversation message. This is not a `voice_fallback` belief insertion, not a SpeechQueue enqueue, and not a CoherenceGate path.

On successful LLM composition:

- Admin-scoped anti-repeat can issue one additional VoiceClient request using the same assembled prompt plus a bounded variation instruction.
- Admin-scoped provenance can issue one additional request using the same assembled prompt plus a provenance cue, retaining it only if the mirror score improves.
- These retries do not repeat initial Membrane retrieval, tools, or VoiceEngine retrieval. They reuse the already assembled prompt.
- The provenance snapshot is created only on the LLM composition path. It is based on `_retrieved_belief_text`, captured immediately after initial route/fallback retrieval and before subsequent augmentations. It therefore excludes later tool injection and other appended context, and it is absent on a direct VoiceEngine hit.

The final sanitized reply is inserted into `conversations.messages`. The inspected Chat path does not insert the user-facing response into `beliefs` or call CoherenceGate on that reply.

## 8. Test coverage observations

- `tests/test_voice_engine.py` covers empty pool, below-threshold miss, above-threshold hit, score axes, trigger logging and state counters. Its tier test confirms T4 scores higher than T8; it does not establish that T8 is excluded.
- `tests/test_throw_net_time_fetch.py` covers keyword matching, confidence and content-length filters, novel-association matching, arc filtering, problem routing and deduplication. The inspected tests do not assert Tier 8, paused or locked exclusions.
- The inspected VoiceEngine/TimeFetch tests do not exercise the GUI-level interaction between gap-gate ordering, VoiceEngine mode, admin HYBRID, tool execution and `tool_used` persistence.
- The source has a direct mode-setting endpoint, but the inspected tests do not establish its persistence across restart; the endpoint itself only changes AppState memory.

These are test-coverage observations, not a recommendation to change tests before Gate 0.

## 9. Phase 0 disposition

### Confirmed source facts

- Normal AppState source default is `use_substrate`; `run.py` does not override it, and an API endpoint can change it in memory.
- The Chat gap gate precedes VoiceEngine.
- VoiceEngine is a direct candidate-return path on hit and a normal LLM path on miss.
- TimeFetch does not exclude Tier 8/paused/locked beliefs or novel associations on its inspected candidate queries; tier 8 is down-scored, not rejected.
- Admin HYBRID converts a VoiceEngine hit into LLM grounding; non-admin/flag-off returns the candidate verbatim.
- Tool execution precedes VoiceEngine, so successful execution and actual prompt consumption can diverge.
- VoiceClient failure returns a static Chat message, persisted in conversations, not a belief or SpeechQueue item.
- SelfModel and BehaviouralSelfModel text are INSIDE-route-specific; SelfMindView is constructed in normal startup; SocialPresence is set to None in normal startup.

### Unverified / authority-dependent

- Host-effective voice mode and operator-composition flag.
- Whether any VoiceEngine candidate was a Tier 8 or paused belief in live operation.
- Whether the universal CoherenceGate contract governs direct user-facing retrieval replies.
- Whether tool-used metadata is intended to mean execution or actual reply consumption.
- Whether the VoiceEngine miss-to-LLM fallback is intended or a stale implementation.
- Whether the normal startup host has used the alternate mode endpoint since boot.

### Boundary

No code or test change is proposed. Do not add status filters, change route order, suppress LLM fallback, alter tool attribution, or gate user-facing responses until the governing Frozen V2.1 authority and Gate 0 decision are recovered or explicitly re-established.
