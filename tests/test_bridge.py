"""Tests for NEX5_BRIDGE — the synergizer's bridging drive. Hermetic: fixture
beliefs/dynamic/conversations dbs, fake embeddings. Replay measurement:
tools/synth_fresh_harness.py --bridge."""
from __future__ import annotations

import json
import os
import re
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


# anchor 1 (systems). 10: systems fresh, closest. 11: markets (active) fresh, a bit further.
# 12: markets fresh but a lineage child of 1 (linked). 13: psychology (inactive).
# 14: markets fresh, linked by a synthesises edge to 12 (in 1's region).
_ANGLE = {1: 0, 10: 60, 11: 64, 12: 62, 13: 61, 14: 61.5, 15: 63}   # 15: synergized, would out-bridge 11 if eligible


class _Fixture:
    def __init__(self, tmp, drive=(0.2, 0.2), cooldown=None, fires=None):
        self.bdb = str(Path(tmp) / "beliefs.db")
        self.ddb = str(Path(tmp) / "dynamic.db")
        self.cdb = str(Path(tmp) / "conversations.db")
        b = sqlite3.connect(self.bdb)
        b.executescript(
            "CREATE TABLE beliefs (id INTEGER PRIMARY KEY, content TEXT, branch_id TEXT, "
            " confidence REAL, created_at REAL, source TEXT, tags TEXT DEFAULT '[]');"
            "CREATE TABLE synergizer_log (id INTEGER PRIMARY KEY, ts REAL, belief_id_a INTEGER, "
            " belief_id_b INTEGER, result_content TEXT, result_belief_id INTEGER);"
            "CREATE TABLE belief_lineage (child_id INTEGER, parent_id INTEGER, relationship TEXT, "
            " weight REAL, created_at REAL);"
            "CREATE TABLE belief_edges (id INTEGER PRIMARY KEY, source_id INTEGER, target_id INTEGER, "
            " edge_type TEXT, weight REAL, created_at REAL);"
            "CREATE TABLE signal_cooldown (content_hash TEXT PRIMARY KEY, content TEXT, "
            " cooldown_until REAL, reason TEXT, created_at REAL);")
        rows = [(1, "a koan about the empty cup", "systems", 0.9, _NOW - 400 * _D, "koan"),
                (10, "systems synthesis on attention loops", "systems", 0.65, _NOW - 2 * _D, "synergized"),
                (11, "markets insight on liquidity cascades", "markets", 0.7, _NOW - 2 * _D, "fountain_insight"),
                (12, "markets child of the koan on liquidity", "markets", 0.65, _NOW - 2 * _D, "synergized"),
                (13, "psychology note on habit formation", "psychology", 0.7, _NOW - 2 * _D, "fountain_insight"),
                (14, "markets insight on order books", "markets", 0.7, _NOW - 2 * _D, "fountain_insight"),
                (15, "markets synthesis on spreads widening", "markets", 0.7, _NOW - 2 * _D, "synergized")]
        # maxDF* window filler: 50 older crystallized beliefs with unique words, so
        # the fixture tokens are not "grooving" by small-corpus arithmetic. Their
        # confidence (0.4) keeps them out of the synergizer's candidate set.
        def _word(i):
            w = ""
            for _ in range(3):
                w += "bcdfghjklmnpqrstvwz"[i % 19]; i //= 19
            return "zq" + w + "ville"
        rows += [(100 + i, f"{_word(i)} {_word(i + 500)} {_word(i + 1000)}", "history", 0.4,
                  _NOW - (30 + i) * _D, "fountain_insight") for i in range(50)]
        b.executemany("INSERT INTO beliefs (id, content, branch_id, confidence, created_at, source) "
                      "VALUES (?,?,?,?,?,?)", rows)
        b.execute("INSERT INTO belief_lineage VALUES (12, 1, 'synergy', 1.0, ?)", (_NOW,))
        b.execute("INSERT INTO belief_edges (source_id, target_id, edge_type, weight, created_at) "
                  "VALUES (14, 12, 'synthesises', 0.5, ?)", (_NOW,))
        if cooldown:
            b.execute("INSERT INTO signal_cooldown VALUES ('h', ?, ?, 'test', ?)",
                      (cooldown, _NOW + 3600, _NOW - 60))
        b.commit(); b.close()
        d = sqlite3.connect(self.ddb)
        d.execute("CREATE TABLE fountain_events (id INTEGER PRIMARY KEY, ts REAL, hot_branch TEXT)")
        fires = fires or {"markets": 6, "emerging_tech": 3, "quiescent": 20, "psychology": 0}
        k = 0
        for br, n in fires.items():
            for _ in range(n):
                k += 1
                d.execute("INSERT INTO fountain_events VALUES (?, ?, ?)", (k, _NOW - 600, br))
        d.commit(); d.close()
        c = sqlite3.connect(self.cdb)
        c.execute("CREATE TABLE drives_competing_log (id INTEGER PRIMARY KEY, tick_at REAL, "
                  "weights_json TEXT, inputs_json TEXT, tension_active INTEGER)")
        c.execute("INSERT INTO drives_competing_log (tick_at, weights_json, tension_active) VALUES (?,?,0)",
                  (_NOW - 60, json.dumps({"curiosity": drive[0], "exploration": drive[1]})))
        c.commit(); c.close()

    def syn(self):
        return BS(None, Reader(self.bdb), None)

    def ctx(self, syn=None):
        syn = syn or self.syn()
        rows = [dict(r) for r in Reader(self.bdb).read("SELECT * FROM beliefs")]
        anchors = [r for r in rows if r["source"] in BS._ANCHOR_SOURCES]
        fresh = [r for r in rows if r["source"] in BS._FRESH_SOURCES]
        return syn._bridge_context(anchors, fresh, _NOW, Reader(self.ddb), Reader(self.cdb))


