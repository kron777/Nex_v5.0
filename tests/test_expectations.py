"""Build B PR2: the expectations ledger, the single reconciler, valence, learning.

The acceptance tests (Beam), on SYNTHETIC events through the real reconciler:
  1. valence-admissibility 2x2 -- one live cell, three BIT-FOR-BIT zero;
  2. two-channel discrimination -- learning WITHOUT valence must be observable
     (owned band 0: confidence moves, valence and mood exactly 0);
  3. R1 falsifier -- a moderate-confidence, high-cost violation is non-zero;
  4. stakes gate observed both ways (band 0 -> exactly 0, band >= 1 -> non-zero).
Plus the guards: single writer, open-only inserts, deferred subjects, the empty
window -> unresolved, K never moves a verdict, and the canaries.
"""
import json
import logging
import os
import sqlite3
import tempfile
import time
import unittest
from unittest import mock

from tests import _bootstrap  # noqa: F401

from substrate import connect, Row
from theory_x.stage_world import expectations as X

_STAKES = (0.0, 0, 0.2)
T0 = 1_800_000_000.0
DAY = 86400.0


class _Store(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._env = mock.patch.dict(os.environ, {
            "NEX5_DATA_DIR": self._tmp.name, "NEX5_SCHEMA_TRIPWIRE": "1"})
        self._env.start()
        for f in ("NEX5_EXPECT_LEARN", "NEX5_EXPECT_MOOD", "NEX5_RECONCILER"):
            os.environ.pop(f, None)
        from substrate.init_db import init_all
        init_all()
        from substrate.paths import db_paths
        p = db_paths()
        self.conv, self.bel, self.dyn = str(p["conversations"]), str(p["beliefs"]), str(p["dynamic"])
        self._snap = mock.patch("theory_x.stage_world.frozen_at_made.snapshot_stakes",
                                return_value=_STAKES)
        self._snap.start()
        from theory_x.stage_world import owned_belief
        owned_belief.ensure_schema()

    def tearDown(self):
        self._snap.stop()
        self._env.stop()
        self._tmp.cleanup()

    # -- fixtures ---------------------------------------------------------------
    def _belief(self, content, source, conf=0.7, locked=0, tier=6):
        cx = connect(self.bel)
        try:
            bid = cx.execute(
                "INSERT INTO beliefs (content, tier, confidence, created_at, source, locked, "
                "use_count) VALUES (?, ?, ?, ?, ?, ?, 5)",
                (content, tier, conf, int(T0), source, locked)).lastrowid
            cx.commit()
            return bid
        finally:
            cx.close()

    def _kind(self, bid):
        cx = connect(self.bel)
        try:
            return cx.execute("SELECT source_kind FROM beliefs WHERE id=?", (bid,)).fetchone()[0]
        finally:
            cx.close()

    def _conf(self, bid):
        cx = connect(self.bel)
        try:
            return cx.execute("SELECT confidence FROM beliefs WHERE id=?", (bid,)).fetchone()[0]
        finally:
            cx.close()

    def _expect(self, basis_ids, band, confidence=0.7, cbasis="stated_p", made=T0,
                horizon=DAY, target=None):
        """A producer row in owned_belief_expectations: 'target' holds-claim over
        basis_ids, band as given (band 4 only on an all-authored basis)."""
        from theory_x.stage_world.frozen_at_made import (
            FROZEN_INSERT_COLS, FROZEN_PLACEHOLDERS, basis_entry, frozen_values)
        target = target if target is not None else basis_ids[0]
        basis = [basis_entry(b, self._kind(b), self._conf(b)) for b in basis_ids]
        frozen = frozen_values(confidence, cbasis, 0.0, "exact_label", _STAKES,
                               basis=basis, cost_band=band)
        claimed = {"belief_id": target, "holds": True, "tier": 6, "paused": 0,
                   "erosion_stage": "external"}
        cx = connect(self.conv)
        try:
            rid = cx.execute(
                "INSERT INTO owned_belief_expectations (made_at, belief_id, claimed_state, "
                "resolve_at, state, " + FROZEN_INSERT_COLS + ") VALUES (?,?,?,?, 'open', "
                + FROZEN_PLACEHOLDERS + ")",
                (made, target, json.dumps(claimed), made + horizon, *frozen)).lastrowid
            cx.commit()
            return rid
        finally:
            cx.close()

    def _break(self, bid):
        """Evidence that the belief no longer holds: the harmonizer paused it."""
        cx = connect(self.bel)
        cx.execute("UPDATE beliefs SET paused=1 WHERE id=?", (bid,))
        cx.commit(); cx.close()

    def _valence_of(self, producer_row_id):
        cx = connect(self.conv)
        cx.row_factory = Row
        try:
            return dict(cx.execute(
                "SELECT v.*, e.state AS e_state FROM event_valence v JOIN expectations e "
                "ON e.id = v.expectation_id WHERE e.producer='owned_belief_expectations' "
                "AND e.producer_row_id=?", (producer_row_id,)).fetchone())
        finally:
            cx.close()

    def _all_valence(self):
        cx = connect(self.conv)
        try:
            return [r[0] for r in cx.execute("SELECT valence FROM event_valence")]
        finally:
            cx.close()


class TestPureMath(unittest.TestCase):

    def test_label_kinds_are_magnitude_free(self):
        self.assertEqual(X.adjudicate("exact_label", 0.0, 4, 1.0), ("violated", None, 1.0))
        self.assertEqual(X.adjudicate("strict_direction", 0.0, 4, 0.0), ("confirmed", None, 0.0))

    def test_distance_kind(self):
        self.assertEqual(X.adjudicate("distance", 0.5, 4, 0.25), ("confirmed", 0.5, 0.125))
        state, ratio, sal = X.adjudicate("distance", 0.5, 4, 0.9)
        self.assertEqual((state, ratio), ("violated", 1.8))
        self.assertAlmostEqual(sal, 0.45)
        self.assertEqual(X.adjudicate("distance", 0.5, 4, 4.0)[2], 1.0)    # clamped

    def test_k_never_changes_a_verdict(self):
        for d in [i / 20 for i in range(0, 41)]:
            verdicts = {X.adjudicate("distance", 0.5, k, d)[0] for k in (0.5, 1, 2, 4, 8, 100)}
            self.assertEqual(len(verdicts), 1, d)

    def test_no_evidence_never_reaches_the_divider(self):
        with self.assertRaises(ValueError):
            X.adjudicate("distance", 0.5, 4, None)
        with self.assertRaises(ValueError):
            X.adjudicate("distance", 0.0, 4, 0.3)

    def test_admission_is_a_gate_not_a_weight(self):
        # same violation at confidence 0.51 and 0.99 -> identical valence
        a = X.valence("violated", 1.0, 4, 1.0, "stated_p", 0.51)
        b = X.valence("violated", 1.0, 4, 1.0, "stated_p", 0.99)
        self.assertEqual(a, b)
        self.assertEqual(a[0], -1.0)
        self.assertEqual(X.valence("violated", 1.0, None, 1.0, "stated_p", 0.9)[2],
                         "band_unrecorded")
        for cb, c in (("stated_p", 0.5), ("coin", 0.5), ("none_stated", None)):
            self.assertEqual(X.valence("violated", 1.0, 4, 1.0, cb, c)[:2], (0.0, 0))

    def test_ownership_share(self):
        self.assertEqual(X.ownership([]), 0.0)
        mix = [{"source_kind": k} for k in ("authored", "self", "world", "seeded")]
        self.assertEqual(X.ownership(mix), 0.5)
        self.assertEqual(X.basis_kind(mix), "owned")
        self.assertEqual(X.basis_kind(mix[2:]), "external")


class TestGuards(_Store):

    def _header(self, **kw):
        row = dict(subject="self", producer="test", producer_row_id=1, made_at=T0,
                   claimed_state="{}", ownership=0.0, basis_kind="none", horizon_at=T0,
                   horizon_kind="timer")
        row.update(kw)
        cols = ", ".join(row)
        cx = connect(self.conv)
        try:
            cx.execute(f"INSERT INTO expectations ({cols}) VALUES "
                       f"({', '.join('?' * len(row))})", tuple(row.values()))
            cx.commit()
        finally:
            cx.close()

    def test_deferred_subjects_rejected_and_logged(self):
        for subject in ("commitment", "goal"):
            with self.assertLogs("substrate.guard", "ERROR"):
                with self.assertRaisesRegex(sqlite3.IntegrityError, "deferred subject"):
                    self._header(subject=subject, producer_row_id=hash(subject) % 1000)

    def test_producers_write_open_only(self):
        with self.assertLogs("substrate.guard", "ERROR"):
            with self.assertRaisesRegex(sqlite3.IntegrityError, "open only"):
                self._header(state="confirmed")
        with self.assertLogs("substrate.guard", "ERROR"):
            with self.assertRaises(sqlite3.IntegrityError):
                self._header(resolved_by="reconciler", producer_row_id=2)

    def test_only_the_reconciler_resolves(self):
        self._header()
        cx = connect(self.conv)
        try:
            with self.assertLogs("substrate.guard", "ERROR"):
                with self.assertRaisesRegex(sqlite3.IntegrityError, "not from the reconciler"):
                    cx.execute("UPDATE expectations SET state='violated', resolved_by='producer'")
            cx.execute("UPDATE expectations SET state='violated', resolved_by='reconciler'")
        finally:
            cx.close()

    def test_commitment_terminals_declared(self):
        self.assertIn("breached", X.STATES)
        self.assertIn("released", X.STATES)

    def test_event_valence_never_reads_mood(self):
        # One-way coupling: no SQL or import in the reconciler touches the mood
        # tables (docstrings excluded).
        import ast
        tree = ast.parse(open(X.__file__).read())
        docs = {id(n.body[0].value) for n in ast.walk(tree)
                if isinstance(n, (ast.Module, ast.FunctionDef)) and n.body
                and isinstance(n.body[0], ast.Expr)
                and isinstance(n.body[0].value, ast.Constant)}
        code_strings = [n.value for n in ast.walk(tree)
                        if isinstance(n, ast.Constant) and isinstance(n.value, str)
                        and id(n) not in docs]
        for s in code_strings:
            self.assertNotIn("affect_state", s)
            self.assertNotIn("affect_history", s)
        imports = [a.name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))
                   for a in n.names] + [n.module or "" for n in ast.walk(tree)
                                        if isinstance(n, ast.ImportFrom)]
        self.assertFalse([m for m in imports if "affect" in m])


