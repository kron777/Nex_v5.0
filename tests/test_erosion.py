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


if __name__ == "__main__":
    unittest.main()
