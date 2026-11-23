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

### 4.1 Session isolation and lifecycle boundary

The inspected source creates one module-level `_focal_set = FocalSet(K=4)` for the server process, while WorkingMemory instances are created separately in the module-level `_working_memory_by_session` dictionary. Each Chat request updates that shared FocalSet with the current request's candidates, then uses the resulting focal IDs to add content to the requesting session's WorkingMemory. FocalSet's hold-time and prior-priority state therefore span requests and sessions; where candidate belief IDs overlap, a previous request can affect which candidates are protected/selected for a later session's WorkingMemory. This is a cross-session coupling path in the current implementation. Whether that shared attention state is intended by the governing design is unresolved; do not classify it as a defect without the authoritative acceptance rules.

The session WorkingMemory dictionary is process-local and the inspected module exposes a lazy create/get helper but no corresponding deletion/eviction path for session keys. Each individual WorkingMemory is bounded to seven items, but the number of retained session objects is not bounded by this helper. Session retirement, cleanup and memory-growth behaviour remain unverified outside the inspected module. These are lifecycle/acceptance questions for Phase 0, not permission to redesign or change the runtime.


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

The current implementation is a **six-component** weighted score, despite the VoiceEngine module's opening description still calling it a “five-axis grader”: semantic 0.45, confidence 0.23, tier 0.14, recency/reinforcement 0.08, drive alignment 0.10, and Genius 0.15. The source explicitly notes that the Genius component was added without renormalising the earlier weights, so the component weights sum to 1.15 rather than 1.0. This means the score is not a normalized probability or a simple [0,1] weighted average; its threshold is an implementation threshold whose interpretation depends on the current scoring revision. This is an important source/documentation qualification, not an independent finding that the chosen weights or threshold are incorrect.

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


## 11. VoiceEngine / TimeFetch source-audit addendum (23 Nov 2026)

The VoiceEngine candidate pathway is now traced one level further upstream. `VoiceEngine._retrieve_candidates()` delegates to `TimeFetch.run(query)`, which performs four ordered source sweeps: beliefs, novel associations, arcs, then open problem gaps. The source-specific limits are 20, 10, 10 and 10 respectively; results are concatenated in that order, deduplicated by exact content string with first occurrence retained, and capped at 40. Consequently, source priority affects which duplicate survives and can affect which candidates reach the scoring stage. The candidate pool is a keyword/SQL-LIKE retrieval result, not a globally ranked semantic-retrieval set. Beliefs require confidence > 0.4 and content length > 30; associations match either paired belief's content and sort by similarity; arcs exclude `return_transformation` and require a non-null quality grade and theme; problem candidates come from `ProblemMemory.find_matching()`.

VoiceEngine then enriches belief candidates with tier/reinforcement metadata and, when configured, performs cross-database Genius enrichment: belief ID → fountain event ID in beliefs DB → Genius tag in conversations DB. The query orders tags by `tagged_at DESC` and keeps the first score per event. Although `weights_version` is selected, the inspected consumer does not filter on or preserve it in the candidate. Whether scores from different versions are comparable is not established by this source trace; this remains a provenance/acceptance question, not a declared defect.

The scoring implementation has six components, with weights 0.45 semantic, 0.23 confidence, 0.14 tier, 0.08 reinforcement/recency, 0.10 drive alignment and 0.15 Genius. The first five weights sum to 1.00; the Genius term raises the possible maximum to 1.15 and is explicitly not renormalised. Thus `min_score=0.6` is a threshold on this implementation-specific composite, not a calibrated probability or normalized [0,1] confidence. The module header and `_score_candidate` docstring still describe a five-axis grader / five-axis score, while the implementation and a later test comment describe six components. This is a documentation consistency issue.

Test coverage qualification: `tests/test_voice_engine.py::TestScoringAxes::test_score_candidate_returns_zero_on_embed_error` does not cause `embed()` to raise; it passes a zero query vector. The test therefore checks a numeric score for a zero-vector case, not the claimed exception path. In implementation, candidate-embedding/cosine errors are caught locally, semantic is set to zero, and the remaining score components are still calculated. The outer error handler returns 0.0 only when an exception escapes the component-level handling. This is a test-name/docstring and coverage mismatch; no assertion is made here about a user-visible failure.

Evidence boundary: static source inspection only. No host retrieval distribution, Genius tag-version population, score calibration, or runtime incidence was measured. No runtime or test changes are included. Relevant source hashes: `theory_x/stage_throw_net/time_fetch.py` `7a97a76a48eb54d621d1a436fc5c64d5f6ddfd7b`; `theory_x/stage_throw_net/voice_engine.py` `ea52711e13b7ea71531a3bec9a394d18e2574b40`; `tests/test_voice_engine.py` `a82f104fbd2bc3efd1b3fed9d6410b838f38fd6f`.


