"""Learning-delta provenance + the subtractability test (learning's flip condition).

Learning is not ownership-scaled (R7), so external-basis expectations can move
her authored beliefs with no valence trace. Before learning may go ON, every
delta must be self-describing (basis_kind, the belief's source_kind, the factor)
and authored confidence must be reconstructable with every external-basis
contribution removed -- exactly, on a controlled sequence that includes clamping
and non-learning changes in between. Then a coup is undoable, not just visible.
"""
import json
import os
import tempfile
import unittest
from unittest import mock

from tests import _bootstrap  # noqa: F401

from substrate import connect, Row
from theory_x.stage_world import expectations as X

T0 = 1_800_000_000.0


class _Store(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._env = mock.patch.dict(os.environ, {
            "NEX5_DATA_DIR": self._tmp.name, "NEX5_SCHEMA_TRIPWIRE": "1",
            "NEX5_EXPECT_LEARN": "1"})
        self._env.start()
        from substrate.init_db import init_all
        init_all()
        from substrate.paths import db_paths
        p = db_paths()
        self.conv, self.bel = str(p["conversations"]), str(p["beliefs"])
        self._n = 0

    def tearDown(self):
        self._env.stop()
        self._tmp.cleanup()

    def _belief(self, content, source="wonder_loop", conf=0.7):
        cx = connect(self.bel)
        try:
            bid = cx.execute("INSERT INTO beliefs (content, tier, confidence, created_at, source) "
                             "VALUES (?, 6, ?, ?, ?)", (content, conf, int(T0), source)).lastrowid
            cx.commit()
            return bid
        finally:
            cx.close()

    def _conf(self, bid):
        cx = connect(self.bel)
        try:
            return cx.execute("SELECT confidence FROM beliefs WHERE id=?", (bid,)).fetchone()[0]
        finally:
            cx.close()

    def _set_conf(self, bid, value):           # a non-learning change (erosion, an edit)
        cx = connect(self.bel)
        cx.execute("UPDATE beliefs SET confidence=? WHERE id=?", (value, bid))
        cx.commit(); cx.close()

    def _learn(self, basis_ids, basis_kind, state, sal=1.0, band=1):
        """One learning step through the real _learn(), from a ledger header."""
        self._n += 1
        basis = [{"belief_id": b, "source_kind": "authored", "confidence": None}
                 for b in basis_ids]
        cx = connect(self.conv)
        cx.row_factory = Row
        try:
            eid = cx.execute(
                "INSERT INTO expectations (subject, producer, producer_row_id, made_at, "
                "claimed_state, cost_band, basis_snapshot, ownership, basis_kind, horizon_at, "
                "horizon_kind) VALUES ('surprise', 'predictions', ?, ?, '{}', ?, ?, ?, ?, ?, "
                "'window')", (self._n, T0, band, json.dumps(basis),
                              1.0 if basis_kind == "owned" else 0.0, basis_kind, T0)).lastrowid
            e = cx.execute("SELECT * FROM expectations WHERE id=?", (eid,)).fetchone()
            X._learn(cx, e, state, sal, T0 + self._n)
            cx.commit()
        finally:
            cx.close()


class TestProvenance(_Store):

    def test_every_delta_is_self_describing(self):
        mine = self._belief("an authored belief")
        news = self._belief("a headline", source="fetch_loop")
        self._learn([mine, news], "external", "violated", sal=0.5)
        self._learn([mine], "owned", "confirmed")
        cx = connect(self.conv)
        rows = cx.execute("SELECT belief_id, basis_kind, source_kind, factor FROM "
                          "expectation_learning_log ORDER BY id").fetchall()
        cx.close()
        self.assertEqual([r[:3] for r in rows], [(mine, "external", "authored"),
                                                 (news, "external", "world"),
                                                 (mine, "owned", "authored")])
        self.assertAlmostEqual(rows[0][3], 1 - X.LEARN_VIOLATE * 0.5 / 2)
        self.assertAlmostEqual(rows[2][3], 1 + X.LEARN_CONFIRM)


class TestSubtractability(_Store):

    def test_reconstruction_is_exact_on_a_controlled_sequence(self):
        mine = self._belief("I keep returning to thresholds", conf=0.7)
        clamp = lambda c: max(X.CONF_FLOOR, min(X.CONF_CEIL, c))  # noqa: E731
        expected = 0.7
        self._learn([mine], "owned", "violated", sal=1.0)          # owned: kept
        expected = clamp(expected * (1 - X.LEARN_VIOLATE))
        self._learn([mine], "external", "violated", sal=1.0)       # external: removed
        self._set_conf(mine, self._conf(mine) + 0.02)              # erosion-like bump
        expected += 0.02
        self._learn([mine], "external", "violated", sal=0.8)       # external: removed
        self._learn([mine], "owned", "confirmed")                  # owned: kept
        expected = clamp(expected * (1 + X.LEARN_CONFIRM))
        self._set_conf(mine, self._conf(mine) - 0.01)              # an edit after the last delta
        expected -= 0.01
        r = X.reconstruct_without_external(mine, self._conf(mine))
        self.assertTrue(r["reconstructable"])
        self.assertEqual((r["deltas"], r["subtracted"]), (4, 2))
        self.assertAlmostEqual(r["confidence"], expected, places=12)
        self.assertNotAlmostEqual(r["confidence"], self._conf(mine), places=6)

    def test_exact_through_the_ceiling_clamp(self):
        mine = self._belief("near certain", conf=0.985)
        for _ in range(3):
            self._learn([mine], "owned", "confirmed")              # clamps at 0.99
        self._learn([mine], "external", "violated", sal=1.0)
        r = X.reconstruct_without_external(mine, self._conf(mine))
        self.assertAlmostEqual(r["confidence"], X.CONF_CEIL, places=12)

    def test_only_owned_history_reconstructs_to_itself(self):
        mine = self._belief("all mine")
        self._learn([mine], "owned", "violated", sal=0.4)
        self._learn([mine], "owned", "confirmed")
        r = X.reconstruct_without_external(mine, self._conf(mine))
        self.assertAlmostEqual(r["confidence"], self._conf(mine), places=12)
        self.assertEqual(r["subtracted"], 0)

    def test_legacy_rows_are_not_reconstructable(self):
        mine = self._belief("before provenance")
        cx = connect(self.conv)
        cx.execute("INSERT INTO expectations (subject, producer, producer_row_id, made_at, "
                   "claimed_state, ownership, basis_kind, horizon_at, horizon_kind) "
                   "VALUES ('surprise', 'predictions', 999, 0, '{}', 0, 'external', 0, 'window')")
        cx.execute("INSERT INTO expectation_learning_log (expectation_id, belief_id, ts, before, "
                   "after) VALUES (1, ?, 0, 0.7, 0.69)", (mine,))
        cx.commit(); cx.close()
        r = X.reconstruct_without_external(mine, 0.69)
        self.assertEqual((r["reconstructable"], r["confidence"]), (False, None))


class TestEverFired(_Store):

    def test_lines_distinguish_never_from_fired(self):
        got = X.ever_fired()
        self.assertEqual({k: v["fired"] for k, v in got.items()},
                         {"owned_belief_valence": False, "commitment_valence": False,
                          "learning": False, "mood": False})
        mine = self._belief("moves")
        self._learn([mine], "owned", "violated")
        cx = connect(self.conv)
        cx.execute("INSERT INTO mood_nudge_applied (ts, nudge) VALUES (1, -0.05)")
        cx.commit(); cx.close()
        got = X.ever_fired()
        self.assertTrue(got["learning"]["fired"])
        self.assertTrue(got["mood"]["fired"])
        self.assertFalse(got["owned_belief_valence"]["fired"])
        names = [c[0] for c in X.canaries()]
        self.assertIn("ever_fired.commitment_valence", names)


if __name__ == "__main__":
    unittest.main()
