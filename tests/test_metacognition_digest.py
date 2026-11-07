"""SENTIENCE_PROGRAM Phase M — stateful metacognition digest (second-order).

Dark by default: NEX5_METACOG_DIGEST=1 to arm. Covers:
- flag OFF: byte-identical event count, no digest row, no change to
  get_recent()/format_for_prompt() vs not having Phase M at all.
- flag ON: a recurring first-order event_type (>= threshold in the lookback
  window) produces exactly one digest row, surfaced via format_for_prompt().
- below threshold: no fire.
- cooldown: a sustained pattern does not re-digest itself every tick.
- no-runaway (the pre-registered failure mode): the digest's own event_type
  is excluded from its own source query, so prior digest rows can never
  themselves be detected as "a pattern," at any count.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

_FLAG = "NEX5_METACOG_DIGEST"


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_mcog_digest_")
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


def _build_mc(writers, readers):
    from theory_x.stage9_metacognition.metacognition import Metacognition
    return Metacognition(
        writers["conversations"],
        readers["conversations"],
        readers["beliefs"],
    )


def _seed_event(writers, event_type, days_ago=0.0, source="test"):
    created_at = time.time() - days_ago * 86400
    writers["conversations"].write(
        "INSERT INTO meta_cognition_events "
        "(event_type, description, severity, source, created_at) "
        "VALUES (?, ?, 0.5, ?, ?)",
        (event_type, f"Test {event_type} event", source, created_at),
    )


def _count_rows(readers, event_type=None):
    if event_type is None:
        row = readers["conversations"].read_one(
            "SELECT COUNT(*) AS n FROM meta_cognition_events")
    else:
        row = readers["conversations"].read_one(
            "SELECT COUNT(*) AS n FROM meta_cognition_events WHERE event_type = ?",
            (event_type,))
    return int(row["n"])


class TestDigestInertWithFlagOff(unittest.TestCase):
    """The core dark-ship guarantee: with the flag unset, Phase M writes
    nothing and changes nothing an observer could see, at any seeded count."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.mc = _build_mc(self.writers, self.readers)
        os.environ.pop(_FLAG, None)

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def test_detect_digest_returns_empty(self):
        for _ in range(5):
            _seed_event(self.writers, "groove")
        self.assertEqual(self.mc._detect_digest(time.time()), [])

    def test_no_digest_row_written_on_tick(self):
        for _ in range(5):
            _seed_event(self.writers, "groove")
        before = _count_rows(self.readers)
        self.mc.tick()
        after = _count_rows(self.readers)
        self.assertEqual(after, before, "tick() must not write anything with the flag unset")
        self.assertEqual(_count_rows(self.readers, "metacog_digest"), 0)

    def test_format_for_prompt_unaffected(self):
        for _ in range(5):
            _seed_event(self.writers, "groove")
        self.mc.tick()
        text = self.mc.format_for_prompt()
        # Unchanged first-order voice; digest phrasing never appears.
        self.assertIn("repeated patterns", text)
        self.assertNotIn("Digest:", text)


class TestDigestFiresWithFlagOn(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.mc = _build_mc(self.writers, self.readers)
        os.environ[_FLAG] = "1"

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def test_pattern_at_threshold_writes_one_digest_row(self):
        for _ in range(3):  # _DIGEST_PATTERN_MIN_COUNT
            _seed_event(self.writers, "groove")
        findings = self.mc._detect_digest(time.time())
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["event_type"], "metacog_digest")
        self.assertIn("groove", findings[0]["description"])
        self.assertIn("3 groove events", findings[0]["description"])

    def test_below_threshold_does_not_fire(self):
        for _ in range(2):  # one short of _DIGEST_PATTERN_MIN_COUNT
            _seed_event(self.writers, "groove")
        self.assertEqual(self.mc._detect_digest(time.time()), [])

    def test_tick_writes_the_digest_row(self):
        for _ in range(4):
            _seed_event(self.writers, "goal_drift")
        before = _count_rows(self.readers, "metacog_digest")
        self.mc.tick()
        after = _count_rows(self.readers, "metacog_digest")
        self.assertEqual(after, before + 1)

    def test_format_for_prompt_surfaces_digest_line_same_tick(self):
        for _ in range(3):
            _seed_event(self.writers, "vocab_narrowing")
        self.mc.tick()
        text = self.mc.format_for_prompt()
        self.assertTrue(text.startswith("Self-observation: Digest:"))
        self.assertIn("vocab_narrowing", text)
        self.assertIn("growing less distinctive", text)

    def test_cooldown_prevents_immediate_refire(self):
        for _ in range(3):
            _seed_event(self.writers, "groove")
        now = time.time()
        first = self.mc._detect_digest(now)
        self.assertEqual(len(first), 1)
        # same event_type, still within the window, called again right away
        second = self.mc._detect_digest(now + 1.0)
        self.assertEqual(second, [], "a sustained pattern must not re-digest every tick")

    def test_independent_event_types_each_get_one_digest(self):
        for _ in range(3):
            _seed_event(self.writers, "groove")
        for _ in range(3):
            _seed_event(self.writers, "goal_drift")
        findings = self.mc._detect_digest(time.time())
        self.assertEqual(len(findings), 2)
        descriptions = " ".join(f["description"] for f in findings)
        self.assertIn("groove", descriptions)
        self.assertIn("goal_drift", descriptions)


class TestDigestNoRunaway(unittest.TestCase):
    """The pre-registered failure mode: digest rows feeding the first-order
    count. Verifies the exclusion holds at any accumulated digest-row count."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.mc = _build_mc(self.writers, self.readers)
        os.environ[_FLAG] = "1"

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def test_accumulated_digest_rows_never_self_trigger(self):
        # Simulate many PRIOR digest firings sitting in the table already --
        # if the exclusion were missing, this alone would cross threshold
        # and the digest would detect "a pattern" in its own output.
        for _ in range(10):
            _seed_event(self.writers, "metacog_digest", source="metacognition/digest")
        findings = self.mc._detect_digest(time.time())
        self.assertEqual(findings, [],
                          "metacog_digest rows must never themselves be a detectable pattern")

    def test_mixed_digest_and_real_pattern_only_fires_on_the_real_one(self):
        for _ in range(10):
            _seed_event(self.writers, "metacog_digest", source="metacognition/digest")
        for _ in range(3):
            _seed_event(self.writers, "groove")
        findings = self.mc._detect_digest(time.time())
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["event_type"], "metacog_digest")
        self.assertIn("groove", findings[0]["description"])


if __name__ == "__main__":
    unittest.main()
