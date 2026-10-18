"""Round 11, item 3(b) — the two variance-bearing targets: authored_30m and
selfdesc_novel. Fixture DBs, no live endpoint.
"""
import os
import sqlite3
import tempfile
import time
import unittest
from unittest import mock

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

    def test_resolve_selfdesc_against_next_statement(self):
        # resolve compares the NEXT self-description after made_at to the one current
        # at made_at; a genuinely new token -> actual 'differ', outcome consistent.
        now = time.time()
        self._add("curious about mathematics always steady", now - 300)
        self._add("curious about mathematics always steady", now - 200)
        out = SP.make_selfdesc_prediction(self.conv, self.dyn)
        self._add("restless toward philosophy lately shifting", now + 50)
        n = SP.resolve_selfdesc(self.conv, self.dyn)
        self.assertEqual(n, 2)
        conn = SP._connect(self.conv)
        row = conn.execute(
            "SELECT actual, outcome FROM self_predictions WHERE source='self'").fetchone()
        conn.close()
        self.assertEqual(row["actual"], "differ")
        self.assertEqual(row["outcome"], "correct" if out["self"] == "differ" else "wrong")

    def test_insufficient_history(self):
        self._add("only one statement here", time.time())
        out = SP.make_selfdesc_prediction(self.conv, self.dyn)
        self.assertEqual(out.get("error"), "insufficient_history")

    def test_adaptive_persists_when_persistent(self):
        # every statement adds a NEW token -> every transition is 'differ' -> the
        # persistence estimate is high -> predict 'differ' (persist the last label).
        base = time.time() - 1000
        # all tokens >=5 chars so each one is a genuine new distinctive token
        words = "alpha gamma delta sigma omega theta kappa flora prism grove".split()
        acc = []
        for i, w in enumerate(words):
            acc.append(w)
            self._add("mind holds " + " ".join(acc), base + i)
        pers = SP.selfdesc_persistence(self.dyn)
        self.assertGreater(pers["persistence"], 0.5)
        out = SP.make_selfdesc_prediction(self.conv, self.dyn)
        self.assertEqual(out["self"], "differ")  # last label 'differ', p>0.5 -> persist

    def test_conditional_predicts_per_prev_state(self):
        # Q6: the predictor uses P(next differ | prev = last_label), not a pooled
        # symmetric persistence. Build strict alternation (add-new, repeat, add-new,...)
        # so after 'differ' comes 'same' and after 'same' comes 'differ'.
        base = time.time() - 1000
        acc = ["alpha"]
        self._add("mind " + " ".join(acc), base)
        t = 1
        for w in ["gamma", "delta", "sigma", "omega", "theta", "kappa"]:
            acc.append(w)
            self._add("mind " + " ".join(acc), base + t); t += 1   # differ
            self._add("mind " + " ".join(acc), base + t); t += 1   # same (repeat)
        cond = SP.selfdesc_conditional(self.dyn)
        self.assertLess(cond["p_differ_given_differ"], 0.5)   # after differ -> same
        self.assertGreater(cond["p_differ_given_same"], 0.5)  # after same -> differ
        # sequence ends on a 'same' transition -> conditional says 'differ'. A pooled
        # symmetric model would NOT make this state-specific call.
        with mock.patch.object(SP, "_SELFDESC_MIN_EFF_N", 1):
            out = SP.make_selfdesc_prediction(self.conv, self.dyn)
        self.assertEqual(out["self"], "differ")


if __name__ == "__main__":
    unittest.main()