class TestTwoByTwo(_Store):
    """Identical discrepancy (label miss, d=1) and identical salience (1.0);
    the expectation cells differ ONLY in owned+band>=1 vs external/band 0."""

    def test_one_live_cell_three_exact_zeros(self):
        mine = self._belief("I keep coming back to thresholds", "wonder_loop")
        news = self._belief("Markets slide on rate fears", "fetch_loop")
        owned = self._expect([mine], band=4)
        external = self._expect([news], band=0, target=news)
        self._break(mine); self._break(news)
        X.reconcile(now=T0 + DAY + 1)
        a, b = self._valence_of(owned), self._valence_of(external)
        self.assertEqual((a["state"], a["salience"]), ("violated", 1.0))
        self.assertEqual((b["state"], b["salience"]), ("violated", 1.0))   # matched pair
        self.assertLess(a["valence"], 0.0)                                 # live cell
        self.assertEqual(a["valence"], -1.0)
        self.assertEqual(b["valence"], 0.0)                                # exactly 0
        # load-only spikes, no expectation: a burst of her own beliefs and a burst
        # of sensed events. Nothing to adjudicate -> no valence anywhere.
        before = self._all_valence()
        for i in range(30):
            self._belief(f"burst of my own thought {i}", "fountain_insight")
        cx = connect(self.dyn)
        for i in range(30):
            cx.execute("INSERT INTO surprise_events (triggered_at, prediction_id, "
                       "prediction_type, surprise_score, surprise_flag, big_surprise) "
                       "VALUES (?, 999999, 'external_input', 0.95, 1, 1)", (T0 + 2 * DAY,))
        cx.commit(); cx.close()
        X.reconcile(now=T0 + 3 * DAY)
        self.assertEqual(self._all_valence(), before)
        self.assertEqual(X.mood_nudge(T0 + DAY + 2, T0 + 4 * DAY), 0.0)


