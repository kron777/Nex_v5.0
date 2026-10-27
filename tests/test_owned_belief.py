"""Build B PR1: frozen basis snapshot + cost band on every producer row, and the
owned-belief producer.

Pinned here:
  * every producer row records basis_snapshot (beliefs + their source_kind +
    confidence AT made_at) and its cost band; self/world probes record [] --
    ownership 0, the honest result;
  * the surprise producer's internal_belief basis is the beliefs it averaged;
  * band 4 is refused at write time unless the whole basis is authored;
  * owned-belief draws UNIFORMLY from every eligible belief -- the candidate set
    is never narrowed toward easy ones -- and writes 'open' only;
  * the confirmation-rate canary fires above 90% over >= 20 resolutions.
"""
import json
import os
import random
import sqlite3
import tempfile
import time
import unittest
from unittest import mock

from tests import _bootstrap  # noqa: F401

from substrate import connect, Row

_STAKES = (0.0, 0, 0.2)


class _Store(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._env = mock.patch.dict(os.environ, {
            "NEX5_DATA_DIR": self._tmp.name, "NEX5_SCHEMA_TRIPWIRE": "1"})
        self._env.start()
        from substrate.init_db import init_all
        init_all()
        from substrate.paths import db_paths
        p = db_paths()
        self.conv, self.bel, self.dyn = str(p["conversations"]), str(p["beliefs"]), str(p["dynamic"])
        self._snap = mock.patch("theory_x.stage_world.frozen_at_made.snapshot_stakes",
                                return_value=_STAKES)
        self._snap.start()

    def tearDown(self):
        self._snap.stop()
        self._env.stop()
        self._tmp.cleanup()

    def _belief(self, content, source, use_count=5, locked=0, paused=0, conf=0.7):
        cx = connect(self.bel)
        try:
            bid = cx.execute(
                "INSERT INTO beliefs (content, tier, confidence, created_at, source, locked, "
                "paused, use_count) VALUES (?, 6, ?, ?, ?, ?, ?, ?)",
                (content, conf, int(time.time()), source, locked, paused, use_count)).lastrowid
            cx.commit()
            return bid
        finally:
            cx.close()

    def _rows(self, db, table):
        cx = connect(db)
        cx.row_factory = Row
        try:
            return [dict(r) for r in cx.execute(f"SELECT * FROM {table} ORDER BY id")]
        finally:
            cx.close()


class TestBasisOnEveryProducer(_Store):

    def test_self_and_world_record_empty_basis(self):
        from theory_x.stage_world import self_prediction as sp, world_predictions as wp
        sp.ensure_schema(self.conv)
        with mock.patch.object(sp, "snapshot_stakes", return_value=_STAKES):
            sp._insert_pred(self.conv, "authored_30m", [("self", "yes"), ("random", "no")],
                            time.time() + 60)
        with mock.patch.object(wp, "fetch_price", return_value=100.0):
            wp.make_prediction("bitcoin", "up", 60, db_path=self.conv, source="voice")
        for r in self._rows(self.conv, "self_predictions"):
            self.assertEqual((json.loads(r["basis_snapshot"]), r["cost_band"], r["salience_k"]),
                             ([], 0, 4.0))
        w = self._rows(self.conv, "world_predictions")[0]
        self.assertEqual((json.loads(w["basis_snapshot"]), w["cost_band"]), ([], 1))

    def test_surprise_internal_records_the_beliefs_it_averaged(self):
        import numpy as np
        from substrate import Reader, Writer
        from theory_x.stage_prediction.predictive_substrate import PredictiveSubstrate
        ids = [self._belief(f"thought number {i}", "fountain_insight") for i in range(3)]
        ids.append(self._belief("a headline", "precipitated_from_sense"))
        cx = connect(self.bel)   # make them the most recent (init seeds share this second)
        cx.execute(f"UPDATE beliefs SET created_at = created_at + 100 WHERE id IN "
                   f"({','.join(map(str, ids))})")
        cx.commit(); cx.close()
        w = Writer(self.dyn, name="dynamic")
        self.addCleanup(w.close)
        ps = PredictiveSubstrate(Reader(self.dyn), w, Reader(self.bel), Reader(self.conv),
                                 Reader(self.dyn))
        with mock.patch.object(PredictiveSubstrate, "_embed_belief",
                               staticmethod(lambda i, c: np.ones(8, dtype=np.float32))), \
             mock.patch.object(PredictiveSubstrate, "_embed",
                               staticmethod(lambda c: np.ones(8, dtype=np.float32))), \
             mock.patch.object(PredictiveSubstrate, "_dist", staticmethod(lambda a, b: 0.1)):
            self.assertEqual(ps._predict_internal(), 1)
        row = self._rows(self.dyn, "predictions")[-1]
        basis = json.loads(row["basis_snapshot"])
        got = {b["belief_id"]: b["source_kind"] for b in basis}
        for i in ids[:3]:
            self.assertEqual(got[i], "authored")
        self.assertEqual(got[ids[3]], "received")      # sense row with no stream
        self.assertEqual((row["cost_band"], row["tolerance"], row["tolerance_basis"],
                          row["confidence_basis"], row["frozen"]),
                         (1, 0.5, "distance", "none_stated", "at_made"))

    def test_basis_is_frozen(self):
        from theory_x.stage_world import world_predictions as wp
        with mock.patch.object(wp, "fetch_price", return_value=100.0):
            pid = wp.make_prediction("bitcoin", "up", 60, db_path=self.conv, source="voice")
        cx = connect(self.conv)
        try:
            for sql in ("UPDATE world_predictions SET basis_snapshot='[1]' WHERE id=?",
                        "UPDATE world_predictions SET cost_band=4 WHERE id=?"):
                with self.assertRaisesRegex(sqlite3.IntegrityError, "frozen-at-made"):
                    cx.execute(sql, (pid,))
        finally:
            cx.close()

    def test_predictions_legacy_rows_marked_on_init(self):
        cx = connect(self.dyn)
        cx.execute("DROP TRIGGER IF EXISTS trg_predictions_frozen_at_made")
        cx.execute("ALTER TABLE predictions RENAME TO predictions_new")
        cx.execute("CREATE TABLE predictions (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                   "made_at REAL NOT NULL, target_window_end REAL NOT NULL, "
                   "prediction_type TEXT NOT NULL, centroid_embedding BLOB NOT NULL, "
                   "representative_content TEXT, verified_at REAL, surprise_score REAL, "
                   "surprise_flag INTEGER, tags TEXT NOT NULL DEFAULT '[]')")
        cx.execute("DROP TABLE predictions_new")
        cx.execute("INSERT INTO predictions (made_at, target_window_end, prediction_type, "
                   "centroid_embedding) VALUES (1, 2, 'internal_belief', x'00')")
        cx.commit(); cx.close()
        from substrate.init_db import init_all
        init_all()
        r = self._rows(self.dyn, "predictions")[0]
        self.assertEqual((r["frozen"], r["basis_snapshot"]), ("legacy_unfrozen", None))


class TestBandFourGuard(_Store):

    def test_refused_on_a_non_authored_basis(self):
        from theory_x.stage_world.frozen_at_made import basis_entry, frozen_values
        for basis in ([], [basis_entry(1, "world", 0.7)],
                      [basis_entry(1, "authored", 0.7), basis_entry(2, "self", 0.5)]):
            with self.assertLogs("theory_x.stage_world.frozen_at_made", "ERROR"):
                with self.assertRaises(ValueError):
                    frozen_values(0.7, "stated_p", 0.0, "exact_label", _STAKES,
                                  basis=basis, cost_band=4)
        ok = frozen_values(0.7, "stated_p", 0.0, "exact_label", _STAKES,
                           basis=[basis_entry(1, "authored", 0.7)], cost_band=4)
        self.assertEqual(ok[-3], 4)
        with self.assertRaises(ValueError):
            frozen_values(0.7, "stated_p", 0.0, "exact_label", _STAKES, cost_band=5)


class TestOwnedBeliefProducer(_Store):

    def test_eligibility(self):
        from theory_x.stage_world import owned_belief as ob
        good = self._belief("i keep returning to thresholds", "wonder_loop")
        self._belief("too new", "wonder_loop", use_count=1)
        self._belief("locked", "fountain_insight", locked=1)
        self._belief("paused", "synergized", paused=1)
        self._belief("a headline", "precipitated_from_sense")
        self._belief("a witness note", "witness_loop")
        self.assertEqual(ob.eligible_ids(), [good])

    def test_draws_uniformly_from_every_eligible_belief(self):
        from theory_x.stage_world import owned_belief as ob
        ids = [self._belief(f"mine {i}", "fountain_insight", conf=0.3 + 0.1 * i)
               for i in range(5)]
        seen = []

        class _Rec(random.Random):
            def choice(self, seq):
                seen.append(list(seq))
                return super().choice(seq)
        out = ob.make_owned_belief_expectation(rng=_Rec(7))
        # the whole eligible set reaches the draw: nothing filtered by ease/confidence
        self.assertEqual(sorted(seen[0]), sorted(ids))
        # and the draw itself is uniform
        counts = {i: 0 for i in ids}
        r = random.Random(1)
        for _ in range(5000):
            counts[r.choice(sorted(ids))] += 1
        self.assertLess(max(counts.values()) - min(counts.values()), 200)
        self.assertIn(out["belief_id"], ids)

    def test_row_is_open_owned_band_four_with_its_own_confidence(self):
        from theory_x.stage_world import owned_belief as ob
        bid = self._belief("what I attend to changes me", "wonder_loop", conf=0.64)
        out = ob.make_owned_belief_expectation(rng=random.Random(0), now=1000.0)
        r = self._rows(self.conv, "owned_belief_expectations")[0]
        self.assertEqual(out["belief_id"], bid)
        self.assertEqual((r["state"], r["resolved_by"], r["cost_band"], r["confidence"],
                          r["confidence_basis"], r["tolerance_basis"], r["frozen"]),
                         ("open", None, 4, 0.64, "stated_p", "exact_label", "at_made"))
        self.assertEqual(json.loads(r["basis_snapshot"]),
                         [{"belief_id": bid, "source_kind": "authored", "confidence": 0.64}])
        claimed = json.loads(r["claimed_state"])
        self.assertEqual((claimed["holds"], claimed["tier"], claimed["paused"]), (True, 6, 0))
        self.assertEqual(r["resolve_at"], 1000.0 + ob.HORIZON_S)

    def test_open_beliefs_are_not_drawn_twice_and_rate_limited(self):
        from theory_x.stage_world import owned_belief as ob
        a = self._belief("one", "wonder_loop")
        b = self._belief("two", "wonder_loop")
        x = ob.make_owned_belief_expectation(rng=random.Random(0), now=1000.0)
        y = ob.make_owned_belief_expectation(rng=random.Random(0), now=1001.0)
        self.assertEqual({x["belief_id"], y["belief_id"]}, {a, b})
        self.assertEqual(ob.make_owned_belief_expectation(now=1002.0),
                         {"skipped": "no_eligible_belief"})
        self.assertFalse(ob.due(now=1001.0 + ob.EVERY_S - 1))
        self.assertTrue(ob.due(now=1001.0 + ob.EVERY_S))

    def test_dark_by_default(self):
        from theory_x.stage_world import owned_belief as ob
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NEX5_OWNED_BELIEF", None)
            self.assertFalse(ob.enabled())


class TestConfirmationRateCanary(_Store):

    def _resolved(self, confirmed, violated):
        from theory_x.stage_world import owned_belief as ob
        ob.ensure_schema()
        cx = connect(self.conv)
        for state in ["confirmed"] * confirmed + ["violated"] * violated:
            cx.execute("INSERT INTO owned_belief_expectations (made_at, belief_id, "
                       "claimed_state, resolve_at, state) VALUES (1, 1, '{}', 2, ?)", (state,))
        cx.commit(); cx.close()
        return ob.confirmation_rate_canary()

    def test_fires_above_ninety_percent(self):
        c = self._resolved(19, 1)
        self.assertEqual((c["resolved"], c["flag"]), (20, True))

    def test_quiet_when_real_or_too_few(self):
        self.assertFalse(self._resolved(17, 3)["flag"])

    def test_too_few_never_flags(self):
        self.assertEqual(self._resolved(10, 0)["flag"], False)

    def test_nightly_activity_reports_it(self):
        from theory_x.life import daily_life as dl
        self._resolved(19, 1)
        with self.assertLogs("theory_x.life.daily_life", "WARNING"):
            msg = dl._ACTIVITY_FUNCS["expectation_canaries"]("2026-10-27")
        self.assertIn("CANARY", msg)


if __name__ == "__main__":
    unittest.main()
