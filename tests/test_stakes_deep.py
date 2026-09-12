"""Tests for _stakes_pick (NEX5_STAKES_DEEP) — situated drive-pull on selection.

A genuinely-held emergent drive should PULL what she engages this fire — toward a
candidate that resonates with the drive's genuine content — while staying
situated (this fire's items only), register/groove-guarded, and fail-safe. It
must measurably shift selection vs the off-state, and must NOT pull toward
register/frame vocabulary or a groove (the design guard: a felt pull, not a
global optimiser, and never an amplifier of her own voice).

Isolated tempdir DBs (NEX5_DATA_DIR) — never the live soak DBs.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest

from tests import _bootstrap  # noqa: F401

_ITEMS = [
    "Sourdough hydration ratios and crumb structure",
    "Quantum entanglement research at the new collider facility",
    "Local council parking policy update",
]


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_stakes_")
    os.environ["NEX5_DATA_DIR"] = tmp
    from substrate.init_db import init_all
    init_all()
    from substrate import Writer, db_paths
    return tmp, Writer(db_paths()["conversations"], name="conversations"), \
        Writer(db_paths()["beliefs"], name="beliefs")


def _cleanup(tmp, *writers):
    for w in writers:
        try:
            w.close()
        except Exception:
            pass
    shutil.rmtree(tmp, ignore_errors=True)
    os.environ.pop("NEX5_DATA_DIR", None)


class TestStakesPick(unittest.TestCase):

    def setUp(self):
        self.tmp, self.cw, self.bw = _make_env()

    def tearDown(self):
        _cleanup(self.tmp, self.cw, self.bw)

    def _set_drive(self, topic, strength):
        self.cw.write(
            "INSERT OR REPLACE INTO drives "
            "(id, topic, source_beliefs, drive_strength, repetition_score, "
            " convergence_score, formed_at, last_reinforced_at) "
            "VALUES (1, ?, '[]', ?, 1.0, 0.5, ?, ?)",
            (topic, strength, time.time(), time.time()),
        )
        time.sleep(0.03)

    def _pick(self):
        from theory_x.stage6_fountain.generator import _stakes_pick
        return _stakes_pick(list(_ITEMS))

    # --- the drive BITES: a held content drive pulls the resonant item ---
    def test_held_content_drive_pulls_resonant_item(self):
        self._set_drive("quantum entanglement collider physics", strength=3.0)
        self.assertEqual(self._pick(), _ITEMS[1])  # the quantum item, deterministically

    def test_measurably_shifts_vs_offstate(self):
        # off-state = uniform over 3 items: the resonant one is not guaranteed.
        # stakes: with the drive held, the resonant item is picked every time.
        self._set_drive("quantum entanglement collider physics", strength=3.0)
        picks = {self._pick() for _ in range(20)}
        self.assertEqual(picks, {_ITEMS[1]})  # deterministic pull, not 1-in-3

    # --- guards: it must NOT fire on junk/weak/absent drives ---
    def test_no_drive_returns_none(self):
        self.assertIsNone(self._pick())

    def test_weak_drive_defers(self):
        self._set_drive("quantum entanglement collider physics", strength=0.30)  # < 0.6 floor
        self.assertIsNone(self._pick())

    def test_register_only_drive_defers(self):
        # the live failure mode: drive converged on frame vocabulary ('item aligns')
        self._set_drive("clear impactful messages item aligns discusses", strength=3.0)
        self.assertIsNone(self._pick())

    def test_no_resonant_candidate_defers(self):
        self._set_drive("volcanology basalt magma chambers", strength=3.0)  # matches no item
        self.assertIsNone(self._pick())

    def test_groove_flagged_content_is_stripped(self):
        # if the drive's only content token is under active convergence, don't
        # amplify it -> defer. Build a corpus where 'quantum' dominates maxDF*.
        for i in range(40):
            self.bw.write(
                "INSERT INTO beliefs (content, tier, confidence, created_at, source, branch_id, locked) "
                "VALUES (?, 6, 0.6, ?, 'fountain_insight', 'x', 0)",
                (f"quantum quantum dominates belief number {i}", time.time() - i),
            )
            time.sleep(0.003)
        self._set_drive("quantum", strength=3.0)
        # 'quantum' is groove-flagged -> stripped -> no genuine content -> defer
        self.assertIsNone(self._pick())


if __name__ == "__main__":
    unittest.main()
