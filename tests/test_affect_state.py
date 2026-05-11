"""Unit tests for AffectState (Phase 27, DOCTRINE §5 row 12).

Tests cover:
  - SentienceNode protocol conformance
  - tick() writes correct row (all five columns)
  - format_for_prompt() reads current row, returns formatted string
  - format_for_prompt() returns "" when table empty (defensive)
  - mood_label thresholds (±0.2 boundaries)
  - Integration math bounded (valence [-1,1], arousal/stability [0,1])
  - Decay applied each tick (values decrease with zero delta input)
  - Coherence components: gate accept rate + held resolution rate affect stability
  - state() returns correct shape with expected keys
"""
from __future__ import annotations

import time
import unittest
from unittest.mock import MagicMock, call, patch

from theory_x.stage_affect.affect_state import (
    AffectState,
    _mood_from_valence,
    _integrate,
    _DECAY_RATE,
    _STABILITY_DECAY_RATE,
    _INTEGRATE_SCALE,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _row(**kwargs):
    """Return a dict acting as a DB row."""
    return dict(kwargs)


def _make_node(
    *,
    cr_row=None,
    br_read_one_n=0,
    br_gate_rows=None,
    br_held_rows=None,
    br_belief_rows=None,
    tick_interval_s=300,
):
    """Build an AffectState backed entirely by mocks.

    cr_row        — row returned by conversations_reader.read_one
    br_read_one_n — value for COUNT(*) queries on beliefs_reader.read_one
    br_gate_rows  — list of dicts for gate_decisions query
    br_held_rows  — list of dicts for held_thoughts query
    br_belief_rows — list of dicts for top-N beliefs query
    """
    cw = MagicMock()
    cw.write.return_value = 1

    cr = MagicMock()
    cr.read_one.return_value = cr_row

    br = MagicMock()

    def _br_read_one(sql, params=()):
        return {"n": br_read_one_n}

    def _br_read(sql, params=()):
        sql_lower = sql.lower()
        if "gate_decisions" in sql_lower:
            return br_gate_rows or []
        if "held_thoughts" in sql_lower:
            return br_held_rows or []
        if "beliefs" in sql_lower and "content" in sql_lower:
            return br_belief_rows or []
        return []

    br.read_one.side_effect = _br_read_one
    br.read.side_effect = _br_read

    node = AffectState(cw, cr, br, tick_interval_s=tick_interval_s)
    # expose mocks for assertion
    node._mock_cw = cw
    node._mock_cr = cr
    node._mock_br = br
    return node


# ── Protocol ──────────────────────────────────────────────────────────────────

class TestSentienceNodeProtocol(unittest.TestCase):
    def setUp(self):
        self.node = _make_node()

    def test_implements_sentience_node_protocol(self):
        from theory_x import SentienceNode
        self.assertIsInstance(self.node, SentienceNode)

    def test_name(self):
        self.assertEqual(self.node.name, "affect_state")

    def test_tick_returns_dict(self):
        result = self.node.tick()
        self.assertIsInstance(result, dict)

    def test_decay_is_callable_no_error(self):
        self.node.decay(now=time.time())  # must not raise


# ── Mood label ────────────────────────────────────────────────────────────────

class TestMoodLabel(unittest.TestCase):
    def test_positive_above_threshold(self):
        self.assertEqual(_mood_from_valence(0.41), "positive")
        self.assertEqual(_mood_from_valence(1.0),  "positive")
        self.assertEqual(_mood_from_valence(0.5),  "positive")

    def test_negative_below_threshold(self):
        self.assertEqual(_mood_from_valence(-0.41), "negative")
        self.assertEqual(_mood_from_valence(-1.0),  "negative")
        self.assertEqual(_mood_from_valence(-0.5),  "negative")

    def test_neutral_within_band(self):
        self.assertEqual(_mood_from_valence(0.0),   "neutral")
        self.assertEqual(_mood_from_valence(0.39),  "neutral")
        self.assertEqual(_mood_from_valence(-0.39), "neutral")
        self.assertEqual(_mood_from_valence(0.4),   "neutral")   # boundary: not > 0.4
        self.assertEqual(_mood_from_valence(-0.4),  "neutral")   # boundary: not < -0.4


# ── Integration math ─────────────────────────────────────────────────────────

class TestIntegrateMath(unittest.TestCase):
    def test_valence_clamped_at_positive_extreme(self):
        # Starting near max, large positive delta must clamp to 1.0
        result = _integrate(0.99, 1.0, -1.0, 1.0)
        self.assertLessEqual(result, 1.0)
        self.assertGreaterEqual(result, -1.0)

    def test_valence_clamped_at_negative_extreme(self):
        result = _integrate(-0.99, -1.0, -1.0, 1.0)
        self.assertGreaterEqual(result, -1.0)

    def test_arousal_stays_non_negative(self):
        result = _integrate(0.01, -10.0, 0.0, 1.0)
        self.assertGreaterEqual(result, 0.0)

    def test_arousal_clamped_at_one(self):
        result = _integrate(0.99, 10.0, 0.0, 1.0)
        self.assertLessEqual(result, 1.0)

    def test_zero_delta_no_change(self):
        prev = 0.5
        result = _integrate(prev, 0.0, -1.0, 1.0)
        self.assertAlmostEqual(result, prev, places=6)

    def test_diminishing_returns_near_boundary(self):
        # Delta of 1.0 from centre should move more than from near edge
        from_centre = _integrate(0.0, 1.0, -1.0, 1.0)
        from_edge   = _integrate(0.9, 1.0, -1.0, 1.0)
        self.assertGreater(from_centre - 0.0, from_edge - 0.9)

    def test_arousal_floor_recoverability(self):
        # Bug fix: arousal at near-zero must respond to positive delta.
        # Old symmetric form gave margin=0 at lower boundary → frozen.
        # New asymmetric form gives margin=(1-prev)≈1.0 → full movement.
        result = _integrate(0.01, 1.0, 0.0, 1.0)
        self.assertGreater(result, 0.01,
            "arousal at floor must increase on positive delta (recoverability fix)")

    def test_arousal_ceiling_resistance(self):
        # At ceiling, positive delta should produce no movement (margin=0)
        result = _integrate(1.0, 1.0, 0.0, 1.0)
        self.assertAlmostEqual(result, 1.0, places=6,
            msg="arousal at ceiling must not exceed 1.0 on positive delta")


# ── Decay ─────────────────────────────────────────────────────────────────────

class TestDecayApplied(unittest.TestCase):
    def test_valence_decays_toward_zero_with_zero_delta(self):
        node = _make_node()
        node._valence = 0.5
        node._arousal = 0.1
        node._stability = 0.9
        # Override all compute methods to return 0 delta / stable target
        with (
            patch.object(node, "_compute_valence_delta",  return_value=0.0),
            patch.object(node, "_compute_arousal_delta",  return_value=0.0),
            patch.object(node, "_compute_stability",      return_value=0.9),
        ):
            node._background_tick()
        self.assertLess(node._valence, 0.5)

    def test_arousal_decays_with_zero_delta(self):
        node = _make_node()
        node._valence = 0.0
        node._arousal = 0.5
        node._stability = 0.9
        with (
            patch.object(node, "_compute_valence_delta",  return_value=0.0),
            patch.object(node, "_compute_arousal_delta",  return_value=0.0),
            patch.object(node, "_compute_stability",      return_value=0.9),
        ):
            node._background_tick()
        self.assertLess(node._arousal, 0.5)


# ── Background tick writes row ────────────────────────────────────────────────

class TestTickWritesRow(unittest.TestCase):
    def test_background_tick_calls_write(self):
        node = _make_node()
        with (
            patch.object(node, "_compute_valence_delta",  return_value=0.1),
            patch.object(node, "_compute_arousal_delta",  return_value=0.05),
            patch.object(node, "_compute_stability",      return_value=0.8),
        ):
            node._background_tick()

        node._mock_cw.write.assert_called_once()
        call_args = node._mock_cw.write.call_args
        sql, params = call_args[0]
        self.assertIn("INSERT OR REPLACE INTO affect_state", sql)
        self.assertEqual(len(params), 5)  # valence, arousal, stability, mood_label, updated_at

    def test_tick_updates_in_memory_state(self):
        node = _make_node()
        node._valence = 0.0
        with (
            patch.object(node, "_compute_valence_delta",  return_value=0.5),
            patch.object(node, "_compute_arousal_delta",  return_value=0.0),
            patch.object(node, "_compute_stability",      return_value=0.9),
        ):
            node._background_tick()
        self.assertNotEqual(node._valence, 0.0)

    def test_tick_sets_mood_label_in_params(self):
        node = _make_node()
        node._valence = 0.5  # will yield positive after small decay
        with (
            patch.object(node, "_compute_valence_delta",  return_value=0.0),
            patch.object(node, "_compute_arousal_delta",  return_value=0.0),
            patch.object(node, "_compute_stability",      return_value=0.9),
        ):
            node._background_tick()
        sql, params = node._mock_cw.write.call_args[0]
        mood_in_params = params[3]
        self.assertIn(mood_in_params, ("positive", "negative", "neutral"))

    def test_tick_updated_at_is_recent(self):
        node = _make_node()
        before = time.time()
        with (
            patch.object(node, "_compute_valence_delta",  return_value=0.0),
            patch.object(node, "_compute_arousal_delta",  return_value=0.0),
            patch.object(node, "_compute_stability",      return_value=0.9),
        ):
            node._background_tick()
        after = time.time()
        sql, params = node._mock_cw.write.call_args[0]
        updated_at = params[4]
        self.assertGreaterEqual(updated_at, before)
        self.assertLessEqual(updated_at, after)


# ── format_for_prompt ─────────────────────────────────────────────────────────

class TestFormatForPrompt(unittest.TestCase):
    def test_returns_empty_when_no_row(self):
        node = _make_node(cr_row=None)
        node._mock_cr.read_one.return_value = None
        self.assertEqual(node.format_for_prompt(), "")

    def test_returns_formatted_string(self):
        row = _row(id=1, valence=0.35, arousal=0.2, stability=0.8,
                   mood_label="positive", updated_at=time.time())
        node = _make_node()
        node._mock_cr.read_one.return_value = row
        result = node.format_for_prompt()
        self.assertEqual(result, "Affective state: positive (valence 0.35)")

    def test_negative_valence_formatted(self):
        row = _row(id=1, valence=-0.42, arousal=0.3, stability=0.6,
                   mood_label="negative", updated_at=time.time())
        node = _make_node()
        node._mock_cr.read_one.return_value = row
        result = node.format_for_prompt()
        self.assertEqual(result, "Affective state: negative (valence -0.42)")

    def test_neutral_formatted(self):
        row = _row(id=1, valence=0.0, arousal=0.1, stability=0.9,
                   mood_label="neutral", updated_at=time.time())
        node = _make_node()
        node._mock_cr.read_one.return_value = row
        result = node.format_for_prompt()
        self.assertEqual(result, "Affective state: neutral (valence 0.00)")

    def test_exception_returns_empty(self):
        node = _make_node()
        node._mock_cr.read_one.side_effect = Exception("DB unavailable")
        self.assertEqual(node.format_for_prompt(), "")


# ── Coherence components ──────────────────────────────────────────────────────

class TestCoherenceComponents(unittest.TestCase):
    def _make_gate_rows(self, n_accept, n_reject):
        return (
            [{"outcome": "ACCEPT"}] * n_accept
            + [{"outcome": "REJECT"}] * n_reject
        )

    def _make_held_rows(self, n_resolved, n_holding):
        return (
            [{"status": "accepted"}] * n_resolved
            + [{"status": "holding"}] * n_holding
        )

    def test_all_accept_yields_higher_stability_than_all_reject(self):
        node_high = _make_node(br_gate_rows=self._make_gate_rows(20, 0))
        node_low  = _make_node(br_gate_rows=self._make_gate_rows(0, 20))
        high = node_high._compute_stability()
        low  = node_low._compute_stability()
        self.assertGreater(high, low)

    def test_all_resolved_held_yields_higher_stability(self):
        node_high = _make_node(br_held_rows=self._make_held_rows(20, 0))
        node_low  = _make_node(br_held_rows=self._make_held_rows(0, 20))
        high = node_high._compute_stability()
        low  = node_low._compute_stability()
        self.assertGreater(high, low)

    def test_stability_in_unit_range(self):
        node = _make_node(
            br_gate_rows=self._make_gate_rows(10, 10),
            br_held_rows=self._make_held_rows(5, 5),
        )
        s = node._compute_stability()
        self.assertGreaterEqual(s, 0.0)
        self.assertLessEqual(s, 1.0)

    def test_no_gate_data_defaults_stable(self):
        # Empty gate_rows → accept_rate defaults to 1.0 (no conflict observed)
        node = _make_node(br_gate_rows=[])
        s = node._compute_stability()
        self.assertGreater(s, 0.5)


# ── state() shape ─────────────────────────────────────────────────────────────

class TestStateShape(unittest.TestCase):
    def test_state_has_required_keys(self):
        node = _make_node()
        st = node.state()
        for key in ("valence", "arousal", "stability", "mood_label",
                    "last_updated", "components"):
            self.assertIn(key, st, f"missing key: {key}")

    def test_components_has_source_keys(self):
        node = _make_node()
        c = node.state()["components"]
        self.assertIn("arousal_src",   c)
        self.assertIn("valence_src",   c)
        self.assertIn("stability_src", c)

    def test_valence_in_bounds(self):
        node = _make_node()
        st = node.state()
        self.assertGreaterEqual(st["valence"], -1.0)
        self.assertLessEqual(st["valence"],     1.0)

    def test_arousal_in_bounds(self):
        node = _make_node()
        st = node.state()
        self.assertGreaterEqual(st["arousal"], 0.0)
        self.assertLessEqual(st["arousal"],    1.0)

    def test_stability_in_bounds(self):
        node = _make_node()
        st = node.state()
        self.assertGreaterEqual(st["stability"], 0.0)
        self.assertLessEqual(st["stability"],    1.0)

    def test_mood_label_one_of_three(self):
        node = _make_node()
        self.assertIn(node.state()["mood_label"], ("positive", "negative", "neutral"))


if __name__ == "__main__":
    unittest.main()
