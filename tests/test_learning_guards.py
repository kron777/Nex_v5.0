"""Learning guards G1-G4, the subtraction rule, and the two pinned structural claims.

Every guard has a POSITIVE control (must fire) and a NEGATIVE control (must not):
a guard that can print the same number for two different causes is not a guard.
"""
import json
import os
import sqlite3
import tempfile
import time
import unittest
from unittest import mock

from tests import _bootstrap  # noqa: F401

from substrate import connect, Row
from theory_x.stage_world import expectations as X
from theory_x.stage_world import learning_guards as G

T0 = 1_800_000_000.0
H, DAY = 3600.0, 86400.0


class _Store(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._env = mock.patch.dict(os.environ, {
            "NEX5_DATA_DIR": self._tmp.name, "NEX5_SCHEMA_TRIPWIRE": "1",
            "NEX5_EXPECT_LEARN": "1"})
        self._env.start()
        for f in ("NEX5_LEARN_CAP", "NEX5_LEARN_RATIO_SUBTRACT", "NEX5_LEARN_ATTRIBUTION_SUBTRACT"):
            os.environ.pop(f, None)
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

    def _learn(self, ids, basis_kind, state="confirmed", sal=1.0, at=T0, band=1):
        self._n += 1
        basis = [{"belief_id": b, "source_kind": "authored", "confidence": None} for b in ids]
        cx = connect(self.conv)
        cx.row_factory = Row
        try:
            eid = cx.execute(
                "INSERT INTO expectations (subject, producer, producer_row_id, made_at, "
                "claimed_state, cost_band, basis_snapshot, ownership, basis_kind, horizon_at, "
                "horizon_kind) VALUES ('surprise','predictions',?,?,'{}',?,?,?,?,?,'window')",
                (self._n, at, band, json.dumps(basis), 1.0 if basis_kind == "owned" else 0.0,
                 basis_kind, at)).lastrowid
            e = cx.execute("SELECT * FROM expectations WHERE id=?", (eid,)).fetchone()
            X._learn(cx, e, state, sal, at)
            cx.commit()
        finally:
            cx.close()

    def _log_rows(self, bid):
        cx = connect(self.conv)
        try:
            return cx.execute("SELECT basis_kind, before, after, factor, skipped FROM "
                              "expectation_learning_log WHERE belief_id=? ORDER BY id",
                              (bid,)).fetchall()
        finally:
            cx.close()


# ----------------------------------------------------------------------- G1 --

class TestCap(_Store):

    def _basis(self, bid):
        """bid plus 9 fillers: a 10-row basis, so each step is ~0.001 like live."""
        if not hasattr(self, "_fillers"):
            self._fillers = [self._belief(f"filler {i}", source="fetch_loop") for i in range(9)]
        return [bid] + self._fillers

    def _cum(self, bid):
        cx = connect(self.conv)
        try:
            return G.cumulative_external(cx, bid)
        finally:
            cx.close()

    def _fill_to_edge(self, bid):
        """External confirms (cap OFF) until the NEXT step would cross 0.02."""
        for _ in range(100):
            step = self._conf(bid) * X.LEARN_CONFIRM / 10
            if self._cum(bid) + step > G.EXTERNAL_CAP:
                return
            self._learn(self._basis(bid), "external")
        raise AssertionError("never reached the cap edge")

    def test_boundary_skips_whole_never_clips(self):
        bid = self._belief("mine", conf=0.7)
        self._fill_to_edge(bid)
        cum, before = self._cum(bid), self._conf(bid)
        step = before * X.LEARN_CONFIRM / 10
        self.assertLessEqual(cum, G.EXTERNAL_CAP)
        self.assertGreater(cum + step, G.EXTERNAL_CAP)          # e.g. 0.019x + 0.0011 > 0.02
        self.assertGreater(cum, 0.018)
        os.environ["NEX5_LEARN_CAP"] = "1"
        with self.assertLogs("theory_x.stage_world.learning_guards", "WARNING"):
            self._learn(self._basis(bid), "external")
        self.assertEqual(self._conf(bid), before)                # nothing applied, no clipping
        last = self._log_rows(bid)[-1]
        self.assertEqual((last[0], last[1], last[2], last[3], last[4]),
                         ("external", before, before, None, 1))   # logged as skipped
        self._learn(self._basis(bid), "external")                 # second skip: no new finding
        cx = connect(self.conv)
        self.assertEqual(cx.execute("SELECT COUNT(*) FROM learning_cap_hits").fetchone()[0], 1)
        cx.close()
        self._learn([bid], "owned")                               # owned: uncapped
        self.assertGreater(self._conf(bid), before)
        mixed = X.reconstruct_without_external(bid, self._conf(bid))   # skips are no-ops
        self.assertTrue(mixed["reconstructable"])
        owned_only = 0.7                                          # strip external: owned only
        for kind, b0, a0, factor, skipped in self._log_rows(bid):
            if kind == "owned":
                owned_only *= factor
        self.assertAlmostEqual(mixed["confidence"], owned_only, places=12)

    def test_self_kind_capped_world_kind_not_flag_off_uncapped(self):
        os.environ["NEX5_LEARN_CAP"] = "1"
        mine = self._belief("a witnessed thing", source="witness_loop")   # kind 'self'
        news = self._belief("a headline", source="fetch_loop")            # kind 'world'
        for _ in range(3):                                                 # 1-row basis: ~0.01/step
            self._learn([mine], "external")
            self._learn([news], "external")
        c0, n0 = self._conf(mine), self._conf(news)
        self.assertEqual(c0, self._conf(mine))
        self._learn([mine], "external")
        self.assertEqual(self._conf(mine), c0)                             # 'self' kind: capped
        self._learn([news], "external")
        self.assertGreater(self._conf(news), n0)                           # 'world' kind: not
        os.environ.pop("NEX5_LEARN_CAP")
        self._learn([mine], "external")                                    # flag off: applies
        self.assertGreater(self._conf(mine), c0)

    def test_subtraction_reopens_headroom_and_over_cap_report(self):
        bid = self._belief("mine")
        for i in range(25):
            self._learn([bid], "external", at=T0 + i)
        self.assertEqual([b for b, _ in G.over_cap()], [bid])               # report at flip
        G.subtract([bid], T0 - 1, T0 + 100, "test", "w1", now=T0 + 200)
        cx = connect(self.conv)
        self.assertAlmostEqual(G.cumulative_external(cx, bid), 0.0, places=12)
        cx.close()
        self.assertEqual(G.over_cap(), [])


# ----------------------------------------------------------------------- G2 --

class TestRatio(_Store):

    def _ticks(self, now, ext, own, n=96, gap=None):
        cx = connect(self.conv)
        for i in range(n):
            ts = now - DAY + 60 + i * 900
            e = ext if gap is None or i != gap else own
            cx.execute("INSERT INTO learning_guard_ticks (ts, external, owned) VALUES (?,?,?)",
                       (ts, e, own))
        cx.commit(); cx.close()

    def test_sustained_needs_every_tick_over_a_covered_24h(self):
        now = T0 + 5 * DAY
        self._ticks(now, 0.03, 0.01)
        self.assertTrue(G.ratio_status(now)["sustained_2x"])
        cx = connect(self.conv)
        cx.execute("DELETE FROM learning_guard_ticks")
        cx.commit(); cx.close()
        self._ticks(now, 0.03, 0.01, gap=40)                     # one tick below 2x
        self.assertFalse(G.ratio_status(now)["sustained_2x"])
        cx = connect(self.conv)
        cx.execute("DELETE FROM learning_guard_ticks")
        cx.commit(); cx.close()
        self._ticks(now, 0.03, 0.01, n=20)                       # not covered
        self.assertFalse(G.ratio_status(now)["sustained_2x"])

    def test_observational_tier_always_visible(self):
        bid = self._belief("mine")
        self._learn([bid], "external", at=T0)
        self.assertTrue(G.ratio_status(T0 + 10)["observational"])

    def test_auto_subtract_exact_idempotent_reversible_and_silent(self):
        os.environ["NEX5_LEARN_RATIO_SUBTRACT"] = "1"
        now = T0 + 2 * DAY
        a = self._belief("first", conf=0.7)
        self._learn([a], "owned", at=now - 30 * H)                 # outside window: kept
        for i in range(6):
            self._learn([a], "external", at=now - 20 * H + i)       # inside: removed
        self._learn([a], "owned", at=now - 10 * H)                  # inside but owned: kept
        expected = X.replay(a, self._conf(a), lambda r: r["basis_kind"] != "owned" and
                            r["ts"] > now - DAY, False)["confidence"]
        full_before = X.reconstruct_without_external(a, self._conf(a))["confidence"]
        cx = connect(self.conv)
        counts = lambda: (cx.execute("SELECT COUNT(*) FROM event_valence").fetchone()[0],  # noqa
                          cx.execute("SELECT COUNT(*) FROM expectations WHERE state != 'open'"
                                     ).fetchone()[0])
        before_counts = counts()
        self._ticks(now, 0.03, 0.01)
        out = G.run(now)
        self.assertEqual(out["subtracted"], 1)
        self.assertAlmostEqual(self._conf(a), expected, places=12)
        self.assertEqual(G.run(now)["subtracted"], 0)                # idempotent
        self.assertEqual(counts(), before_counts)                   # no valence, no resolution
        cx.close()
        b = connect(self.bel)
        self.assertEqual(b.execute("SELECT COUNT(*) FROM undo_events").fetchone()[0], 0)
        b.close()
        self.assertAlmostEqual(X.reconstruct_without_external(a, self._conf(a))["confidence"],
                               full_before, places=12)              # no double subtraction
        cx = connect(self.conv)
        sid, rr = cx.execute("SELECT id, review_required FROM learning_subtractions").fetchone()
        cx.close()
        self.assertEqual(rr, 1)
        G.revert_subtraction(sid, now + 1)
        self.assertAlmostEqual(self._conf(a), X.replay(a, self._conf(a), lambda r: False,
                                                       False)["confidence"], places=12)


# ------------------------------------------------------------------ Part 2 --

class TestAttribution(_Store):

    def test_external_only_belief_fails_mixed_does_not(self):
        now = T0 + DAY
        ext_only = self._belief("only sensed movement")
        mixed = self._belief("mixed")
        big = self._belief("big but attributed")
        for i in range(3):
            self._learn([ext_only], "external", at=now - H + i)
        self._learn([mixed], "external", at=now - H)
        self._learn([mixed], "owned", at=now - H + 1)
        for i in range(15):                                          # magnitude alone
            self._learn([big], "external", at=now - H + i)
        self._learn([big], "owned", "violated", at=now - H + 20)
        f = G.attribution_failures(now)
        self.assertIn(ext_only, f["failed"])
        self.assertNotIn(mixed, f["failed"])
        self.assertNotIn(big, f["failed"])
        self.assertEqual(G.run(now)["subtracted"], 0)               # flag off: nothing
        os.environ["NEX5_LEARN_ATTRIBUTION_SUBTRACT"] = "1"
        c0 = self._conf(ext_only)
        self.assertEqual(G.run(now)["subtracted"], 1)
        self.assertLess(self._conf(ext_only), c0)

    def test_counterfactual_material_only_when_a_threshold_is_crossed(self):
        near = self._belief("near the line", conf=0.497)
        far = self._belief("far from any line", conf=0.30)
        for i in range(4):
            self._learn([near], "external", at=T0 + i)
            self._learn([far], "external", at=T0 + i)
        m = G.counterfactual_material()
        hits = {x["belief_id"]: x["crosses"] for x in m["material"]}
        self.assertEqual(hits, {near: [0.5]})


# ------------------------------------------------------------------- G3/G4 --

class TestSymmetry(_Store):

    def _stream(self, signs, start):
        bid = self._belief("streamed", conf=0.1)       # low start: stay clear of the 0.99 clamp
        for i, up in enumerate(signs):
            self._learn([bid], "external", "confirmed" if up else "violated",
                        at=start + i * (4 * DAY / len(signs)))

    def test_all_up_over_days_is_a_ratchet(self):
        now = T0 + 5 * DAY
        self._stream([True] * 60, now - 4 * DAY)
        s = G.sign_symmetry(now)
        self.assertEqual((s["up"], s["down"], s["run"]), (60, 0, 60))
        self.assertTrue(s["ratchet"])

    def test_balanced_or_short_is_not(self):
        now = T0 + 5 * DAY
        self._stream([i % 2 == 0 for i in range(60)], now - 4 * DAY)
        self.assertFalse(G.sign_symmetry(now)["ratchet"])

    def test_one_day_of_all_up_is_not_yet_persistent(self):
        now = T0 + 5 * DAY
        bid = self._belief("short", conf=0.1)
        for i in range(60):
            self._learn([bid], "external", at=now - DAY + i * 60)
        self.assertFalse(G.sign_symmetry(now)["ratchet"])


class TestComposition(_Store):

    def _expectation(self, producer, kinds, made):
        self._n += 1
        cx = connect(self.conv)
        cx.execute("INSERT INTO expectations (subject, producer, producer_row_id, made_at, "
                   "claimed_state, basis_snapshot, ownership, basis_kind, horizon_at, "
                   "horizon_kind) VALUES ('surprise', ?, ?, ?, '{}', ?, 0, 'external', ?, "
                   "'window')", (producer, self._n, made,
                                 json.dumps([{"belief_id": 1, "source_kind": k} for k in kinds]),
                                 made))
        cx.commit(); cx.close()

    def test_skew_needs_three_sustained_days(self):
        now = T0 + 10 * DAY
        self._expectation("predictions", ["world"] * 8 + ["authored"] * 2, now - H)
        self._expectation("owned_belief_expectations", ["authored"], now - H)
        c = G.composition(now)
        self.assertEqual((c["surprise"], c["owned_belief"]), (0.8, 0.0))
        self.assertFalse(c["skew"])                                   # one day only
        cx = connect(self.conv)
        for v in (0.7, 0.75):
            cx.execute("INSERT INTO expectation_canary_log (ts, name, value, n, flag) "
                       "VALUES (?, 'composition.surprise', ?, 0, 0)", (now, v))
        cx.commit(); cx.close()
        self.assertTrue(G.composition(now)["skew"])

    def test_stable_low_composition_does_not_flag(self):
        now = T0 + 10 * DAY
        self._expectation("predictions", ["authored"] * 7 + ["world"] * 3, now - H)
        cx = connect(self.conv)
        for v in (0.3, 0.3):
            cx.execute("INSERT INTO expectation_canary_log (ts, name, value, n, flag) "
                       "VALUES (?, 'composition.surprise', ?, 0, 0)", (now, v))
        cx.commit(); cx.close()
        self.assertFalse(G.composition(now)["skew"])

    def test_sampling_pool_is_recorded_per_tick(self):
        for i in range(10):
            self._belief(f"recent headline {i}", source="fetch_loop")
        t = G.record_tick(T0)
        self.assertEqual(t["pool_external_share"], 1.0)


# --------------------------------------------------------------------- pins --

class TestPinnedStructure(_Store):

    def test_a1_both_verdicts_resolve_only_at_horizon(self):
        src = open(os.path.join(os.path.dirname(X.__file__), "..", "stage_prediction",
                                "predictive_substrate.py")).read()
        self.assertIn("WHERE target_window_end <= ? AND verified_at IS NULL", src)
        from theory_x.stage_world.frozen_at_made import (
            FROZEN_INSERT_COLS, FROZEN_PLACEHOLDERS, frozen_values)
        from substrate.paths import db_paths
        dx = connect(str(db_paths()["dynamic"]))
        for score, content in ((0.9, "missed"), (0.2, "hit")):
            f = frozen_values(None, "none_stated", 0.5, "distance", (0.0, 0, 0.0),
                              basis=[], cost_band=0)
            pid = dx.execute("INSERT INTO predictions (made_at, target_window_end, "
                             "prediction_type, centroid_embedding, verified_at, surprise_score, "
                             + FROZEN_INSERT_COLS + ") VALUES (?,?,?,?,?,?, "
                             + FROZEN_PLACEHOLDERS + ")",
                             (T0, T0 + 300, "internal_belief", b"\x00", T0 + 1, score, *f)).lastrowid
            dx.execute("INSERT INTO surprise_events (triggered_at, prediction_id, prediction_type, "
                       "surprise_score, surprise_flag, big_surprise, actual_content) "
                       "VALUES (?,?,?,?,0,0,?)", (T0 + 1, pid, "internal_belief", score, content))
        dx.commit(); dx.close()
        X.reconcile(now=T0 + 299)                                  # verified, not yet at horizon
        cx = connect(self.conv)
        self.assertEqual({s for (s,) in cx.execute("SELECT state FROM expectations")}, {"open"})
        cx.close()
        X.reconcile(now=T0 + 300)
        cx = connect(self.conv)
        self.assertEqual(sorted(s for (s,) in cx.execute("SELECT state FROM expectations")),
                         ["confirmed", "violated"])
        cx.close()

    def test_a2_erosion_never_writes_source_kind_and_ownership_ignores_it(self):
        from theory_x.stage3_world_model import erosion
        self.assertNotIn("source_kind", open(erosion.__file__).read())
        from substrate import Reader, Writer
        news = self._belief("a headline she keeps reading", source="fetch_loop")
        cx = connect(self.bel)
        cx.execute("UPDATE beliefs SET reinforce_count = 10 WHERE id = ?", (news,))
        cx.commit(); cx.close()
        w = Writer(self.bel, name="beliefs")
        try:
            erosion.ProvenanceErosion(w, Reader(self.bel))._erosion_check(news)
        finally:
            w.close()
        cx = connect(self.bel)
        stage, kind = cx.execute("SELECT erosion_stage, source_kind FROM beliefs WHERE id=?",
                                 (news,)).fetchone()
        cx.close()
        self.assertEqual((stage, kind), ("nex_absorbed", "world"))
        basis = [{"source_kind": "world", "erosion_stage": "nex_core"}]
        self.assertEqual(X.ownership(basis), 0.0)                    # ageing never owns it

    def test_a2b_source_kind_immutable_once_set(self):
        bid = self._belief("a headline", source="fetch_loop")
        cx = connect(self.bel)
        try:
            with self.assertRaisesRegex(sqlite3.IntegrityError, "immutable"):
                cx.execute("UPDATE beliefs SET source_kind = 'authored' WHERE id = ?", (bid,))
            with self.assertRaisesRegex(sqlite3.IntegrityError, "immutable"):
                cx.execute("UPDATE beliefs SET source_kind = NULL WHERE id = ?", (bid,))
            cx.execute("UPDATE beliefs SET source_kind = 'world' WHERE id = ?", (bid,))  # same: ok
        finally:
            cx.close()


if __name__ == "__main__":
    unittest.main()