class TestTwoChannel(_Store):
    """Learning WITHOUT valence must be observable (cell 2 is the point)."""

    def setUp(self):
        super().setUp()
        os.environ["NEX5_EXPECT_LEARN"] = "1"
        os.environ["NEX5_EXPECT_MOOD"] = "1"

    def _cell(self, basis_source, band, day):
        made = T0 + day * 10 * DAY
        bid = self._belief(f"cell belief {day}", basis_source)
        rid = self._expect([bid], band=band, made=made)
        before = self._conf(bid)
        self._break(bid)
        X.reconcile(now=made + DAY + 1)
        v = self._valence_of(rid)["valence"]
        mood = X.mood_nudge(made, made + 2 * DAY)
        return v, mood, before, self._conf(bid)

    def test_three_cells(self):
        v1, m1, b1, a1 = self._cell("wonder_loop", 4, 1)       # owned, band >= 1
        self.assertLess(v1, 0.0)
        self.assertTrue(-X.MOOD_CAP <= m1 < 0.0)                # moves, within cap
        self.assertLess(a1, b1)                                 # confidence moves

        v2, m2, b2, a2 = self._cell("synergized", 0, 2)        # owned, band 0
        self.assertEqual(v2, 0.0)
        self.assertEqual(m2, 0.0)
        self.assertLess(a2, b2)                                 # learning without valence

        v3, m3, b3, a3 = self._cell("fetch_loop", 0, 3)        # external
        self.assertEqual(v3, 0.0)
        self.assertEqual(m3, 0.0)
        self.assertLess(a3, b3)                                 # it still learns


