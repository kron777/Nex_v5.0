"""Tests for SelfModel and BehaviouralSelfModel — SentienceNode protocol conformance
and Phase 5.2 additions (caching, format_for_prompt).

Does NOT test the wiring in gui/server.py — that is validated by real-traffic smoke
tests (DOCTRINE §6 anti-pattern: synthetic tests as verification).
"""
from __future__ import annotations

import os
import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path

from tests._bootstrap import *  # noqa: F401, F403


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_sm_")
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


# ── BehaviouralSelfModel — SentienceNode protocol ─────────────────────────────

class TestBSMSentienceNodeProtocol(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.writers, cls.readers, cls.tmp = _make_env()

    @classmethod
    def tearDownClass(cls):
        _cleanup(cls.writers, cls.tmp)

    def _make_bsm(self):
        from theory_x.stage4_membrane.behavioural_self_model import BehaviouralSelfModel
        return BehaviouralSelfModel(self.readers["conversations"])

    def test_implements_sentience_node_protocol(self):
        from theory_x import SentienceNode
        bsm = self._make_bsm()
        self.assertIsInstance(bsm, SentienceNode)

    def test_name_attribute(self):
        from theory_x.stage4_membrane.behavioural_self_model import BehaviouralSelfModel
        self.assertEqual(BehaviouralSelfModel.name, "behavioural_self_model")
        self.assertEqual(self._make_bsm().name, "behavioural_self_model")

    def test_tick_returns_dict(self):
        bsm = self._make_bsm()
        result = bsm.tick()
        self.assertIsInstance(result, dict)
        self.assertIn("name", result)
        self.assertIn("hedge_rate", result)

    def test_decay_accepts_float(self):
        bsm = self._make_bsm()
        bsm.decay(now=time.time())  # must not raise

    def test_state_no_args(self):
        bsm = self._make_bsm()
        s = bsm.state()
        self.assertIsInstance(s, dict)
        self.assertIn("name", s)
        self.assertIn("dominant_register", s)
        self.assertIn("sample_size", s)
        self.assertIn("cache_age_s", s)

    def test_state_with_float(self):
        bsm = self._make_bsm()
        s = bsm.state(now=time.time())
        self.assertIsInstance(s, dict)


# ── BehaviouralSelfModel — cache behaviour ────────────────────────────────────

class TestBSMCache(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.writers, cls.readers, cls.tmp = _make_env()

    @classmethod
    def tearDownClass(cls):
        _cleanup(cls.writers, cls.tmp)

    def _make_bsm(self):
        from theory_x.stage4_membrane.behavioural_self_model import BehaviouralSelfModel
        return BehaviouralSelfModel(self.readers["conversations"])

    def test_tick_populates_cache(self):
        bsm = self._make_bsm()
        self.assertIsNone(bsm._cached_metrics)
        bsm.tick()
        self.assertIsNotNone(bsm._cached_metrics)

    def test_cache_not_refreshed_within_ttl(self):
        from theory_x.stage4_membrane.behavioural_self_model import BehaviouralSelfModel, _CACHE_TTL
        bsm = BehaviouralSelfModel(self.readers["conversations"])
        bsm.tick()
        ts_after_first = bsm._cache_ts
        bsm.tick()  # within TTL — should NOT call observe() again
        self.assertEqual(bsm._cache_ts, ts_after_first)

    def test_state_empty_without_tick(self):
        bsm = self._make_bsm()
        s = bsm.state()
        # No tick yet — returns empty metrics
        self.assertEqual(s["sample_size"], 0)
        self.assertEqual(s["hedge_rate"], 0.0)

    def test_tick_thread_safe(self):
        bsm = self._make_bsm()
        errors = []

        def worker():
            try:
                bsm.tick()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)
        self.assertEqual(errors, [], f"Thread errors: {errors}")


# ── BehaviouralSelfModel — format_for_prompt ──────────────────────────────────

class TestBSMFormatForPrompt(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.writers, cls.readers, cls.tmp = _make_env()
        # Seed some messages so observe() returns real data
        import time as t
        w = cls.writers["conversations"]
        sid = "test-fmt-session"
        now = int(t.time())
        w.write("INSERT INTO sessions (id, started_at) VALUES (?, ?)", (sid, now))
        for i in range(10):
            w.write(
                "INSERT INTO messages (session_id, role, content, register, timestamp) "
                "VALUES (?, 'nex', ?, 'Philosophical', ?)",
                (sid, f"I think perhaps this is message {i}", now + i),
            )

    @classmethod
    def tearDownClass(cls):
        _cleanup(cls.writers, cls.tmp)

    def _make_bsm(self):
        from theory_x.stage4_membrane.behavioural_self_model import BehaviouralSelfModel
        return BehaviouralSelfModel(self.readers["conversations"])

    def test_format_empty_when_no_data(self):
        from theory_x.stage4_membrane.behavioural_self_model import BehaviouralSelfModel
        # Fresh BSM without tick — _cached_metrics is None, returns empty
        bsm = BehaviouralSelfModel(self.readers["conversations"])
        result = bsm.format_for_prompt()
        self.assertEqual(result, "")

    def test_format_returns_string_after_tick(self):
        bsm = self._make_bsm()
        bsm.tick()
        result = bsm.format_for_prompt()
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_format_contains_expected_fields(self):
        bsm = self._make_bsm()
        bsm.tick()
        result = bsm.format_for_prompt()
        self.assertIn("Behavioural self-knowledge", result)
        self.assertIn("Typical response", result)
        self.assertIn("Hedging", result)

    def test_format_never_raises(self):
        bsm = self._make_bsm()
        # Call without tick — should return "" not raise
        try:
            result = bsm.format_for_prompt()
        except Exception as e:
            self.fail(f"format_for_prompt raised: {e}")


# ── SelfModel — SentienceNode protocol ────────────────────────────────────────

class TestSelfModelProtocol(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.writers, cls.readers, cls.tmp = _make_env()

    @classmethod
    def tearDownClass(cls):
        _cleanup(cls.writers, cls.tmp)

    def _make_sm(self):
        from theory_x.stage4_membrane.self_model import SelfModel
        return SelfModel(
            sense_reader=self.readers["sense"],
            beliefs_reader=self.readers["beliefs"],
            dynamic_state=None,
        )

    def test_implements_sentience_node_protocol(self):
        from theory_x import SentienceNode
        sm = self._make_sm()
        self.assertIsInstance(sm, SentienceNode)

    def test_name_attribute(self):
        from theory_x.stage4_membrane.self_model import SelfModel
        self.assertEqual(SelfModel.name, "self_model")
        self.assertEqual(self._make_sm().name, "self_model")

    def test_tick_returns_dict(self):
        sm = self._make_sm()
        result = sm.tick()
        self.assertIsInstance(result, dict)
        self.assertIn("name", result)
        self.assertIn("belief_count", result)
        self.assertIn("inside_belief_count", result)

    def test_decay_accepts_float(self):
        sm = self._make_sm()
        sm.decay(now=time.time())  # must not raise

    def test_state_no_args(self):
        sm = self._make_sm()
        s = sm.state()
        self.assertIsInstance(s, dict)
        self.assertIn("name", s)
        self.assertIn("belief_count", s)
        self.assertIn("snapshot_age_s", s)

    def test_state_with_float(self):
        sm = self._make_sm()
        s = sm.state(now=time.time())
        self.assertIsInstance(s, dict)

    def test_tick_populates_cache(self):
        sm = self._make_sm()
        self.assertIsNone(sm._snapshot_cache)
        sm.tick()
        self.assertIsNotNone(sm._snapshot_cache)

    def test_cache_not_refreshed_within_ttl(self):
        sm = self._make_sm()
        sm.tick()
        ts_after_first = sm._snapshot_ts
        sm.tick()  # within TTL
        self.assertEqual(sm._snapshot_ts, ts_after_first)

    def test_snapshot_still_works(self):
        sm = self._make_sm()
        snap = sm.snapshot()
        for key in ("proprioception", "temporal", "interoception",
                    "meta_awareness", "attention", "inside_beliefs"):
            self.assertIn(key, snap)

    def test_tick_thread_safe(self):
        sm = self._make_sm()
        errors = []

        def worker():
            try:
                sm.tick()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)
        self.assertEqual(errors, [], f"Thread errors: {errors}")


if __name__ == "__main__":
    unittest.main()
