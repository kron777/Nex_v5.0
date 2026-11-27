"""Provenance erosion tests.

Covers:
- use_count increments via record_use()
- reinforce_count increments via record_reinforce()
- Stage advances at threshold (external → nex_absorbed at 10 reinforcements)
- Protected sources skip erosion entirely
- erosion_pass() runs correctly
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_er_")
    os.environ["NEX5_DATA_DIR"] = tmp
    os.environ["NEX5_ADMIN_HASH_FILE"] = str(Path(tmp) / "admin.argon2")
    from substrate.init_db import init_all
    init_all()
    from substrate import Reader, Writer, db_paths
    paths = db_paths()
    writers = {n: Writer(p, name=n) for n, p in paths.items()}
    readers = {n: Reader(p) for n, p in paths.items()}
    return writers, readers, tmp


def _cleanup(writers, tmp):
    for w in writers.values():
        try:
            w.close()
        except Exception:
            pass
    shutil.rmtree(tmp, ignore_errors=True)
    os.environ.pop("NEX5_DATA_DIR", None)
    os.environ.pop("NEX5_ADMIN_HASH_FILE", None)


def _insert_belief(writer, content, source="test", tier=5, confidence=0.6):
    now = int(time.time())
    return writer.write(
        "INSERT INTO beliefs (content, tier, confidence, created_at, source) "
        "VALUES (?, ?, ?, ?, ?)",
        (content, tier, confidence, now, source),
    )


class TestErosionTracking(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_use_count_increments(self):
        from theory_x.stage3_world_model.erosion import ProvenanceErosion
        w = self.writers["beliefs"]
        r = self.readers["beliefs"]
        erosion = ProvenanceErosion(w, r)

        bid = _insert_belief(w, "Test belief for use count tracking")
        erosion.record_use(bid)
        erosion.record_use(bid)

        row = r.read_one("SELECT use_count FROM beliefs WHERE id = ?", (bid,))
        self.assertEqual(row["use_count"], 2)

    def test_reinforce_count_increments(self):
        from theory_x.stage3_world_model.erosion import ProvenanceErosion
        w = self.writers["beliefs"]
        r = self.readers["beliefs"]
        erosion = ProvenanceErosion(w, r)

        bid = _insert_belief(w, "Test belief for reinforce tracking")
        erosion.record_reinforce(bid)

        row = r.read_one("SELECT reinforce_count FROM beliefs WHERE id = ?", (bid,))
        self.assertEqual(row["reinforce_count"], 1)

    def test_stage_advances_at_threshold(self):
        from theory_x.stage3_world_model.erosion import ProvenanceErosion, THRESHOLDS
        w = self.writers["beliefs"]
        r = self.readers["beliefs"]
        erosion = ProvenanceErosion(w, r)

        bid = _insert_belief(w, "Belief to advance to nex_absorbed")
        threshold = THRESHOLDS["external"]

        # Set reinforce_count to threshold - 1 directly, then call record_reinforce once
        w.write(
            "UPDATE beliefs SET reinforce_count = ? WHERE id = ?",
            (threshold - 1, bid),
        )
        erosion.record_reinforce(bid)

        row = r.read_one("SELECT erosion_stage FROM beliefs WHERE id = ?", (bid,))
        self.assertEqual(row["erosion_stage"], "nex_absorbed")

    def test_protected_source_skipped(self):
        from theory_x.stage3_world_model.erosion import ProvenanceErosion, THRESHOLDS
        w = self.writers["beliefs"]
        r = self.readers["beliefs"]
        erosion = ProvenanceErosion(w, r)

        bid = _insert_belief(w, "Protected belief", source="keystone_seed")
        threshold = THRESHOLDS["external"]
        w.write("UPDATE beliefs SET reinforce_count = ? WHERE id = ?", (threshold, bid))

        erosion._erosion_check(bid)

        row = r.read_one("SELECT erosion_stage FROM beliefs WHERE id = ?", (bid,))
        self.assertEqual(row["erosion_stage"], "external")

    def test_erosion_pass(self):
        from theory_x.stage3_world_model.erosion import ProvenanceErosion, THRESHOLDS
        w = self.writers["beliefs"]
        r = self.readers["beliefs"]
        erosion = ProvenanceErosion(w, r)

        threshold = THRESHOLDS["external"]
        bid = _insert_belief(w, "Belief for erosion_pass test")
        w.write("UPDATE beliefs SET reinforce_count = ? WHERE id = ?", (threshold, bid))

        advanced = erosion.erosion_pass()
        self.assertGreaterEqual(advanced, 1)

        row = r.read_one("SELECT erosion_stage FROM beliefs WHERE id = ?", (bid,))
        self.assertEqual(row["erosion_stage"], "nex_absorbed")



    def test_erosion_pass_reaches_ready_rows_after_500_unadvanced_rows(self):
        from theory_x.stage3_world_model.erosion import ProvenanceErosion, THRESHOLDS
        w = self.writers["beliefs"]
        r = self.readers["beliefs"]
        erosion = ProvenanceErosion(w, r)

        # Keep seed rows out of this controlled scan; the 500 low-reinforcement
        # rows deliberately occupy the first page ahead of five ready rows.
        w.write("UPDATE beliefs SET locked = 1")
        first_id = None
        low_ids = []
        for index in range(500):
            bid = _insert_belief(w, f"Low reinforcement row {index}")
            first_id = bid if first_id is None else first_id
            low_ids.append(bid)
        ready_ids = [
            _insert_belief(w, f"Ready row {index}") for index in range(5)
        ]
        w.write(
            "UPDATE beliefs SET erosion_stage='nex_integrated', reinforce_count=0 "
            "WHERE id >= ?",
            (first_id,),
        )
        placeholders = ",".join("?" for _ in ready_ids)
        w.write(
            f"UPDATE beliefs SET reinforce_count=? WHERE id IN ({placeholders})",
            (THRESHOLDS["nex_integrated"], *ready_ids),
        )

        advanced = erosion.erosion_pass()
        self.assertEqual(advanced, 5)

        low_rows = r.read(
            f"SELECT id, erosion_stage FROM beliefs WHERE id IN "
            f"({','.join('?' for _ in low_ids)})",
            tuple(low_ids),
        )
        ready_rows = r.read(
            f"SELECT id, erosion_stage FROM beliefs WHERE id IN ({placeholders})",
            tuple(ready_ids),
        )
        self.assertTrue(all(row["erosion_stage"] == "nex_integrated" for row in low_rows))
        self.assertTrue(all(row["erosion_stage"] == "nex_core" for row in ready_rows))

    def test_erosion_pass_keyset_does_not_skip_rows_that_leave_eligible_set(self):
        from theory_x.stage3_world_model.erosion import ProvenanceErosion, THRESHOLDS
        w = self.writers["beliefs"]
        r = self.readers["beliefs"]
        erosion = ProvenanceErosion(w, r)

        w.write("UPDATE beliefs SET locked = 1")
        belief_ids = [
            _insert_belief(w, f"Ready for keyset page {index}") for index in range(505)
        ]
        first_id = belief_ids[0]
        placeholders = ",".join("?" for _ in belief_ids)
        w.write(
            "UPDATE beliefs SET erosion_stage='nex_integrated', reinforce_count=? "
            "WHERE id >= ?",
            (THRESHOLDS["nex_integrated"], first_id),
        )

        advanced = erosion.erosion_pass()
        self.assertEqual(advanced, 505)

        rows = r.read(
            f"SELECT id, erosion_stage FROM beliefs WHERE id IN ({placeholders})",
            tuple(belief_ids),
        )
        self.assertEqual(len(rows), 505)
        self.assertTrue(all(row["erosion_stage"] == "nex_core" for row in rows))

        undo_rows = r.read(
            "SELECT belief_id FROM undo_events "
            "WHERE kind='eroded' AND cause_ref='erosion_pass:nex_integrated->nex_core'"
        )
        self.assertEqual(
            {row["belief_id"] for row in undo_rows}, set(belief_ids)
        )


if __name__ == "__main__":
    unittest.main()
