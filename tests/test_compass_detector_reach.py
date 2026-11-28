"""Characterize what the compass reads when only NEX5_COMPASS is armed (G-95).

The detectors' own prompt surfaces are flag-gated: amoha_detector.format_for_prompt()
by NEX5_AMOHA, self_binding.afflictions_for_prompt() by NEX5_AFFLICTIONS. The
compass does not go through those surfaces. compass.weigh() calls
amoha_detector.detect() and self_binding._cluster_reads() -- which calls all five
affliction detectors -- without checking either flag. gui/server.py's chat
handler calls compass.stance_for() on admin turns whenever NEX5_COMPASS=1.

Pinned here, with the detectors stubbed (no database, no embedding model):

- weigh() invokes all six detectors with NEX5_AMOHA and NEX5_AFFLICTIONS unset;
- a high read from one of them (mana) reaches the compass stance text;
- the detectors' own flag-gated prompt surfaces stay silent meanwhile.

This is a characterization of current behaviour, not a policy. The reach is
deliberate -- the commits that disarmed NEX5_AFFLICTIONS (b941c796) and NEX5_AMOHA
(280125c3) both state that the compass keeps reading these detectors directly --
and this pins it so the mind map and the faculty flags can be read against it.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tests import _bootstrap  # noqa: F401

_DETECTORS = ("raga", "dvesa", "mana", "avidya", "moha", "amoha")
_QUIET = {"raga": "free", "dvesa": "calm", "mana": "grounded",
          "avidya": "seeing", "moha": "coherent", "amoha": "clear"}
_GATES = ("NEX5_AMOHA", "NEX5_AFFLICTIONS", "NEX5_COMPASSION")
_MESSAGE = "is it right to keep this from them"


class TestCompassReachesDetectors(unittest.TestCase):
    def setUp(self):
        self._saved = {k: os.environ.pop(k) for k in _GATES if k in os.environ}
        self.calls = []
        self._patches = [
            mock.patch("theory_x.stage_affect.compass.moral_weight", return_value=0.0),
            mock.patch("theory_x.stage_affect.compassion._distress_read",
                       return_value=(0.0, "acute")),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        os.environ.update(self._saved)

    def _stub(self, name, state):
        def detect():
            self.calls.append(name)
            return {"state": state}
        return mock.patch(f"theory_x.stage_tom.{name}_detector.detect", detect)

    def _weigh_with(self, states):
        from theory_x.stage_affect import compass
        patches = [self._stub(n, states[n]) for n in _DETECTORS]
        for p in patches:
            p.start()
        try:
            return compass.weigh(_MESSAGE)
        finally:
            for p in patches:
                p.stop()

    def test_weigh_calls_every_detector_with_their_own_flags_unset(self):
        for gate in _GATES:
            self.assertNotIn(gate, os.environ)
        reads = self._weigh_with(_QUIET)
        self.assertEqual(sorted(self.calls), sorted(_DETECTORS))
        self.assertEqual(reads["clarity"], "clear")
        self.assertEqual(reads["distortions"], [])

    def test_a_high_mana_read_reaches_the_stance(self):
        from theory_x.stage_affect import compass
        reads = self._weigh_with(dict(_QUIET, mana="inflated"))
        self.assertEqual(reads["distortions"], ["mana"])
        stance = compass.format_stance(reads)
        self.assertIn("mana", stance)

    def test_the_detectors_own_prompt_surfaces_stay_gated(self):
        from theory_x.stage_tom import amoha_detector, self_binding
        with self._stub("mana", "inflated"), self._stub("amoha", "clouded"):
            self.assertEqual(self_binding.afflictions_for_prompt(), "")
            self.assertEqual(amoha_detector.format_for_prompt(), "")
        self.assertEqual(self.calls, [])   # the gated surfaces never read


if __name__ == "__main__":
    unittest.main()