class TestBridgeFactor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_only_absent_active_crossbranch_bridges_are_boosted(self):
        ctx = _Fixture(self.tmp.name).ctx()
        self.assertIn("markets", ctx["active"])
        self.assertNotIn("quiescent", ctx["active"])
        self.assertGreater(BS.bridge_factor(ctx, 1, 11), 1.0)    # active, unlinked, cross-branch
        self.assertEqual(BS.bridge_factor(ctx, 1, 10), 1.0)      # same branch as the anchor
        self.assertEqual(BS.bridge_factor(ctx, 1, 12), 1.0)      # its lineage child: linked
        self.assertEqual(BS.bridge_factor(ctx, 1, 14), 1.0)      # synthesises edge into region
        self.assertEqual(BS.bridge_factor(ctx, 1, 13), 1.0)      # psychology inactive

    def test_min_cosine_floor(self):
        ctx = _Fixture(self.tmp.name).ctx()
        f = BS._BRIDGE_MIN_COS
        self.assertEqual(BS.bridge_factor(ctx, 1, 11, cos=f - 0.01), 1.0)    # too weak: no boost
        self.assertGreater(BS.bridge_factor(ctx, 1, 11, cos=f + 0.01), 1.0)
        self.assertGreater(BS.bridge_factor(ctx, 1, 11), 1.0)               # no cos given: unchanged
        # the sample's calibration points
        self.assertEqual(BS.bridge_factor(ctx, 1, 11, cos=0.362), 1.0)      # moon pun
        self.assertEqual(BS.bridge_factor(ctx, 1, 11, cos=0.372), 1.0)      # dyslexia non-sequitur
        self.assertGreater(BS.bridge_factor(ctx, 1, 11, cos=0.389), 1.0)    # Cook Ding
        self.assertGreater(BS.bridge_factor(ctx, 1, 11, cos=0.421), 1.0)    # juggling

    def test_max_cosine_cap(self):
        ctx = _Fixture(self.tmp.name).ctx()
        m = BS._BRIDGE_MAX_COS
        self.assertGreater(BS.bridge_factor(ctx, 1, 11, cos=m - 0.01), 1.0)
        self.assertEqual(BS.bridge_factor(ctx, 1, 11, cos=m), 1.0)
        # the re-sample's restatements
        self.assertEqual(BS.bridge_factor(ctx, 1, 11, cos=0.599), 1.0)      # sun/cloud paraphrase
        self.assertEqual(BS.bridge_factor(ctx, 1, 11, cos=0.693), 1.0)      # flag restatement

    def test_synergized_fresh_never_bridged(self):
        ctx = _Fixture(self.tmp.name).ctx()
        self.assertNotIn(15, ctx["eligible"])        # active, cross-branch, unlinked — but her own output
        self.assertEqual(BS.bridge_factor(ctx, 1, 15), 1.0)
        self.assertEqual(BS.bridge_factor(ctx, 1, 15, cos=0.45), 1.0)

    def test_groove_guard_blocks_boost(self):
        ctx = _Fixture(self.tmp.name, cooldown="liquidity cascades are everywhere").ctx()
        self.assertEqual(BS.bridge_factor(ctx, 1, 11), 1.0)

    def test_drive_weighting(self):
        lo = _Fixture(self.tmp.name, drive=(0.05, 0.05)).ctx()["factor"]
        t2 = tempfile.TemporaryDirectory()
        try:
            hi = _Fixture(t2.name, drive=(0.3, 0.3)).ctx()["factor"]
        finally:
            t2.cleanup()
        self.assertGreater(hi, lo)
        self.assertLessEqual(hi, 1 + BS._BRIDGE_GAIN * BS._BRIDGE_DRIVE_CAP + 1e-9)

    def test_no_drive_or_no_active_branch_means_no_context(self):
        self.assertIsNone(_Fixture(self.tmp.name, drive=(0.0, 0.0)).ctx())
        t2 = tempfile.TemporaryDirectory()
        try:
            self.assertIsNone(_Fixture(t2.name, fires={"quiescent": 9}).ctx())
        finally:
            t2.cleanup()

    def test_groove_margin_matches_curiosity(self):
        src = (Path(__file__).resolve().parents[1] / "theory_x" / "stage6_fountain"
               / "generator.py").read_text()
        m = re.search(r"^_CURIOSITY_GROOVE_MARGIN\s*=\s*([0-9.]+)", src, re.M)
        self.assertEqual(float(m.group(1)), BS._GROOVE_MARGIN)


