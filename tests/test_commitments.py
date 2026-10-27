"""The commitment faculty: her stated, time-bound obligations (bands 2/3).

Pinned here:
  * only an unhedged "I will X by T" with an explicit deadline of HERS is a
    commitment; no deadline or a hedge -> an intention (no resolution point);
  * band 3 iff a named counterparty at made_at, else band 2; the claim is frozen;
  * breach needs positive evidence (complete record, opportunity, unmet);
    no opportunity / uncheckable -> unresolved, never breached;
  * release: only her or the named counterparty, before the deadline -- the
    system never; the schema refuses and logs;
  * phase-2 controls: released = 0, uncheckable = 0, band 2 != band 3 in
    magnitude, and a breach writes NOTHING to the belief graph.
"""
import datetime as dt
import json
import os
import sqlite3
import tempfile
import time
import unittest
from unittest import mock

from tests import _bootstrap  # noqa: F401

from substrate import connect, Row
from theory_x.stage_world import commitments as C
from theory_x.stage_world import expectations as X

_STAKES = (0.0, 0, 0.0)
T0 = 1_800_000_000.0          # 2027-01-15 08:00 UTC = 10:00 SAST, a Friday
HOUR, DAY = 3600.0, 86400.0


class _Store(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._env = mock.patch.dict(os.environ, {
            "NEX5_DATA_DIR": self._tmp.name, "NEX5_SCHEMA_TRIPWIRE": "1",
            "NEX5_TZ": "Africa/Johannesburg"})
        self._env.start()
        for f in ("NEX5_EXPECT_LEARN", "NEX5_EXPECT_MOOD", "NEX5_COMMITMENT_VALENCE"):
            os.environ.pop(f, None)
        from substrate.init_db import init_all
        init_all()
        from substrate.paths import db_paths
        p = db_paths()
        self.conv, self.bel, self.dyn = str(p["conversations"]), str(p["beliefs"]), str(p["dynamic"])
        self._snap = mock.patch("theory_x.stage_world.frozen_at_made.snapshot_stakes",
                                return_value=_STAKES)
        self._snap.start()
        C.ensure_schema()

    def tearDown(self):
        self._snap.stop()
        self._env.stop()
        self._tmp.cleanup()

    def _fire(self, ts, thought):
        cx = connect(self.dyn)
        try:
            fid = cx.execute("INSERT INTO fountain_events (ts, thought, readiness) "
                             "VALUES (?, ?, 0.8)", (ts, thought)).lastrowid
            cx.commit()
            return fid
        finally:
            cx.close()

    def _chat(self, ts, role, content, admin=1, session="jon-session"):
        cx = connect(self.conv)
        try:
            cx.execute("INSERT OR IGNORE INTO sessions (id, started_at, admin) VALUES (?, ?, ?)",
                       (session, ts, admin))
            cx.execute("INSERT INTO messages (session_id, role, content, timestamp) "
                       "VALUES (?, ?, ?, ?)", (session, role, content, ts))
            cx.commit()
        finally:
            cx.close()

    def _rows(self):
        cx = connect(self.conv)
        cx.row_factory = Row
        try:
            return [dict(r) for r in cx.execute("SELECT * FROM commitments ORDER BY id")]
        finally:
            cx.close()

    def _valence(self):
        cx = connect(self.conv)
        cx.row_factory = Row
        try:
            return {r["pid"]: dict(r) for r in cx.execute(
                "SELECT e.producer_row_id AS pid, e.state, v.valence, v.reason, v.cost_band "
                "FROM expectations e LEFT JOIN event_valence v ON v.expectation_id = e.id "
                "WHERE e.producer = 'commitments'")}
        finally:
            cx.close()


class TestParser(unittest.TestCase):

    def setUp(self):
        self._env = mock.patch.dict(os.environ, {"NEX5_TZ": "Africa/Johannesburg"})
        self._env.start()

    def tearDown(self):
        self._env.stop()

    def _one(self, text, **kw):
        out = C.parse(text, T0, **kw)
        self.assertEqual(len(out), 1, out)
        return out[0]

    def test_think_commitment_with_her_deadline(self):
        c = self._one("I will reflect on the threshold problem by tomorrow.")
        self.assertEqual(c["kind"], "commitment")
        self.assertEqual(c["discharge"], {"kind": "think", "topic": ["problem", "threshold"]})
        end = dt.datetime(2027, 1, 16, 23, 59, 59,
                          tzinfo=dt.timezone(dt.timedelta(hours=2))).timestamp()
        self.assertEqual(c["deadline"], end)
        self.assertIsNone(c["counterparty"])

    def test_named_counterparty(self):
        c = self._one("I'll tell Jon about the threshold idea within 2 hours")
        self.assertEqual((c["discharge"]["kind"], c["counterparty"], c["deadline"]),
                         ("speak", "operator", T0 + 2 * HOUR))

    def test_you_in_an_operator_session_is_the_operator(self):
        c = self._one("I will answer you properly by 5pm", operator_present=True)
        self.assertEqual(c["counterparty"], "operator")
        self.assertIsNone(self._one("I will answer you properly by 5pm")["counterparty"])

    def test_no_deadline_or_hedge_is_an_intention(self):
        for text in ("I will think about thresholds more.",
                     "I'll try to think about thresholds by tonight",
                     "Maybe I will revisit thresholds by tomorrow",
                     "I will think about thresholds by 3"):         # "by 3" is not explicit
            c = self._one(text)
            self.assertEqual((c["kind"], c["deadline"]), ("intention", None), text)

    def test_uncheckable_discharge(self):
        c = self._one("I will be more patient with myself by tomorrow")
        self.assertEqual((c["kind"], c["discharge"]["kind"]), ("commitment", "uncheckable"))

    def test_no_intention_language_no_row(self):
        self.assertEqual(C.parse("The market moved; I notice the pull of it.", T0), [])


class TestProducer(_Store):

    def test_scan_records_frozen_rows_once(self):
        self._fire(T0, "I will reflect on the threshold problem by tomorrow. "
                       "I will think about patience someday.")
        self._chat(T0 + 5, "nex", "I'll tell Jon about the threshold idea within 2 hours")
        self.assertEqual(C.scan(), {"commitments": 2, "intentions": 1, "releases": 0})
        self.assertEqual(C.scan(), {"commitments": 0, "intentions": 0, "releases": 0})
        rows = self._rows()
        think, intent, speak = rows
        self.assertEqual((think["kind"], think["cost_band"], think["checkable"]),
                         ("commitment", 2, 1))
        self.assertEqual((speak["cost_band"], speak["counterparty"]), (3, "operator"))
        self.assertEqual((intent["kind"], intent["resolve_at"], intent["cost_band"]),
                         ("intention", None, 0))       # the system never assigns a deadline
        self.assertEqual((think["confidence"], think["confidence_basis"], think["frozen"]),
                         (1.0, "stated_p", "at_made"))
        self.assertEqual(json.loads(think["claimed_state"])["obligation"],
                         "reflect on the threshold problem")
        with self.assertRaises(sqlite3.IntegrityError):         # frozen
            cx = connect(self.conv)
            try:
                cx.execute("UPDATE commitments SET cost_band=3 WHERE id=?", (think["id"],))
            finally:
                cx.close()

    def test_intentions_never_enter_the_ledger(self):
        self._fire(T0, "I will think about patience someday.")
        C.scan()
        X.reconcile(now=T0 + 10 * DAY)
        self.assertEqual(self._valence(), {})


class TestReleaseGuard(_Store):

    def _commit(self, text="I'll tell Jon about the threshold idea within 2 hours"):
        self._fire(T0, text)
        C.scan()
        return self._rows()[-1]["id"]

    def test_system_can_never_release(self):
        cid = self._commit()
        for by in ("system", "reconciler", None and "x"):
            if by is None:
                continue
            with self.assertLogs("substrate.guard", "ERROR"):
                with self.assertRaisesRegex(sqlite3.IntegrityError, "release not by her"):
                    C.record_release(cid, by, T0 + 60, "test")

    def test_only_before_the_deadline_and_counterparty_must_exist(self):
        cid = self._commit()
        with self.assertLogs("substrate.guard", "ERROR"):
            with self.assertRaises(sqlite3.IntegrityError):
                C.record_release(cid, "self", T0 + 3 * HOUR, "late")
        other = self._commit("I will reflect on the threshold problem by tomorrow")
        with self.assertLogs("substrate.guard", "ERROR"):
            with self.assertRaises(sqlite3.IntegrityError):
                C.record_release(other, "counterparty", T0 + 60, "nobody named")
        C.record_release(cid, "counterparty", T0 + 60, "chat:1")
        C.record_release(other, "self", T0 + 60, "fountain:2")

    def test_scan_finds_her_release_and_the_counterpartys(self):
        self._fire(T0, "I will reflect on the threshold problem by tomorrow.")
        self._fire(T0 + 1, "I'll tell Jon about the margin question within 3 hours")
        C.scan()
        self._fire(T0 + 600, "I release my plan to reflect on the threshold problem.")
        self._chat(T0 + 700, "user", "no need to tell me about the margin question")
        self.assertEqual(C.scan()["releases"], 2)
        by = [r["released_by"] for r in self._rows()]
        self.assertEqual(by, ["self", "counterparty"])


class TestTerminals(_Store):
    """Positive evidence only; released is an act; no opportunity is not a breach."""

    def _think(self, ts=T0, text="I will reflect on the threshold problem within 2 hours."):
        self._fire(ts, text)
        C.scan()
        return self._rows()[-1]["id"]

    def test_discharged_breached_unresolved(self):
        kept = self._think(T0)
        self._fire(T0 + HOUR, "The threshold problem looks different now; a problem of scale.")
        broken = self._think(T0 + 10 * DAY)
        self._fire(T0 + 10 * DAY + HOUR, "Markets, rain, a kettle.")       # active, unmet
        idle = self._think(T0 + 20 * DAY)                                  # silent window
        X.reconcile(now=T0 + 30 * DAY)
        v = self._valence()
        self.assertEqual(v[kept]["state"], "confirmed")
        self.assertEqual(v[broken]["state"], "breached")
        self.assertEqual(v[idle]["state"], "unresolved")
        self.assertIsNone(v[idle]["valence"])                  # no row: exactly nothing
        obs = json.loads(self._rows()[1]["observed_state"])
        # the window is (made_at, deadline]: the statement itself never discharges it
        self.assertEqual((obs["discharged"], obs["examined"]), (False, 1))

    def test_uncheckable_and_released_are_zero(self):
        os.environ["NEX5_COMMITMENT_VALENCE"] = "1"
        vague = self._think(T0, "I will be more patient with myself within 2 hours.")
        self._fire(T0 + HOUR, "Something else entirely.")
        rel = self._think(T0 + 10 * DAY)
        C.record_release(rel, "self", T0 + 10 * DAY + 60, "fountain:x")
        X.reconcile(now=T0 + 30 * DAY)
        v = self._valence()
        self.assertEqual(v[vague]["state"], "unresolved")
        self.assertIsNone(v[vague]["valence"])                 # exactly 0: no valence row
        self.assertEqual((v[rel]["state"], v[rel]["valence"], v[rel]["reason"]),
                         ("released", 0.0, "released"))


class TestPhaseTwoControls(_Store):

    def _breach(self, text, day):
        base = T0 + day * 10 * DAY
        self._fire(base, text)
        self._fire(base + 600, "Weather, prices, nothing on it.")
        C.scan()
        return self._rows()[-1]["id"]

    def test_band_two_vs_three_magnitude(self):
        os.environ["NEX5_COMMITMENT_VALENCE"] = "1"
        b2 = self._breach("I will reflect on the threshold problem within 2 hours.", 1)
        self._chat(T0 + 20 * DAY + 600, "nex", "Hello Jon, about the weather.")
        b3 = self._breach("I'll tell Jon about the margin question within 2 hours.", 2)
        X.reconcile(now=T0 + 40 * DAY)
        v = self._valence()
        self.assertEqual((v[b2]["state"], v[b2]["cost_band"]), ("breached", 2))
        self.assertEqual((v[b3]["state"], v[b3]["cost_band"]), ("breached", 3))
        self.assertEqual(v[b2]["valence"], -0.5)
        self.assertEqual(v[b3]["valence"], -0.75)
        self.assertNotEqual(v[b2]["valence"], v[b3]["valence"])   # a weight, not a gate

    def test_flag_off_is_zero(self):
        b = self._breach("I will reflect on the threshold problem within 2 hours.", 1)
        X.reconcile(now=T0 + 40 * DAY)
        v = self._valence()[b]
        self.assertEqual((v["state"], v["valence"], v["reason"]),
                         ("breached", 0.0, "commitment_valence_off"))

    def test_breach_writes_nothing_to_the_belief_graph(self):
        os.environ["NEX5_COMMITMENT_VALENCE"] = "1"
        os.environ["NEX5_EXPECT_LEARN"] = "1"
        cx = connect(self.bel)
        cx.execute("INSERT INTO beliefs (content, tier, confidence, created_at, source, "
                   "use_count) VALUES ('I keep returning to the threshold problem', 6, 0.7, "
                   "?, 'wonder_loop', 5)", (int(T0),))
        cx.commit(); cx.close()

        def graph():
            g = connect(self.bel)
            try:
                return (g.execute("SELECT id, confidence, tier, paused, erosion_stage, "
                                  "last_demoted_at FROM beliefs ORDER BY id").fetchall(),
                        g.execute("SELECT COUNT(*) FROM belief_edges").fetchone()[0])
            finally:
                g.close()
        before = graph()
        b = self._breach("I will reflect on the threshold problem within 2 hours.", 1)
        X.reconcile(now=T0 + 40 * DAY)
        self.assertEqual(self._valence()[b]["state"], "breached")
        self.assertEqual(graph(), before)          # zero confidence change, zero new edges


class TestCanaries(_Store):

    def test_release_rate_flags_when_breach_never_fires(self):
        for i in range(10):
            self._fire(T0 + i * DAY, f"I will reflect on the threshold problem number{i}x "
                                     f"within 2 hours.")
        C.scan()
        for r in self._rows()[:6]:
            C.record_release(r["id"], "self", r["made_at"] + 60, "test")
        for i in range(10):
            self._fire(T0 + i * DAY + 600, "Something unrelated.")
        X.reconcile(now=T0 + 20 * DAY)
        r = C.release_rate()
        self.assertEqual((r["terminal"], r["released"], r["flag"]), (10, 6, True))

    def test_divergence_pending_then_build_undo_log(self):
        now = time.time()
        cx = connect(self.bel)
        a = cx.execute("INSERT INTO beliefs (content, tier, confidence, created_at, source) "
                       "VALUES ('x one', 6, 0.7, ?, 'wonder_loop')", (int(now),)).lastrowid
        b = cx.execute("INSERT INTO beliefs (content, tier, confidence, created_at, source) "
                       "VALUES ('x two', 6, 0.7, ?, 'wonder_loop')", (int(now),)).lastrowid
        cx.execute("INSERT INTO belief_edges (source_id, target_id, edge_type, weight, "
                   "created_at) VALUES (?, ?, 'opposes', 0.6, ?)", (a, b, now - 60))
        cx.commit(); cx.close()
        u = X.belief_undo_divergence(now)
        self.assertFalse(u["diverged"])
        self.assertTrue(u["status"].startswith("pending"))
        with mock.patch.object(X, "falsifiability", return_value={
                "resolved": 5, "exercised": 0, "rate": None, "status": "UNEXERCISED (5 resolved)",
                "escalate": False}):
            u = X.belief_undo_divergence(now)
        self.assertTrue(u["diverged"])
        self.assertTrue(u["status"].startswith("BUILD UNDO-LOG: 1 belief undos"))

    def test_canaries_report_both_new_entries(self):
        names = [c[0] for c in X.canaries()]
        self.assertIn("release_rate", names)
        self.assertIn("belief_undo_divergence", names)


if __name__ == "__main__":
    unittest.main()
