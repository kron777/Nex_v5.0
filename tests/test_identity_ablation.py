"""Identity-block ablation (self-as-cause experiment, step 1).

A=normal / B=reframe (same statement, neutral header) / C=filler. File-based condition
(no restart), length-matched, idempotent normal, fail-safe DEFAULTS TO CONTROL.
"""
import json
import logging
import os
import tempfile
import time
import unittest
from unittest import mock

from tests import _bootstrap  # noqa: F401

from theory_x.stage_tom import identity_ablation as IA

_STMT = "I am curious and restless about mathematics."
_MIN = 5


class TestIdentityAblation(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._tmp.name, "identity_ablation.json")
        self._patch = mock.patch.object(IA, "_condition_path", lambda: self.path)
        self._patch.start()
        IA._cache.update({"mtime": None, "mode": "normal", "logged": None})
        IA._gate_warned.clear()
        IA._flip.update({"current": None, "flips": 0, "prev_stamp_arm": "normal",
                         "first_stamp": True})

    def tearDown(self):
        self._patch.stop()
        self._tmp.cleanup()

    def _set(self, mode):
        with open(self.path, "w") as fh:
            fh.write(json.dumps({"mode": mode}))
        os.utime(self.path, (time.time() + 1, time.time() + 1))

    # ---- block_for modes --------------------------------------------------
    def test_normal_is_original_block(self):
        self.assertEqual(IA.block_for(_STMT, _MIN, "normal"),
                         f"This is who you said you are ({_MIN} min ago):\n  {_STMT}")

    def test_reframe_token_parity_exact(self):
        # CRIT-3: the length control IS arm B's whole point, and the budget the model
        # sees is TOKENS -> assert EXACT token-count parity (the real control).
        normal = IA.block_for(_STMT, _MIN, "normal")
        rf = IA.block_for(_STMT, _MIN, "reframe")
        self.assertIn(_STMT, rf)                               # SAME statement
        self.assertNotIn("who you said you are", rf)           # identity CLAIM removed
        self.assertEqual(len(rf.split()), len(normal.split())) # EXACT token parity

    def test_filler_token_parity_exact_and_absent(self):
        normal = IA.block_for(_STMT, _MIN, "normal")
        c = IA.block_for(_STMT, _MIN, "filler")
        self.assertEqual(len(c.split()), len(normal.split()))  # EXACT token parity
        self.assertNotIn(_STMT, c)                             # content absent
        self.assertNotIn("who you said you are", c)            # framing absent
        self.assertNotIn("curious", c)

    def test_filler_non_instructional_inert_and_shared(self):
        # Verify item + MINOR-2: filler must be non-instructional AND semantically inert
        # (no concrete nouns / spatial / sensory anchors -- else it reads as world-state,
        # not padding), and the SAME string for arm B's pad and arm C.
        f = IA._FILLER_UNIT.lower()
        self.assertNotIn("you", f)
        for bad in ("continue", "respond", "write", "describe", "remember", "imagine",
                    "pretend", "please"):
            self.assertNotIn(bad, f)                    # non-instructional
        for concrete in ("wall", "light", "fan", "dust", "room", "sill", "afternoon",
                          "hum", "window", "floor", "sound", "colour", "color"):
            self.assertNotIn(concrete, f)               # inert: no concrete/sensory/spatial
        # same filler words drive arm B's pad and arm C
        first = IA._FILLER_WORDS[0]
        c = IA.block_for(_STMT, _MIN, "filler")
        self.assertIn(first, c)
        rf = IA.block_for(_STMT, _MIN, "reframe")
        self.assertIn(first, rf)                         # B is padded from the same filler
        self.assertIn("\n\n", rf)                        # ...delimited into its own paragraph

    def test_join_rule_picks_strictly_earlier_row(self):
        # CRIT-1: outcome attributed to the identity_log row with greatest composed_at
        # STRICTLY LESS THAN the outcome ts; a tie is excluded.
        rows = [{"composed_at": 100.0, "ablation_arm": "normal"},
                {"composed_at": 101.0, "ablation_arm": "reframe"}]  # 1s apart
        # outcome after both -> the later (the arm that ACTED)
        self.assertEqual(IA.arm_for_outcome(rows, 101.5)["ablation_arm"], "reframe")
        # outcome between -> the earlier
        self.assertEqual(IA.arm_for_outcome(rows, 100.5)["ablation_arm"], "normal")
        # tie with the later row -> that row excluded (strictly-less-than), earlier wins
        self.assertEqual(IA.arm_for_outcome(rows, 101.0)["ablation_arm"], "normal")
        # no row strictly earlier -> excluded (None)
        self.assertIsNone(IA.arm_for_outcome(rows, 100.0))

    def test_flip_stamp_three_fields_with_restart_sentinel(self):
        # Q11 + CRIT-2: first stamp after process start -> flips=-1 (UNKNOWN), never a
        # fabricated flips=0; subsequent stamps carry real counts and reset per stamp.
        self._set("normal"); IA.current_condition()
        s0 = IA.stamp_fields()
        self.assertEqual((s0["arm"], s0["arm_prev"], s0["flips"]), ("normal", "normal", -1))
        self._set("reframe"); IA.current_condition()
        self._set("filler"); IA.current_condition()
        s1 = IA.stamp_fields()
        self.assertEqual(s1["arm"], "filler")
        self.assertEqual(s1["arm_prev"], "normal")      # arm at the previous stamp
        self.assertEqual(s1["flips"], 2)                # normal->reframe->filler, real count
        s2 = IA.stamp_fields()
        self.assertEqual(s2["flips"], 0)                # counter reset after stamp
        self.assertEqual(s2["arm_prev"], "filler")

    # ---- file-based condition --------------------------------------------
    def test_file_change_without_restart(self):
        self.assertEqual(IA.current_condition(), "normal")
        self._set("reframe"); self.assertEqual(IA.current_condition(), "reframe")
        self._set("filler"); self.assertEqual(IA.current_condition(), "filler")

    def test_bad_mode_falls_back_to_normal(self):
        self._set("garbage")
        self.assertEqual(IA.current_condition(), "normal")

    # ---- append_block + fail-safe (SEV-2) --------------------------------
    def test_append_normal_is_three_part_control(self):
        self._set("normal")
        parts = []
        arm = IA.append_block(parts, _STMT, _MIN)
        self.assertEqual(arm, "normal")
        self.assertEqual(parts, [f"This is who you said you are ({_MIN} min ago):",
                                 f"  {_STMT}", ""])

    def test_failsafe_defaults_to_control_and_warns_once(self):
        # SEV-2: a gate error must emit CONTROL (arm A), never a silent treatment.
        self._set("reframe")
        buf = io_capture(IA.logger)
        with mock.patch.object(IA, "current_condition", side_effect=RuntimeError("boom")):
            parts1, parts2 = [], []
            arm1 = IA.append_block(parts1, _STMT, _MIN)
            arm2 = IA.append_block(parts2, _STMT, _MIN)
        self.assertEqual(arm1, "normal")               # defaulted to control
        self.assertEqual(parts1, [f"This is who you said you are ({_MIN} min ago):",
                                  f"  {_STMT}", ""])
        self.assertEqual(buf.getvalue().count("defaulting to CONTROL"), 1)  # once, de-duped


def io_capture(logger):
    import io
    buf = io.StringIO()
    h = logging.StreamHandler(buf)
    h.setLevel(logging.WARNING)
    logger.addHandler(h)
    logger.setLevel(logging.WARNING)
    return buf


if __name__ == "__main__":
    unittest.main()
