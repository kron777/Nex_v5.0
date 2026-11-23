# NEX Chat Pathway Audit — Phase 0 Source Evidence

**Status:** Working source audit; not a Gate 0 submission  
**Inspection date:** 2026-11-23  
**Audited implementation revision:** `3d5df48e6539818097b58b6e936059fae946ceca` (PR #65 integrated Phase 0 branch)  
**Scope:** `gui/server.py::api_chat`, its directly called Chat routing/selection mechanisms, the VoiceEngine retrieval path, and the default boot wiring inspected at the same source revision.  
**Method:** Static source inspection through GitHub file contents. No local checkout, deployed host, live database, process, or runtime flags were inspected.

> This document is a revision-bound source map, not a claim that the inspected branch is deployed or that any environment flag is active. Optional state objects and environment flags are source-level conditions only; their live values remain UNKNOWN.

## 1. Executive findings

The Chat handler is not one linear retrieval-to-LLM pathway. It contains two distinct reply-producing routes after a shared input/session/routing stage:

1. **VoiceEngine substrate hit:** when the request is not a probe or instruction query, a VoiceEngine is present, and `voice_mode == "use_substrate"`, a qualifying candidate can be returned verbatim. In the operator-composition case the candidate is instead prepended as grounding and the request continues to model composition.
2. **VoiceClient composition:** when no direct substrate reply has been selected, the handler builds a prompt from retrieved beliefs, multiple optional and always-on faculty/context contributors, and ordered prompt blocks, then calls `state.voice.speak()`. Anti-repeat and provenance may each trigger one additional model call.

The existing trace overlay represents the main route boundaries, but does not yet expose a complete source-to-sink causal graph for Chat. In particular, many context contributors are combined into one digest-only `context_selection` record without individual producer IDs or explicit parent edges. The trace must not be described as complete causal closure.

A source-comment discrepancy was also found: the FocalSet block is labelled “log-only attention tracking”, but it updates per-session Working Memory, and that memory can be injected into the same turn's prompt on a later branch. This is a source-confirmed prompt-influence path, conditional on the relevant objects/register/belief-count conditions. It is not evidence that the path is active on the deployed host.

## 2. Shared entry and routing

### 2.1 Request acceptance and session persistence

- `POST /api/chat` reads JSON, strips `prompt`, and returns HTTP 400 for an empty prompt before opening a trace.
- The trace overlay is optional and starts only when `NEX5_TRACE_OVERLAY=1`; accepted non-empty prompts receive an `input_arrival` record.
- Register selection uses an explicit `register` value when supplied; otherwise the source currently selects Philosophical (falling back to the default register).
- If a conversations Writer exists, the handler creates a session row when necessary and inserts the user message. Writer failures are caught and logged; the request continues. A missing Writer means those message writes are not performed.
- A best-effort `ec_decision` log records the chosen register and whether the caller overrode it.

### 2.2 Membrane / WorldModel retrieval alternatives

- If both `state.membrane` and `state.world_model` exist, the handler calls `membrane.route()` with the prompt, the WorldModel retriever and dynamic state. It takes `belief_text` and a possible `register_hint` from the route result.
- Otherwise, if a WorldModel exists, it calls the retriever directly with active dynamic branch hints and a limit of three. Chat then applies its own token-overlap filter (at least two shared content tokens) and caps the formatted belief block at approximately 800 characters.
- If neither route is available, the initial belief context remains empty.
- The trace's `retrieval` event records the formatted belief block at this point, before the later Chat-specific additions described below. It does not separately identify each underlying belief row or every downstream context producer.

The membrane route and direct-retriever fallback are alternatives, not two sequential retrieval passes.

### 2.3 Internal membrane/retrieval dependencies

The two membrane routes have materially different upstream dependencies:

- **INSIDE:** the router first calls `SelfModel.snapshot()`. The snapshot reads the latest `internal.proprioception`, `internal.temporal`, `internal.interoception`, and `internal.meta_awareness` payloads from `sense_events`; when DynamicState is present it calls `status()` for meta-awareness and again for attention; and it queries up to 30 eligible INSIDE-source beliefs, scores them by confidence × tier weight, then formats the top five (the prompt formatter emits up to three standing-points). Separately, the router calls `BeliefRetriever.retrieve()` with `branch_hints=["systems"]`, `limit=5`, and `side_filter="INSIDE"`. That retriever first reads the eligible belief pool (tier ≤ 6, unpaused, locked or confidence ≥ 0.15, ordered by confidence, limit 20,000), applies the membrane source filter, computes keyword overlap and optional semantic fallback, then attempts spreading activation/typed-role enrichment before returning its top results. The SelfModel snapshot and routed BeliefRetriever result are separate contributions; the snapshot's inside-belief selection is not the same query-ranked result.
- **OUTSIDE:** the router optionally reads DynamicState status and selects branch IDs whose `focus_num > 0.1`, then calls BeliefRetriever with those hints and `limit=8`, without an explicit side filter. The Chat handler subsequently applies its own two-token overlap filter and prompt-length cap. When DynamicState is absent or fails, the route proceeds with an empty active-branch hint list.

These source paths show that the trace's single initial `retrieval` boundary collapses several distinct reads and transforms. The current trace does not expose the selected belief IDs, sense-event row IDs, dynamic branch snapshot, activation seeds/results, or the distinction between SelfModel's top-five standing-points and router's query-ranked INSIDE beliefs. The above is source behaviour, not proof those optional dependencies are present on the deployed host.


## 3. Context contributors after initial retrieval

The following source paths can add material or affect the prompt after the initial retrieval record. Their presence in AppState and their internal conditions are not proof that they produce content on every turn.

| Contributor / mechanism | Source behaviour in the audited handler | Causal-trace status / limitation |
|---|---|---|
| BehaviouralSelfModel | On an INSIDE membrane route, ticks and formats behavioural metrics; appends non-empty text to `belief_text`. | No distinct trace record or parent edge. |
| SelfModel snapshot | Reads the route's self-model snapshot and logs its composition; source comment says its content was already injected by the router's inside route. | Handler block is observability; actual injection is upstream in the membrane route and is not separately identified in the current Chat trace. |
| Harmonizer | On an INSIDE route with WorldModel, ticks; if active paradoxes exist, appends formatted tension text. | No distinct trace record or parent edge. |
| Disturbance | Reads WorldModel disturbance; under register conditions appends a tension note and decrements its remaining-cycle value. | This is a state-changing read/consume path as well as prompt assembly; no distinct trace edge. |
| ProblemMemory | Finds matching open problems and appends the first match's formatted text. | No distinct trace record. |
| GoalManager | Reads active goal and logs it; the current handler explicitly does not append goal text to Chat prompt. | Read/log only in this handler path; do not classify as prompt influence here. |
| Metacognition | Ticks, formats a self-pattern summary and appends it when non-empty. | No distinct trace record. |
| NovelAssociation | Formats the latest unannotated association and appends it when non-empty; comments describe marking it annotated. | No distinct trace record or explicit association ID edge. |
| SelfNarrative | Formats topic-matched autobiographical context and appends it when non-empty. | No distinct trace record. |
| AffectState | Reads/formats current affect and appends it when non-empty. | No distinct trace record. |
| DriveEmergence | Reads/formats current drive topic and appends it when non-empty. | No distinct trace record. |
| SelfMindView | Reads current cognitive-state summary and appends it when non-empty. | No distinct trace record. |
| SocialPresence | Reads current social-posture summary and appends it when non-empty. | No distinct trace record. |
| ToolCaller / ToolRegistry | Heuristically chooses a tool, builds kwargs, executes it, and appends a successful result's prompt block. The source exposes three tools: allowlisted-domain `web_fetch`, subprocess-backed `python_exec`, and NEX `beliefs_query`. The caller's precedence is price/crypto → math → explicit belief query → current/latest → factual query with no beliefs. | No explicit tool-selection, invocation, result, or prompt-injection trace edge. Successful tool name is later stored in the assistant message row. |
| FocalSet / WorkingMemory | Retrieves up to ten raw beliefs, updates FocalSet, adds focal contents to per-session Working Memory, then reads/logs that memory. | **Not merely log-only:** Working Memory is read later in the same handler and may be injected into the prompt (see §4). No trace edge connects the selected belief IDs to that injection. |
| Spectrum standing-points | Reads random `source='spectrum'` beliefs for a foundation block; for Philosophical/thin context, reads up to four more and appends Tier 1 markers. | No trace record for row IDs or random selection. |
| Cross-turn WorkingMemory injection | For Conversational register with enough counted Tier markers, appends up to five active Working Memory items. | No trace record connecting prior-turn memory entries or FocalSet additions to the composed prompt. |
| Faculty prompt blocks | May include operator model/anchor, compassion, compass, equanimity, apramada, virya, sraddha, prasrabdhi, affect-carry, recent conversation, spectrum, and tag-retrieval blocks. | Collapsed into one `context_selection` digest; individual block provenance and flag decisions are not represented as separate edges. |

Errors in many optional contributors are caught and treated as absence of that contribution. The resulting prompt can therefore vary with object availability, internal state, flags, and error paths.

## 4. FocalSet / WorkingMemory discrepancy

The source labels the FocalSet section “log-only attention tracking” and the nested Working Memory section “log-only”. The code does more than log:

1. It retrieves up to ten raw beliefs for the current prompt.
2. It advances the FocalSet tick and calls `_focal_set.update()`.
3. It obtains focal belief IDs.
4. For each focal ID, it adds the corresponding belief content to the session Working Memory object via `_wm.add()`.
5. Later in the same request, the Working Memory injection branch reads active items and, when the session exists, the register is Conversational, and the previously computed `belief_count` meets `CHAT_GAP_MIN_BELIEFS`, appends up to five items to `belief_text`.

Therefore, under those conditions, the FocalSet → WorkingMemory path can influence the current Chat prompt, not merely produce logs. The code also allows the accumulated Working Memory to affect later turns within the same server process: `_working_memory_by_session` is a module-level in-memory dictionary keyed by session ID, and the inspected path does not persist these WorkingMemory items to SQLite. A process restart therefore does not have a durable WorkingMemory restore path established by this code. This is a documentation/comment accuracy issue and an omitted causal edge in the current trace, not a finding that the mechanism is defective or currently active in deployment.

A related ordering fact: `belief_count` is computed before the spectrum and Working Memory additions. The gap decision therefore uses the earlier assembled `belief_text`, not a recount of the final prompt after those later additions.

## 5. Gap gate and response routing

After the first group of context contributors and tool execution:

- The final register may be overridden by the membrane route if the caller did not explicitly choose one.
- The handler computes `belief_count` by counting the `- [Tier` marker in the current `belief_text`.
- Probe requests, social queries, and configured thin-register cases are exempt from the ordinary thin-belief deflection.
- Otherwise, when the count is below `CHAT_GAP_MIN_BELIEFS`, the handler records a gap-gate deflection, attempts to persist the refusal message, records a trigger-detector gap deflection if available, closes the trace, and returns without entering VoiceEngine or VoiceClient composition.
- If the gate passes, later spectrum/WorkingMemory material can still be added before the response route is selected.

The gap refusal is a distinct response sink. It is not a model-generated answer.

### 5.1 VoiceEngine substrate route

The route is eligible only when all are true:

- not a probe;
- not an instruction query according to `_is_instruction_query()`;
- `state.voice_engine` exists;
- `state.voice_mode == "use_substrate"`.

The normal `run.py` source constructs VoiceEngine and supplies it to AppState, but that source fact does not establish the deployed runtime's mode or successful construction.

VoiceEngine's `query_reply()` calls TimeFetch, which sweeps four sources:

1. Beliefs: keyword LIKE retrieval with confidence and content-length filters.
2. Novel associations: matched pairs joined back to beliefs.
3. Arcs: theme-summary matches excluding return-transformation arcs.
4. Open problems: ProblemMemory matches.

It deduplicates by content, preserving source priority belief → novel association → arc → problem, and caps the pool at 40. Belief candidates are enriched with tier and reinforce count; when enabled and the conversations Reader is available, belief candidates may also be enriched with Genius scores through belief → Fountain crystallization → genius-tag lookups. Candidates are scored using semantic similarity, confidence, tier, reinforcement count, drive alignment, and Genius score. The best candidate is returned only when it meets `min_score` (default 0.6 in the class source); otherwise the route misses.

On a hit:
- ordinary non-probe/non-instruction requests use the candidate content directly as the reply and skip VoiceClient composition;
- the admin/operator-composition case retains the candidate as grounding and continues to the composition route.

On a miss or VoiceEngine exception, the handler continues to the VoiceClient route. VoiceEngine records a query-trigger row; that write is not itself proof that the candidate was used as the reply. The handler's `substrate_voice` trace event records hit/miss and a source-scoped candidate reference when an origin ID exists, but does not expose the underlying TimeFetch read sequence or candidate-pool construction as separate causal events.

### 5.2 VoiceClient composition route

When no direct substrate reply is selected:

- Successful operator composition may prepend the VoiceEngine hit as grounding.
- Tag retrieval, operator model/anchor, recent conversation, compassion, compass, equanimity, apramada, virya, sraddha, prasrabdhi, and affect-carry blocks are assembled in a defined prompt order.
- `_assemble_chat_blocks()` concatenates all blocks when `NEX5_CHAT_WORKSPACE` is not enabled. When enabled, it performs budgeted salience selection, with compassion and compass exempt from eviction. Optional self-presence salience carry is a further conditional branch. The ablation flag can omit non-exempt block kinds.
- The final prompt combines those blocks with the assembled `belief_text` and user prompt (or uses the block string plus prompt when no belief text exists).
- The handler calls `state.voice.speak()`.
- If Chat Memory is active and the reply matches recent openings, it may issue one anti-repeat retry. A retry replaces the first answer only if it passes the repeat check.
- If provenance is active and the reply triggers a cue, it may issue one provenance retry. The retry replaces the first answer only if the measured mirror score is lower.
- Question-parrot stripping and final reply sanitization occur before persistence and HTTP response.
- A successful assistant-message insert records the selected tool name when the tool call succeeded. Persistence failure is caught; the response is still returned.

The trace records a composed prompt digest, model input/output markers, retry decisions and final sanitization/persistence. It does not individually link all upstream faculty, tool results, FocalSet/WorkingMemory items, random spectrum rows, and other substrate reads into the selected model input.

## 6. Source-to-sink map and evidence boundary

| Route | Source → decision/transform → sink | What source establishes | What remains UNKNOWN |
|---|---|---|---|
| Empty prompt | Request JSON → validation → HTTP 400 | Rejected before trace/session/message path. | Host request mix/frequency. |
| Gap refusal | Input/retrieval/context → Tier-marker count gate → refusal message/HTTP JSON | Conditional early response path; no VoiceEngine/VoiceClient call after deflection. | Live flag/object state and observed frequency. |
| Substrate hit | User query → TimeFetch candidates → VoiceEngine scoring/threshold → candidate content → sanitize/store/HTTP | Source-defined direct-reply path and candidate-ranking mechanism. | Live mode, candidate hit rate, actual downstream use on host, outcome quality. |
| Substrate miss / ineligible | Query → no eligible candidate or miss → prompt composition → VoiceClient → sanitize/store/HTTP | Source-defined fallback to composition. | Host path frequency and backend/model behaviour. |
| Operator hybrid | VoiceEngine hit + admin/flag → grounding prepended → VoiceClient composition | Source-defined hybrid route. | Live admin/flag conditions and use frequency. |
| Model retries | First VoiceClient answer → repeat/provenance checks → at most one retry per guard → selected reply | Conditional bounded retry paths and acceptance conditions. | Runtime incidence and effects. |
| Tool contribution | Prompt → heuristic selection → registry execution → successful result injected → assistant row records tool name | Source-defined tool path and persistence of successful tool name. | Which tools are registered/live, execution incidence, exact tool side effects. |

No route in this table proves that context was attended to, relied upon, or decision-changing. A model request containing context is evidence of context presence, not model reliance.

## 7. Trace coverage assessment against PR #65

The tested overlay has useful, explicit route markers: input arrival, user-message Writer delta, initial retrieval, gap gate, VoiceEngine query/hit/miss, composed prompt input, model output, repeat/provenance retry markers, sanitization, assistant-message Writer delta, and trace end.

The following causal edges remain unrepresented or only coarsely represented:

- Individual retrieved belief IDs and the retrieval SQL/result set.
- Membrane route outcome and its internal self-model/context inputs.
- Each subsequent faculty/context append operation.
- Disturbance state read/decrement and ProblemMemory matching result.
- FocalSet selected IDs → WorkingMemory writes → current/later prompt injection.
- Random spectrum rows and the exact selection outcome.
- Tool selection, invocation, result, and prompt insertion.
- TimeFetch's four candidate sources, candidate deduplication, tier/reinforcement enrichment, Genius cross-database enrichment, score components, and selected candidate's full provenance.
- Chat Workspace block-level salience selection, exclusions, budget and selected/dropped block identities.
- Provenance snapshot inputs and the causal basis for a provenance retry.
- Direct SQL readers and stateful objects whose reads are not routed through the NEX Reader observer.

The current `context_selection` record is a useful boundary marker for the composed prompt, but its parent list (initial retrieval, gap gate, and optional substrate voice) is not a complete list of the mechanisms that contributed to its payload. Do not infer omitted parentage from source order.

### 7.1.1 Conditional ToolCaller → Python execution defect (DRAFT-002)

A source-level hand-off mismatch is visible across the Chat caller and tool registry:

1. `ToolCaller.should_use_tool()` selects `python_exec` for phrases such as `calculate 15 * 37`.
2. `ToolCaller.build_tool_kwargs()` returns `{"query": query, "code": ""}` for `python_exec`; it does not translate the natural-language calculation into Python source.
3. `ToolRegistry._python_exec()` replaces an empty code argument with the original query and passes it to `python3 -c`.
4. A natural-language query such as `calculate 15 * 37` is invalid Python syntax. The tool returns `success=False`; `api_chat` appends tool output only when `tool_result.success` is true.

The existing `tests/test_tools.py` verifies that a calculation phrase selects `python_exec` and separately verifies that direct Python code such as `print(2 + 2)` executes. Its kwargs test only checks that the query key exists. It does not test the integrated natural-language query → kwargs → registry execution contract.

**Classification:** conditional source-confirmed integration defect DRAFT-002. Live incidence, severity and user impact are UNKNOWN. No runtime fix is included or implied; remediation remains outside this Phase 0 audit and subject to the governing authority/approval process.

### 7.1 Tool path detail

The Chat handler passes an empty belief list to `ToolCaller.should_use_tool(prompt, [])`, so its “no beliefs retrieved” factual-query fallback is eligible whenever the query matches the corresponding phrase pattern; it is not passed the actual retrieved belief set. The precedence is price/crypto → math → explicit belief query → current/latest → factual phrasing with the supplied empty list. `build_tool_kwargs()` passes the query to the selected tool (and an empty code string for `python_exec`, which the registry replaces with the query). `ToolRegistry.execute()` dispatches to the selected implementation and returns a `ToolResult`; the handler injects only successful results. `web_fetch` uses a domain allowlist and a bounded response read; `python_exec` runs a subprocess with a five-second timeout and import-name blocklist; `beliefs_query` performs a separate BeliefRetriever query. These source details do not establish actual tool registration/use in a live environment.

Trace event names such as `model_input` and `model_output` are observer labels; they do not prove that the external model used a particular context item or that a reply was correct.

## 8. Tests and what they establish

PR #65 includes a paired Chat trace OFF/ON route fixture using the Flask route and isolated SQLite substrate. The test constructs a deliberately minimal `AppState` with Writers/Readers and a deterministic `VoiceClient`; it clears all `NEX5_*` environment flags except the trace controls. It does not supply a WorldModel, Membrane, VoiceEngine, ToolCaller/ToolRegistry, FocalSet, or the other optional faculties. The deterministic test prompt follows the ordinary model-composition route. It compares model request bytes, returned behaviour, message/session rows, complete non-internal table contents, Reader SELECT/WITH sequences, and the trace's explicit parent links. Its measured elapsed time is one paired diagnostic sample only.

Separate `tests/test_focal_set.py` and `tests/test_working_memory.py` exercise those classes in isolation. They do not establish the GUI integration path from FocalSet selection through session Working Memory into the assembled Chat prompt. No integrated route test for that conditional influence path was identified in this bounded test inspection.

The latest integrated PR #65 CI run `45250499152` passed full pytest and the mind-map sourcing check on head `3d5df48e6539818097b58b6e936059fae946ceca`.

That result does not establish:
- membrane/WorldModel retrieval, direct VoiceEngine hits, operator hybrid, tool use, faculty blocks, FocalSet/WorkingMemory prompt injection, spectrum selection, or retry branches are exercised by the paired trace fixture;
- every Chat branch or flag combination is covered;
- arbitrary direct SQLite access is observed;
- runtime flag values or host wiring;
- statistical latency neutrality;
- model reliance or decision-changing effect;
- deployed-host behaviour.

No live trace was captured, and no production prompt, private conversation, or runtime database content is included in this audit.

## 8.1 Membrane classifier boundary finding (DRAFT-003)

The inspected `MembraneClassifier.classify_query()` lowercases the full query and tests each configured self-inquiry keyword using substring membership. The keyword `"you"` therefore matches inside the product name `YouTube`. For example, `how do I use YouTube` deterministically classifies as INSIDE, even though it is a world/product query. The Chat handler then follows the INSIDE route: self-model snapshot plus INSIDE-filtered belief retrieval, with a Philosophical register hint. This is a source-confirmed conditional routing defect, not evidence of live host incidence.

The current membrane tests cover examples such as `how are you feeling?` and `what do you believe?` as INSIDE, and BTC/news/research queries as OUTSIDE, but contain no token-boundary/product-name case. No runtime fix is included. Classification and routing source hashes are recorded in the source manifest.

## 9. Remaining Phase 0 work

1. Complete source-level edge tracing for the unrepresented contributors and branches above, including membrane classifier boundaries, FocalSet/WorkingMemory, tool path, and VoiceEngine candidate ranking.
2. Audit the membrane route and its internal producer dependencies, and the full VoiceEngine candidate-selection path, with IDs and exact read/write boundaries.
3. Audit the Chat handler's alternate error, retry, admin and feature-flag branches against the Frozen V2.1 specification when the exact authoritative copy is available.
4. Obtain the exact Frozen V2.1 specification and Founder Sign-Off record; no acceptance criterion should be inferred from this source audit.
5. Obtain approved host-side evidence before claiming runtime activation or capturing a production trace.

## 10. Source manifest

All hashes below identify the inspected PR #65 integrated branch files, not the deployed host:

| Source | Blob SHA | Audit relevance |
|---|---|---|
| `gui/server.py` | `d67df10f4449004c255e38b11b4a1888a4e4934c` | Chat route, prompt assembly, retry and response handling |
| `theory_x/stage_throw_net/voice_engine.py` | `ea52711e13b7ea71531a3bec9a394d18e2574b40` | Candidate retrieval enrichment, scoring and substrate reply selection |
| `theory_x/stage_throw_net/time_fetch.py` | `7a97a76a48eb54d621d1a436fc5c64d5f6ddfd7b` | Four-source VoiceEngine candidate sweep |
| `theory_x/stage_tom/global_workspace.py` | `54ddab05112702eef34faaa4f24d45139350b349` | Chat budgeted block-selection helper |
| `run.py` | `73a2c58a4f5f0348135a46eb83d6cdd61db874e7` | VoiceEngine construction and AppState wiring |
| `theory_x/focal_set.py` | `e12531f2858085778ebca75f73a7dee6ec8ce416` | FocalSet selection and selected-ID state |
| `theory_x/working_memory.py` | `4e9badadbb3ada939c05fcb4a82455723c0efa36` | Per-session short-term buffer, activation and decay |
| `theory_x/stage_capability/tool_caller.py` | `31faba3cc49b60f21069679e920c73442249f919` | Heuristic tool selection and kwargs/prompt construction |
| `theory_x/stage_capability/tools.py` | `ff5f251b225c975c01f6bf3c3da9cbad1f77fbee` | Tool registry and implementation dispatch |
| `tests/test_trace_equivalence.py` | `d6c89025affae77cddb4b91d4d2c2301b51c3e60` | Minimal deterministic Chat OFF/ON trace fixture |
| `tests/test_focal_set.py` | `083b8053ff09ef0975f8aab35a120904b2f55423` | FocalSet unit tests; no Chat route integration |
| `tests/test_working_memory.py` | `446d90f4c79a515eba08aaac1b24c5c33f0797e3` | WorkingMemory unit tests; no Chat route integration |
| `theory_x/stage4_membrane/classifier.py` | `84f68975083266ba1a3fecf5322664392711bf10` | INSIDE/OUTSIDE substring classifier |
| `theory_x/stage4_membrane/router.py` | `74d82fe0f9fe210c75d86105e205dcb0c4151d79` | INSIDE/OUTSIDE retrieval route |
| `tests/test_membrane.py` | `42c0347534b765ef4c24685e333c8fe4047fdce8` | Classifier and route tests; no YouTube token-boundary case |
| `theory_x/stage3_world_model/retrieval.py` | `aa3eeb15c9a4a19a24a6d328bc370cd0a4438cf3` | Belief pool, side filter, keyword/semantic scoring and activation blend |
| `theory_x/stage3_world_model/activation.py` | `509a021671c7f698fb740086dfffa170d2543b84` | Spreading activation over belief edges |
| `theory_x/stage4_membrane/self_model.py` | `c3646242ee244d7434228fcabf0550ebd0d37947` | Sense-event snapshot and INSIDE standing-point selection |
| `substrate/trace_overlay.py` | `fbccc3b63bc94dab8e9f01951a581ba3af3f087e` | Trace record envelope and payload digest behaviour |

The Chat route's line ranges in this audit are from the same `gui/server.py` blob; line numbers may shift on later commits. Recheck the branch head and file hashes before relying on this map after further source changes.

**Gate status:** This is a partial source audit. It does not complete the Master Roadmap's forward/backward audit, does not satisfy Gate 0, does not authorise behavioural changes, and does not supersede any higher-authority document.
