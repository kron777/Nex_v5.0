# NEX sentence-to-tool wire trace — 2026-11-28

**Scope:** Stage B ToolCaller → ToolRegistry → arithmetic operation → response-context injection.  
**Repository:** `kron777/Nex_v5.0`  
**Method:** source trace plus isolated tests; no live service or database access.

**Historical implementation status at main snapshot `5ba30077` (before PR #369 merge):** the bounded correction below was still a candidate at that snapshot; the legacy query-to-code fallback, regex import blacklist and subprocess execution were then present. This paragraph is historical, not the current-main status. PR #369 subsequently merged on 28 November 2026; see §9 for exact post-merge evidence.

## 0. Governing objective and architectural boundary

The target pathway remains: human sentence intake → cognitive interpretation through the existing Mind Aspects → the existing Sentence Code representation → Recursive Extrapolator → executable interfaces → verified result.

The Mind Aspects contribute cognitive interpretation. The Tibetan mind map is a model of those aspects, not an action-control authority: an aspect must not gate, score, block or veto an action merely because of its place in that map.

This increment does not recreate, replace or claim to wire the Sentence Code or Mind Aspects. It hardens one legacy arithmetic tool interface downstream of sentence intake. It is supporting work on an existing execution edge, not evidence that the complete governing pathway is operational.

## 1. Existing wire

The inspected path in `gui/server.py` is:

```text
/api/chat human sentence
  -> AppState.tool_caller.should_use_tool(prompt)
  -> ToolCaller.build_tool_kwargs(prompt, tool_name)
  -> AppState.tool_registry.execute(tool_name, **kwargs)
  -> ToolResult
  -> ToolCaller.build_tool_prompt(prompt, result)
  -> appended to belief_text / response context
  -> voice response
```

This is an actual language-triggered capability route. It is not a general sentence compiler and does not synthesize arbitrary machine instructions. The current ToolCaller uses keyword patterns to select among web fetch, arithmetic and belief retrieval.

The original note's empty-belief-list concern is withdrawn: current main's ToolCaller.should_use_tool() accepts only the raw query, and gui/server.py calls it with one argument. The ToolCaller selects from the user's sentence; retrieved belief_text is assembled separately and later injected into the response context. No belief-list parameter or no-beliefs fallback exists in the current API. Whether tool selection should use retrieved context is a design question, not an established defect.

## 2. Defect found at the execution boundary

Before this increment:

- `ToolCaller` selected `python_exec` for calculation-like wording.
- `build_tool_kwargs()` passed the original sentence as `query` and an empty `code`.
- `ToolRegistry._python_exec()` replaced empty code with the query and passed it to `python3 -c`.
- The import blacklist was regex-based and therefore not a reliable execution sandbox; Python expressions such as dynamic imports are not stopped by a blacklist that only searches for import statements.

The sentence was therefore being treated as source code rather than being translated into a bounded operation.

## 3. Bounded correction implemented by PR #369 (merged 28 November 2026)

PR #369 implemented the following bounded correction:

1. Selects the tool only when a recognised sentence prefix contains a numeric expression.
2. Extracts the expression using a strict character allowlist and syntax parse.
3. Passes an explicit arithmetic expression, never the natural-language sentence, to the registry.
4. Interprets a small AST allowlist in-process; it does not call `exec`, `eval`, `compile`, or a subprocess.
5. Allows numeric constants, bounded arithmetic, unary signs, a small allowlist of `math` constants/functions at the registry boundary, and `print(expression)`.
6. Rejects imports other than `math`, attribute traversal, file access, dynamic imports, assignments, loops, oversized expressions and excessive exponents.
7. Rejects query-only invocation instead of silently treating the query as code.
8. The sentence-level extractor is deliberately narrower than the registry: it accepts numeric operators only, not `math.*` function/constant names. Its input is capped at 990 characters and 61 AST nodes before the registry's 1,000-character/64-node limits are reached.

The output still follows the existing ToolResult → response-context path. No new node or execution authority was introduced.

## 4. Tests added and merged in PR #369

- Safe arithmetic returns the expected numeric result.
- `math.pi` and bounded `math.sqrt` work.
- OS/sys imports, dynamic imports, file access, assignments, loops and excessive exponents are rejected.
- Query-only input is rejected by the registry.
- A natural-language calculation sentence is traced through ToolCaller, ToolRegistry and response-context formatting, then through the Flask `/api/chat` route into the actual voice request prompt.
- A sentence containing a dynamic-import payload is not selected as a calculation operation.
- Oversized expressions are rejected before AST parsing, parser recursion failures become non-selection, and the sentence-level AST node budget is enforced.

Exact-head workflow `46119302748` passed on `f9bd490eebab6c82f1a3704f7527291ff5489869`: 2,930 passed, 7 skipped, 62 subtests; baseline and disposable sandbox checks passed; mind-map check reported 30 nodes, 0 unverified, 14 dark and 2 blocked. Main snapshot `18c8f06171e1de35c3210831a49b63d0e2487af0` subsequently passed workflow `46153028417` (`pytest`) at 14:13 UTC.

## 5. Adjacent RDO path — related, but not yet connected

NEX also contains a more structured objective-intake path:

- rdo/OBJECTIVE_INTAKE.md defines provider-neutral rdo.objective.v1 input.
- The contract preserves the original human request, submitted intent, scope, constraints, exclusions, assumptions, acceptance criteria, proposed seed obligations and typed relationships.
- The deterministic RDO validates the input and reuses its existing expansion, reconciliation, graph and planning pipeline.
- The intake is explicitly advisory: it does not accept reconciliation outcomes, approval flags, executable commands or deployment instructions.
- The Stage-7 path is a separate, reviewed development handoff; it is not a general runtime action executor.

This is a promising objective-level intermediate representation, but it is not the user's Sentence Code and not yet a free-form sentence-to-machine-operation compiler. The inspected gui/server.py chat route has no rdo, rdo_adapters or objective_intake call. The chat-to-RDO wire is therefore absent in the inspected source.

The RDO's Recursive Extrapolator is also specifically a development-network expander: it consumes already-structured seed obligations, applies generic engineering decomposition rules, reconciles them against repository mechanisms, and produces a bounded obligation graph and work packages. It does not parse a free-form human sentence, produce executable runtime instructions, or execute the generated work. Stage-7 hands reviewed development packages to an external execution agent and verifies the resulting source/tests separately. This is valuable downstream machinery for developing NEX, but it must not be mistaken for the runtime Sentence Code pathway.

Do not connect it blindly: RDO objective obligations describe development work, while runtime tool operations describe actions NEX may perform in response to a user. Their authority, validation and execution contracts differ. Reuse may be possible at the representation/provenance layer, but that requires a deliberate mapping.

## 6. Limits and next wire

This is a narrow safety and dataflow correction, not completion of the human-sentence-to-machine-code objective. It covers simple arithmetic only. The next step is to design and test a typed intermediate operation representation for broader capabilities, with explicit schemas, provenance, preconditions, approval policy and post-execution verification. It must reuse the existing capability and governance boundaries rather than introducing a second execution framework.

## 7. Sentience 5.5 comparison — useful sketch, not a working execution bridge

The inspected Sentience 5.5 source provides three relevant but separate pieces:

- Voice_Interaction_Node.submit_command() queues a raw string; _generate_response() places it in a simple LLM prompt. No structured Sentence Code or machine-operation representation is produced in this path.
- Action_Execution_Node.execute_action() accepts a pre-structured dictionary and performs simple rule checks plus optional LLM advice. Its _perform_action() is explicitly a placeholder that returns a random simulated success value. When its local LLM is unavailable, the advisory fallback reports is_safe=True; that fallback must not be copied into a real execution authority.
- Interaction_Interface_Node receives a control dictionary and maps a few action labels to canned response strings such as task_execution_started. It emits a versioned interaction frame, but does not itself perform the requested task.

These are valuable architectural sketches of voice intake, structured action envelopes, safety review and interaction feedback. They are not an integrated human-sentence-to-machine-execution pipeline. The present NEX arithmetic route is more concrete at its narrow terminal sink, but is not a general operation compiler. Neither source justifies claiming the full target is already operational.

## 8. Governance

No cognitive node, prompt policy, salience threshold, database schema, feature flag, frozen S-01–S-25 register, M1.8 content, or M0/M1 gate order was changed. The change narrows the existing arithmetic tool boundary and adds isolated tests only.


## 9. Post-merge status and correction — 28 November 2026

PR #369 merged at 07:21:56 UTC (merge commit 194c75c313e695b60f61d1f02b16f99434e2847d). Its exact head passed workflow 46119302748 before merge: 2,930 passed, 7 skipped, 62 subtests; baseline and disposable sandbox checks passed. The later main snapshot 18c8f06171e1de35c3210831a49b63d0e2487af0 passed pytest workflow 46153028417 at 14:13 UTC.

Current main now contains the bounded in-process arithmetic AST interpreter described in §3. The legacy query-to-code fallback, regex import blacklist and subprocess execution described in §2 are historical pre-merge behavior, not current behavior.

Correction to §1: the current ToolCaller API takes one query argument; the GUI calls should_use_tool(prompt), not should_use_tool(prompt, []). The previous empty-belief-list/no-beliefs-fallback claim was inaccurate for current main and is withdrawn. Tool selection is based on the raw user sentence; belief context is assembled separately for response composition.

The autonomous Fountain/fire-path tool caller remains unbuilt. Current theory_x/stage6_fountain/generator.py contains no ToolCaller, ToolRegistry, python_exec, web_fetch or beliefs_query references. The separate observation_reports/fire_path_tools_SCOPE.md remains a read-only scope note; it is not approval to arm tools from autonomous fires.


## 10. Post-characterization: successful capability result followed by chat gap refusal (28 November 2026)

NEX main source snapshot: 18c8f06171e1de35c3210831a49b63d0e2487af0.

The GUI route executes the ToolCaller/ToolRegistry selection at gui/server.py:1912-1948, then appends a successful ToolResult prompt block into belief_text. Later, the normal chat grounding gate counts only tier-labelled entries using belief_text.count("- [Tier") at line 2048. The tool block itself is not tier-labelled. A non-probe, non-social Technical turn with insufficient tier entries returns the graph-gap refusal before voice prompt assembly at line 2514 and voice invocation around line 2567.

Draft PR #459 adds the missing non-probe Technical-register characterization. On exact head db4a22d0078844992829613dbb9a4a90eb4a51e9, workflow 46186063413 passed **3,078 passed, 7 skipped, 86 subtests**. The disposable test sandbox probe passed and the baseline script reported OK. The test observes one successful arithmetic execution (17 × 23 = 391), followed by the configured gap refusal, tool_used: null, and no voice request.

This is a response-grounding / execution-order distinction, not proof of an unsafe state-changing action. The present arithmetic operation is pure. The other Stage-B capability, allowlisted HTTP GET, does make an external network read. The gate is not an execution approval boundary. The source's tool_prompt_injected trace event is emitted when the result is staged in local belief_text, not when the model has consumed it; the early refusal bypasses chat_prompt_ready and the voice call.

No fix is proposed. Whether a valid ToolResult should count as grounding evidence remains undecided. Do not increment the belief count with tool text or treat arbitrary tool output as a belief. A future approved design should encode capability evidence explicitly with provenance and a trust class, separate from beliefs. No defect ID is assigned without a decision on intended behavior. Host occurrence remains UNKNOWN.

## 11. Cognitive interpretation versus the executable-capability selector (28 November 2026)

On current NEX main, the inspected chat capability call is ToolCaller.should_use_tool(prompt). The selector receives the raw human sentence, uses bounded language patterns and returns a capability name. It does not receive a typed Sentence Code object or a Mind Aspect result on this call chain. Existing faculty outputs are independently assembled into Chat's response context; the inspected source does not show them feeding the capability selector.

The mind map is intentionally non-runtime. mind_map/MIND_MAP.yaml declares descriptive-only status, and mind_map/mind_map.py::check_descriptive_only() rejects runtime imports/reads and action-authority fields. tests/test_mind_map_policy.py locks these boundaries. The development DAG and RDO tooling are external engineering instruments, not NEX cognitive action authorities.

The inspected NEX call chain therefore establishes three distinct surfaces:
- faculty interpretation/context, assembled for natural-language composition;
- a narrow heuristic sentence-to-capability selector for three existing Stage-B tools;
- a ToolResult response-context block.

The trace does not establish an end-to-end typed Sentence Code → Recursive Extrapolator → validated capability → approved execution → verified outcome path. The existing Sentence Code representation may have a disconnected producer or consumer elsewhere; this focused trace has not located that connection, so global absence remains UNKNOWN.

A comparison with Sentience 5.5 at 1767acf1fdb321d046261eb3c3059084c85fc0c8 shows raw-string voice intake in Voice_Interaction_Node.py:152-162, a separate dictionary-based Action_Execution_Node.execute_action() at line 113, and placeholder simulated execution in _perform_action() at line 157. The inspected Integration_Node is a latest-value aggregator and does not itself connect those paths into a verified sentence-to-action pipeline. These are sketches, not a validated substitute.

Next research target: locate the existing Sentence Code owner/schema and trace one ordinary sentence through its existing Mind Aspect interpretation, typed representation, Recursive Extrapolator and the first real capability boundary. Preserve separate validation, approval, execution and verification transitions. Start with a read-only or pure fixture; no new autonomous caller, operation store or authority change is warranted in Phase 0.


## 12. Typed thought packets versus machine-operation representations (28 November 2026)

On current main, `ThoughtPacket` is the input contract for belief-substrate ingestion. It carries content, source node, confidence, optional branch and metadata. Fountain, Stage 2, Synergizer, CounterfactualNode, ThrowNet and the reshape resolver construct/re-submit these packets. `CoherenceGate` checks candidate thought content and routes it through ACCEPT / REJECT / HOLD / RESHAPE handling. Its documented exception fallback is ACCEPT, so it must not be described as an execution-approval boundary.

This is distinct from Stage-B:
- ToolCaller selects a bounded existing capability from the raw chat sentence.
- ToolRegistry runs that selected capability.
- ToolResult describes output after execution.

It is also distinct from RDO: `objective.v1` is an advisory engineering objective. The schema description explicitly says input obligations are proposals; the intake validator rejects payload fields for reconciliation outcomes, evidence claims, approval flags and arbitrary execution instructions. The Recursive Extrapolator expands these engineering obligations, not the user's NEX runtime sentence into a machine action.

No general typed Sentence Code object, owner/schema or complete producer-consumer path was established by this selected-path trace. Global absence remains UNKNOWN.

## 13. Existing chat faculty network and duplicate evidence-count experiment (28 November 2026)

The current-day `NEX_CHAT_FACULTY_WIRE_MAP_2026-11-28.md` records thirteen ordered faculty/context blocks and source-level cross-faculty interactions. The relevant source was rechecked against the current main descendant. These are real bounded reads, dependencies, prompt-context contributions and optional salience carry. They are not an unrestricted recursive network and do not possess machine-action authority. Default-off flags are not proof of current host activation; that remains UNKNOWN.

PR #460 studies another reader-to-reader interaction. The membrane's normal OUTSIDE RAG and Stage-B `beliefs_query` use the same retriever with no side filter. Their independent reads can select the same belief ID, then both format it as a `- [Tier` line. The route gap gate counts tier lines, not distinct IDs. The component-level fixture demonstrates shared IDs and duplicate formatting. A full route fixture is intended to show the potential effect against the Technical minimum of two, using one unique seed in an isolated substrate. Exact-head workflow 46187314674 completed successfully on 6b016802831350ff1cf1cf1c19c99fb49e3964b2: 3,079 passed, 7 skipped, 86 subtests; disposable sandbox probe and baseline check OK. The full-route fixture confirms a single unique belief can be represented twice, produce two tier markers and reach the mocked voice request. This is fixture-level evidence only; live host occurrence and impact remain UNKNOWN. No runtime change or defect declaration.

The next evidence step is the exact-head result. If it passes, document the narrow fixture behaviour, then decide whether this is an intended evidence-count contract, a test-only artefact, or a candidate defect requiring source-specific provenance and distinct-evidence counting. Do not silently alter counts or combine arbitrary tool output with belief evidence.
