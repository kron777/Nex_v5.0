"""Identity-block ablation (self-as-cause experiment, step 1).

File-based condition (no restart), drop=filler (length held), idempotent normal,
fail-safe. Identity is NOT exempt -- it is the thing under test.
"""
import json
import os
import tempfile
import time
import unittest
from unittest import mock

from tests import _bootstrap  # noqa: F401

from theory_x.stage_tom import identity_ablation as IA

_BLOCK = "This is who you said you are (5 min ago):\n  I am curious and restless.\n"


class TestIdentityAblation(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._tmp.name, "identity_ablation.json")
        self._patch = mock.patch.object(IA, "_condition_path", lambda: self.path)
        self._patch.start()
        IA._cache.update({"mtime": None, "mode": "normal", "logged": None})

    def tearDown(self):
        self._patch.stop()
        self._tmp.cleanup()

    def _set(self, mode):
        with open(self.path, "w") as fh:
            fh.write(json.dumps({"mode": mode}))
        # ensure a distinct mtime so the cache re-reads
        os.utime(self.path, (time.time() + 1, time.time() + 1))

    def test_default_normal_no_file(self):
        self.assertEqual(IA.current_condition(), "normal")
        self.assertEqual(IA.apply_to_identity_block(_BLOCK), _BLOCK)  # idempotent

    def test_drop_is_length_matched_filler(self):
        self._set("drop")
        self.assertEqual(IA.current_condition(), "drop")
        out = IA.apply_to_identity_block(_BLOCK)
        self.assertEqual(len(out), len(_BLOCK))          # length held (budget/length control)
        self.assertNotIn("curious", out)                 # identity content gone
        self.assertNotIn("who you said you are", out)

    def test_swap_uses_substitute_length_matched(self):
        self._set("swap")
        sub = "The lattice of prime gaps resists every closed form so far in analysis."
        out = IA.apply_to_identity_block(_BLOCK, substitute=sub)
        self.assertEqual(len(out), len(_BLOCK))
        self.assertIn("lattice", out)                     # substitute content present
        self.assertNotIn("curious", out)

    def test_file_change_is_picked_up_without_restart(self):
        self.assertEqual(IA.current_condition(), "normal")
        self._set("drop")
        self.assertEqual(IA.current_condition(), "drop")   # re-read on mtime change
        self._set("normal")
        self.assertEqual(IA.current_condition(), "normal")

    def test_bad_mode_falls_back_to_normal(self):
        self._set("garbage")
        self.assertEqual(IA.current_condition(), "normal")
        self.assertEqual(IA.apply_to_identity_block(_BLOCK), _BLOCK)


if __name__ == "__main__":
    unittest.main()