**Additional retrieval detail — open-problem source:** `ProblemMemory.find_matching()` obtains `list_open()` (open rows ordered by `last_touched_at DESC`) and retains problems with at least two shared cleaned content tokens between query and title+description. It does not rank the matches by overlap count or semantic similarity. TimeFetch preserves that returned order in the gap segment; VoiceEngine later computes candidate embeddings and scores the resulting candidates. Thus the gap source's pre-scoring inclusion/order is determined by the two-token filter and recency order, not a semantic top-k. Source hash: `theory_x/stage7_sustained/problem_memory.py` `4a9dcc839bf0be7bf28338168d8946309c7002f5`. This describes source behaviour only; whether it is intended remains an acceptance question.


**Genius-version design cross-check:** `GENIUS_SCORE_v2.md` specifies a unique `genius_tags` row per `(fountain_event_id, weights_version)` and explicitly says old and new version tags coexist for comparison after weights are re-fit. The VoiceEngine consumer instead orders all tags for each event by `tagged_at DESC` and takes the first, without selecting an intended weights version. Therefore the consumer's selected score is “most recently tagged”, not demonstrably “score from the currently approved weights version”. Whether that is intended requires the active-version/consumer contract; no active-version selector was inferred. Design doc hash: `be73cb4f7b494c48eb37eeec8635aba89ea5751e`.


## 12. FocalSet → session WorkingMemory → prompt integration (23 Nov 2026)

The prior description of FocalSet as “log-only” is incomplete at the full Chat handler boundary. The code comment at the FocalSet update site calls the attention tracking log-only/no behaviour change, but the subsequent production path does more: the process-global `_focal_set` (constructed once with `K=4`) is updated from each request's own `WorldModel.retriever.retrieve(query=prompt, limit=10)` result. Its `get_focal_ids()` are then used to add matching current-request candidate content to a `WorkingMemory` instance keyed by that request's `session_id`. The WorkingMemory object is bounded internally (capacity 7), but `_working_memory_by_session` is a process-global dictionary with lazy creation and no deletion/eviction path visible in the inspected server module.

The same handler later reads that session's active WorkingMemory items and appends up to five as `Recently attended (cross-turn)` to `belief_text`, but only when the register is `Conversational` and the retrieved `belief_count >= CHAT_GAP_MIN_BELIEFS` (2). That text enters the composed voice prompt. Therefore this is not merely diagnostic logging: FocalSet-selected items can influence later chat prompt content.

**Cross-session coupling mechanism:** FocalSet state (`focal_belief_ids`, `last_shift_tick`, priorities/mode) is shared across requests/sessions, while WorkingMemory is session-keyed. Its hold-time logic protects existing focal IDs that are still in the current request's candidate set and uses a process-global `last_shift_tick`; an update from one session can therefore affect focal selection for another session, particularly where their retrieved candidate sets overlap and the global hold window is active. The selected IDs are then copied into the receiving session's own WorkingMemory and may be injected on a later eligible turn. This is not evidence that one session's WorkingMemory object is directly read by another, nor does it prove arbitrary private conversation text crosses sessions: the cross-session influence is through shared attention state over globally stored belief candidates.

**Evidence/test boundary:** `tests/test_focal_set.py` tests FocalSet mechanics in isolation; `tests/test_working_memory.py` tests WorkingMemory mechanics in isolation; `tests/test_chat_memory.py` tests a different admin-scoped ConversationMemory path. The inspected tests do not exercise two Flask chat sessions interleaving through the module-global FocalSet and their separate WorkingMemory buffers, nor assert the resulting prompt blocks. This is a source-confirmed integration/coupling path with an unverified intended isolation contract, not a declared defect until Founder Sign-Off/Frozen V2.1 criteria establish the required scope of attention continuity.

Source hashes on this branch: `gui/server.py` `5ee8b167f386466c383090445c63a84810bbae52`; `theory_x/focal_set.py` `e12531f2858085778ebca75f73a7dee6ec8ce416`; `theory_x/working_memory.py` `4e9badadbb3ada939c05fcb4a82455723c0efa36`; `tests/test_focal_set.py` `083b8053ff09ef0975f8aab35a120904b2f55423`; `tests/test_working_memory.py` `446d90f4c79a515eba08aaac1b24c5c33f0797e3`; `tests/test_chat_memory.py` `b8123747372956ff38ab28838a8368429006b3f6`.


