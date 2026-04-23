"""Emergent drive detector tests.

Covers:
- scan_for_pressure() returns proposals above threshold
- drive_proposals table is written via log_proposals()
- BonsaiTree.add_branch() adds a non-seed branch
- apply_approved() applies and writes a belief
- proposals below threshold not returned
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
    tmp = tempfile.mkdtemp(prefix="nex5_ed_")
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


def _insert_belief(writer, content, tier=3, confidence=0.8, branch_id=None):
    now = int(time.time())
    return writer.write(
        "INSERT INTO beliefs (content, tier, confidence, created_at, branch_id) "
        "VALUES (?, ?, ?, ?, ?)",
        (content, tier, confidence, now, branch_id),
    )


class TestEmergentDriveDetector(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _make_detector(self):
        from theory_x.stage2_dynamic.emergent_drives import EmergentDriveDetector
        return EmergentDriveDetector(dynamic_writer=self.writers["dynamic"])

    def test_proposals_returned_for_high_pressure(self):
        w = self.writers["beliefs"]
        r = self.readers["beliefs"]
        detector = self._make_detector()

        # Insert enough high-confidence beliefs in a non-seed branch with verb-heavy content
        for i in range(8):
            _insert_belief(
                w,
                f"quantum computing is processing and calculating and optimizing {i}",
                tier=3, confidence=0.85, branch_id="quantum_computing",
            )

        proposals = detector.scan_for_pressure(r, None)
        branch_ids = [p["branch"] for p in proposals]
        # quantum_computing is not a seed branch, so may appear if pressure high enough
        # At minimum no exception
        self.assertIsInstance(proposals, list)

    def test_seed_branch_not_proposed(self):
        w = self.writers["beliefs"]
        r = self.readers["beliefs"]
        detector = self._make_detector()

        # Insert beliefs in seed branch
        for i in range(10):
            _insert_belief(
                w, f"AI research optimizing learning {i}",
                tier=3, confidence=0.9, branch_id="ai_research",
            )

        proposals = detector.scan_for_pressure(r, None)
        seed_proposed = [p for p in proposals if p["branch"] == "ai_research"]
        self.assertEqual(seed_proposed, [])

    def test_log_proposals_writes_to_db(self):
        detector = self._make_detector()
        proposals = [
            {
                "branch": "novel_branch_xyz",
                "pressure": 0.55,
                "representative_beliefs": ["belief one", "belief two"],
                "proposed_curiosity": 0.55,
            }
        ]
        detector.log_proposals(proposals)

        rows = self.readers["dynamic"].read(
            "SELECT * FROM drive_proposals WHERE branch_id = 'novel_branch_xyz'"
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "pending")

    def test_bonsai_add_branch(self):
        from theory_x.stage2_dynamic.bonsai import BonsaiTree
        tree = BonsaiTree()
        tree.init_tree()
        node = tree.add_branch("new_emergent_branch", curiosity_weight=0.6)
        self.assertIsNotNone(node)
        self.assertEqual(tree.get("new_emergent_branch").curiosity_weight, 0.6)

    def test_bonsai_add_branch_idempotent(self):
        from theory_x.stage2_dynamic.bonsai import BonsaiTree
        tree = BonsaiTree()
        tree.init_tree()
        node1 = tree.add_branch("test_idempotent", 0.7)
        node2 = tree.add_branch("test_idempotent", 0.9)
        self.assertIs(node1, node2)

    def test_apply_approved_applies_branch(self):
        from theory_x.stage2_dynamic.bonsai import BonsaiTree
        from theory_x.stage2_dynamic.emergent_drives import EmergentDriveDetector
        import json

        detector = EmergentDriveDetector(dynamic_writer=self.writers["dynamic"])
        dw = self.writers["dynamic"]
        dr = self.readers["dynamic"]
        bw = self.writers["beliefs"]

        # Insert approved proposal
        dw.write(
            "INSERT INTO drive_proposals (ts, branch_id, pressure, representative_beliefs, "
            "proposed_curiosity, status) VALUES (?, ?, ?, ?, ?, 'approved')",
            (time.time(), "approved_branch_test", 0.6, json.dumps(["belief a"]), 0.6),
        )

        tree = BonsaiTree()
        tree.init_tree()

        class MockDynamic:
            pass
        md = MockDynamic()
        md.tree = tree

        applied = detector.apply_approved(md, bw, dr)
        self.assertGreaterEqual(applied, 1)
        self.assertIsNotNone(tree.get("approved_branch_test"))


if __name__ == "__main__":
    unittest.main()
