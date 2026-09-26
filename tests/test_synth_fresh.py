"""Tests for NEX5_SYNTH_FRESH — the synergizer's fresh-side recency weight plus
the lineage-descendant penalty. Embeddings are faked (deterministic vectors) so
no model loads. Replay measurement: tools/synth_fresh_harness.py."""
from __future__ import annotations

import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

import numpy as np

from tests import _bootstrap  # noqa: F401

from substrate import Reader
from theory_x.diversity import embeddings as emb
from theory_x.stage3_world_model.synergizer import BeliefSynergizer as BS

_NOW = time.time()
_D = 86400


def _vec(angle_deg):
    a = np.deg2rad(angle_deg)
    v = np.zeros(384, dtype=np.float32)
    v[0], v[1] = np.cos(a), np.sin(a)
    return v


# anchor at 0 deg; fresh beliefs at increasing angles (smaller = closer)
_ANGLE = {1: 0, 10: 60, 11: 65, 12: 64}


def _db(path, rows, lineage=()):
    c = sqlite3.connect(path)
    c.executescript(
        "CREATE TABLE beliefs (id INTEGER PRIMARY KEY, content TEXT, branch_id TEXT, "
        " confidence REAL, created_at REAL, source TEXT, tags TEXT DEFAULT '[]');"
        "CREATE TABLE synergizer_log (id INTEGER PRIMARY KEY, ts REAL, belief_id_a INTEGER, "
        " belief_id_b INTEGER, result_content TEXT, result_belief_id INTEGER);"
        "CREATE TABLE belief_lineage (child_id INTEGER, parent_id INTEGER, relationship TEXT, "
        " weight REAL, created_at REAL);")
    c.executemany("INSERT INTO beliefs (id, content, branch_id, confidence, created_at, source) "
                  "VALUES (?,?,?,?,?,?)", rows)
    c.executemany("INSERT INTO belief_lineage VALUES (?,?,'synergy',1.0,?)",
                  [(ch, p, _NOW) for ch, p in lineage])
    c.commit(); c.close()


class TestSynthFresh(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "beliefs.db")
        self._orig = (emb.embed_belief, emb.distance)
        emb.embed_belief = lambda bid, content: _vec(_ANGLE[bid])
        self._env = os.environ.get("NEX5_SYNTH_FRESH")

    def tearDown(self):
        emb.embed_belief, emb.distance = self._orig
        if self._env is None:
            os.environ.pop("NEX5_SYNTH_FRESH", None)
        else:
            os.environ["NEX5_SYNTH_FRESH"] = self._env
        self.tmp.cleanup()

    def _pair(self, flag):
        if flag:
            os.environ["NEX5_SYNTH_FRESH"] = "1"
        else:
            os.environ.pop("NEX5_SYNTH_FRESH", None)
        a, b = BS(None, Reader(self.db), None)._select_pair()
        return a["id"], b["id"]

    def _rows(self, old_offspring_age_d=60, insight_age_d=0.5):
        return [
            (1, "a koan", None, 0.9, _NOW - 400 * _D, "koan"),
            # 10: the koan's own old offspring, CLOSEST to it
            (10, "old synthesis of the koan", "systems", 0.65, _NOW - old_offspring_age_d * _D, "synergized"),
            # 11: a recent fountain insight, a little further away
            (11, "a fresh fountain insight", "markets", 0.7, _NOW - insight_age_d * _D, "fountain_insight"),
        ]

    def test_off_keeps_todays_pick(self):
        _db(self.db, self._rows(), lineage=[(10, 1)])
        self.assertEqual(self._pair(False), (1, 10))    # closest wins, offspring and all

    def test_on_prefers_fresh_non_offspring(self):
        _db(self.db, self._rows(), lineage=[(10, 1)])
        self.assertEqual(self._pair(True), (1, 11))

    def test_descendant_penalty_is_transitive(self):
        rows = self._rows(old_offspring_age_d=0.2) + [
            (12, "mid synthesis", "systems", 0.65, _NOW - 500 * _D, "synergized")]
        # 10 descends from 12 which descends from koan 1 — still the koan's offspring
        _db(self.db, rows, lineage=[(10, 12), (12, 1)])
        self.assertEqual(self._pair(True), (1, 11))

    def test_old_material_is_not_excluded(self):
        # only old, non-offspring candidates: still picked (bias, not ban)
        rows = [(1, "a koan", None, 0.9, _NOW - 400 * _D, "koan"),
                (10, "an old synthesis", "systems", 0.65, _NOW - 300 * _D, "synergized")]
        _db(self.db, rows)
        self.assertEqual(self._pair(True), (1, 10))

    def test_fail_safe_to_todays_pick(self):
        _db(self.db, self._rows(), lineage=[(10, 1)])
        c = sqlite3.connect(self.db); c.execute("DROP TABLE belief_lineage"); c.commit(); c.close()
        self.assertEqual(self._pair(True), self._pair(False))

    def test_fresh_weight_bounds(self):
        self.assertAlmostEqual(BS.fresh_weight(_NOW, _NOW), 1.0)
        self.assertAlmostEqual(BS.fresh_weight(_NOW - 3650 * _D, _NOW), BS._FRESH_FLOOR, places=6)
        self.assertGreater(BS.fresh_weight(_NOW - 1 * _D, _NOW), BS.fresh_weight(_NOW - 9 * _D, _NOW))


if __name__ == "__main__":
    unittest.main()
