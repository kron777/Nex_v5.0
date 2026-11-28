# NEX SelfMindView → Metacognition attention wire correction

**Date:** 28 November 2026  
**Base:** `kron777/Nex_v5.0` main at `b5e78842f43ac93c2624697f686da0b600306177`  
**Branch:** `fix/selfmindview-metacog-attention-wire-2026-11-28`  
**Status:** one-column read-path correction and real integration test added; exact-head CI pending.

## 1. Broken edge

The persisted `self_mind_snapshots` table already contains `current_themes_json`. `SelfMindView._snapshot()` writes it from the five most common tags across recent beliefs.

Metacognition's `_detect_drift()` calls:

`self._smv.aspect_history("attention", window_s=...)`

and parses `row["current_themes_json"]` to calculate overlap across recent snapshots. But `SelfMindView.aspect_history("attention")` selected only:

- `taken_at`
- `recent_belief_count_5m`
- `recent_gate_count_5m`
- `current_drive_theme`

It omitted `current_themes_json`. The detector's real input therefore contained no theme sets; it silently treated snapshots as empty. Existing Metacognition tests used a `MagicMock` returning rows with `current_themes_json`, so they tested the detector in isolation and masked the real adapter mismatch.

## 2. Correction

`theory_x/stage_tom/self_mind_view.py` now includes `current_themes_json` in the attention projection returned by `aspect_history()`.

The snapshot schema, snapshot writer, theme calculation, Metacognition detector thresholds, event descriptions, prompt wording and feature flags are unchanged. The correction makes an already-persisted field available to its existing consumer.

## 3. Real integration test

`tests/test_metacognition_drift.py::TestSelfMindViewAttentionWire.test_real_snapshot_themes_reach_metacognition_and_prompt`:

1. Creates an isolated substrate and seeds five controlled beliefs with the same three tags.
2. Takes five real SelfMindView snapshots using the shared dynamic Writer.
3. Reads the actual `aspect_history("attention")` result and verifies that each row includes the expected `current_themes_json`.
4. Passes the real SelfMindView instance to Metacognition and verifies that `_detect_drift()` emits `attention_groove`.
5. Calls the actual `tick()`, verifies persistence to `meta_cognition_events`, and confirms `format_for_prompt()` surfaces the expected self-observation.

This closes the real source-to-sink path: beliefs/tags → SelfMindView snapshot → attention history → Metacognition drift detector → event ledger → prompt context.

## 4. Scope and validation

This is a one-column read projection plus an isolated integration test. No database schema, prompt text, detector threshold, feature flag, cognitive policy or governance register changed. The runtime may now emit an existing `attention_groove` observation when repeated themes genuinely appear across snapshots; that is the intended previously disconnected detector behavior.

Exact-head full-suite CI is pending. No pass count is claimed until it completes.
