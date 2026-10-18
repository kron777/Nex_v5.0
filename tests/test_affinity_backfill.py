"""Affinity backfill (D-A PR B part 2): dry-run safe, gated, GO/STOP, idempotent."""
import csv
import os
import tempfile
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

from substrate import connect
import nex_affinity_backfill as BF
from theory_x.life.affinity_loop import _provenance_affinity, _usage_score

_SCHEMA = Path(__file__).resolve().parent.parent / "substrate" / "schema"


def _make_db(path, extra=None):
    cx = connect(path)
    cx.executescript((_SCHEMA / "beliefs.sql").read_text())
    for stmt in ("ALTER TABLE beliefs ADD COLUMN affinity REAL",
                 "ALTER TABLE beliefs ADD COLUMN affinity_updated_at REAL",
                 "ALTER TABLE beliefs ADD COLUMN affinity_model TEXT",
                 "ALTER TABLE beliefs ADD COLUMN affinity_legacy REAL"):
        cx.execute(stmt)
    cx.execute("CREATE TABLE IF NOT EXISTS belief_edges "
               "(id INTEGER PRIMARY KEY, source_id INTEGER, target_id INTEGER)")
    rows = [
        ("her synthesis", 4, 0.9, 1.0, "fountain_insight", 0.90, None, None),
        ("a surprise", 4, 0.5, 2.0, "surprise", 0.50, None, None),
        ("imported claim", 4, 0.5, 3.0, "identity_loop", 0.50, None, None),
        ("unscored", 4, 0.5, 4.0, "wonder_loop", None, None, None),       # affinity NULL -> skip
        ("already done", 4, 0.5, 5.0, "pattern_loop", 0.42, "prov_v1", 0.33),  # stamped -> skip
    ] + (extra or [])
    for content, tier, conf, ts, source, aff, model, legacy in rows:
        cx.execute(
            "INSERT INTO beliefs (content, tier, confidence, created_at, source, "
            "affinity, affinity_model, affinity_legacy) VALUES (?,?,?,?,?,?,?,?)",
            (content, tier, conf, ts, source, aff, model, legacy))
    cx.commit()
    cx.close()


