"""Phase M1 — LLM-generated reflective self-critique (`tools/metacog_digest.py`).

Dark by default: NEX5_METACOG_REFLECT=1 to arm. Covers:
- flag OFF: run_once() is a pure no-op -- no DB read of consequence, no LLM
  call attempted, no metacog_summaries row.
- flag ON, zero salience peaks in window: still a no-op (no degenerate
  "reflect on nothing" call).
- flag ON, peaks present: the window/threshold filter is exact (surprise
  below 0.8 excluded, events outside the window excluded), the reflection
  prompt actually contains the included peaks' text, and exactly one
  metacog_summaries row is written with the mocked model's output.

This is a different mechanism from theory_x/stage9_metacognition/
metacognition.py's NEX5_METACOG_DIGEST (template-based, count-triggered,
writes back into meta_cognition_events) -- see tools/metacog_digest.py's
module docstring. Not wired into gui/server.py or any chat-block assembly;
these tests never touch the live process or any real LLM endpoint (the
VoiceClient request_fn is always injected/mocked here).
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

_FLAG = "NEX5_METACOG_REFLECT"


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_mcog_reflect_")
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


def _seed_meta_event(writers, description, hours_ago, severity=0.5, event_type="groove"):
    created_at = time.time() - hours_ago * 3600
    writers["conversations"].write(
        "INSERT INTO meta_cognition_events "
        "(event_type, description, severity, source, created_at) "
        "VALUES (?, ?, ?, 'test', ?)",
        (event_type, description, severity, created_at))


def _seed_surprise(writers, actual_content, hours_ago, score):
    triggered_at = time.time() - hours_ago * 3600
    writers["dynamic"].write(
        "INSERT INTO surprise_events "
        "(triggered_at, prediction_id, prediction_type, surprise_score, "
        "surprise_flag, big_surprise, predicted_content, actual_content, tags) "
        "VALUES (?, 1, 'internal_belief', ?, ?, ?, '', ?, '[]')",
        (triggered_at, score, int(score > 0.8), int(score > 0.8), actual_content))


class _FakeClient:
    """Stands in for VoiceClient: records the prompt it was asked to speak,
    returns a fixed reflective text, carries a fake .model for storage."""
    def __init__(self, text="line one\nline two\nline three"):
        self.model = "fake-model"
        self.calls: list = []
        self._text = text

    def speak(self, req, beliefs=None, belief_count=0):
        self.calls.append(req)
        from voice.llm import VoiceResponse
        return VoiceResponse(text=self._text, register=req.register, raw={})


class TestFlagOff(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        os.environ.pop(_FLAG, None)
        _seed_meta_event(self.writers, "groove event", hours_ago=1)
        _seed_surprise(self.writers, "big surprise", hours_ago=1, score=0.95)

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def test_returns_none_and_writes_nothing(self):
        from tools.metacog_digest import run_once
        client = _FakeClient()
        result = run_once(self.readers["conversations"], self.readers["dynamic"],
                           self.writers["conversations"], client=client)
        self.assertIsNone(result)
        self.assertEqual(client.calls, [], "flag OFF must never call the LLM")
        row = self.readers["conversations"].read_one(
            "SELECT COUNT(*) AS n FROM metacog_summaries")
        self.assertEqual(row["n"], 0)


class TestFlagOnNoPeaks(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        os.environ[_FLAG] = "1"

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def test_empty_window_is_a_noop(self):
        from tools.metacog_digest import run_once
        client = _FakeClient()
        result = run_once(self.readers["conversations"], self.readers["dynamic"],
                           self.writers["conversations"], client=client)
        self.assertIsNone(result)
        self.assertEqual(client.calls, [])


class TestFlagOnWithPeaks(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        os.environ[_FLAG] = "1"
        # in-window, included
        _seed_meta_event(self.writers, "INCLUDED meta event", hours_ago=2,
                          event_type="value_drift_abandonment")
        _seed_surprise(self.writers, "INCLUDED surprise content", hours_ago=1, score=0.91)
        # in-window but below threshold -- excluded
        _seed_surprise(self.writers, "EXCLUDED low-score surprise", hours_ago=1, score=0.5)
        # outside the (default 6h) window -- excluded
        _seed_meta_event(self.writers, "EXCLUDED stale meta event", hours_ago=48)
        _seed_surprise(self.writers, "EXCLUDED stale surprise", hours_ago=48, score=0.99)

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def test_filters_and_stores_exactly_one_row(self):
        from tools.metacog_digest import run_once
        client = _FakeClient(text="A\nB\nC")
        result = run_once(self.readers["conversations"], self.readers["dynamic"],
                           self.writers["conversations"], client=client)
        self.assertIsNotNone(result)
        self.assertEqual(result["peak_count"], 2)
        self.assertEqual(result["reflective_text"], "A\nB\nC")
        self.assertEqual(result["model"], "fake-model")

        self.assertEqual(len(client.calls), 1, "exactly one LLM call per run")
        prompt = client.calls[0].prompt
        self.assertIn("INCLUDED meta event", prompt)
        self.assertIn("INCLUDED surprise content", prompt)
        self.assertNotIn("EXCLUDED", prompt)
        self.assertIn("Reflective Context", prompt)

        rows = self.readers["conversations"].read(
            "SELECT * FROM metacog_summaries")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["peak_count"], 2)
        self.assertEqual(rows[0]["reflective_text"], "A\nB\nC")
        self.assertEqual(rows[0]["model"], "fake-model")

    def test_second_run_adds_a_second_row_not_a_duplicate_guard(self):
        # No cooldown/dedup is claimed for M1 (unlike the count-based digest);
        # confirm that's actually the behaviour, not an assumption.
        from tools.metacog_digest import run_once
        client = _FakeClient()
        run_once(self.readers["conversations"], self.readers["dynamic"],
                  self.writers["conversations"], client=client)
        run_once(self.readers["conversations"], self.readers["dynamic"],
                  self.writers["conversations"], client=client)
        row = self.readers["conversations"].read_one(
            "SELECT COUNT(*) AS n FROM metacog_summaries")
        self.assertEqual(row["n"], 2)
        self.assertEqual(len(client.calls), 2)


if __name__ == "__main__":
    unittest.main()
