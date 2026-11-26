# NEX Phase 0 — Self-Continuity Consumer Semantics Audit (25 November 2026)

## Scope and evidence boundary

Static-source review of the default-OFF SENTIENCE Phase 1 continuity consumer against source baseline `de93134f34adac07a3a41c2a05b33720510a2bfc`. This increment follows the current reconciliation's §5 continuity candidate list and checks:

- the `self_state_history` query and phrase-selection rules;
- the `SelfMindView.current_summary()` integration;
- the Chat prompt append point;
- the default-off, read-only and fail-safe tests;
- the current continuity wiring document against the actual import/call path.

No live flag values, history rows, model outputs or host process were inspected. The continuity flag was not enabled; no runtime/code/test/DB state was changed.

## 1. Activation and route

- `run.py` constructs and starts SelfMindView in normal startup, then passes it into AppState.
- The Chat handler calls `state.self_mind_view.current_summary()` and appends its result to `belief_text` when non-empty.
- `SelfMindView.current_summary()` calls `self_binding.continuity_for_prompt()` and appends the returned clause to the normal templated summary.
- `continuity_for_prompt()` returns an empty string unless `NEX5_SELF_CONTINUITY=1`; source default is OFF. The rest of the SelfMindView summary remains normal-wired.
- The continuity helper is descriptive only and uses SELECT; it does not gate, score, block or veto a choice.
- The current Chat provenance snapshot is captured earlier than this SelfMindView augmentation, so the continuity clause is not part of the narrow `_retrieved_belief_text` snapshot described in the existing provenance audits. This is consistent with that snapshot's limited retrieval-only scope, not a complete prompt transcript.

The helper's import by Fountain for other self-binding functions does not mean the Fountain fire path calls `continuity_for_prompt()`; the inspected direct call is through SelfMindView in Chat.

## 2. Exact query and phrase rules

The helper opens the dynamic DB and selects:

`emotion, raga, drive FROM self_state_history ORDER BY bound_at DESC LIMIT max(2, window)`

Default `window=6`. It then uses only the first two rows for current/previous emotion and filters the window to non-empty emotion values for the “held steady” test.

Phrase selection:

1. If at least two rows exist and current emotion is non-empty, and every non-empty emotion in the selected window equals current emotion, emit “held steady.”
2. Else, if current and immediately previous emotion are both non-empty and differ, emit “a shift from how I was.”
3. Else, emit “moving rather than settling.”

The query retrieves raga and drive, but no branch of the phrase logic reads either field.

## 3. Verified semantic boundaries

### 3.1 Raga and drive do not contribute to the decision

The consumer's stated input is a three-dimensional tuple (emotion, raga, drive), but the phrase logic only inspects emotion. If emotion is unchanged while raga or drive changes, it can say “held steady.” Conversely, if emotion is missing while raga or drive changes, it falls through to the generic “moving rather than settling” phrase without demonstrating which selected dimension moved.

This is a source-level dimensional mismatch. It does not prove the phrase is false in any live history; no rows were inspected.

### 3.2 Empty emotion values are removed from the persistence test

The “held steady” branch evaluates:

`emotions = [r["emotion"] for r in rows if r["emotion"]]`

It ignores rows with empty emotion rather than treating them as unknown samples. For example, a selected history with current emotion “equanimity,” a previous row with NULL emotion, and older non-empty rows all “equanimity” can still yield “held steady across my recent self-bindings.” The phrase therefore describes continuity across the non-empty subset, not necessarily across every selected binding.

This may be a deliberate missing-data policy, but the wording does not expose the skipped samples.

### 3.3 Generic fallback can overstate movement

When there are at least two history rows but current/previous emotion cannot establish persistence or a shift (including both missing), the helper emits “My self-state has been moving rather than settling, lately.” The retrieved raga/drive values are not checked to support that statement. A history with unchanged or missing emotion and unchanged raga/drive can still reach this fallback.

### 3.4 Equal timestamps are not deterministically ordered

The SQL orders only by `bound_at DESC`. If multiple rows have equal timestamps, the query has no explicit secondary key. Which row becomes “current” and “previous” is not guaranteed by the query contract. The history table has an integer ID that could serve as a tie-breaker, but no such ordering is present.

### 3.5 Connection cleanup is not protected by finally

The helper creates a SQLite connection, runs the SELECT, then calls `c.close()` on the success path. The query and fetch are inside a broad `try/except`, but there is no `finally`. If an exception occurs after connection creation and before the explicit close, the helper returns `""` while leaving cleanup to object destruction/GC. The error is fail-safe for prompt composition but not explicitly resource-safe.

## 4. Tests and what they establish

`tests/test_self_continuity.py` uses a temporary dynamic DB and covers:

- default-off silence;
- a held-emotion phrase;
- an emotion-shift phrase;
- insufficient history;
- SELECT-only/no history writes;
- missing-table fail-safe;
- SelfMindView summary unchanged when off and coloured when armed.

It does not cover:

- emotion unchanged while raga/drive change;
- emotion missing/NULL rows mixed with stable emotion rows;
- a generic fallback with all dimensions unchanged or absent;
- equal `bound_at` timestamps;
- a forced SELECT/fetch exception after connection creation and explicit close verification.

The tests prove the intended default-off/read-only integration on isolated fixtures, not semantic accuracy across the full tuple or host activation.

## 5. Documentation alignment

`CONTINUITY_WIRE.md` correctly describes the default-off, read-only, descriptive intention and the SelfMindView consumer. Its statement that SelfMindView has zero importers is stale relative to normal `run.py` construction and the Chat handler's direct `current_summary()` call. It also describes the fire path as unaffected because Fountain does not call the continuity helper; that narrower statement is consistent with the current source, but should not be confused with “no Chat path consumer.”

The current reconciliation already records the broader wiring correction: SelfMindView is constructed in `run.py` and consumed in Chat. This audit does not update or arm the Phase 1 feature.

## 6. Phase 0 disposition

### Confirmed source facts

- Continuity is default-OFF behind `NEX5_SELF_CONTINUITY=1`.
- When armed, the Chat SelfMindView summary is coloured by a read-only dynamic DB query.
- The query selects emotion/raga/drive, but the phrase decision uses emotion only.
- Empty emotion samples are ignored for the held-steady test.
- The generic fallback can be emitted without checking any dimension for actual movement.
- Equal timestamps have no deterministic secondary order.
- The explicit connection close is not in a finally block.
- Current tests cover basic emotion-only examples, default-off, read-only and fail-safe behaviour, but not the semantic/resource edge cases above.

### Unverified / authority-dependent

- Whether continuity is intentionally defined by emotion alone, or whether raga and drive are meant to contribute.
- Whether missing emotion should be ignored, treated as a discontinuity, or reported as unknown.
- Whether “moving rather than settling” is an acceptable epistemic fallback without a detected change.
- Whether `bound_at` is guaranteed unique by the writer in all paths.
- Whether the resource-cleanup edge is considered material for this short-lived read helper.
- Whether the flag is enabled on any live host; no host state was inspected.

### Boundary

No wording, dimensions, ordering, resource handling, tests, flags or prompt placement were changed. Do not arm the feature or modify its semantics before the Gate 0 decision and governing Frozen V2.1 authority are resolved.
