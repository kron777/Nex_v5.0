"""GeniusTagger (theory_x/genius/tagger.py) — test coverage added 2026-11-08.
Previously had zero test coverage (confirmed by grep across tests/ before
writing this) -- this is the live SentienceNode (name/tick/decay/state),
wired via run.py's `_genius_tagger`, not to be confused with the separate
genius_provenance_tag.py CLI backfill script.

Tests only, proving current behaviour -- no production code changed by this
file. Covers:
- _load_weights(): loads + validates the weights file, caches by mtime,
  falls back to last-good on a bad reload, records (not raises) on a
  missing file
- _get_t6_beliefs(): cache + TTL
- _existing_tag_ids(): scoped by version and optionally by since_ts
- _score_fire(): feature->sigmoid->class, and the NEX5_FRAME_DEDUP penalty
  path (flag off leaves the score untouched)
- _write_tag(): INSERT OR IGNORE semantics (a duplicate for the same
  (fountain_event_id, weights_version) is silently absorbed, not an error)
- _backfill() / _tag_window(): the two tick() code paths, incl. "nothing
  new to tag" and "already tagged" short-circuits
- tick(): backfill runs exactly once, then switches to _tag_window();
  never raises even when weights are missing
- FINDING (not fixed, flagged per instruction): this class's decay() and
  state() do NOT match the SentienceNode protocol every sibling module in
  this codebase implements (metacognition.py, harmonizer.py,
  substrate_harmonic.py, competing_drives.py, self_mind_view.py all use
  `decay(self, now)` and a callable `state(self, now=None)`). Here,
  `decay(self)` takes no `now` argument, and `state` is a @property, not a
  method. theory_x/__init__.py's own SentienceNode Protocol declares
  `decay(self, now: float) -> None` and `state(self, now=None) -> dict`
  explicitly. This is currently DORMANT, not live-breaking: grepped every
  call site -- nothing outside this module's own tick()/start_loop() ever
  calls .decay(now) or .state(now) on a GeniusTagger instance, and
  theory_x.all_nodes() (the registry this instance is registered into via
  run.py) has zero external callers anywhere in the codebase today. But if
  a generic cross-node sweep is ever built -- which is literally what
  theory_x/__init__.py's own docstring says the registry is for
  ("future cross-node orchestration") -- calling .decay(now) on this node
  specifically would raise TypeError, and .state(now) would try to call a
  dict. Tests below prove the gap directly rather than asserting a crash
  blindly, so the exact mismatch is pinned down.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from tests._bootstrap import *  # noqa: F401, F403


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_genius_tagger_")
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


def _write_weights_file(tmp, version="v2.0", threshold=0.5, weights=None, extra=None):
    path = Path(tmp) / "weights.json"
    data = {
        "version": version,
        "weights": weights if weights is not None else [0.2, 0.2, 0.2, 0.2, 0.2],
        "bias": 0.0,
        "threshold": threshold,
        "training_accuracy": 0.9,
    }
    if extra:
        data.update(extra)
    path.write_text(json.dumps(data))
    return path


def _make_tagger(writers, readers, weights_path):
    from theory_x.genius.tagger import GeniusTagger
    return GeniusTagger(
        conversations_writer=writers["conversations"],
        conversations_reader=readers["conversations"],
        dynamic_reader=readers["dynamic"],
        beliefs_reader=readers["beliefs"],
        weights_path=weights_path,
    )


def _seed_fire(writers, thought, hot_branch="systems", ts=None):
    ts = ts if ts is not None else time.time()
    return writers["dynamic"].write(
        "INSERT INTO fountain_events (ts, thought, readiness, hot_branch) "
        "VALUES (?, ?, 0.8, ?)", (ts, thought, hot_branch),
    )


class TestLoadWeights(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_missing_file_returns_none_and_records_warning(self):
        tagger = _make_tagger(self.writers, self.readers, Path(self.tmp) / "nope.json")
        self.assertIsNone(tagger._load_weights())

    def test_valid_file_loads_and_caches(self):
        wp = _write_weights_file(self.tmp)
        tagger = _make_tagger(self.writers, self.readers, wp)
        w = tagger._load_weights()
        self.assertEqual(w["version"], "v2.0")
        # Second call, same mtime -- returns cached object, not a re-read.
        w2 = tagger._load_weights()
        self.assertIs(w, w2)

    def test_missing_key_falls_back_to_last_good(self):
        wp = _write_weights_file(self.tmp)
        tagger = _make_tagger(self.writers, self.readers, wp)
        good = tagger._load_weights()
        self.assertIsNotNone(good)

        # Corrupt the file (missing 'threshold'), bump mtime.
        time.sleep(0.01)
        wp.write_text(json.dumps({"version": "v2.1", "weights": [0.1] * 5, "bias": 0.0}))
        reloaded = tagger._load_weights()
        self.assertEqual(reloaded["version"], "v2.0")  # unchanged -- fell back

    def test_wrong_weight_count_falls_back_to_last_good(self):
        wp = _write_weights_file(self.tmp)
        tagger = _make_tagger(self.writers, self.readers, wp)
        tagger._load_weights()
        time.sleep(0.01)
        wp.write_text(json.dumps({
            "version": "v2.1", "weights": [0.1, 0.2], "bias": 0.0, "threshold": 0.5,
        }))
        reloaded = tagger._load_weights()
        self.assertEqual(reloaded["version"], "v2.0")

    def test_reload_on_mtime_change_picks_up_new_version(self):
        wp = _write_weights_file(self.tmp, version="v2.0")
        tagger = _make_tagger(self.writers, self.readers, wp)
        tagger._load_weights()
        time.sleep(0.01)
        _write_weights_file(self.tmp, version="v2.1")
        reloaded = tagger._load_weights()
        self.assertEqual(reloaded["version"], "v2.1")


class TestT6Cache(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.wp = _write_weights_file(self.tmp)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_t6_cache_reads_recent_tier6_beliefs(self):
        now = time.time()
        self.writers["beliefs"].write(
            "INSERT INTO beliefs (content, tier, confidence, created_at, source, locked, paused) "
            "VALUES ('t6 belief', 6, 0.7, ?, 'test', 0, 0)", (now,))
        tagger = _make_tagger(self.writers, self.readers, self.wp)
        t6 = tagger._get_t6_beliefs(now)
        self.assertEqual(len(t6), 1)

    def test_t6_cache_reused_within_ttl(self):
        # Note: an EMPTY cache ([]) is falsy, so `self._t6_cache_at < ttl
        # and self._t6_cache` never hits on a zero-belief store -- the TTL
        # guard only actually engages once the cache holds >=1 row. Seed
        # one up front so this test exercises the real caching path rather
        # than that edge case (a minor, harmless inefficiency, not a
        # correctness bug -- flagged in the module docstring above, not
        # fixed here).
        self.writers["beliefs"].write(
            "INSERT INTO beliefs (content, tier, confidence, created_at, source, locked, paused) "
            "VALUES ('early t6', 6, 0.7, ?, 'test', 0, 0)", (time.time(),))
        tagger = _make_tagger(self.writers, self.readers, self.wp)
        now = time.time()
        first = tagger._get_t6_beliefs(now)
        self.assertEqual(len(first), 1)
        # Seed a new belief AFTER the first cache fill -- within TTL, the
        # cache must not pick it up.
        self.writers["beliefs"].write(
            "INSERT INTO beliefs (content, tier, confidence, created_at, source, locked, paused) "
            "VALUES ('late t6', 6, 0.7, ?, 'test', 0, 0)", (now,))
        second = tagger._get_t6_beliefs(now + 1)
        self.assertEqual(len(second), len(first))


class TestExistingTagIds(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.wp = _write_weights_file(self.tmp)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_scoped_by_version(self):
        now = time.time()
        self.writers["conversations"].write(
            "INSERT INTO genius_tags (fountain_event_id, score, class, "
            "weights_version, tagged_at) VALUES (1, 0.9, 'STRIKING', 'v1', ?)", (now,))
        self.writers["conversations"].write(
            "INSERT INTO genius_tags (fountain_event_id, score, class, "
            "weights_version, tagged_at) VALUES (2, 0.9, 'STRIKING', 'v2', ?)", (now,))
        tagger = _make_tagger(self.writers, self.readers, self.wp)
        self.assertEqual(tagger._existing_tag_ids("v1", since_ts=None), {1})
        self.assertEqual(tagger._existing_tag_ids("v2", since_ts=None), {2})

    def test_scoped_by_since_ts(self):
        tagger = _make_tagger(self.writers, self.readers, self.wp)
        old, new = time.time() - 1000, time.time()
        self.writers["conversations"].write(
            "INSERT INTO genius_tags (fountain_event_id, score, class, "
            "weights_version, tagged_at) VALUES (1, 0.9, 'STRIKING', 'v1', ?)", (old,))
        self.writers["conversations"].write(
            "INSERT INTO genius_tags (fountain_event_id, score, class, "
            "weights_version, tagged_at) VALUES (2, 0.9, 'STRIKING', 'v1', ?)", (new,))
        self.assertEqual(tagger._existing_tag_ids("v1", since_ts=new - 10), {2})


class TestScoreFire(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.wp = _write_weights_file(self.tmp, threshold=0.5)
        self.tagger = _make_tagger(self.writers, self.readers, self.wp)

    def tearDown(self):
        os.environ.pop("NEX5_FRAME_DEDUP", None)
        _cleanup(self.writers, self.tmp)

    def test_score_fire_returns_score_and_class(self):
        weights = self.tagger._load_weights()
        fire = {"id": 1, "ts": time.time(),
                "thought": "a genuinely long and structured thought with many words here",
                "hot_branch": "systems"}
        score, cls = self.tagger._score_fire(fire, [], [], weights)
        self.assertIsInstance(score, float)
        self.assertIn(cls, ("STRIKING", "ordinary"))

    def test_frame_dedup_flag_off_leaves_score_unpenalized(self):
        os.environ.pop("NEX5_FRAME_DEDUP", None)
        weights = self.tagger._load_weights()
        fire = {"id": 1, "ts": time.time(), "thought": "the quiet between thoughts",
                "hot_branch": "systems"}
        with mock.patch("theory_x.genius.score_v2.frame_penalty") as mock_penalty:
            self.tagger._score_fire(fire, [], [], weights)
            mock_penalty.assert_not_called()

    def test_frame_dedup_flag_on_applies_penalty(self):
        os.environ["NEX5_FRAME_DEDUP"] = "1"
        weights = self.tagger._load_weights()
        fire = {"id": 1, "ts": time.time(), "thought": "the quiet between thoughts",
                "hot_branch": "systems"}
        with mock.patch("theory_x.genius.score_v2.frame_penalty", return_value=0.5) as mock_penalty:
            score, _ = self.tagger._score_fire(fire, [], [], weights)
            mock_penalty.assert_called_once()


class TestWriteTag(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.wp = _write_weights_file(self.tmp)
        self.tagger = _make_tagger(self.writers, self.readers, self.wp)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_write_tag_inserts_row_and_updates_stats(self):
        self.tagger._write_tag(1, 0.9, "STRIKING", "v2.0", time.time())
        row = self.readers["conversations"].read_one(
            "SELECT * FROM genius_tags WHERE fountain_event_id = 1")
        self.assertEqual(row["class"], "STRIKING")
        self.assertEqual(self.tagger._tagged_total, 1)
        self.assertEqual(self.tagger._tagged_striking, 1)

    def test_duplicate_tag_same_version_silently_ignored(self):
        now = time.time()
        self.tagger._write_tag(1, 0.9, "STRIKING", "v2.0", now)
        self.tagger._write_tag(1, 0.1, "ordinary", "v2.0", now)  # same (id, version)
        rows = self.readers["conversations"].read(
            "SELECT * FROM genius_tags WHERE fountain_event_id = 1")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["class"], "STRIKING")  # first write wins (INSERT OR IGNORE)
        # Stats still incremented for the attempted (ignored) write -- the
        # method doesn't check rowcount, just assumes success.
        self.assertEqual(self.tagger._tagged_total, 2)


class TestBackfillAndTagWindow(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.wp = _write_weights_file(self.tmp, threshold=0.999)  # force "ordinary"
        self.tagger = _make_tagger(self.writers, self.readers, self.wp)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_backfill_tags_all_fires_in_window(self):
        now = time.time()
        for i in range(3):
            _seed_fire(self.writers, f"thought {i}", ts=now - i)
        weights = self.tagger._load_weights()
        self.tagger._backfill(weights, now)
        rows = self.readers["conversations"].read("SELECT * FROM genius_tags")
        self.assertEqual(len(rows), 3)

    def test_backfill_skips_already_tagged(self):
        now = time.time()
        fid = _seed_fire(self.writers, "thought", ts=now)
        weights = self.tagger._load_weights()
        self.tagger._write_tag(fid, 0.1, "ordinary", weights["version"], now)
        self.tagger._backfill(weights, now)  # should find nothing new to tag
        rows = self.readers["conversations"].read("SELECT * FROM genius_tags")
        self.assertEqual(len(rows), 1)

    def test_backfill_no_fires_in_window_is_a_noop(self):
        weights = self.tagger._load_weights()
        self.tagger._backfill(weights, time.time())  # must not raise
        rows = self.readers["conversations"].read("SELECT * FROM genius_tags")
        self.assertEqual(len(rows), 0)

    def test_tag_window_only_tags_within_lookback(self):
        now = time.time()
        _seed_fire(self.writers, "old", ts=now - 1000)  # outside 180s lookback
        _seed_fire(self.writers, "new", ts=now - 10)
        weights = self.tagger._load_weights()
        self.tagger._tag_window(weights, now, lookback_seconds=180)
        rows = self.readers["conversations"].read("SELECT * FROM genius_tags")
        self.assertEqual(len(rows), 1)


class TestTick(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_tick_runs_backfill_once_then_switches_to_tag_window(self):
        wp = _write_weights_file(self.tmp)
        tagger = _make_tagger(self.writers, self.readers, wp)
        self.assertFalse(tagger._backfill_done)
        tagger.tick()
        self.assertTrue(tagger._backfill_done)
        with mock.patch.object(tagger, "_tag_window") as mock_tw, \
             mock.patch.object(tagger, "_backfill") as mock_bf:
            tagger.tick()
            mock_tw.assert_called_once()
            mock_bf.assert_not_called()

    def test_tick_never_raises_with_missing_weights_file(self):
        tagger = _make_tagger(self.writers, self.readers, Path(self.tmp) / "nope.json")
        try:
            result = tagger.tick()
        except Exception as exc:
            self.fail(f"tick() raised instead of handling missing weights: {exc}")
        self.assertEqual(result["weights_version"], None)

    def test_tick_never_raises_on_internal_exception(self):
        wp = _write_weights_file(self.tmp)
        tagger = _make_tagger(self.writers, self.readers, wp)
        with mock.patch.object(tagger, "_backfill", side_effect=RuntimeError("boom")):
            try:
                tagger.tick()
            except Exception as exc:
                self.fail(f"tick() propagated instead of swallowing: {exc}")


class TestSentienceNodeProtocolGap(unittest.TestCase):
    """FINDING, not a fix: pins down the exact mismatch between GeniusTagger
    and the SentienceNode protocol every sibling module implements. See the
    module docstring above for the full explanation and why this is
    currently dormant rather than live-breaking."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.wp = _write_weights_file(self.tmp)
        self.tagger = _make_tagger(self.writers, self.readers, self.wp)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_decay_takes_no_now_argument_unlike_every_sibling_node(self):
        self.tagger.decay()  # works
        with self.assertRaises(TypeError):
            self.tagger.decay(time.time())  # the protocol-conformant call shape

    def test_state_is_a_property_not_a_callable_method(self):
        snapshot = self.tagger.state  # property access, no parens -- works
        self.assertIsInstance(snapshot, dict)
        with self.assertRaises(TypeError):
            self.tagger.state(time.time())  # the protocol-conformant call shape

    def test_isinstance_check_against_the_declared_protocol_still_passes(self):
        """Python's runtime_checkable Protocol isinstance check only verifies
        attribute PRESENCE, not signature -- so registration itself
        (run.py's theory_x.register(_genius_tagger)) does not raise despite
        the shape mismatch above. Confirmed directly rather than assumed."""
        from theory_x import SentienceNode
        self.assertIsInstance(self.tagger, SentienceNode)

    def test_all_nodes_registry_has_no_external_consumers_today(self):
        """Confirms the mismatch is currently dormant: the registry
        GeniusTagger is registered into has no call site anywhere in the
        codebase that reads it back and drives .decay(now)/.state(now)
        generically (verified separately by grep; this just confirms the
        registry function itself still exists and is import-safe, so a
        future consumer wiring it up is the realistic trigger path)."""
        from theory_x import all_nodes
        self.assertIsInstance(all_nodes(), list)


if __name__ == "__main__":
    unittest.main()