class TestFalsifierAndStakesGate(_Store):

    def test_moderate_confidence_high_cost_violation_is_non_zero(self):
        mine = self._belief("what I attend to changes me", "wonder_loop", conf=0.55)
        rid = self._expect([mine], band=4, confidence=0.55)
        self._break(mine)
        X.reconcile(now=T0 + DAY + 1)
        self.assertEqual(self._valence_of(rid)["valence"], -1.0)

    def test_gate_observed_both_ways(self):
        a = self._belief("first of mine", "wonder_loop")
        b = self._belief("second of mine", "wonder_loop")
        open_ = self._expect([a], band=1)
        shut = self._expect([b], band=0, target=b)
        self._break(a); self._break(b)
        X.reconcile(now=T0 + DAY + 1)
        self.assertEqual(self._valence_of(open_)["valence"], -0.25)
        self.assertEqual(self._valence_of(shut)["valence"], 0.0)
        h = X.stakes_histogram()
        self.assertEqual(h[0], {"resolved": 1, "valence_nonzero": 0})
        self.assertEqual(h[1], {"resolved": 1, "valence_nonzero": 1})

    def test_confirm_is_small_and_only_at_band_one_plus(self):
        a = self._belief("holds fine", "wonder_loop")
        b = self._belief("holds too", "wonder_loop")
        hi = self._expect([a], band=4)
        lo = self._expect([b], band=0, target=b)
        X.reconcile(now=T0 + DAY + 1)
        self.assertEqual(self._valence_of(hi)["valence"], X.CONFIRM_POSITIVE)
        self.assertEqual(self._valence_of(lo)["valence"], 0.0)


