"""Tests for theory_x/probes/context_snapshot.py.

Covers:
- Empty substrate returns all REQUIRED FIELDS with valid empty values
- Populated substrate returns non-empty values for relevant fields
- A reader raising on every call still produces a complete snap with
  "[ERROR: ...]" values — the probe must never be aborted by a bad reader
- ENV override NEX5_PROBE_SNAPSHOT_WINDOW_SEC is respected (content
  outside the window is excluded)
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from tests import _bootstrap  # noqa: F401

REQUIRED_FIELDS = (
    "active_arcs",
    "dormant_top5",
    "open_signals",
    "recent_fires",
    "groove_alerts",
    "cooldowns",
    "feed_activity",
    "branch_activations",
    "current_mode",
)

LIST_FIELDS = {f for f in REQUIRED_FIELDS if f != "current_mode"}


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_snap_")
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


def _exploding_reader():
    """A reader that raises on every call — used for error-resilience tests."""
    r = MagicMock()
    r.read.side_effect = RuntimeError("boom")
    r.read_one.side_effect = RuntimeError("boom")
    return r


class TestSnapshotRequiredFields(unittest.TestCase):
    """Empty substrate: all keys present, list fields are valid JSON arrays."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _snap(self):
        from theory_x.probes.context_snapshot import snapshot_context
        return snapshot_context(
            beliefs_reader=self.readers["beliefs"],
            dynamic_reader=self.readers["dynamic"],
            sense_reader=self.readers["sense"],
        )

    def test_all_required_keys_present(self):
        snap = self._snap()
        for key in REQUIRED_FIELDS:
            self.assertIn(key, snap, f"Missing required key: {key}")

    def test_list_fields_are_json_arrays(self):
        snap = self._snap()
        for key in LIST_FIELDS:
            try:
                parsed = json.loads(snap[key])
                self.assertIsInstance(parsed, list, f"{key} is not a JSON array")
            except json.JSONDecodeError:
                self.fail(f"{key} is not valid JSON: {snap[key]!r}")

    def test_current_mode_is_string(self):
        snap = self._snap()
        self.assertIsInstance(snap["current_mode"], str)

    def test_empty_substrate_has_empty_lists(self):
        snap = self._snap()
        for key in LIST_FIELDS:
            val = json.loads(snap[key])
            self.assertEqual(val, [], f"{key} should be [] on empty substrate, got {val!r}")

    def test_current_mode_unknown_when_not_set(self):
        snap = self._snap()
        self.assertEqual(snap["current_mode"], "unknown")


