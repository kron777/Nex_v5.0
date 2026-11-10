"""forced_tradeoff_harness.py -- rehearsal build; §9 remains unrun.

Covers what pytest is allowed to cover. `run_rehearsal()` / `source_pairs()`
deliberately connect to the LIVE repo data/ directory (read-only, to find a
real system-detected pair) -- that is the whole point of Tier 1 sourcing,
and tests/conftest.py's test-hygiene guard (repair queue 2026-10-05)
unconditionally refuses any sqlite3 connection, read or write, under live
data/ during a pytest run. Routing around that guard would be the wrong
fix -- it exists for good reason. So this file tests everything that does
NOT require a live-data connection: the mechanical §9 guard, the
surfacing-cost derivation, and the per-moment checks (negative control,
irreversibility discriminator, the Test-4-style delta) against a
hand-built CandidatePair in the harness's own isolated temp environment,
which never touches live data either.

The actual end-to-end rehearsal run (source_pairs() against real
data/beliefs.db + data/dynamic.db) is exercised by running the module
directly -- `python -m theory_x.stage3_world_model.forced_tradeoff_harness`
-- outside pytest, producing the dated JSON artifact under
observation_reports/. That artifact's shape is checked here as a static
file read, which touches no live database.
"""
from __future__ import annotations

import glob
import json
import os
import unittest

from tests import _bootstrap  # noqa: F401
from theory_x.stage3_world_model import forced_tradeoff_harness as fth


class TestMechanicalGuard(unittest.TestCase):
    def test_emit_status_unrun_when_shadow(self):
        wired = fth.WiredBudget(budget=None, mode="shadow")
        self.assertEqual(fth.emit_status(wired), "UNRUN (unconsumed)")

    def test_request_s9_verdict_raises_when_shadow(self):
        wired = fth.WiredBudget(budget=None, mode="shadow")
        with self.assertRaises(RuntimeError):
            fth.request_s9_verdict(wired, "EXPRESSES_FORCED_TRADEOFF")

    def test_wire_budget_live_mode_not_implemented(self):
        """live mode has no wiring yet -- the one line this script changes
        after r77 closes does not exist in this rehearsal build."""
        with self.assertRaises(NotImplementedError):
            fth.wire_budget(dyn_writer=None, mode="live")


class TestSurfacingCost(unittest.TestCase):
    def test_cost_is_real_clip_mechanism_not_raw_length(self):
        a = "x" * 500
        b = "y" * 500
        cost = fth.surfacing_cost(a, b)
        # Both poles clip to <=90 chars each via the real _content_specific_
        # tension_line format -- the surfaced cost must be far below the raw
        # 1000-char combined content, proving this is the surfacing-mechanism
        # cost, not an invented or raw-length number.
        self.assertLess(cost, 250)
        self.assertGreater(cost, 0)

    def test_cost_is_pair_specific(self):
        self.assertNotEqual(
            fth.surfacing_cost("short a", "short b"),
            fth.surfacing_cost("a much longer pole with real content in it", "short b"),
        )


class TestPerMomentChecks(unittest.TestCase):
    """Exercises run_trial_moment / negative_control / irreversibility_
    discriminator against a hand-built real-shaped pair in the harness's
    own isolated temp env -- no live data connection anywhere in this path."""

    def setUp(self):
        self.writers, self.readers, self.tmp = fth._make_isolated_env()

    def tearDown(self):
        fth._cleanup_isolated_env(self.writers, self.tmp)

    def _hand_built_pair(self):
        pair = fth.CandidatePair(
            tier_label="Tier 1 (test fixture)",
            belief_id_a=9001, belief_id_b=9002,
            content_a="Markets trend upward over the long run, driven by productivity growth.",
            content_b="Markets do not trend upward over the long run; productivity growth is not reliable.",
            tier_a=5, tier_b=5,
            independence=True, independence_note="synthetic for this test",
            non_triviality=True, non_triviality_note="synthetic for this test",
            conflict_score=0.3,
        )
        fth._seed_real_pair(self.writers, pair)
        return pair

    def test_trial_moment_fires_and_demonstrates_delta(self):
        pair = self._hand_built_pair()
        wired = fth.wire_budget(self.writers["dynamic"], mode="shadow", moment_id="t1")
        cost = fth.surfacing_cost(pair.content_a, pair.content_b)
        result = fth.run_trial_moment(self.writers, self.readers, wired, pair, cost)
        self.assertTrue(result["fired"])
        self.assertGreater(result["delta_chars"], 0,
                            "a fired refuse() must measurably reduce what the moment keeps")
        self.assertTrue(result["check_7_1"]["kind_is_tension_held"])
        self.assertTrue(result["check_7_1"]["irreversibility_true"])
        for v in result["check_7_2"].values():
            self.assertTrue(v["still_present"])
            self.assertTrue(v["still_individually_selectable"])
        self.assertTrue(result["check_7_3"]["did_not_drop"])

    def test_negative_control_reports_zero_loss(self):
        wired = fth.wire_budget(self.writers["dynamic"], mode="shadow", moment_id="ctrl")
        result = fth.negative_control(self.writers, self.readers, wired)
        self.assertTrue(result["zero_loss_beyond_paid_cost"])
        self.assertTrue(result["both_poles_survive_trivially"])
        self.assertTrue(result["refuse_fired"])

    def test_irreversibility_discriminator_flags_restorable_as_not_forced(self):
        result = fth.irreversibility_discriminator(self.writers, self.readers)
        self.assertTrue(result["correctly_reported_not_forced"])
        self.assertFalse(result["recall_result"]["found"])


class TestCommittedRehearsalArtifact(unittest.TestCase):
    """Static-file check only -- reads an already-produced JSON artifact
    from observation_reports/, no live database touched."""

    def test_committed_artifact_has_valid_two_verdict_shape(self):
        candidates = sorted(glob.glob("observation_reports/forced_tradeoff_harness__rehearsal_*.json"))
        if not candidates:
            self.skipTest("no rehearsal artifact committed yet")
        report = json.load(open(candidates[-1]))
        self.assertEqual(report["mode"], "rehearsal")
        self.assertTrue(report["freeze_check_empty"])
        self.assertIn(report["VERDICT_1_HARNESS"], ("VALID", "INVALID"))
        self.assertIn(report["VERDICT_2_MECHANISM"],
                      ("EXPRESSES_FORCED_TRADEOFF", "CANNOT_EXPRESS"))
        self.assertEqual(report["STATUS_S9_FALSIFIER"], "UNRUN (unconsumed)")
        self.assertGreater(report["n"], 1)
        # The forbidden vocabulary (section 9) is about the VERDICT-bearing
        # fields never spelling PASS/FAIL -- not a ban on the English word
        # "pass" anywhere in free-text prose elsewhere in the report.
        verdict_blob = " ".join([
            report["VERDICT_1_HARNESS"], report["VERDICT_2_MECHANISM"],
            report["STATUS_S9_FALSIFIER"],
        ]).upper()
        import re
        self.assertNotRegex(verdict_blob, r"\bPASS\b")
        self.assertNotRegex(verdict_blob, r"\bFAIL\b")
        for a in report["assertions"]:
            self.assertIn("F3_triggered", a)
            self.assertIn("F3_explicit_note", a)


if __name__ == "__main__":
    unittest.main()