class TestLearning(_Store):

    def test_off_by_default(self):
        mine = self._belief("dark by default", "wonder_loop")
        self._expect([mine], band=4)
        self._break(mine)
        X.reconcile(now=T0 + DAY + 1)
        self.assertEqual(self._conf(mine), 0.7)

    def test_distributed_and_seeded_locked_untouched(self):
        os.environ["NEX5_EXPECT_LEARN"] = "1"
        target = self._belief("the claim", "wonder_loop")
        others = [self._belief(f"peer {i}", "synergized") for i in range(3)]
        seeded = self._belief("I am the one who attends.", "identity", tier=1, locked=1)
        locked = self._belief("a locked one", "fountain_insight", locked=1)
        self._expect([target, *others, seeded, locked], band=1, target=target)
        self._break(target)
        X.reconcile(now=T0 + DAY + 1)
        n = 4                                        # seeded + locked are excluded
        expect = 0.7 * (1 - X.LEARN_VIOLATE / n)
        for bid in (target, *others):
            self.assertAlmostEqual(self._conf(bid), expect)
        self.assertEqual(self._conf(seeded), 0.7)
        self.assertEqual(self._conf(locked), 0.7)

    def test_confirm_consolidates_load_only_moves_nothing(self):
        os.environ["NEX5_EXPECT_LEARN"] = "1"
        mine = self._belief("still true", "wonder_loop")
        self._expect([mine], band=4)
        idle = self._belief("nobody expects anything of me", "wonder_loop")
        X.reconcile(now=T0 + DAY + 1)
        self.assertAlmostEqual(self._conf(mine), 0.7 * (1 + X.LEARN_CONFIRM))
        self.assertEqual(self._conf(idle), 0.7)


class TestProducersThroughTheLedger(_Store):

    def test_self_and_world_are_learning_only(self):
        from theory_x.stage_world import self_prediction as sp, world_predictions as wp
        sp.ensure_schema(self.conv)
        with mock.patch.object(sp, "snapshot_stakes", return_value=_STAKES):
            sp._insert_pred(self.conv, "selfdesc_novel", [("self", "same"), ("random", "same")],
                            T0 + 60, confidence=0.9)
        with mock.patch.object(wp, "fetch_price", return_value=100.0):
            wp.make_prediction("bitcoin", "up", 60, db_path=self.conv, source="voice")
        cx = connect(self.conv)
        cx.execute("UPDATE self_predictions SET made_at=?, resolve_at=?", (T0, T0 + 60))
        cx.execute("UPDATE self_predictions SET actual='differ', resolved_at=?", (T0 + 61,))
        cx.execute("UPDATE world_predictions SET made_at=?, resolve_at=?, price_at_resolve=99, "
                   "outcome='wrong', resolved_at=?", (T0, T0 + 60, T0 + 61))
        cx.commit(); cx.close()
        X.reconcile(now=T0 + 120)
        cx = connect(self.conv)
        rows = cx.execute("SELECT e.producer, e.state, v.valence, v.reason FROM expectations e "
                          "JOIN event_valence v ON v.expectation_id = e.id ORDER BY e.id").fetchall()
        cx.close()
        self.assertEqual(len(rows), 3)
        for producer, state, val, reason in rows:
            self.assertEqual(state, "violated")
            self.assertEqual(val, 0.0)                 # no basis -> never valence
        reasons = {r[3] for r in rows}
        self.assertEqual(reasons, {"band_0", "confidence_not_admitted"})

    def test_surprise_empty_window_is_unresolved_never_violated(self):
        cx = connect(self.dyn)
        from theory_x.stage_world.frozen_at_made import (
            FROZEN_INSERT_COLS, FROZEN_PLACEHOLDERS, frozen_values)
        ids = []
        for score, content in ((1.0, None), (0.9, "a real different thing"), (0.2, "close")):
            f = frozen_values(None, "none_stated", 0.5, "distance", _STAKES, basis=[], cost_band=0)
            pid = cx.execute(
                "INSERT INTO predictions (made_at, target_window_end, prediction_type, "
                "centroid_embedding, verified_at, surprise_score, surprise_flag, "
                + FROZEN_INSERT_COLS + ") VALUES (?,?,?,?,?,?,?, " + FROZEN_PLACEHOLDERS + ")",
                (T0, T0 + 300, "internal_belief", b"\x00", T0 + 301, score,
                 int(score > 0.5), *f)).lastrowid
            cx.execute("INSERT INTO surprise_events (triggered_at, prediction_id, prediction_type, "
                       "surprise_score, surprise_flag, big_surprise, actual_content) "
                       "VALUES (?,?,?,?,?,?,?)", (T0 + 301, pid, "internal_belief", score,
                                                  int(score > 0.5), int(score > 0.8), content))
            ids.append(pid)
        cx.commit(); cx.close()
        X.reconcile(now=T0 + 400)
        cx = connect(self.conv)
        got = dict(cx.execute("SELECT producer_row_id, state FROM expectations "
                              "WHERE producer='predictions'").fetchall())
        cx.close()
        self.assertEqual([got[i] for i in ids], ["unresolved", "violated", "confirmed"])