class TestSelectPairWithBridge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fx = _Fixture(self.tmp.name)
        self._orig = emb.embed_belief
        emb.embed_belief = lambda bid, content: _vec(_ANGLE[bid])
        self._env = {k: os.environ.get(k) for k in ("NEX5_BRIDGE", "NEX5_SYNTH_FRESH")}

    def tearDown(self):
        emb.embed_belief = self._orig
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.tmp.cleanup()

    def _pick(self, bridge, fresh=False, broken=False):
        for k, on in (("NEX5_BRIDGE", bridge), ("NEX5_SYNTH_FRESH", fresh)):
            if on:
                os.environ[k] = "1"
            else:
                os.environ.pop(k, None)
        syn = self.fx.syn()
        real = syn._bridge_context
        if broken:
            def _boom(*a, **k):
                raise RuntimeError("boom")
            syn._bridge_context = _boom
        else:
            syn._bridge_context = lambda a, f, now: real(a, f, now, Reader(self.fx.ddb), Reader(self.fx.cdb))
        a, b = syn._select_pair()
        return a["id"], b["id"]

    def test_off_is_todays_pick(self):
        self.assertEqual(self._pick(False), (1, 10))

    def test_on_picks_the_absent_bridge(self):
        # gain large enough to flip 60deg vs 64deg in this toy geometry
        old = BS._BRIDGE_GAIN
        BS._BRIDGE_GAIN = 0.25
        try:
            self.assertEqual(self._pick(True), (1, 11))
            self.assertEqual(self._pick(True, fresh=True), (1, 11))   # composes with SYNTH_FRESH
        finally:
            BS._BRIDGE_GAIN = old

    def test_bridge_does_not_need_synth_fresh(self):
        self.assertIn(self._pick(True, fresh=False), {(1, 10), (1, 11)})   # no crash

    def test_fail_safe_to_todays_pick(self):
        self.assertEqual(self._pick(True, broken=True), self._pick(False))


if __name__ == "__main__":
    unittest.main()
