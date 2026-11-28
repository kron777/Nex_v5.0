# NEX sentence-to-tool wire trace — 2026-11-28

**Scope:** Stage B ToolCaller → ToolRegistry → arithmetic operation → response-context injection.  
**Repository:** `kron777/Nex_v5.0`  
**Method:** source trace plus isolated tests; no live service or database access.

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

## 3. Bounded correction

The arithmetic route now:

1. Selects the tool only when a recognised sentence prefix contains a numeric expression.
2. Extracts the expression using a strict character allowlist and syntax parse.
3. Passes an explicit arithmetic expression, never the natural-language sentence, to the registry.
4. Interprets a small AST allowlist in-process; it does not call `exec`, `eval`, `compile`, or a subprocess.
5. Allows numeric constants, bounded arithmetic, unary signs, a small allowlist of `math` constants/functions, and `print(expression)`.
6. Rejects imports other than `math`, attribute traversal, file access, dynamic imports, assignments, loops, oversized expressions and excessive exponents.
7. Rejects query-only invocation instead of silently treating the query as code.

The output still follows the existing ToolResult → response-context path. No new node or execution authority was introduced.

## 4. Tests added

- Safe arithmetic returns the expected numeric result.
- `math.pi` and bounded `math.sqrt` work.
- OS/sys imports, dynamic imports, file access, assignments, loops and excessive exponents are rejected.
- Query-only input is rejected by the registry.
- A natural-language calculation sentence is traced through ToolCaller, ToolRegistry and response-context formatting, then through the Flask `/api/chat` route into the actual voice request prompt.
- A sentence containing a dynamic-import payload is not selected as a calculation operation.

## 5. Adjacent RDO path — related, but not yet connected

NEX also contains a more structured objective-intake path:

- rdo/OBJECTIVE_INTAKE.md defines provider-neutral rdo.objective.v1 input.
- The contract preserves the original human request, submitted intent, scope, constraints, exclusions, assumptions, acceptance criteria, proposed seed obligations and typed relationships.
- The deterministic RDO validates the input and reuses its existing expansion, reconciliation, graph and planning pipeline.
- The intake is explicitly advisory: it does not accept reconciliation outcomes, approval flags, executable commands or deployment instructions.
- The Stage-7 path is a separate, reviewed development handoff; it is not a general runtime action executor.

This is a promising objective-level intermediate representation, but it is not the user's Sentence Code and not yet a free-form sentence-to-machine-operation compiler. The inspected gui/server.py chat route has no rdo, rdo_adapters or objective_intake call. The chat-to-RDO wire is therefore absent in the inspected source.

Do not connect it blindly: RDO objective obligations describe development work, while runtime tool operations describe actions NEX may perform in response to a user. Their authority, validation and execution contracts differ. Reuse may be possible at the representation/provenance layer, but that requires a deliberate mapping.

## 5. Limits and next wire

This is a narrow safety and dataflow correction, not completion of the human-sentence-to-machine-code objective. It covers simple arithmetic only. The next step is to design and test a typed intermediate operation representation for broader capabilities, with explicit schemas, provenance, preconditions, approval policy and post-execution verification. It must reuse the existing capability and governance boundaries rather than introducing a second execution framework.

## 6. Governance

No cognitive node, prompt policy, salience threshold, database schema, feature flag, frozen S-01–S-25 register, M1.8 content, or M0/M1 gate order was changed. The change narrows the existing arithmetic tool boundary and adds isolated tests only.
