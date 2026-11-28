# NEX sentence-to-tool wire trace — 2026-11-28

**Scope:** Stage B ToolCaller → ToolRegistry → arithmetic operation → response-context injection.  
**Repository:** `kron777/Nex_v5.0`  
**Method:** source trace plus isolated tests; no live service or database access.

**Implementation status at main snapshot `5ba30077`:** the bounded correction described below is a candidate in PR #369, not yet merged. Current main still contains the legacy query-to-code fallback, regex import blacklist and subprocess execution. The pre-rebase PR head `786c5743` passed full-suite run `46118580628` on the earlier base `bbce6317`; the candidate must be rebased onto this main snapshot and revalidated before it can be called implemented.

## 0. Governing objective and architectural boundary

The target pathway remains: human sentence intake → cognitive interpretation through the existing Mind Aspects → the existing Sentence Code representation → Recursive Extrapolator → executable interfaces → verified result.

The Mind Aspects contribute cognitive interpretation. The Tibetan mind map is a model of those aspects, not an action-control authority: an aspect must not gate, score, block or veto an action merely because of its place in that map.

This increment does not recreate, replace or claim to wire the Sentence Code or Mind Aspects. It hardens one legacy arithmetic tool interface downstream of sentence intake. It is supporting work on an existing execution edge, not evidence that the complete governing pathway is operational.

## 1. Existing wire

The inspected path in `gui/server.py` is:

```text
/api/chat human sentence
  -> AppState.tool_caller.should_use_tool(prompt, [])
  -> ToolCaller.build_tool_kwargs(prompt, tool_name)
  -> AppState.tool_registry.execute(tool_name, **kwargs)
  -> ToolResult
  -> ToolCaller.build_tool_prompt(prompt, result)
  -> appended to belief_text / response context
  -> voice response
```

This is an actual language-triggered capability route. It is not a general sentence compiler and does not synthesize arbitrary machine instructions. The current ToolCaller uses keyword patterns to select among web fetch, arithmetic and belief retrieval.

A second connection detail remains open: the inspected chat call invokes \`should_use_tool(prompt, [])\` with an empty belief list, even after the membrane route has assembled \`belief_text\`. Therefore the ToolCaller cannot distinguish a query already supported by retrieved beliefs from one with no belief support; its no-beliefs factual fallback is effectively given an empty list on this path. This is recorded as a separate context-propagation edge, not changed in this increment.

## 2. Defect found at the execution boundary

Before this increment:

- `ToolCaller` selected `python_exec` for calculation-like wording.
- `build_tool_kwargs()` passed the original sentence as `query` and an empty `code`.
- `ToolRegistry._python_exec()` replaced empty code with the query and passed it to `python3 -c`.
- The import blacklist was regex-based and therefore not a reliable execution sandbox; Python expressions such as dynamic imports are not stopped by a blacklist that only searches for import statements.

The sentence was therefore being treated as source code rather than being translated into a bounded operation.

## 3. Bounded correction candidate — PR #369 (not yet on main)

The PR #369 candidate changes the arithmetic route to:

1. Selects the tool only when a recognised sentence prefix contains a numeric expression.
2. Extracts the expression using a strict character allowlist and syntax parse.
3. Passes an explicit arithmetic expression, never the natural-language sentence, to the registry.
4. Interprets a small AST allowlist in-process; it does not call `exec`, `eval`, `compile`, or a subprocess.
5. Allows numeric constants, bounded arithmetic, unary signs, a small allowlist of `math` constants/functions at the registry boundary, and `print(expression)`.
6. Rejects imports other than `math`, attribute traversal, file access, dynamic imports, assignments, loops, oversized expressions and excessive exponents.
7. Rejects query-only invocation instead of silently treating the query as code.
8. The sentence-level extractor is deliberately narrower than the registry: it accepts numeric operators only, not `math.*` function/constant names. Its input is capped at 990 characters and 61 AST nodes before the registry's 1,000-character/64-node limits are reached.

The output still follows the existing ToolResult → response-context path. No new node or execution authority was introduced.

## 4. Tests in PR #369 candidate branch

- Safe arithmetic returns the expected numeric result.
- `math.pi` and bounded `math.sqrt` work.
- OS/sys imports, dynamic imports, file access, assignments, loops and excessive exponents are rejected.
- Query-only input is rejected by the registry.
- A natural-language calculation sentence is traced through ToolCaller, ToolRegistry and response-context formatting, then through the Flask `/api/chat` route into the actual voice request prompt.
- A sentence containing a dynamic-import payload is not selected as a calculation operation.
- Oversized expressions are rejected before AST parsing, parser recursion failures become non-selection, and the sentence-level AST node budget is enforced.

The previous PR head passed full-suite CI run `46118580628`; that run predates the rebase and the added parser-boundary tests. Exact-head CI must be rerun.

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
