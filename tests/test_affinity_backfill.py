"""Affinity backfill (D-A PR B part 2): dry-run safe, gated, idempotent."""
import os
import tempfile
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

from substrate import connect
import nex_affinity_backfill as BF
from theory_x.life.affinity_loop import _provenance_affinity, _usage_score

_SCHEMA = Path(__file__).resolve().parent.parent / "substrate" / "schema"


def _make_db(path):
    cx = connect(path)
    cx.executescript((_SCHEMA / "beliefs.sql").read_text())
    for stmt in ("ALTER TABLE beliefs ADD COLUMN affinity REAL",
                 "ALTER TABLE beliefs ADD COLUMN affinity_updated_at REAL",
                 "ALTER TABLE beliefs ADD COLUMN affinity_model TEXT",
                 "ALTER TABLE beliefs ADD COLUMN affinity_legacy REAL"):
        cx.execute(stmt)
    cx.execute("CREATE TABLE IF NOT EXISTS belief_edges "
               "(id INTEGER PRIMARY KEY, source_id INTEGER, target_id INTEGER)")
    # Three rows with an old affinity (previously scored); one unscored (NULL);
    # one already migrated (affinity_model stamped) -> must be skipped.
    rows = [
        ("her synthesis", 4, 0.9, 1.0, "fountain_insight", 0.90, None, None),
        ("a headline", 4, 0.5, 2.0, "surprise", 0.50, None, None),
        ("imported claim", 4, 0.5, 3.0, "identity_loop", 0.50, None, None),
        ("unscored", 4, 0.5, 4.0, "wonder_loop", None, None, None),
        ("already done", 4, 0.5, 5.0, "pattern_loop", 0.42, "prov_v1", 0.33),
    ]
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
        _make_db(self.db)

    def tearDown(self):
        os.environ.pop("NEX5_AFFINITY_PROVENANCE", None)
        self._tmp.cleanup()

    def test_plan_selects_only_unmigrated_scored_rows(self):
        cx = connect(self.db)
        try:
            rows = BF.plan(cx)
        finally:
            cx.close()
        srcs = sorted(r[1] for r in rows)
        # fountain_insight, surprise, identity_loop — not the NULL-affinity row,
        # not the already-stamped one.
        self.assertEqual(srcs, ["fountain_insight", "identity_loop", "surprise"])
        # New value matches the single-source scoring function exactly.
        by_src = {r[1]: r[3] for r in rows}
        expect = _provenance_affinity("fountain_insight", _usage_score(0, 0, None))
        self.assertAlmostEqual(by_src["fountain_insight"], expect, 6)
        # Ordering preserved: authored (fountain) > witnessed? surprise is authored
        # now; identity_loop (received) must be the lowest of the three.
        self.assertLess(by_src["identity_loop"], by_src["fountain_insight"])

    def test_dry_run_writes_nothing(self):
        rc = BF.main(["--db", self.db])  # no --apply
        self.assertEqual(rc, 0)
        cx = connect(self.db)
        try:
            n = cx.execute("SELECT COUNT(*) FROM beliefs "
                           "WHERE affinity_model='prov_v1'").fetchone()[0]
        finally:
            cx.close()
        self.assertEqual(n, 1)  # only the pre-existing stamped row

    def test_apply_refused_without_flag(self):
        os.environ.pop("NEX5_AFFINITY_PROVENANCE", None)
        rc = BF.main(["--db", self.db, "--apply"])
        self.assertEqual(rc, 2)
        cx = connect(self.db)
        try:
            n = cx.execute("SELECT COUNT(*) FROM beliefs "
                           "WHERE affinity_model='prov_v1'").fetchone()[0]
        finally:
            cx.close()
        self.assertEqual(n, 1)  # unchanged — refused

    def test_apply_with_flag_migrates_and_preserves_legacy(self):
        os.environ["NEX5_AFFINITY_PROVENANCE"] = "on"
        rc = BF.main(["--db", self.db, "--apply"])
        self.assertEqual(rc, 0)
        cx = connect(self.db)
        try:
            # fountain_insight row: legacy holds the old 0.9, affinity is new, stamped.
            row = cx.execute(
                "SELECT affinity, affinity_legacy, affinity_model FROM beliefs "
                "WHERE source='fountain_insight'").fetchone()
            self.assertAlmostEqual(row[1], 0.9, 6)          # legacy = old value
            self.assertNotAlmostEqual(row[0], 0.9, 3)        # affinity changed
            self.assertEqual(row[2], "prov_v1")
            # NULL-affinity row untouched; already-stamped row keeps its legacy.
            n_stamped = cx.execute("SELECT COUNT(*) FROM beliefs "
                                   "WHERE affinity_model='prov_v1'").fetchone()[0]
            self.assertEqual(n_stamped, 4)  # 3 migrated + 1 pre-existing
            unscored = cx.execute("SELECT affinity, affinity_model FROM beliefs "
                                  "WHERE source='wonder_loop'").fetchone()
            self.assertIsNone(unscored[0])
            self.assertIsNone(unscored[1])
        finally:
            cx.close()

    def test_apply_is_idempotent(self):
        os.environ["NEX5_AFFINITY_PROVENANCE"] = "on"
        BF.main(["--db", self.db, "--apply"])
        cx = connect(self.db)
        try:
            rows = BF.plan(cx)  # nothing left to migrate
        finally:
            cx.close()
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
