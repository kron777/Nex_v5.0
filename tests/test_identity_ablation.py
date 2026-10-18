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
        IA._flip.update({"current": None, "flips": 0, "prev_stamp_arm": "normal"})

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

    def test_reframe_same_statement_neutral_header_length_matched(self):
        normal = IA.block_for(_STMT, _MIN, "normal")
        rf = IA.block_for(_STMT, _MIN, "reframe")
        self.assertIn(_STMT, rf)                       # SAME statement (the point)
        self.assertNotIn("who you said you are", rf)   # identity CLAIM removed
        self.assertEqual(len(rf), len(normal))         # length held -> only claim varies

    def test_filler_absent_info_and_framing_length_matched(self):
        normal = IA.block_for(_STMT, _MIN, "normal")
        c = IA.block_for(_STMT, _MIN, "filler")
        self.assertEqual(len(c), len(normal))
        self.assertNotIn(_STMT, c)                     # content absent
        self.assertNotIn("who you said you are", c)    # framing absent (block absent, not just content)
        self.assertNotIn("curious", c)

    def test_filler_is_non_instructional_and_shared(self):
        # Verify item: filler must be non-instructional (it sits after the statement in
        # prompt position 3) and the SAME string padding arm B and filling arm C.
        f = IA._FILLER_UNIT.lower()
        self.assertNotIn("you", f)                      # no second person
        for bad in ("continue", "respond", "write", "describe", "you are", "remember",
                    "imagine", "pretend", "note that", "please"):
            self.assertNotIn(bad, f)                    # no imperative / self-reference
        # arm B's pad region and arm C both draw from the same _FILLER_UNIT
        rf = IA.block_for(_STMT, _MIN, "reframe")
        c = IA.block_for(_STMT, _MIN, "filler")
        self.assertTrue(rf.endswith(IA._FILLER_UNIT[:5]) or IA._FILLER_UNIT[:5] in rf)
        self.assertTrue(c.startswith(IA._FILLER_UNIT[:5]))

    def test_flip_stamp_three_fields(self):
        # Q11: arm / arm_prev / flips, reset per stamp. Primary analysis filters flips==0.
        self._set("normal"); IA.current_condition()
        s0 = IA.stamp_fields()
        self.assertEqual((s0["arm"], s0["arm_prev"], s0["flips"]), ("normal", "normal", 0))
        self._set("reframe"); IA.current_condition()
        self._set("filler"); IA.current_condition()
        s1 = IA.stamp_fields()
        self.assertEqual(s1["arm"], "filler")
        self.assertEqual(s1["arm_prev"], "normal")      # arm at the previous stamp
        self.assertEqual(s1["flips"], 2)                # normal->reframe->filler
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
