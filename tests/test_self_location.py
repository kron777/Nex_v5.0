"""Phase 6 smoke tests — Self-Location commitment.

Covers:
- commit() writes locked Tier 1 belief with correct content/source/tier
- commit() is idempotent — second call returns same id, no duplicate written
- is_committed() returns True after commit, False on empty DB
- committed belief has locked=1, tier=1, source='self_location'
- committed belief cannot be demoted by BeliefPromoter.decisive_contradiction()
- /api/system/status returns 200 with all expected fields
- self_location_committed is True after commit
"""
from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_selfloc_")
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
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    os.environ.pop("NEX5_DATA_DIR", None)
    os.environ.pop("NEX5_ADMIN_HASH_FILE", None)


class TestSelfLocationCommitment(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _make_commitment(self):
        from theory_x.stage5_self_location.commitment import SelfLocationCommitment
        return SelfLocationCommitment()

    def test_commit_writes_tier1_locked_belief(self):
        c = self._make_commitment()
        bid = c.commit(self.writers["beliefs"], self.readers["beliefs"])
        self.assertIsNotNone(bid)
        time.sleep(0.05)
        rows = self.readers["beliefs"].read(
            "SELECT * FROM beliefs WHERE id=?", (bid,)
        )
        self.assertEqual(len(rows), 1)
        b = rows[0]
        self.assertEqual(b["tier"], 1)
        self.assertEqual(b["locked"], 1)
        self.assertEqual(b["source"], "self_location")

    def test_commit_content_matches_constant(self):
        from theory_x.stage5_self_location.commitment import COMMITMENT_CONTENT, SelfLocationCommitment
        c = SelfLocationCommitment()
        bid = c.commit(self.writers["beliefs"], self.readers["beliefs"])
        time.sleep(0.05)
        rows = self.readers["beliefs"].read(
            "SELECT content FROM beliefs WHERE id=?", (bid,)
        )
        self.assertEqual(rows[0]["content"], COMMITMENT_CONTENT)

    def test_commit_is_idempotent(self):
        c = self._make_commitment()
        id1 = c.commit(self.writers["beliefs"], self.readers["beliefs"])
        time.sleep(0.05)
        id2 = c.commit(self.writers["beliefs"], self.readers["beliefs"])
        self.assertEqual(id1, id2)
        time.sleep(0.05)
        rows = self.readers["beliefs"].read(
            "SELECT COUNT(*) as cnt FROM beliefs WHERE source='self_location'"
        )
        self.assertEqual(rows[0]["cnt"], 1)

    def test_is_committed_false_before_commit(self):
        c = self._make_commitment()
        self.assertFalse(c.is_committed(self.readers["beliefs"]))

    def test_is_committed_true_after_commit(self):
        c = self._make_commitment()
        c.commit(self.writers["beliefs"], self.readers["beliefs"])
        time.sleep(0.05)
        self.assertTrue(c.is_committed(self.readers["beliefs"]))

    def test_committed_belief_immune_to_decisive_contradiction(self):
        from theory_x.stage5_self_location.commitment import SelfLocationCommitment
        from theory_x.stage3_world_model.promotion import BeliefPromoter
        c = SelfLocationCommitment()
        bid = c.commit(self.writers["beliefs"], self.readers["beliefs"])
        time.sleep(0.05)
        promoter = BeliefPromoter(self.writers["beliefs"], self.readers["beliefs"])
        promoter.decisive_contradiction(bid)
        time.sleep(0.05)
        rows = self.readers["beliefs"].read(
            "SELECT tier, locked FROM beliefs WHERE id=?", (bid,)
        )
        self.assertEqual(rows[0]["tier"], 1)
        self.assertEqual(rows[0]["locked"], 1)


class TestSystemStatusEndpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.writers, cls.readers, cls.tmp = _make_env()
        from admin.auth import set_password
        set_password("selfloc-test-pw")
        from voice.llm import VoiceClient
        from gui.server import AppState, create_app
        from theory_x.stage5_self_location.commitment import SelfLocationCommitment

        commitment = SelfLocationCommitment()
        commitment.commit(cls.writers["beliefs"], cls.readers["beliefs"])
        time.sleep(0.1)

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

    def test_system_status_200(self):
        r = self.client.get("/api/system/status")
        self.assertEqual(r.status_code, 200)

    def test_system_status_has_expected_fields(self):
        data = self.client.get("/api/system/status").get_json()
        for key in ("scheduler", "dynamic", "world_model", "membrane",
                    "self_location_committed", "alpha"):
            self.assertIn(key, data, f"missing key: {key}")

    def test_system_status_self_location_committed_true(self):
        data = self.client.get("/api/system/status").get_json()
        self.assertTrue(data["self_location_committed"])

    def test_system_status_alpha_nonempty(self):
        data = self.client.get("/api/system/status").get_json()
        self.assertGreater(len(data["alpha"]), 10)

    def test_system_status_subsystems_false_when_not_wired(self):
        data = self.client.get("/api/system/status").get_json()
        self.assertFalse(data["scheduler"])
        self.assertFalse(data["dynamic"])
        self.assertFalse(data["world_model"])
        self.assertFalse(data["membrane"])


if __name__ == "__main__":
    unittest.main()
