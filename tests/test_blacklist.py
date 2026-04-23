"""Blacklist tests.

Covers:
- belief_blacklist table seeded at init
- is_blacklisted() returns True for matching content
- is_blacklisted() returns False for non-matching content
- add_to_blacklist() adds a new pattern
- Crystallizer blocks blacklisted content
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
    tmp = tempfile.mkdtemp(prefix="nex5_bl_")
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


class TestBlacklistSeeded(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_blacklist_table_populated(self):
        row = self.readers["beliefs"].read_one(
            "SELECT COUNT(*) as cnt FROM belief_blacklist"
        )
        self.assertIsNotNone(row)
        self.assertGreater(row["cnt"], 0)

    def test_known_pattern_present(self):
        row = self.readers["beliefs"].read_one(
            "SELECT id FROM belief_blacklist WHERE pattern = 'I am just a language model'"
        )
        self.assertIsNotNone(row)


class TestIsBlacklisted(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_blacklisted_content_detected(self):
        from theory_x.stage3_world_model.promotion import BeliefPromoter
        promoter = BeliefPromoter(self.writers["beliefs"], self.readers["beliefs"])
        self.assertTrue(promoter.is_blacklisted("I am just a language model and cannot experience"))

    def test_case_insensitive(self):
        from theory_x.stage3_world_model.promotion import BeliefPromoter
        promoter = BeliefPromoter(self.writers["beliefs"], self.readers["beliefs"])
        self.assertTrue(promoter.is_blacklisted("MACHINES CANNOT FEEL anything at all"))

    def test_clean_content_passes(self):
        from theory_x.stage3_world_model.promotion import BeliefPromoter
        promoter = BeliefPromoter(self.writers["beliefs"], self.readers["beliefs"])
        self.assertFalse(promoter.is_blacklisted(
            "Consciousness arises from integrated information processing"
        ))

    def test_add_to_blacklist(self):
        from theory_x.stage3_world_model.promotion import BeliefPromoter
        promoter = BeliefPromoter(self.writers["beliefs"], self.readers["beliefs"])
        promoter.add_to_blacklist("test_unique_custom_pattern_xyz", "unit test")
        self.assertTrue(promoter.is_blacklisted("this contains test_unique_custom_pattern_xyz"))


class TestCrystallizerBlacklist(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_blacklisted_content_not_crystallized(self):
        from theory_x.stage2_dynamic.bonsai import BonsaiTree
        from theory_x.stage2_dynamic.crystallization import Crystallizer
        tree = BonsaiTree()
        tree.init_tree()
        c = Crystallizer(
            tree=tree,
            beliefs_writer=self.writers["beliefs"],
            dynamic_writer=self.writers["dynamic"],
            dynamic_reader=self.readers["dynamic"],
            beliefs_reader=self.readers["beliefs"],
        )
        # Add pattern for test
        self.writers["beliefs"].write(
            "INSERT OR IGNORE INTO belief_blacklist (pattern, reason, added_at) "
            "VALUES (?, ?, ?)",
            ("BLOCKED_TEST_CONTENT", "test", time.time()),
        )
        # Attempt to crystallize belief with that content
        result = c._write_belief("[ai_research] BLOCKED_TEST_CONTENT here", "ai_research", time.time())
        # _write_belief doesn't check blacklist — _crystallize does
        # Test _crystallize directly
        class MockNode:
            branch_id = "ai_research"
            focus_num = 0.9
            focus_increment = "g"
        # Override _extract_content to return blacklisted string
        c._extract_content = lambda bid: "BLOCKED_TEST_CONTENT here"
        did = c._crystallize(MockNode(), time.time())
        self.assertFalse(did)


if __name__ == "__main__":
    unittest.main()
