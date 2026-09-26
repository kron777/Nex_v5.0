"""Tests for NEX5_SYNTH_FRESH_SIBLING — the synergizer's per-generation penalty
on recent synthesis-of-synthesis fresh beliefs (any anchor's, not just the
current one's). Fake embeddings, fixture db. Replay: tools/synth_fresh_harness.py --sibling."""
from __future__ import annotations

import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401
from tests.test_synth_fresh import _db, _vec, _NOW, _D

from substrate import Reader
from theory_x.diversity import embeddings as emb
from theory_x.stage3_world_model.synergizer import BeliefSynergizer as BS

_H = 3600
# anchor 1 at 0 deg; the other koans (2, 3) sit opposite so they never win.
# 22: g=2 synthesis (of koan 3 + recent synthesis 21), CLOSEST to anchor 1.
# 23: g=3 (of 3 + 22). 11: a recent fountain insight, a little further.
# 21: g=1 synthesis (of koan 2 + an old insight 30). 20: old synthesis.
_ANGLE = {1: 0, 2: 180, 3: 175, 22: 60, 23: 62, 11: 64, 21: 70, 20: 80, 30: 100}
_ROWS = [
    (1, "koan one", None, 0.9, _NOW - 400 * _D, "koan"),
    (2, "koan two", None, 0.9, _NOW - 400 * _D, "koan"),
    (3, "koan three", None, 0.9, _NOW - 400 * _D, "koan"),
    (30, "old insight", "markets", 0.7, _NOW - 90 * _D, "fountain_insight"),
    (20, "old synthesis", "systems", 0.65, _NOW - 60 * _D, "synergized"),
    (21, "gen-1 synthesis", "systems", 0.65, _NOW - 3 * _H, "synergized"),
    (22, "gen-2 synthesis", "systems", 0.65, _NOW - 2 * _H, "synergized"),
    (23, "gen-3 synthesis", "systems", 0.65, _NOW - 1 * _H, "synergized"),
    (11, "a fresh fountain insight", "markets", 0.7, _NOW - 5 * _H, "fountain_insight"),
]
_LINEAGE = [(20, 2), (21, 2), (21, 30), (22, 3), (22, 21), (23, 3), (23, 22)]
_FLAGS = ("NEX5_SYNTH_FRESH", "NEX5_SYNTH_FRESH_SIBLING")


class TestSynthSibling(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "beliefs.db")
        self._orig = emb.embed_belief
        emb.embed_belief = lambda bid, content: _vec(_ANGLE[bid])
        self._env = {k: os.environ.get(k) for k in _FLAGS}

    def tearDown(self):
        emb.embed_belief = self._orig
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.tmp.cleanup()

    def _pair(self, fresh=True, sibling=False):
        for k, on in zip(_FLAGS, (fresh, sibling)):
            if on:
                os.environ[k] = "1"
            else:
                os.environ.pop(k, None)
        a, b = BS(None, Reader(self.db), None)._select_pair()
        return a["id"], b["id"]

    def test_generations(self):
        _db(self.db, _ROWS, _LINEAGE)
        g = BS(None, Reader(self.db), None)._synth_generations([20, 21, 22, 23, 11], _NOW)
        self.assertEqual(g, {22: 2, 23: 3})           # g=1 and old/non-synthesis omitted

    def test_weight_compounds(self):
        self.assertEqual([BS.sibling_weight(g) for g in (1, 2, 3)], [1.0, 0.5, 0.25])

    def test_off_is_todays_synth_fresh_pick(self):
        _db(self.db, _ROWS, _LINEAGE)
        self.assertEqual(self._pair(sibling=False), (1, 22))   # the chain slips through today

    def test_on_skips_the_chain(self):
        _db(self.db, _ROWS, _LINEAGE)
        self.assertEqual(self._pair(sibling=True), (1, 11))

    def test_independent_of_synth_fresh(self):
        _db(self.db, _ROWS, _LINEAGE)
        self.assertEqual(self._pair(fresh=False, sibling=True), (1, 11))

    def test_window_breaks_chain(self):
        rows = [r if r[0] != 21 else (21, r[1], r[2], r[3], _NOW - 3 * _D, r[5]) for r in _ROWS]
        _db(self.db, rows, _LINEAGE)
        g = BS(None, Reader(self.db), None)._synth_generations([21, 22, 23], _NOW)
        self.assertEqual(g, {23: 2})                   # 22 is now gen-1: its parent is >48h old

    def test_fail_safe(self):
        _db(self.db, _ROWS, _LINEAGE)
        c = sqlite3.connect(self.db); c.execute("DROP TABLE belief_lineage"); c.commit(); c.close()
        self.assertEqual(self._pair(fresh=False, sibling=True), self._pair(fresh=False, sibling=False))


if __name__ == "__main__":
    unittest.main()
