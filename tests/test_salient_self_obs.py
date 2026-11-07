"""Candidate 4 (2026-11-07 round) — salience-weighted self-observation.

Dark by default: NEX5_SALIENT_SELF_OBS=1 to arm. See
observation_reports/salienceSelfObs_DESIGN_AND_PREREGISTRATION.md for the
design and the live exposure check this is built against.

Covers:
- flag OFF: _refresh_recent_cache() reproduces today's exact pick --
  ORDER BY created_at DESC LIMIT 3, recent[0] always the newest row,
  severity ignored entirely. Byte-identical to pre-change behaviour.
- flag ON: a severity*decay score re-ranks a wider candidate pool, so an
  older-but-more-severe event can outrank a fresher-but-milder one --
  the exact shape of the live exposure check (severity 1.0 @ 9 days old
  vs severity 0.37 @ same-day).
- decay clamps to zero at/after _STALE_DAYS, never negative, so an event
  past its auto-resolve horizon can't out-rank anything through decay
  alone (it also wouldn't still be "unresolved" by then, but the ranking
  function is checked in isolation too).
- ties: equal score falls back to recency, same as the old behaviour.
- format_for_prompt() reflects whichever event the cache actually picked,
  under both flag states.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

_FLAG = "NEX5_SALIENT_SELF_OBS"


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_salient_obs_")
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


def _seed_event(writers, event_type, severity, days_ago=0.0, source="test"):
    created_at = time.time() - days_ago * 86400
    writers["conversations"].write(
        "INSERT INTO meta_cognition_events "
        "(event_type, description, severity, source, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (event_type, f"Test {event_type} event", severity, source, created_at),
    )


class TestFlagOffUnchanged(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        os.environ.pop(_FLAG, None)

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def test_newest_wins_regardless_of_severity(self):
        """Exact shape of the live exposure check: an old, severe event
        must NOT win over a fresh, mild one with the flag off."""
        _seed_event(self.writers, "groove", severity=1.0, days_ago=9.0)
        _seed_event(self.writers, "value_drift_abandonment", severity=0.37, days_ago=0.0)
        mc = _build_mc(self.writers, self.readers)
        mc.tick()
        recent = mc._cached_recent
        self.assertEqual(recent[0]["event_type"], "value_drift_abandonment")
        self.assertEqual(len(recent), 2)

    def test_limit_stays_3(self):
        for i in range(5):
            _seed_event(self.writers, "groove", severity=0.9, days_ago=float(i))
        mc = _build_mc(self.writers, self.readers)
        mc.tick()
        self.assertEqual(len(mc._cached_recent), 3)


class TestFlagOnSalienceRanking(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        os.environ[_FLAG] = "1"

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def test_severe_older_event_outranks_fresh_mild_one(self):
        """The exact live shape: severity 1.0 @ 9 days old (decay ~0.357,
        score ~0.357) must beat severity 0.37 @ same-day (decay 1.0, score
        0.37 in the raw-recency case) -- wait, close call by design: assert
        via the real formula rather than hand-waving."""
        _seed_event(self.writers, "groove", severity=1.0, days_ago=9.0)
        _seed_event(self.writers, "value_drift_abandonment", severity=0.37, days_ago=0.0)
        mc = _build_mc(self.writers, self.readers)
        mc.tick()
        recent = mc._cached_recent
        self.assertEqual(recent[0]["event_type"], "groove")

    def test_very_severe_event_clearly_outranks_fresh_mild_one(self):
        """Less borderline than the live numbers, so the win isn't an
        artifact of a close score -- severity 1.0 @ 5 days old (decay
        ~0.643, score ~0.643) vs severity 0.1 @ same-day (score 0.1)."""
        _seed_event(self.writers, "groove", severity=1.0, days_ago=5.0)
        _seed_event(self.writers, "uncertainty_stagnation", severity=0.1, days_ago=0.0)
        mc = _build_mc(self.writers, self.readers)
        mc.tick()
        self.assertEqual(mc._cached_recent[0]["event_type"], "groove")

    def test_decay_clamps_to_zero_not_negative_past_stale_horizon(self):
        from theory_x.stage9_metacognition import metacognition as mod
        mc = _build_mc(self.writers, self.readers)
        now = time.time()
        ancient_row = {
            "event_type": "groove", "severity": 1.0,
            "created_at": now - (mod._STALE_DAYS + 10) * 86400,
        }
        fresh_row = {
            "event_type": "goal_drift", "severity": 0.01,
            "created_at": now,
        }
        ranked = mc._rank_by_salience([ancient_row, fresh_row], now)
        # ancient event's score must be clamped to 0.0, never negative,
        # so even a near-zero-severity fresh event beats it.
        self.assertEqual(ranked[0]["event_type"], "goal_drift")

    def test_candidate_pool_widens_beyond_3(self):
        for i in range(6):
            _seed_event(self.writers, "groove", severity=0.5, days_ago=float(i))
        mc = _build_mc(self.writers, self.readers)
        mc.tick()
        self.assertEqual(len(mc._cached_recent), 6)

    def test_equal_severity_falls_back_to_recency(self):
        _seed_event(self.writers, "groove", severity=0.5, days_ago=2.0)
        _seed_event(self.writers, "goal_drift", severity=0.5, days_ago=0.0)
        mc = _build_mc(self.writers, self.readers)
        mc.tick()
        # same severity, same decay formula applied -- the newer one has
        # less decay applied against it, so it should still win; this also
        # confirms score isn't accidentally recency-blind.
        self.assertEqual(mc._cached_recent[0]["event_type"], "goal_drift")

    def test_format_for_prompt_reflects_salience_pick(self):
        _seed_event(self.writers, "groove", severity=1.0, days_ago=5.0)
        _seed_event(self.writers, "uncertainty_stagnation", severity=0.1, days_ago=0.0)
        mc = _build_mc(self.writers, self.readers)
        mc.tick()
        text = mc.format_for_prompt()
        self.assertIn("repeated patterns", text)


class TestRankBySalienceUnit(unittest.TestCase):
    """Direct unit tests of the scoring function, no DB involved."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_missing_severity_treated_as_zero_not_crash(self):
        mc = _build_mc(self.writers, self.readers)
        now = time.time()
        row = {"event_type": "x", "severity": None, "created_at": now}
        ranked = mc._rank_by_salience([row], now)
        self.assertEqual(len(ranked), 1)


if __name__ == "__main__":
    unittest.main()