class TestSnapshotPopulated(unittest.TestCase):
    """Populated substrate returns non-empty values for seeded fields."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _snap(self):
        from theory_x.probes.context_snapshot import snapshot_context
        return snapshot_context(
            beliefs_reader=self.readers["beliefs"],
            dynamic_reader=self.readers["dynamic"],
            sense_reader=self.readers["sense"],
        )

    def test_recent_fires_populated(self):
        now = time.time()
        self.writers["dynamic"].write(
            "INSERT INTO fountain_events (ts, thought, readiness) VALUES (?, ?, ?)",
            (now - 10, "I wonder if the quiet is structural.", 0.75),
        )
        time.sleep(0.05)
        snap = self._snap()
        fires = json.loads(snap["recent_fires"])
        self.assertEqual(len(fires), 1)
        self.assertEqual(fires[0]["thought"], "I wonder if the quiet is structural.")

    def test_cooldowns_populated(self):
        now = time.time()
        self.writers["beliefs"].write(
            "INSERT INTO signal_cooldown (content_hash, content, cooldown_until, reason, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("abc123", "the server hum is still here", now + 3600, "groove", now),
        )
        time.sleep(0.05)
        snap = self._snap()
        cooldowns = json.loads(snap["cooldowns"])
        self.assertEqual(len(cooldowns), 1)
        self.assertEqual(cooldowns[0]["content"], "the server hum is still here")

    def test_expired_cooldowns_excluded(self):
        now = time.time()
        self.writers["beliefs"].write(
            "INSERT INTO signal_cooldown (content_hash, content, cooldown_until, reason, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("old123", "old pattern", now - 1, "groove", now - 7200),
        )
        time.sleep(0.05)
        snap = self._snap()
        cooldowns = json.loads(snap["cooldowns"])
        self.assertEqual(cooldowns, [], "Expired cooldown must not appear")

    def test_groove_alerts_only_unacknowledged(self):
        now = time.time()
        # Unacknowledged alert
        self.writers["beliefs"].write(
            "INSERT INTO groove_alerts "
            "(detected_at, alert_type, severity, pattern, window_size) "
            "VALUES (?, ?, ?, ?, ?)",
            (now - 30, "ngram_repeat", 0.7, "hum", 5),
        )
        # Acknowledged alert (should be excluded)
        self.writers["beliefs"].write(
            "INSERT INTO groove_alerts "
            "(detected_at, alert_type, severity, pattern, window_size, acknowledged_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (now - 60, "exact_repeat", 0.5, "cursor", 3, now - 20),
        )
        time.sleep(0.05)
        snap = self._snap()
        alerts = json.loads(snap["groove_alerts"])
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["alert_type"], "ngram_repeat")

    def test_feed_activity_grouped_by_stream(self):
        now = int(time.time())
        for _ in range(3):
            self.writers["sense"].write(
                "INSERT INTO sense_events (stream, payload, timestamp) VALUES (?, ?, ?)",
                ("news.reuters", '{"title":"test"}', now - 5),
            )
        self.writers["sense"].write(
            "INSERT INTO sense_events (stream, payload, timestamp) VALUES (?, ?, ?)",
            ("agi.arxiv_cs_ai", '{"title":"x"}', now - 5),
        )
        time.sleep(0.05)
        snap = self._snap()
        feeds = json.loads(snap["feed_activity"])
        streams = {f["stream"] for f in feeds}
        self.assertIn("news.reuters", streams)
        reuters = next(f for f in feeds if f["stream"] == "news.reuters")
        self.assertEqual(reuters["event_count"], 3)

    def test_current_mode_persisted(self):
        now = time.time()
        self.writers["beliefs"].write(
            "INSERT OR REPLACE INTO config (key, value, updated_at) VALUES (?, ?, ?)",
            ("current_mode", "drift", now),
        )
        time.sleep(0.05)
        snap = self._snap()
        self.assertEqual(snap["current_mode"], "drift")

    def test_open_signals_within_window(self):
        now = time.time()
        os.environ["NEX5_PROBE_SNAPSHOT_WINDOW_SEC"] = "300"
        try:
            # Signal inside window
            self.writers["beliefs"].write(
                "INSERT INTO signals "
                "(detected_at, detector_name, signal_type, payload, confidence) "
                "VALUES (?, ?, ?, ?, ?)",
                (now - 100, "groove_spotter", "ngram_repeat", '{"pattern":"hum"}', 0.8),
            )
            # Signal outside window
            self.writers["beliefs"].write(
                "INSERT INTO signals "
                "(detected_at, detector_name, signal_type, payload, confidence) "
                "VALUES (?, ?, ?, ?, ?)",
                (now - 400, "groove_spotter", "ngram_repeat", '{"pattern":"old"}', 0.6),
            )
            time.sleep(0.05)
            from theory_x.probes.context_snapshot import snapshot_context
            snap = snapshot_context(
                beliefs_reader=self.readers["beliefs"],
                dynamic_reader=self.readers["dynamic"],
                sense_reader=self.readers["sense"],
            )
            signals = json.loads(snap["open_signals"])
            self.assertEqual(len(signals), 1)
            self.assertEqual(signals[0]["signal_type"], "ngram_repeat")
        finally:
            os.environ.pop("NEX5_PROBE_SNAPSHOT_WINDOW_SEC", None)

    def test_branch_activations_grouped(self):
        now = time.time()
        for i in range(4):
            self.writers["dynamic"].write(
                "INSERT INTO pipeline_events (ts, step, branch_id, magnitude) "
                "VALUES (?, ?, ?, ?)",
                (now - i * 10, "attend", "systems", 0.6),
            )
        self.writers["dynamic"].write(
            "INSERT INTO pipeline_events (ts, step, branch_id, magnitude) "
            "VALUES (?, ?, ?, ?)",
            (now - 5, "attend", "philosophy", 0.4),
        )
        time.sleep(0.05)
        snap = self._snap()
        activations = json.loads(snap["branch_activations"])
        branch_ids = [a["branch_id"] for a in activations]
        self.assertIn("systems", branch_ids)
        systems = next(a for a in activations if a["branch_id"] == "systems")
        self.assertEqual(systems["hit_count"], 4)


class TestSnapshotErrorResilience(unittest.TestCase):
    """Readers that always raise must not abort the snapshot."""

    def test_exploding_readers_produce_complete_snap(self):
        from theory_x.probes.context_snapshot import snapshot_context
        boom = _exploding_reader()
        snap = snapshot_context(
            beliefs_reader=boom,
            dynamic_reader=boom,
            sense_reader=boom,
        )
        for key in REQUIRED_FIELDS:
            self.assertIn(key, snap, f"Missing key after explosion: {key}")

    def test_exploding_readers_show_error_values(self):
        from theory_x.probes.context_snapshot import snapshot_context
        boom = _exploding_reader()
        snap = snapshot_context(
            beliefs_reader=boom,
            dynamic_reader=boom,
            sense_reader=boom,
        )
        error_fields = [k for k, v in snap.items() if v.startswith("[ERROR:")]
        self.assertGreater(
            len(error_fields), 0,
            "Expected at least one [ERROR:...] value when all readers explode",
        )

    def test_partial_failure_rest_still_populated(self):
        """One bad reader should not prevent other readers from contributing."""
        self.writers, self.readers, self.tmp = _make_env()
        try:
            now = time.time()
            self.writers["dynamic"].write(
                "INSERT INTO fountain_events (ts, thought, readiness) VALUES (?, ?, ?)",
                (now - 10, "Something stirs.", 0.8),
            )
            time.sleep(0.05)

            from theory_x.probes.context_snapshot import snapshot_context
            snap = snapshot_context(
                beliefs_reader=_exploding_reader(),
                dynamic_reader=self.readers["dynamic"],
                sense_reader=_exploding_reader(),
            )
            # recent_fires uses dynamic_reader — should succeed
            fires = json.loads(snap["recent_fires"])
            self.assertEqual(len(fires), 1)
            # active_arcs uses beliefs_reader — should be error
            self.assertTrue(snap["active_arcs"].startswith("[ERROR:"))
        finally:
            _cleanup(self.writers, self.tmp)


if __name__ == "__main__":
    unittest.main()
