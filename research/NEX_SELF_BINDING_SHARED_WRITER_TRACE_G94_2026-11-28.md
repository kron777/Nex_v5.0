# NEX self-binding shared-Writer trace — G-94

**Date:** 28 November 2026  
**Base:** `kron777/Nex_v5.0` main at `bbca5deb3a0398331503ce61c95a62f8d1b3d33d`  
**Implementation branch:** `fix/self-binding-shared-writer-2026-11-28`  
**Status:** bounded source correction and regression tests added; exact-head CI pending.

## 1. Finding

NEX's one-pen persistence rule requires one canonical Writer per substrate database, with runtime writers injected into faculties that mutate that database. `self_binding.bind(dynamic_writer=None)` intentionally retains a self-owned Writer fallback for standalone use, but two runtime callers failed to provide their already-available shared Writer.

### Call path A — Fountain recursive self-reading

Before the correction:

`FountainGenerator._build_prompt → recursive_self.format_for_prompt() → perturbation() → _bound_state() → self_binding.bind(dynamic_writer=None) → Writer(dynamic.db)`

The helper `_bound_state(dynamic_writer=None)` already forwarded its parameter to `self_binding.bind`, but `format_for_prompt` did not accept or forward a Writer. FountainGenerator already owns `self._dynamic_writer`.

After the correction:

`FountainGenerator._build_prompt → recursive_self.format_for_prompt(dynamic_writer=self._dynamic_writer) → perturbation(dynamic_writer) → _bound_state(dynamic_writer) → self_binding.bind(dynamic_writer)`

The existing recursive-self behavioural logic and generated prompt text are unchanged; only persistence ownership is corrected.

### Call path B — SelfMindView snapshot

Before:

`run.py → SelfMindView(dynamic_writer=writers["dynamic"]) → _snapshot() → self_binding.bind() → Writer(dynamic.db)`

SelfMindView already owns `self._dw`, the shared AppState dynamic Writer. Its snapshot path omitted that dependency.

After:

`SelfMindView._snapshot() → self_binding.bind(dynamic_writer=self._dw)`

### Standalone fallback

`self_binding.bind()` remains usable from the module's standalone/CLI entry point. In that mode it may own and close a Writer. The rule is that runtime call sites must inject the canonical Writer, not that every standalone diagnostic invocation must receive AppState.

## 2. Changes

- `theory_x/stage_tom/recursive_self.py`: `format_for_prompt(dynamic_writer=None)` now forwards the optional Writer through `perturbation` to the existing `_bound_state` helper.
- `theory_x/stage6_fountain/generator.py`: passes `self._dynamic_writer` into recursive self prompt generation.
- `theory_x/stage_tom/self_mind_view.py`: passes `self._dw` into `self_binding.bind`.
- `tests/test_self_state_history.py`: adds an end-to-end helper-level assertion that recursive prompt generation passes the exact injected Writer into the binding path.
- `tests/test_self_mind_view.py`: adds a regression test that makes any attempt to construct a second `self_binding.Writer` fail while a snapshot runs, then confirms the bound self-state was written.

## 3. Evidence and limitations

The defect is verified from source-level call sites and constructor ownership. The regression tests are isolated; they do not connect to a live database or start the Fountain/GUI runtime.

**CI status:** pending for the current branch head. Do not report the tests as passing until exact-head GitHub Actions completes.

No schema, prompt wording, faculty inputs, attention logic, feature flag, selection weight, or runtime activation was changed. The fix does not establish whether recursive self-reading improves attention; it only ensures the existing write is routed through the intended canonical Writer.

## 4. Governance

- Preserve the frozen S-01–S-25/M1.8 register.
- Preserve M0.1–M0.5 → Founder Gate 0 → M1.1–M1.10 order.
- No live service restart, flag activation, live database write, Gate 0 bypass or Phase 1 transition.
- Manual update: canonical `INDEX.md` §47 and its plain-text mirror are updated on this branch.


## 5. Broader self-network interactions and remaining semantic gaps

### Wider self-integration trace and unresolved edges

The Writer correction preserves an existing multi-faculty path:

`compositional emotion + rāga + competing-drive state + latest Fountain thought/readiness + open problem + proprioceptive substrate` → `self_binding.bind()` → `self_state` and append-only `self_state_history`.

Two consumers then use related but distinct aspects of this state:

- Fountain's recursive-self path rebinds on the thought-generation path, reads the resulting components and turns selected emotion/rāga patterns into a first-person prompt nudge. It does not directly write Bonsai focus or mechanically select a new branch; the intended behavioural influence is through the prompt.
- SelfMindView's 300-second snapshot captures the bound synthesis in `self_mind_snapshots.bound_self_synthesis`. Its separate `current_summary()` recomputes beliefs, intentions, knowledge, uncertainty and attention for Chat. `run.py` also injects SelfMindView into Metacognition; Metacognition reads its attention and uncertainty histories to detect recurring attention themes and unresolved-problem stagnation, records those as metacognitive events, and can surface the recent event as prompt text.

This is a genuine chain of connected representations and consumers, but the prompt-mediated feedback should not be mistaken for a measured change in selection or attention.

**Unresolved semantic edges (not changed in this PR):**

1. `self_binding.bind()` currently assigns `drift = "clean"` as a placeholder. The nearby comment says it reads the last logged verdict, but the inspected function contains no such read. The field is persisted but is not included in the returned `components` or synthesis. Do not treat `clean` as a measured value-drift result.
2. The binder's attention input is the latest Fountain thought/readiness plus the newest open problem. It does not read the live Bonsai focus vector or identify the current hottest branch. That may be a deliberate narrow definition, but it is not a complete representation of Stage-2 attention.
3. The recursive perturbation currently consumes rāga and emotion (plus the named attending text); drive, readiness and substrate tone are bound but do not directly participate in its nudge rules. Their presence in the unified record does not prove they influence the recursive loop.
4. SelfMindView's Chat summary is recomputed from its five live aspects and is not the same object as the last persisted `bound_self_synthesis`. The snapshot and conversational summary are parallel views, not one shared narrative.

These are candidates for further source tracing and controlled experiments. No extra faculty or behavioural wire should be added until the intended semantics, consumers and effects are clear.
