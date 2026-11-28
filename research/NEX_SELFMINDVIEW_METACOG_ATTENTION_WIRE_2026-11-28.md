# NEX SelfMindView → Metacognition attention wire correction

**Date:** 28 November 2026  
**Evidence base:** `kron777/Nex_v5.0` main at `f5cf19c32b0151043ca90b139b25c24e01e384fb`  
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

## 3. Live runtime call site confirmed

This is an active chat-turn path, not a dormant API. `run.py` injects the real SelfMindView instance into Metacognition (`metacognition._smv = _self_mind_view`). In `gui/server.py`, chat assembly calls `state.metacognition.tick()`, then `format_for_prompt()`, and appends any returned self-observation to `belief_text` before prompt generation. Therefore, once the missing column is exposed, qualifying theme recurrence can flow into actual chat context on subsequent turns.

## 4. Real integration test

`tests/test_metacognition_drift.py::TestSelfMindViewAttentionWire.test_real_snapshot_themes_reach_metacognition_and_prompt`:

1. Creates an isolated substrate and seeds five controlled beliefs with the same three tags.
2. Takes five real SelfMindView snapshots using the shared dynamic Writer.
3. Reads the actual `aspect_history("attention")` result and verifies that each row includes the expected `current_themes_json`.
4. Passes the real SelfMindView instance to Metacognition and verifies that `_detect_drift()` emits `attention_groove`.
5. Calls the actual `tick()`, verifies persistence to `meta_cognition_events`, and confirms `format_for_prompt()` surfaces the expected self-observation.

This closes the real source-to-sink path: beliefs/tags → SelfMindView snapshot → attention history → Metacognition drift detector → event ledger → prompt context.

## 5. Semantic boundary: two different meanings of attention

The SelfMindView attention aspect is derived from recent belief tags and recent gate counts. Its `current_themes_json` represents recurring semantic themes; it is not the Stage-2 Bonsai branch-focus vector. Metacognition's `attention_groove` is therefore a detector of thematic repetition across snapshots, not a detector of fixation in the Stage-2 attention network.

NEX also has the separate Stage-2 path from external sense events → A–F → Bonsai focus/texture → Fountain branch selection and Global Workspace framing. The inspected SelfMindView attention reader does not consume that Bonsai status. These two uses of “attention” should remain semantically distinct until an explicit mapping is justified and measured. This PR repairs only the theme-history → Metacognition wire; it does not merge the two attention representations.

## 6. Possible repeated-event amplification (not changed)

The Phase-40 `attention_groove` finding is emitted on every `Metacognition.tick()` while the theme-overlap condition remains true. `tick()` writes every finding, and `_write_event()` performs an unconditional insert and invalidates the recent-event cache. The module's `_DRIFT_COOLDOWN` is used for goal-drift events; the inspected attention-groove path does not apply it or deduplicate an ongoing episode.

Because `gui/server.py` calls `tick()` on each chat turn, sustained identical themes may create another `attention_groove` row on each qualifying turn and repeatedly occupy the recent-event prompt context. Once this previously disconnected wire is active, that could become a self-reinforcing prompt loop: recurring themes trigger an observation, the observation is injected, and subsequent responses may continue the same theme. This is a hypothesis about a possible amplification effect, not a demonstrated harmful outcome.

The integration test now calls three consecutive qualifying chat-turn ticks and asserts that three `attention_groove` rows are written. It seeds an older distinct unresolved `value_drift_distance` observation first, then verifies that the three attention rows displace it from `get_recent(limit=3)`. This confirms both repeated-event behaviour and recency-pool starvation in an isolated fixture, rather than relying only on source inspection. The test labels it as characterization, not a desired permanent event-count contract. This PR deliberately does not add a cooldown or episode-deduplication policy. The next observation should measure event frequency and repeated prompt exposure under controlled, sustained themes before choosing whether to add an episode identity, cooldown, resolution condition or decay rule.
## 7. Scope and validation

This is a one-column read projection plus an isolated integration test. No database schema, prompt text, detector threshold, feature flag, cognitive policy or governance register changed. The runtime may now emit an existing `attention_groove` observation when repeated themes genuinely appear across snapshots; that is the intended previously disconnected detector behavior.

Exact-head full-suite CI is pending for the expanded three-tick/recency-pool characterization. No pass count is claimed until it completes.
