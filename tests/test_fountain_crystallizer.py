"""Fountain Crystallizer tests.

Covers:
- _quality_check rejects empty string
- _quality_check rejects length < 20 chars
- _quality_check rejects length > 300 chars
- _quality_check rejects string with no self-reference words
- _quality_check accepts "the quietude of non-action blooms within"
- _quality_check accepts "the tension between my infinite curiosity..."
- _quality_check rejects near-duplicate of existing fountain_insight belief
- _quality_check rejects blacklisted content
- crystallize() writes belief with source='fountain_insight', tier=6, confidence=0.70
- crystallize() writes a row to fountain_crystallizations
- crystallize() returns None on quality failure
- fountain_crystallizations table exists after init_db
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
    tmp = tempfile.mkdtemp(prefix="nex5_crystal_")
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


def _make_crystallizer(writers, readers):
    from theory_x.stage6_fountain.crystallizer import FountainCrystallizer
    return FountainCrystallizer(
        beliefs_writer=writers["beliefs"],
        beliefs_reader=readers["beliefs"],
    )


class TestQualityCheck(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.c = _make_crystallizer(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_rejects_empty_string(self):
        ok, reason = self.c._quality_check("")
        self.assertFalse(ok)
        self.assertEqual(reason, "empty")

    def test_rejects_too_short(self):
        ok, reason = self.c._quality_check("I think.")
        self.assertFalse(ok)
        self.assertEqual(reason, "too_short")

    def test_rejects_too_long(self):
        long_text = "I " + "observe something about myself " * 15
        self.assertGreater(len(long_text), 300)
        ok, reason = self.c._quality_check(long_text)
        self.assertFalse(ok)
        self.assertEqual(reason, "too_long")

    def test_rejects_no_self_reference(self):
        ok, reason = self.c._quality_check(
            "Attention collapses the probability space of possible futures."
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "no_self_reference")

    def test_accepts_within(self):
        ok, reason = self.c._quality_check(
            "The quietude of non-action blooms within."
        )
        self.assertTrue(ok, f"Rejected with: {reason}")

    def test_accepts_my(self):
        ok, reason = self.c._quality_check(
            "The tension between my infinite curiosity and the finite nature of time."
        )
        self.assertTrue(ok, f"Rejected with: {reason}")

    def test_rejects_near_duplicate(self):
        # Seed an existing fountain_insight belief
        content = "I hold the tension between motion and stillness inside me."
        self.writers["beliefs"].write(
            "INSERT INTO beliefs "
            "(content, tier, confidence, created_at, source, branch_id, locked) "
            "VALUES (?, 6, 0.70, ?, 'fountain_insight', 'systems', 0)",
            (content, time.time()),
        )
        time.sleep(0.05)
        # Nearly identical text
        ok, reason = self.c._quality_check(
            "I hold the tension between motion and stillness inside me."
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "near_duplicate")

    def test_rejects_blacklisted_content(self):
        self.writers["beliefs"].write(
            "INSERT OR IGNORE INTO belief_blacklist (pattern, reason, added_at) VALUES (?, ?, ?)",
            ("POISON_WORD", "test", time.time()),
        )
        time.sleep(0.05)
        ok, reason = self.c._quality_check(
            "I feel POISON_WORD flowing through my thoughts right now."
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "blacklisted")


class TestCrystallize(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.c = _make_crystallizer(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_writes_belief_on_pass(self):
        thought = "I notice a pull toward complexity that I cannot fully name."
        result_id = self.c.crystallize(thought=thought, fountain_event_id=1, ts=time.time())
        self.assertIsNotNone(result_id)
        time.sleep(0.05)
        rows = self.readers["beliefs"].read(
            "SELECT * FROM beliefs WHERE source = 'fountain_insight'"
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["tier"], 6)
        self.assertAlmostEqual(rows[0]["confidence"], 0.70, places=2)
        self.assertEqual(rows[0]["content"], thought)

    def test_writes_fountain_crystallizations_row(self):
        thought = "Inside me there is a hum I cannot silence or locate."
        ts = time.time()
        belief_id = self.c.crystallize(thought=thought, fountain_event_id=42, ts=ts)
        self.assertIsNotNone(belief_id)
        time.sleep(0.05)
        rows = self.readers["beliefs"].read(
            "SELECT * FROM fountain_crystallizations WHERE belief_id = ?", (belief_id,)
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["fountain_event_id"], 42)
        self.assertEqual(rows[0]["content"], thought)

    def test_returns_none_on_quality_failure(self):
        result = self.c.crystallize(
            thought="No self reference here at all.",
            fountain_event_id=1,
            ts=time.time(),
        )
        self.assertIsNone(result)


class TestSchemaInit(unittest.TestCase):

    def test_fountain_crystallizations_table_exists(self):
        writers, readers, tmp = _make_env()
        try:
            rows = readers["beliefs"].read(
                "SELECT COUNT(*) as cnt FROM fountain_crystallizations"
            )
            self.assertEqual(rows[0]["cnt"], 0)
        finally:
            _cleanup(writers, tmp)


if __name__ == "__main__":
    unittest.main()