class TestBackfill(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self._tmp.name) / "beliefs.db")
        self.csv = str(Path(self._tmp.name) / "baseline.csv")
        _make_db(self.db)

    def tearDown(self):
        os.environ.pop("NEX5_AFFINITY_PROVENANCE", None)
        self._tmp.cleanup()

    def _stamped(self):
        cx = connect(self.db)
        try:
            return cx.execute("SELECT COUNT(*) FROM beliefs "
                              "WHERE affinity_model='prov_v1'").fetchone()[0]
        finally:
            cx.close()

    def test_plan_selects_only_unmigrated_scored_rows(self):
        cx = connect(self.db)
        try:
            rows = BF.plan(cx)
        finally:
            cx.close()
        self.assertEqual(sorted(r["source"] for r in rows),
                         ["fountain_insight", "identity_loop", "surprise"])
        by = {r["source"]: r for r in rows}
        exp = _provenance_affinity("fountain_insight", _usage_score(0, 0, None))
        self.assertAlmostEqual(by["fountain_insight"]["new"], exp, 6)
        self.assertLess(by["identity_loop"]["new"], by["fountain_insight"]["new"])

    def test_dry_run_writes_nothing_and_emits_baseline_csv(self):
        rc = BF.main(["--db", self.db, "--baseline", self.csv])
        self.assertEqual(rc, 0)
        self.assertEqual(self._stamped(), 1)  # only the pre-existing stamped row
        with open(self.csv) as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual({r["source"] for r in rows},
                         {"fountain_insight", "surprise", "identity_loop"})
        self.assertEqual(set(rows[0].keys()),
                         {"belief_id", "source", "usage_score",
                          "affinity_old", "affinity_new"})

    def test_apply_refused_without_flag(self):
        rc = BF.main(["--db", self.db, "--apply"])
        self.assertEqual(rc, 2)
        self.assertEqual(self._stamped(), 1)

    def test_apply_migrates_and_coalesces_legacy(self):
        os.environ["NEX5_AFFINITY_PROVENANCE"] = "on"
        rc = BF.main(["--db", self.db, "--apply", "--baseline", self.csv])
        self.assertEqual(rc, 0)
        cx = connect(self.db)
        try:
            row = cx.execute("SELECT affinity, affinity_legacy, affinity_model "
                             "FROM beliefs WHERE source='fountain_insight'").fetchone()
            self.assertAlmostEqual(row[1], 0.90, 6)       # legacy = old value
            self.assertNotAlmostEqual(row[0], 0.90, 3)    # affinity changed
            self.assertEqual(row[2], "prov_v1")
            self.assertEqual(self._stamped(), 4)          # 3 migrated + 1 pre-existing
        finally:
            cx.close()

    def test_apply_idempotent_preserves_legacy(self):
        os.environ["NEX5_AFFINITY_PROVENANCE"] = "on"
        BF.main(["--db", self.db, "--apply", "--baseline", self.csv])
        cx = connect(self.db)
        try:
            legacy_before = cx.execute("SELECT affinity_legacy FROM beliefs "
                                       "WHERE source='fountain_insight'").fetchone()[0]
            self.assertEqual(BF.plan(cx), [])  # nothing left to migrate
        finally:
            cx.close()
        BF.main(["--db", self.db, "--apply", "--baseline", self.csv])  # re-run
        cx = connect(self.db)
        try:
            legacy_after = cx.execute("SELECT affinity_legacy FROM beliefs "
                                      "WHERE source='fountain_insight'").fetchone()[0]
        finally:
            cx.close()
        self.assertEqual(legacy_before, legacy_after)  # COALESCE did not clobber it

    def test_rollback_restores_old_values(self):
        os.environ["NEX5_AFFINITY_PROVENANCE"] = "on"
        BF.main(["--db", self.db, "--apply", "--baseline", self.csv])
        BF.main(["--db", self.db, "--rollback", "--apply"])
        cx = connect(self.db)
        try:
            row = cx.execute("SELECT affinity, affinity_legacy, affinity_model "
                             "FROM beliefs WHERE source='fountain_insight'").fetchone()
        finally:
            cx.close()
        self.assertAlmostEqual(row[0], 0.90, 6)   # affinity restored from legacy
        self.assertIsNone(row[1])                  # legacy cleared
        self.assertIsNone(row[2])                  # stamp cleared


class TestGoStopGate(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self._tmp.name) / "beliefs.db")
        self.csv = str(Path(self._tmp.name) / "baseline.csv")

    def tearDown(self):
        os.environ.pop("NEX5_AFFINITY_PROVENANCE", None)
        self._tmp.cleanup()

    def test_all_mapped_sources_pass(self):
        _make_db(self.db)  # every source is in the provenance map
        cx = connect(self.db)
        try:
            rows = BF.plan(cx)
            stats, overall = BF.summarize(rows)
            verdict, reasons = BF.evaluate(rows, stats, overall, cx=cx)
        finally:
            cx.close()
        self.assertNotEqual(verdict, "STOP", reasons)  # GO or INVESTIGATE, never STOP

    def test_unmapped_source_stops_and_refuses_apply(self):
        _make_db(self.db, extra=[
            ("mystery belief", 4, 0.5, 9.0, "brand_new_xyz", 0.4, None, None)])
        cx = connect(self.db)
        try:
            rows = BF.plan(cx)
            stats, overall = BF.summarize(rows)
            verdict, reasons = BF.evaluate(rows, stats, overall, cx=cx)
        finally:
            cx.close()
        self.assertEqual(verdict, "STOP")
        self.assertTrue(any("unmapped" in s for s in reasons["stop"]))
        # --apply must refuse (exit 3) even with the flag on.
        os.environ["NEX5_AFFINITY_PROVENANCE"] = "on"
        self.assertEqual(BF.main(["--db", self.db, "--apply", "--baseline", self.csv]), 3)


if __name__ == "__main__":
    unittest.main()