class TestCanaries(_Store):

    def test_unresolved_rate_and_band0_leak(self):
        cx = connect(self.conv)
        for i in range(25):
            cx.execute("INSERT INTO expectations (subject, producer, producer_row_id, made_at, "
                       "claimed_state, ownership, basis_kind, horizon_at, horizon_kind) "
                       "VALUES ('surprise', 'predictions', ?, ?, '{}', 0, 'none', ?, 'window')",
                       (i, T0, T0))
        cx.execute("UPDATE expectations SET state='unresolved', resolved_at=?, "
                   "resolved_by='reconciler' WHERE producer_row_id < 20", (T0 + 10,))
        cx.execute("INSERT INTO event_valence (expectation_id, ts, valence, admitted, reason, "
                   "state, cost_band) VALUES (21, ?, -0.1, 1, 'x', 'violated', 0)", (T0,))
        cx.commit(); cx.close()
        got = {c[0]: c for c in X.canaries(now=T0 + 100)}
        self.assertTrue(got["unresolved_rate"][3])
        self.assertTrue(got["stakes_gate"][3])               # band 0 leaked valence

    def test_confidence_drift_flags_five_straight_falls(self):
        mine = self._belief("drifting", "wonder_loop", conf=0.9)
        cx = connect(self.conv)
        for v in (0.95, 0.94, 0.93, 0.92):
            cx.execute("INSERT INTO expectation_canary_log (ts, name, value, n, flag) "
                       "VALUES (?, 'confidence_drift', ?, 1, 0)", (T0, v))
        cx.commit(); cx.close()
        got = {c[0]: c for c in X.canaries(now=T0)}
        self.assertTrue(got["confidence_drift"][3])
        msg = X.record_canaries(now=T0)
        self.assertIn("confidence_drift", msg)


class TestAffectCoupling(_Store):

    def _tick(self, flag):
        from substrate import Reader, Writer
        from theory_x.stage_affect.affect_state import AffectState
        if flag:
            os.environ["NEX5_EXPECT_MOOD"] = "1"
        else:
            os.environ.pop("NEX5_EXPECT_MOOD", None)
        w = Writer(self.conv, name="conversations")
        self.addCleanup(w.close)
        a = AffectState(w, Reader(self.conv), Reader(self.bel), dynamic_reader=Reader(self.dyn))
        a._last_updated = time.time() - 60
        a._valence = 0.0
        a._background_tick()
        return a._valence

    def test_flag_gates_the_nudge(self):
        cx = connect(self.conv)
        cx.execute("INSERT INTO expectations (subject, producer, producer_row_id, made_at, "
                   "claimed_state, ownership, basis_kind, horizon_at, horizon_kind) "
                   "VALUES ('self', 'owned_belief_expectations', 1, 0, '{}', 1, 'owned', 0, 'timer')")
        cx.execute("INSERT INTO affect_nudges (expectation_id, ts, valence) VALUES (1, ?, -1.0)",
                   (time.time() - 30,))
        cx.commit(); cx.close()
        off, on = self._tick(False), self._tick(True)
        self.assertLess(on, off)
        self.assertGreaterEqual(on - off, -X.MOOD_CAP - 1e-9)


if __name__ == "__main__":
    unittest.main()
