"""SENTIENCE_PROGRAM Phase E — episodic memory (`NEX5_EPISODIC`).

Dark by default. Covers:
- flag OFF: record_episodes()/query_episodes()/reconstruct_episode() are
  all no-ops -- no reads beyond the flag check, no writes, empty/None
  results -- even with qualifying source rows present.
- flag ON: each of the four sources (ghost_flags, meta_cognition_events,
  surprise_events>0.8, held_tensions) produces exactly one episode, with
  the nearest self_state_history affect snapshot attached when one is
  within range, and none attached when nothing is close enough in time.
- idempotency: running record_episodes() twice never duplicates an episode
  for the same source row.
- query_episodes(): time window and min_salience filtering.
- reconstruct_episode(): composes a single account combining what+affect,
  not a raw row; correctly reports "no affect" when nothing was close
  enough; picks the most salient episode in range, not just the nearest.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

_FLAG = "NEX5_EPISODIC"


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_episodic_")
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


def _seed_self_state(writers, bound_at, synthesis="I am curious and my attention moves freely"):
    # self_state_history is created lazily by self_binding.bind() on first use,
    # not by init_all()'s shared schema -- ensure it exists before writing.
    from theory_x.stage_tom import self_binding
    self_binding._ensure_table()
    writers["dynamic"].write(
        "INSERT INTO self_state_history (bound_at, emotion, raga, drive, drift, readiness, "
        "synthesis, components) VALUES (?, 'curious', 'free', 'explore', 'none', 0.8, ?, '{}')",
        (bound_at, synthesis),
    )


def _seed_ghost_flag(writers, ts, reason="felt like a real moment"):
    return writers["dynamic"].write(
        "INSERT INTO ghost_flags (fountain_event_id, ts, reason) VALUES (1, ?, ?)", (ts, reason),
    )


def _seed_meta_event(writers, created_at, description="repeated pattern", event_type="groove"):
    return writers["conversations"].write(
        "INSERT INTO meta_cognition_events (event_type, description, severity, source, created_at) "
        "VALUES (?, ?, 0.6, 'test', ?)", (event_type, description, created_at),
    )


def _seed_surprise(writers, triggered_at, score, content="unexpected price move"):
    return writers["dynamic"].write(
        "INSERT INTO surprise_events (triggered_at, prediction_id, prediction_type, surprise_score, "
        "surprise_flag, big_surprise, predicted_content, actual_content, tags) "
        "VALUES (?, 1, 'internal_belief', ?, ?, ?, '', ?, '[]')",
        (triggered_at, score, int(score > 0.8), int(score > 0.8), content),
    )


def _seed_belief(writers, content):
    return writers["beliefs"].write(
        "INSERT INTO beliefs (content, tier, confidence, created_at, source, locked, paused) "
        "VALUES (?, 5, 0.65, ?, 'test', 0, 0)", (content, int(time.time())),
    )


def _seed_held_tension(writers, created_at, a_id, b_id):
    return writers["dynamic"].write(
        "INSERT INTO held_tensions (belief_id_a, belief_id_b, created_at) VALUES (?, ?, ?)",
        (a_id, b_id, created_at),
    )


class TestFlagOff(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        os.environ.pop(_FLAG, None)
        now = time.time()
        _seed_ghost_flag(self.writers, now - 60)
        _seed_meta_event(self.writers, now - 60)
        _seed_surprise(self.writers, now - 60, 0.95)
        _seed_self_state(self.writers, now - 30)

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def test_record_episodes_is_noop(self):
        from theory_x.memory import episodic
        result = episodic.record_episodes(
            self.readers["conversations"], self.readers["dynamic"],
            self.writers["dynamic"], self.readers["beliefs"])
        self.assertEqual(result, [])
        row = self.readers["dynamic"].read_one("SELECT COUNT(*) AS n FROM episodes")
        self.assertEqual(row["n"], 0)

    def test_query_and_reconstruct_are_inert(self):
        from theory_x.memory import episodic
        self.assertEqual(episodic.query_episodes(self.readers["dynamic"]), [])
        self.assertIsNone(episodic.reconstruct_episode(self.readers["dynamic"], time.time()))


class TestFlagOnRecordsAllSources(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        os.environ[_FLAG] = "1"

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def _record(self):
        from theory_x.memory import episodic
        return episodic.record_episodes(
            self.readers["conversations"], self.readers["dynamic"],
            self.writers["dynamic"], self.readers["beliefs"])

    def test_ghost_flag_recorded_with_affect(self):
        now = time.time()
        _seed_ghost_flag(self.writers, now - 60, reason="a real coincidence")
        _seed_self_state(self.writers, now - 50, synthesis="I am still and attentive")
        recorded = self._record()
        self.assertEqual(len(recorded), 1)
        self.assertEqual(recorded[0]["source_kind"], "ghost_flag")
        self.assertIn("a real coincidence", recorded[0]["what"])
        self.assertEqual(recorded[0]["affect_synthesis"], "I am still and attentive")

    def test_meta_cognition_recorded(self):
        now = time.time()
        _seed_meta_event(self.writers, now - 60, description="vocab narrowing noticed")
        recorded = self._record()
        self.assertEqual(len(recorded), 1)
        self.assertEqual(recorded[0]["source_kind"], "meta_cognition")
        self.assertIn("vocab narrowing noticed", recorded[0]["what"])

    def test_surprise_above_threshold_recorded_below_excluded(self):
        now = time.time()
        _seed_surprise(self.writers, now - 60, 0.95, content="market spiked hard")
        _seed_surprise(self.writers, now - 60, 0.5, content="ignore this one")
        recorded = self._record()
        self.assertEqual(len(recorded), 1)
        self.assertIn("market spiked hard", recorded[0]["what"])

    def test_held_tension_recorded_with_belief_content(self):
        now = time.time()
        a_id = _seed_belief(self.writers, "Markets trend upward over decades")
        b_id = _seed_belief(self.writers, "Markets do not trend upward over decades")
        _seed_held_tension(self.writers, now - 60, a_id, b_id)
        recorded = self._record()
        self.assertEqual(len(recorded), 1)
        self.assertEqual(recorded[0]["source_kind"], "held_tension")
        self.assertIn("Markets trend upward over decades", recorded[0]["what"])
        self.assertIn("Markets do not trend upward over decades", recorded[0]["what"])

    def test_affect_absent_when_nothing_close_in_time(self):
        now = time.time()
        _seed_ghost_flag(self.writers, now - 60)
        _seed_self_state(self.writers, now - 5 * 3600)  # far outside _AFFECT_MAX_GAP_S
        recorded = self._record()
        self.assertEqual(len(recorded), 1)
        self.assertIsNone(recorded[0]["affect_bound_at"])
        self.assertIsNone(recorded[0]["affect_synthesis"])

    def test_idempotent_on_second_run(self):
        now = time.time()
        _seed_ghost_flag(self.writers, now - 60)
        first = self._record()
        self.assertEqual(len(first), 1)
        second = self._record()
        self.assertEqual(second, [])
        row = self.readers["dynamic"].read_one("SELECT COUNT(*) AS n FROM episodes")
        self.assertEqual(row["n"], 1)

    def test_old_events_outside_lookback_not_recorded(self):
        from theory_x.memory import episodic
        now = time.time()
        _seed_ghost_flag(self.writers, now - 48 * 3600)
        recorded = episodic.record_episodes(
            self.readers["conversations"], self.readers["dynamic"],
            self.writers["dynamic"], self.readers["beliefs"], lookback_s=24 * 3600)
        self.assertEqual(recorded, [])


class TestQueryAndReconstruct(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        os.environ[_FLAG] = "1"

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def _record(self):
        from theory_x.memory import episodic
        return episodic.record_episodes(
            self.readers["conversations"], self.readers["dynamic"],
            self.writers["dynamic"], self.readers["beliefs"])

    def test_query_filters_by_salience(self):
        from theory_x.memory import episodic
        now = time.time()
        _seed_meta_event(self.writers, now - 60)  # severity 0.6
        _seed_surprise(self.writers, now - 60, 0.95)
        self._record()
        high = episodic.query_episodes(self.readers["dynamic"], min_salience=0.9)
        self.assertEqual(len(high), 1)
        self.assertEqual(high[0]["source_kind"], "surprise")

    def test_query_filters_by_time_window(self):
        from theory_x.memory import episodic
        now = time.time()
        _seed_ghost_flag(self.writers, now - 60)
        self._record()
        self.assertEqual(len(episodic.query_episodes(self.readers["dynamic"], since=now - 3600)), 1)
        self.assertEqual(len(episodic.query_episodes(self.readers["dynamic"], until=now - 3600)), 0)

    def test_reconstruct_composes_what_and_affect(self):
        from theory_x.memory import episodic
        now = time.time()
        _seed_ghost_flag(self.writers, now - 60, reason="a genuine coincidence")
        _seed_self_state(self.writers, now - 55, synthesis="I am quietly attentive")
        self._record()
        ep = episodic.reconstruct_episode(self.readers["dynamic"], now - 60)
        self.assertIsNotNone(ep)
        self.assertIn("a genuine coincidence", ep["account"])
        self.assertIn("I am quietly attentive", ep["account"])

    def test_reconstruct_reports_no_affect_plainly(self):
        from theory_x.memory import episodic
        now = time.time()
        _seed_ghost_flag(self.writers, now - 60)
        self._record()
        ep = episodic.reconstruct_episode(self.readers["dynamic"], now - 60)
        self.assertIn("no affect snapshot", ep["account"])

    def test_reconstruct_prefers_most_salient_not_just_nearest(self):
        from theory_x.memory import episodic
        now = time.time()
        _seed_meta_event(self.writers, now - 100)  # severity 0.6, nearer
        _seed_surprise(self.writers, now - 500, 0.99)  # farther but much more salient
        self._record()
        ep = episodic.reconstruct_episode(self.readers["dynamic"], now, window_s=3600)
        self.assertEqual(ep["source_kind"], "surprise")


if __name__ == "__main__":
    unittest.main()
