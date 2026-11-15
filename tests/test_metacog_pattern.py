"""Self-pattern detection (NEX5_METACOG_PATTERN) — three more first-order
event_types on top of the existing Metacognition component, all read from
beliefs.branch_id (the existing per-thread identifier emergent_drives.py
already groups by):

- self_circling: the same branch carried forward N+ beliefs in a row.
- self_scattered: branch entropy over a recent window above the measured
  normal-rotation baseline (see the constant's comment in metacognition.py).
- self_resolved_after_stall: a branch resumes after a long gap.

Dark by default: NEX5_METACOG_PATTERN=1 to arm. Surfacing into the prompt is
unaffected by this flag — that still rides the existing NEX5_METACOG_VOICE
gate at the generator.py call site, same as every other event_type here.

Isolated tempdir DB (NEX5_DATA_DIR) — never the live DBs.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

_FLAG = "NEX5_METACOG_PATTERN"


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_mcog_pattern_")
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


_seed_counter = [0]
# init_all() seeds beliefs.db with its own rows (keystones/blacklist/koans)
# timestamped at real wall-clock "now" at seed time. A test's own `now =
# time.time()` is captured microseconds later and can be SMALLER than that
# seed timestamp once a small offset is subtracted (e.g. now - 3600), which
# would let seed rows outrank freshly-seeded test rows in an ORDER BY
# created_at DESC query. Push every test-seeded row comfortably past any
# such real-time collision; only relative ordering between test rows
# matters to the detectors under test, and adding a constant preserves it.
_FUTURE_OFFSET = 10_000_000


def _seed_belief(writers, branch_id, created_at, content=None):
    # beliefs.content is UNIQUE -- every seeded row needs distinct text.
    _seed_counter[0] += 1
    if content is None:
        content = f"seed belief {_seed_counter[0]} ({branch_id})"
    writers["beliefs"].write(
        "INSERT INTO beliefs (content, tier, confidence, created_at, branch_id) "
        "VALUES (?, 1, 0.9, ?, ?)",
        (content, created_at + _FUTURE_OFFSET, branch_id),
    )


class TestSelfPatternInertWithFlagOff(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.mc = _build_mc(self.writers, self.readers)
        os.environ.pop(_FLAG, None)

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def test_detect_self_pattern_returns_empty(self):
        now = time.time()
        for i in range(5):
            _seed_belief(self.writers, "same_branch", now - i)
        self.assertEqual(self.mc._detect_self_pattern(now), [])

    def test_tick_writes_nothing_for_pattern_types(self):
        now = time.time()
        for i in range(5):
            _seed_belief(self.writers, "same_branch", now - i)
        self.mc.tick()
        row = self.readers["conversations"].read_one(
            "SELECT COUNT(*) AS n FROM meta_cognition_events WHERE event_type LIKE 'self_%'"
        )
        self.assertEqual(int(row["n"]), 0)


class TestSelfCircling(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.mc = _build_mc(self.writers, self.readers)
        os.environ[_FLAG] = "1"

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def test_run_at_threshold_fires(self):
        now = time.time()
        for i in range(3):  # _SELF_CIRCLING_MIN_RUN
            _seed_belief(self.writers, "possibilities", now - i)
        findings = self.mc._detect_self_circling(now)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["event_type"], "self_circling")
        self.assertIn("possibilities", findings[0]["description"])
        self.assertIn("3 beliefs", findings[0]["description"])

    def test_run_below_threshold_does_not_fire(self):
        now = time.time()
        _seed_belief(self.writers, "possibilities", now - 1)
        _seed_belief(self.writers, "possibilities", now)
        self.assertEqual(self.mc._detect_self_circling(now), [])

    def test_rotation_breaks_the_run(self):
        now = time.time()
        _seed_belief(self.writers, "a", now - 3)
        _seed_belief(self.writers, "b", now - 2)
        _seed_belief(self.writers, "b", now - 1)
        _seed_belief(self.writers, "b", now)
        # run length 3 on "b" -- should fire
        findings = self.mc._detect_self_circling(now)
        self.assertEqual(len(findings), 1)
        self.assertIn("'b'", findings[0]["description"])

    def test_cooldown_prevents_immediate_refire(self):
        now = time.time()
        for i in range(3):
            _seed_belief(self.writers, "possibilities", now - i)
        first = self.mc._detect_self_circling(now)
        self.assertEqual(len(first), 1)
        second = self.mc._detect_self_circling(now + 1.0)
        self.assertEqual(second, [])


class TestSelfScattered(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.mc = _build_mc(self.writers, self.readers)
        os.environ[_FLAG] = "1"

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def test_insufficient_data_does_not_fire(self):
        now = time.time()
        for i in range(10):  # well below _SELF_SCATTERED_LOOKBACK_N (50)
            _seed_belief(self.writers, f"branch_{i}", now - i)
        self.assertEqual(self.mc._detect_self_scattered(now), [])

    def test_maximally_scattered_window_fires(self):
        now = time.time()
        # 50 beliefs, every single one a distinct branch -- maximum possible
        # entropy for this window size, must clear the measured baseline.
        for i in range(50):
            _seed_belief(self.writers, f"branch_{i}", now - i)
        findings = self.mc._detect_self_scattered(now)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["event_type"], "self_scattered")

    def test_single_branch_window_does_not_fire(self):
        now = time.time()
        # 50 beliefs, all one branch -- zero entropy, far below threshold.
        for i in range(50):
            _seed_belief(self.writers, "one_branch", now - i)
        self.assertEqual(self.mc._detect_self_scattered(now), [])

    def test_cooldown_prevents_immediate_refire(self):
        now = time.time()
        for i in range(50):
            _seed_belief(self.writers, f"branch_{i}", now - i)
        first = self.mc._detect_self_scattered(now)
        self.assertEqual(len(first), 1)
        second = self.mc._detect_self_scattered(now + 1.0)
        self.assertEqual(second, [])


class TestSelfResolvedAfterStall(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.mc = _build_mc(self.writers, self.readers)
        os.environ[_FLAG] = "1"

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def test_resume_after_long_gap_fires(self):
        now = time.time()
        _seed_belief(self.writers, "stalled_thread", now - 3 * 3600)  # 3h ago
        _seed_belief(self.writers, "stalled_thread", now)             # resumes now
        findings = self.mc._detect_self_resolved_after_stall(now)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["event_type"], "self_resolved_after_stall")
        self.assertIn("stalled_thread", findings[0]["description"])

    def test_short_gap_does_not_fire(self):
        now = time.time()
        _seed_belief(self.writers, "active_thread", now - 300)  # 5 min ago
        _seed_belief(self.writers, "active_thread", now)
        self.assertEqual(self.mc._detect_self_resolved_after_stall(now), [])

    def test_first_ever_belief_in_branch_does_not_fire(self):
        now = time.time()
        _seed_belief(self.writers, "brand_new_branch", now)
        self.assertEqual(self.mc._detect_self_resolved_after_stall(now), [])

    def test_cooldown_prevents_immediate_refire(self):
        now = time.time()
        _seed_belief(self.writers, "stalled_thread", now - 3 * 3600)
        _seed_belief(self.writers, "stalled_thread", now)
        first = self.mc._detect_self_resolved_after_stall(now)
        self.assertEqual(len(first), 1)
        second = self.mc._detect_self_resolved_after_stall(now + 1.0)
        self.assertEqual(second, [])


class TestSelfPatternSurfacing(unittest.TestCase):
    """format_for_prompt() phrasing for the three new event_types. Whether
    this is ever actually injected into a real fire is NEX5_METACOG_VOICE's
    gate at the generator.py call site, not this file's concern."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.mc = _build_mc(self.writers, self.readers)
        os.environ[_FLAG] = "1"

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def test_circling_phrase(self):
        now = time.time()
        for i in range(3):
            _seed_belief(self.writers, "possibilities", now - i)
        self.mc.tick()
        self.assertEqual(
            self.mc.format_for_prompt(),
            "Self-observation: I notice I keep circling the same thread.",
        )

    def test_resolved_after_stall_phrase(self):
        now = time.time()
        _seed_belief(self.writers, "stalled_thread", now - 3 * 3600)
        _seed_belief(self.writers, "stalled_thread", now)
        self.mc.tick()
        self.assertEqual(
            self.mc.format_for_prompt(),
            "Self-observation: a thread of mine stalled, and has now picked back up.",
        )


if __name__ == "__main__":
    unittest.main()
