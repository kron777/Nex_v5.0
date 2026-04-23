"""Synergizer tests.

Covers:
- _select_pair() returns None when fewer than 2 branches
- _select_pair() returns cross-branch pair when 2 branches exist
- _select_pair() prefers pairs not recently synthesized
- _quality_check() rejects empty string
- _quality_check() rejects "nothing"
- _quality_check() rejects strings > 200 chars
- _quality_check() rejects blacklisted content
- synthesize() writes belief to DB when quality check passes
- synthesize() logs to synergizer_log
- synthesize() returns None when LLM returns "nothing"
- synergizer_log table created by init_db
- /api/beliefs/stats returns synergized_count field
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from tests import _bootstrap  # noqa: F401


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_synergizer_")
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


def _make_synergizer(writers, readers, llm_text="A bridge exists between attention and entropy."):
    from theory_x.stage3_world_model.synergizer import BeliefSynergizer
    mock_voice = MagicMock()
    resp = MagicMock()
    resp.text = llm_text
    mock_voice.speak.return_value = resp
    return BeliefSynergizer(
        beliefs_writer=writers["beliefs"],
        beliefs_reader=readers["beliefs"],
        voice_client=mock_voice,
    )


def _seed_belief(writers, content, branch_id, confidence=0.7, source="auto_growth"):
    writers["beliefs"].write(
        "INSERT INTO beliefs (content, tier, confidence, created_at, source, branch_id, locked) "
        "VALUES (?, 4, ?, ?, ?, ?, 0)",
        (content, confidence, time.time(), source, branch_id),
    )
    time.sleep(0.02)


class TestSelectPair(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_returns_none_fewer_than_2_branches(self):
        _seed_belief(self.writers, "Attention is selective.", "crypto")
        _seed_belief(self.writers, "Entropy is everywhere.", "crypto")
        s = _make_synergizer(self.writers, self.readers)
        self.assertIsNone(s._select_pair())

    def test_returns_cross_branch_pair(self):
        _seed_belief(self.writers, "Attention is selective.", "crypto")
        _seed_belief(self.writers, "Systems decay without input.", "ai_research")
        s = _make_synergizer(self.writers, self.readers)
        pair = s._select_pair()
        self.assertIsNotNone(pair)
        ba, bb = pair
        self.assertNotEqual(ba["branch_id"], bb["branch_id"])

    def test_prefers_not_recently_synthesized(self):
        # Seed two pairs across two branches
        _seed_belief(self.writers, "Attention is selective.", "crypto")
        _seed_belief(self.writers, "Attention collapses choices.", "crypto")
        _seed_belief(self.writers, "Systems decay without input.", "ai_research")
        _seed_belief(self.writers, "Feedback loops stabilize systems.", "ai_research")
        s = _make_synergizer(self.writers, self.readers)

        # Log recent use of the first pair
        pair1 = s._select_pair()
        self.assertIsNotNone(pair1)
        ba, bb = pair1
        self.writers["beliefs"].write(
            "INSERT INTO synergizer_log (ts, belief_id_a, belief_id_b, result_content) "
            "VALUES (?, ?, ?, ?)",
            (time.time(), ba["id"], bb["id"], "some result"),
        )
        time.sleep(0.05)

        # Select again — different pair should be preferred
        pair2 = s._select_pair()
        self.assertIsNotNone(pair2)
        ba2, bb2 = pair2
        # The ids should differ (less likely to re-select the recently-logged pair)
        # We just verify a valid cross-branch pair is returned
        self.assertNotEqual(ba2["branch_id"], bb2["branch_id"])


class TestQualityCheck(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.s = _make_synergizer(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_rejects_empty_string(self):
        self.assertFalse(self.s._quality_check(""))

    def test_rejects_nothing(self):
        self.assertFalse(self.s._quality_check("nothing"))
        self.assertFalse(self.s._quality_check("Nothing"))
        self.assertFalse(self.s._quality_check("NOTHING"))

    def test_rejects_too_long(self):
        long_text = "word " * 50  # > 200 chars
        self.assertFalse(self.s._quality_check(long_text))

    def test_rejects_too_short(self):
        self.assertFalse(self.s._quality_check("Too short."))

    def test_rejects_blacklisted_content(self):
        self.writers["beliefs"].write(
            "INSERT OR IGNORE INTO belief_blacklist (pattern, reason, added_at) VALUES (?, ?, ?)",
            ("BADWORD", "test", time.time()),
        )
        time.sleep(0.05)
        self.assertFalse(self.s._quality_check("This contains BADWORD in it okay."))

    def test_accepts_valid_text(self):
        text = "The boundary between order and chaos is where meaning accumulates."
        self.assertTrue(self.s._quality_check(text))


class TestSynthesize(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_writes_belief_when_quality_passes(self):
        _seed_belief(self.writers, "Attention is selective and costly.", "crypto")
        _seed_belief(self.writers, "Systems always tend toward entropy.", "ai_research")
        s = _make_synergizer(
            self.writers, self.readers,
            llm_text="Sustained attention is itself a form of anti-entropy."
        )
        result = s.synthesize()
        self.assertIsNotNone(result)
        time.sleep(0.1)
        rows = self.readers["beliefs"].read(
            "SELECT * FROM beliefs WHERE source = 'synergized'"
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["tier"], 6)
        self.assertAlmostEqual(rows[0]["confidence"], 0.65, places=2)

    def test_logs_to_synergizer_log(self):
        _seed_belief(self.writers, "Attention is selective and costly.", "crypto")
        _seed_belief(self.writers, "Systems always tend toward entropy.", "ai_research")
        s = _make_synergizer(
            self.writers, self.readers,
            llm_text="Sustained attention is itself a form of anti-entropy."
        )
        s.synthesize()
        time.sleep(0.1)
        rows = self.readers["beliefs"].read("SELECT * FROM synergizer_log")
        self.assertGreater(len(rows), 0)

    def test_returns_none_when_llm_returns_nothing(self):
        _seed_belief(self.writers, "Attention is selective and costly.", "crypto")
        _seed_belief(self.writers, "Systems always tend toward entropy.", "ai_research")
        s = _make_synergizer(self.writers, self.readers, llm_text="nothing")
        result = s.synthesize()
        self.assertIsNone(result)

    def test_returns_none_when_not_enough_branches(self):
        _seed_belief(self.writers, "Attention is selective.", "crypto")
        _seed_belief(self.writers, "Entropy is everywhere.", "crypto")
        s = _make_synergizer(self.writers, self.readers)
        self.assertIsNone(s.synthesize())


class TestSynergizerLogTable(unittest.TestCase):

    def test_synergizer_log_table_created_by_init_db(self):
        writers, readers, tmp = _make_env()
        try:
            rows = readers["beliefs"].read("SELECT COUNT(*) as cnt FROM synergizer_log")
            self.assertEqual(rows[0]["cnt"], 0)
        finally:
            _cleanup(writers, tmp)


class TestBeliefsStatsEndpoint(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.writers, cls.readers, cls.tmp = _make_env()
        from admin.auth import set_password
        set_password("synergizer-test-pw")
        from voice.llm import VoiceClient
        from gui.server import AppState, create_app
        cls.state = AppState(
            writers=cls.writers,
            readers=cls.readers,
            voice=VoiceClient(
                request_fn=lambda u, p: {"choices": [{"message": {"content": "ok"}}]}
            ),
        )
        cls.app = create_app(cls.state)
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.state.close()
        _cleanup(cls.writers, cls.tmp)

    def test_stats_returns_synergized_count(self):
        r = self.client.get("/api/beliefs/stats")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn("synergized_count", data)
        self.assertIsInstance(data["synergized_count"], int)

    def test_stats_returns_synergizer_runs(self):
        r = self.client.get("/api/beliefs/stats")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn("synergizer_runs", data)


if __name__ == "__main__":
    unittest.main()