**Ordering qualification:** In the handler, the FocalSet update and WorkingMemory add/decay occur at approximately lines 1596–1655, before the `Recently attended (cross-turn)` injection at approximately lines 1733–1742. Therefore, on an eligible Conversational turn, the injected WorkingMemory can include both items added from the current request's just-computed focal set and items retained from earlier turns. The label “cross-turn” does not mean the block is exclusively prior-turn state. This same-turn ordering is important when interpreting prompt provenance and any ablation or attention experiment.


## Independent review reconciliation — exact PR #65 source (23 Nov 2026)

An independent read-only review of PR #49 head `d046d5beadd640cca6df6631d9dbd3166d16fccf` and PR #65 head `3d5df48e6539818097b58b6e936059fae946ceca` identified the following additional qualifications. These are source/test observations, not permission to change behaviour.

### VoiceEngine trace parentage

At `gui/server.py::api_chat`, the `model_input` record for `VoiceEngine.query_reply` currently sets `parent_ids` to both `_trace_input_id` and `_trace_retrieval_id` (PR #65 source lines 1901–1915). The actual call passes `query=prompt`, `session_id`, and `turn_n`; it does not receive the earlier general Chat retrieval result or its selected belief set. VoiceEngine then performs its own TimeFetch retrieval. The shared user query is a common upstream input, but the inspected call path does not establish that the general Chat retrieval result is an immediate causal parent of the VoiceEngine retrieval. Treat this as a **trace-parentage concern requiring reconciliation**, not as a response-quality defect. Do not alter the edge until the intended parent semantics and governing acceptance criteria are confirmed.

### Substrate-mode miss and VoiceClient fallback

The handler comment at approximately lines 2261–2263 says that in `use_substrate` mode an LLM fallback is suppressed on a substrate miss. In the inspected handler, an eligible VoiceEngine miss leaves `text` unset; control reaches `if text is None` and calls `state.voice.speak(...)` at lines 2261–2282. The repository's `voice/llm.py::VoiceClient.speak` constructs a model request and invokes its configured `_request_fn`; the default request function sends an HTTP request to the configured llama-server endpoint. Thus the handler itself does not implement the suppression described by the comment. Whether a particular runtime substitutes another VoiceClient/request function or disables the endpoint remains a wiring/configuration question; do not claim deployed model invocation from this static path alone. Record the discrepancy as **source-confirmed control-flow/comment mismatch; runtime mode effect unresolved**. No fix is authorised by this audit.

### Speech hand-off and observer limits

The commit-before-registration interleaving is directly reproducible in the test fixture: Writer commit makes the pending row visible before the producer records/registers its trace identity. The consumer can therefore start an explicitly unlinked trace. This proves the possibility under the controlled ordering, not the frequency in deployment. The identity registry is process-local and bounded; restart or eviction can also remove the hand-off. The honest unlinked result avoids a fabricated parent but leaves provenance incomplete.

The consumer selects pending rows and only later writes a speaking status; there is no atomic exclusive claim in the inspected path. Two overlapping consumers could select the same row before either status update, but no evidence establishes that the deployed topology overlaps consumers or that duplicate playback occurred. Keep this conditional.

Trace append serializes and writes synchronously under a shared module lock. This creates a possible caller-latency/lock-contention cost; current diagnostic tests do not establish a deployed-host latency distribution or neutrality threshold. The benchmark smoke test is not a performance acceptance test. Event labels remain narrow: selection is not reservation, synthesis return is not waveform validation, player-call return is not audibility, and persisted `spoken` status is not listener receipt.

### Test and authority boundary

Both requested exact PR heads have green pytest workflow runs: PR #49 run `45255379806` on `d046d5beadd640cca6df6631d9dbd3166d16fccf`, and PR #65 run `45250499152` on `3d5df48e6539818097b58b6e936059fae946ceca`. These are separate branch heads and separate workflow runs, not a jointly tested merged tree. They validate their respective workflow assertions only.

The absence of authority artifacts is bounded to the inspected repository tree and PR material. The canonical Frozen V2.1 specification and Founder Sign-Off/approval record remain unlocated in that inspected material; this does not prove they do not exist elsewhere. PR #49 itself says its crosswalk is partial and Gate 0 is not established. The Master Roadmap being reported as reopened from the Library is not equivalent to including and verifying the canonical roadmap and its version/provenance in the reviewed tree.

**Disposition:** Gate 0 remains unestablished. Behavioural changes remain unauthorised pending production of the canonical authority artifacts, reconciliation of their hierarchy and criteria, and the required Founder approval of the defined Gate 0 packet. No source/runtime change, schema change, deployment, merge, or roadmap amendment is made by this reconciliation.
