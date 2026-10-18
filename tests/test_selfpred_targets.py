"""Round 11, item 3(b) — the two variance-bearing targets: authored_30m and
selfdesc_novel. Fixture DBs, no live endpoint.
"""
import os
import sqlite3
import tempfile
import time
import unittest

from tests import _bootstrap  # noqa: F401

from theory_x.stage_world import self_prediction as SP


class TestAuthoredTarget(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.conv = os.path.join(self._tmp.name, "conversations.db")
        self.bel = os.path.join(self._tmp.name, "beliefs.db")
        b = sqlite3.connect(self.bel)
        b.execute("CREATE TABLE beliefs (id INTEGER PRIMARY KEY, created_at INTEGER, source TEXT)")
        b.commit(); b.close()

    def tearDown(self):
        self._tmp.cleanup()

    def _add_belief(self, ts, source):
        b = sqlite3.connect(self.bel)
        b.execute("INSERT INTO beliefs (created_at, source) VALUES (?,?)", (ts, source))
        b.commit(); b.close()

    def test_predict_persistence_and_resolve(self):
        now = time.time()
        # prior window has an authored belief -> persistence predicts 'yes'
        self._add_belief(int(now - 60), "fountain_insight")
        out = SP.make_authored_prediction(self.conv, self.bel, horizon=1800)
        self.assertEqual(out["self"], "yes")
        self.assertEqual(out["prior_count"], 1)
        # a self row + a coin row written under kind authored_30m
        conn = SP._connect(self.conv)
        kinds = [r["kind"] for r in conn.execute("SELECT kind FROM self_predictions")]
        conn.close()
        self.assertEqual(kinds, ["authored_30m", "authored_30m"])
        # produce an authored belief inside the horizon, then resolve at resolve_at
        self._add_belief(int(now + 100), "wonder_loop")
        n = SP.resolve_authored(self.conv, self.bel, now=now + 2000)
        self.assertEqual(n, 2)
        conn = SP._connect(self.conv)
        self_row = conn.execute(
            "SELECT actual, outcome FROM self_predictions WHERE source='self'"
        ).fetchone()
        conn.close()
        self.assertEqual(self_row["actual"], "yes")
        self.assertEqual(self_row["outcome"], "correct")

    def test_admissible_target_only(self):
        # sanity: 'authored_30m' is predicted as yes/no (binary, variance-bearing)
        self._add_belief(int(time.time() - 60), "synergized")
        out = SP.make_authored_prediction(self.conv, self.bel)
        self.assertIn(out["self"], ("yes", "no"))


class TestSelfdescTarget(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.conv = os.path.join(self._tmp.name, "conversations.db")
        self.dyn = os.path.join(self._tmp.name, "dynamic.db")
        d = sqlite3.connect(self.dyn)
        d.execute("CREATE TABLE identity_log (statement TEXT, composed_at REAL)")
        d.commit(); d.close()

    def tearDown(self):
        self._tmp.cleanup()

    def _add(self, statement, ts):
        d = sqlite3.connect(self.dyn)
        d.execute("INSERT INTO identity_log (statement, composed_at) VALUES (?,?)", (statement, ts))
        d.commit(); d.close()

    def test_predict_and_resolve_differ(self):
        now = time.time()
        self._add("I am curious about mathematics always", now - 300)
        self._add("I am curious about mathematics always", now - 200)  # no new token
        out = SP.make_selfdesc_prediction(self.conv, self.dyn)
        self.assertEqual(out["self"], "same")   # last transition added nothing -> persistence 'same'
        # a genuinely new description appears after made_at -> actual 'differ'
        self._add("I notice growing restlessness toward philosophy", now + 50)
        n = SP.resolve_selfdesc(self.conv, self.dyn)
        self.assertEqual(n, 2)
        conn = SP._connect(self.conv)
        row = conn.execute("SELECT actual, outcome FROM self_predictions WHERE source='self'").fetchone()
        conn.close()
        self.assertEqual(row["actual"], "differ")
        self.assertEqual(row["outcome"], "wrong")  # predicted 'same', got 'differ'

    def test_insufficient_history(self):
        self._add("only one statement here", time.time())
        out = SP.make_selfdesc_prediction(self.conv, self.dyn)
        self.assertEqual(out.get("error"), "insufficient_history")


if __name__ == "__main__":
    unittest.main()
