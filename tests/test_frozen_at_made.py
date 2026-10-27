"""Build B phase 0: confidence, tolerance and a stakes snapshot, frozen at made_at.

Pinned here:
  * every producer writes the frozen fields on the row it makes (self fire,
    authored_30m, selfdesc_novel, world voice + random), with the confidence the
    producer actually states -- NULL + 'none_stated' where it states none;
  * rows that predate the columns become 'legacy_unfrozen' with NULL fields;
  * resolution leaves them untouched, and a direct UPDATE of a frozen field on
    an 'at_made' row is ABORTED by the schema, not merely discouraged.
"""
import os
import tempfile
import time
import unittest
from unittest import mock

from tests import _bootstrap  # noqa: F401

from substrate import connect, Row

_STAKES = (0.375, 0, 0.05)


class _Store(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._env = mock.patch.dict(os.environ, {
            "NEX5_DATA_DIR": self._tmp.name, "NEX5_SCHEMA_TRIPWIRE": "1"})
        self._env.start()
        from substrate.init_db import init_all
        init_all()
        from substrate.paths import db_paths
        self.conv = str(db_paths()["conversations"])
        self._snap = mock.patch("theory_x.stage_world.frozen_at_made.snapshot_stakes",
                                return_value=_STAKES)
        self._snap.start()

    def tearDown(self):
        self._snap.stop()
        self._env.stop()
        self._tmp.cleanup()

    def _rows(self, table, where="1"):
        cx = connect(self.conv)
        cx.row_factory = Row
        try:
            return [dict(r) for r in cx.execute(f"SELECT * FROM {table} WHERE {where} ORDER BY id")]
        finally:
            cx.close()


class TestSelfPredictionProducers(_Store):

    def test_fire_arm(self):
        from theory_x.stage_world import self_prediction as sp
        from theory_x.stage_world import frozen_at_made as F
        with mock.patch.object(sp, "_read_status",
                               return_value={"readiness_score": 0.8, "total_fires": 3}), \
             mock.patch.object(sp, "snapshot_stakes", F.snapshot_stakes):
            sp.make_self_prediction(self.conv)
        by = {r["source"]: r for r in self._rows("self_predictions")}
        self.assertEqual((by["self"]["confidence"], by["self"]["confidence_basis"]),
                         (None, "none_stated"))
        self.assertEqual((by["random"]["confidence"], by["random"]["confidence_basis"]),
                         (0.5, "coin"))
        for r in by.values():
            self.assertEqual((r["tolerance"], r["tolerance_basis"], r["frozen"]),
                             (0.0, "exact_label", "at_made"))
            self.assertEqual((r["stakes_at_made"], r["stakes_active_at_made"],
                              r["groove_cost_at_made"]), _STAKES)

    def test_selfdesc_states_its_probability(self):
        from theory_x.stage_world import self_prediction as sp
        sp.ensure_schema(self.conv)
        with mock.patch.object(sp, "snapshot_stakes", return_value=_STAKES):
            sp._insert_pred(self.conv, "selfdesc_novel",
                            [("self", "same"), ("random", "differ")],
                            time.time() + 60, signal=3.0, confidence=0.7)
            sp._insert_pred(self.conv, "authored_30m",
                            [("self", "yes"), ("random", "no")], time.time() + 60)
        rows = {(r["kind"], r["source"]): r for r in self._rows("self_predictions")}
        self.assertEqual(rows[("selfdesc_novel", "self")]["confidence"], 0.7)
        self.assertEqual(rows[("selfdesc_novel", "self")]["confidence_basis"], "stated_p")
        self.assertEqual(rows[("authored_30m", "self")]["confidence_basis"], "none_stated")
        self.assertIsNone(rows[("authored_30m", "self")]["confidence"])
        self.assertEqual(rows[("authored_30m", "random")]["confidence"], 0.5)

    def test_selfdesc_confidence_is_p_of_the_predicted_label(self):
        # p_differ=0.3 -> predicts 'same' with confidence 0.7, not 0.3.
        from theory_x.stage_world import self_prediction as sp
        cond = {"eff_n_differ": 99, "eff_n_same": 99, "p_differ_given_differ": 0.3,
                "p_differ_given_same": 0.3, "p_differ_pooled": 0.3, "n": 40}
        with mock.patch.object(sp, "_identity_statements",
                               return_value=[("alpha bravo",), ("alpha charlie",)]), \
             mock.patch.object(sp, "selfdesc_conditional", return_value=cond), \
             mock.patch.object(sp, "selfdesc_stationarity", return_value={}), \
             mock.patch.object(sp, "snapshot_stakes", return_value=_STAKES):
            out = sp.make_selfdesc_prediction(self.conv, dynamic_db="unused")
        self.assertEqual(out["self"], "same")
        row = self._rows("self_predictions", "source='self'")[0]
        self.assertAlmostEqual(row["confidence"], 0.7)


class TestWorldPredictionProducer(_Store):

    def test_voice_and_random(self):
        from theory_x.stage_world import world_predictions as wp
        with mock.patch.object(wp, "fetch_price", return_value=100.0):
            v = wp.make_prediction("bitcoin", "up", 60, db_path=self.conv, source="voice")
            r = wp.make_prediction("bitcoin", "down", 60, db_path=self.conv, source="random")
        rows = {x["id"]: x for x in self._rows("world_predictions")}
        self.assertEqual((rows[v]["confidence"], rows[v]["confidence_basis"]), (None, "none_stated"))
        self.assertEqual((rows[r]["confidence"], rows[r]["confidence_basis"]), (0.5, "coin"))
        for x in rows.values():
            self.assertEqual((x["tolerance"], x["tolerance_basis"], x["frozen"]),
                             (0.0, "strict_direction", "at_made"))
            self.assertEqual(x["stakes_at_made"], _STAKES[0])

    def test_resolution_and_trust_stamp_leave_frozen_fields(self):
        from theory_x.stage_world import world_predictions as wp
        with mock.patch.object(wp, "fetch_price", return_value=100.0):
            pid = wp.make_prediction("bitcoin", "up", 0, db_path=self.conv, source="voice")
        before = self._rows("world_predictions")[0]
        wp.stamp_trust(pid, "low", 0.1, 12, db_path=self.conv)
        with mock.patch.object(wp, "fetch_price", return_value=101.0):
            wp.resolve_due(now=time.time() + 5, db_path=self.conv)
        after = self._rows("world_predictions")[0]
        self.assertEqual(after["outcome"], "correct")
        from theory_x.stage_world.frozen_at_made import FROZEN_COLUMNS
        for name, _ in FROZEN_COLUMNS:
            self.assertEqual(after[name], before[name], name)


class TestFreezeIsEnforced(_Store):

    def test_update_of_a_frozen_field_aborts(self):
        import sqlite3
        from theory_x.stage_world import world_predictions as wp
        with mock.patch.object(wp, "fetch_price", return_value=100.0):
            pid = wp.make_prediction("bitcoin", "up", 60, db_path=self.conv, source="voice")
        cx = connect(self.conv)
        try:
            for sql in ("UPDATE world_predictions SET tolerance=0.5 WHERE id=?",
                        "UPDATE world_predictions SET confidence=0.9 WHERE id=?",
                        "UPDATE world_predictions SET stakes_at_made=1.0 WHERE id=?"):
                with self.assertRaisesRegex(sqlite3.IntegrityError, "frozen-at-made"):
                    cx.execute(sql, (pid,))
            cx.execute("UPDATE world_predictions SET outcome='wrong' WHERE id=?", (pid,))
        finally:
            cx.close()


class TestFreshTablesCarryEveryColumn(_Store):

    def test_create_statements_match_the_shared_list(self):
        # The CREATE strings spell the columns out (static SQL); pin them to the list.
        from theory_x.stage_world import self_prediction as sp, world_predictions as wp
        from theory_x.stage_world.frozen_at_made import FROZEN_COLUMNS
        sp.ensure_schema(self.conv); wp.ensure_schema(self.conv)
        cx = connect(self.conv)
        try:
            for table in ("self_predictions", "world_predictions"):
                cols = {r[1]: r[2] for r in cx.execute(f"PRAGMA table_info({table})")}
                for name, kind in FROZEN_COLUMNS:
                    self.assertEqual(cols.get(name), kind, (table, name))
        finally:
            cx.close()


class TestLegacyRows(_Store):

    def test_aged_tables_mark_old_rows_legacy(self):
        cx = connect(self.conv)
        cx.execute("CREATE TABLE self_predictions (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                   "made_at REAL NOT NULL, source TEXT NOT NULL, predicted TEXT NOT NULL, "
                   "readiness REAL, baseline_fires INTEGER NOT NULL, resolve_at REAL NOT NULL, "
                   "resolved_at REAL, actual TEXT, outcome TEXT)")
        cx.execute("INSERT INTO self_predictions (made_at, source, predicted, baseline_fires, "
                   "resolve_at) VALUES (1, 'self', 'fire', 0, 2)")
        cx.execute("CREATE TABLE world_predictions (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                   "made_at REAL NOT NULL, asset TEXT NOT NULL, baseline_price REAL NOT NULL, "
                   "direction TEXT NOT NULL, horizon_seconds INTEGER NOT NULL, "
                   "resolve_at REAL NOT NULL, resolved_at REAL, price_at_resolve REAL, "
                   "outcome TEXT, source TEXT NOT NULL DEFAULT 'manual', trust_level TEXT, "
                   "trust_gap REAL, trust_n INTEGER)")
        cx.execute("INSERT INTO world_predictions (made_at, asset, baseline_price, direction, "
                   "horizon_seconds, resolve_at) VALUES (1, 'bitcoin', 1, 'up', 1, 2)")
        cx.commit(); cx.close()
        from theory_x.stage_world import self_prediction as sp, world_predictions as wp
        sp.ensure_schema(self.conv)
        wp.ensure_schema(self.conv)
        with mock.patch.object(wp, "fetch_price", return_value=100.0):
            wp.make_prediction("bitcoin", "up", 60, db_path=self.conv, source="voice")
        for table in ("self_predictions", "world_predictions"):
            rows = self._rows(table)
            self.assertEqual(rows[0]["frozen"], "legacy_unfrozen", table)
            self.assertIsNone(rows[0]["confidence"])
            self.assertIsNone(rows[0]["stakes_at_made"])
        self.assertEqual(self._rows("world_predictions")[1]["frozen"], "at_made")
        # a second ensure doesn't relabel anything
        sp.ensure_schema(self.conv); wp.ensure_schema(self.conv)
        self.assertEqual([r["frozen"] for r in self._rows("world_predictions")],
                         ["legacy_unfrozen", "at_made"])


class TestRealSnapshot(_Store):

    def test_snapshot_reads_both_l4_instruments(self):
        from theory_x.stage_world import frozen_at_made as F
        self._snap.stop()
        try:
            with mock.patch("theory_x.stage_tom.stakes_appraisal.appraise",
                            return_value={"ratio": 0.62, "stakes_active": True}), \
                 mock.patch("theory_x.stage_tom.stakes_appraisal.appraise_groove",
                            return_value={"cost": 0.1}):
                self.assertEqual(F.snapshot_stakes(), (0.62, 1, 0.1))
            # fail-safe on a fresh store: real calls, numbers not errors
            ratio, active, cost = F.snapshot_stakes()
            self.assertEqual((active, cost), (0, 0.0))
        finally:
            self._snap.start()


if __name__ == "__main__":
    unittest.main()
