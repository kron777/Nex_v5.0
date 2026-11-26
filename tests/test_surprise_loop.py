"""Regression tests for surprise promotion tags and retry semantics."""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch


def test_non_big_surprise_has_one_surprise_tag():
    from theory_x.life.surprise_loop import _surprise_tags
    assert _surprise_tags(False) == ["surprise"]


def test_big_surprise_has_both_distinct_tags():
    from theory_x.life.surprise_loop import _surprise_tags
    tags = _surprise_tags(True)
    assert tags == ["surprise", "big_surprise"]
    assert len(tags) == len(set(tags))


class TestSurprisePromotionRetry(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nex5_surprise_retry_")
        os.environ["NEX5_DATA_DIR"] = self.tmp
        from substrate.init_db import init_all
        init_all()
        from substrate import Writer, Reader, db_paths
        self.paths = db_paths()
        self.writers = {n: Writer(p, name=n) for n, p in self.paths.items()}
        self.readers = {n: Reader(p) for n, p in self.paths.items()}

    def tearDown(self):
        for writer in self.writers.values():
            try:
                writer.close()
            except Exception:
                pass
        shutil.rmtree(self.tmp, ignore_errors=True)
        os.environ.pop("NEX5_DATA_DIR", None)

    def test_failed_event_is_retried_even_when_events_share_timestamp(self):
        from theory_x.life import surprise_loop as sl

        ts = time.time() - 60
        rows = [
            (ts, 101, "internal_belief", 0.9, 1, 1,
             "FAIL_SENTINEL expected content", "unexpected actual content", "[]"),
            (ts, 102, "internal_belief", 0.9, 1, 1,
             "NEXT_SENTINEL expected content", "another unexpected input", "[]"),
        ]
        for row in rows:
            self.writers["dynamic"].write(
                "INSERT INTO surprise_events "
                "(triggered_at, prediction_id, prediction_type, surprise_score, "
                "surprise_flag, big_surprise, predicted_content, actual_content, tags) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                row,
            )

        original_connect = sl.connect
        fail_once = {"active": True}
        beliefs_path = str(Path(self.paths["beliefs"]).resolve())

        class ConnectionProxy:
            def __init__(self, inner):
                object.__setattr__(self, "_inner", inner)

            def __getattr__(self, name):
                return getattr(self._inner, name)

            def __setattr__(self, name, value):
                setattr(self._inner, name, value)

            def execute(self, sql, params=()):
                if (fail_once["active"]
                        and sql.lstrip().upper().startswith("INSERT INTO BELIEFS")
                        and params and "FAIL_SENTINEL" in str(params[0])):
                    fail_once["active"] = False
                    raise RuntimeError("injected transient write failure")
                return self._inner.execute(sql, params)

        def connect_with_one_failure(path, timeout=15):
            inner = original_connect(path, timeout=timeout)
            if str(Path(path).resolve()) == beliefs_path:
                return ConnectionProxy(inner)
            return inner

        with patch.object(sl, "connect", side_effect=connect_with_one_failure):
            first = sl.surprise_tick()

        self.assertEqual(first["promoted"], 0)
        self.assertEqual(
            self.readers["beliefs"].read(
                "SELECT id FROM beliefs WHERE source='surprise'"
            ),
            [],
        )
        cursor = self.readers["dynamic"].read_one(
            "SELECT value FROM daemon_kv WHERE key=?",
            (sl.LAST_PROMOTED_ID_KEY,),
        )
        self.assertEqual(int(cursor["value"]), 0)

        with patch.object(sl, "connect", side_effect=original_connect):
            second = sl.surprise_tick()

        self.assertEqual(second["promoted"], 2)
        promoted = self.readers["beliefs"].read(
            "SELECT content FROM beliefs WHERE source='surprise'"
        )
        joined = "\n".join(row["content"] for row in promoted)
        self.assertIn("FAIL_SENTINEL", joined)
        self.assertIn("NEXT_SENTINEL", joined)


if __name__ == "__main__":
    unittest.main()
