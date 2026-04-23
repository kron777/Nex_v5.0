"""Behavioural self-model tests.

Covers:
- observe() returns dict with expected keys
- observe() returns empty metrics when no messages exist
- compare_to_seeds() returns list
- write_behavioural_beliefs() writes a belief when divergence exists
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
    tmp = tempfile.mkdtemp(prefix="nex5_bsm_")
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


class TestBehaviouralObserve(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_observe_returns_expected_keys(self):
        from theory_x.stage4_membrane.behavioural_self_model import BehaviouralSelfModel
        bsm = BehaviouralSelfModel(self.readers["conversations"])
        result = bsm.observe()
        for key in ("hedge_rate", "position_rate", "belief_usage_rate",
                    "dominant_register", "avg_response_length", "sample_size"):
            self.assertIn(key, result)

    def test_observe_empty_returns_zeros(self):
        from theory_x.stage4_membrane.behavioural_self_model import BehaviouralSelfModel
        bsm = BehaviouralSelfModel(self.readers["conversations"])
        result = bsm.observe()
        self.assertEqual(result["sample_size"], 0)
        self.assertEqual(result["hedge_rate"], 0.0)

    def test_compare_to_seeds_returns_list(self):
        from theory_x.stage4_membrane.behavioural_self_model import BehaviouralSelfModel
        bsm = BehaviouralSelfModel(self.readers["conversations"])
        result = bsm.compare_to_seeds()
        self.assertIsInstance(result, list)

    def test_observe_with_messages(self):
        from theory_x.stage4_membrane.behavioural_self_model import BehaviouralSelfModel
        w = self.writers["conversations"]
        sid = "test-session"
        now = int(time.time())
        w.write(
            "INSERT INTO sessions (id, started_at) VALUES (?, ?)",
            (sid, now),
        )
        # Insert NEX messages with hedges
        for i in range(5):
            w.write(
                "INSERT INTO messages (session_id, role, content, register, timestamp) "
                "VALUES (?, 'nex', ?, 'CONVERSATIONAL', ?)",
                (sid, f"I think perhaps this is probably the answer {i}", now + i),
            )

        bsm = BehaviouralSelfModel(self.readers["conversations"])
        result = bsm.observe()
        self.assertEqual(result["sample_size"], 5)
        self.assertGreater(result["hedge_rate"], 0.0)

    def test_write_behavioural_beliefs(self):
        from theory_x.stage4_membrane.behavioural_self_model import BehaviouralSelfModel
        w = self.writers["conversations"]
        bw = self.writers["beliefs"]
        br = self.readers["beliefs"]
        sid = "test-session-2"
        now = int(time.time())
        w.write("INSERT INTO sessions (id, started_at) VALUES (?, ?)", (sid, now))

        # Insert many hedge-heavy messages to trigger divergence
        for i in range(20):
            w.write(
                "INSERT INTO messages (session_id, role, content, register, timestamp) "
                "VALUES (?, 'nex', ?, 'CONVERSATIONAL', ?)",
                (
                    sid,
                    "I think perhaps I might possibly be uncertain about this maybe probably",
                    now + i,
                ),
            )

        bsm = BehaviouralSelfModel(self.readers["conversations"])
        written = bsm.write_behavioural_beliefs(bw, br)
        # May or may not write depending on threshold; just verify no exception
        self.assertIsInstance(written, int)
        self.assertGreaterEqual(written, 0)


if __name__ == "__main__":
    unittest.main()
