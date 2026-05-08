"""Phase 7.2 validation — interoception field-name fixes + fountain parser.

Covers:
  - Bug A fix: locked_beliefs field name in self_model.snapshot()
  - Bug B fix: tier_counts field name in self_model.snapshot()
  - selector._parse_payload: interoception renders as natural language
  - interoception.py delta metric: beliefs_since_last_poll across polls
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

from tests._bootstrap import *  # noqa: F401, F403


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_intro_")
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


def _seed_interoception_event(sense_writer, total=500, locked=23,
                               tier_counts=None, delta=None):
    """Insert one interoception sense_event with given field values."""
    if tier_counts is None:
        tier_counts = {"0": 5, "1": 30, "2": 80, "3": 200, "4": 150, "5": 35}
    payload = json.dumps({
        "total_beliefs": total,
        "locked_beliefs": locked,
        "tier_counts": tier_counts,
        "last_created_at": int(time.time()),
        "beliefs_since_last_poll": delta,
    })
    sense_writer.write(
        "INSERT INTO sense_events (stream, payload, provenance, timestamp) "
        "VALUES (?, ?, ?, ?)",
        ("internal.interoception", payload, "substrate://beliefs.db", int(time.time())),
    )


# ── Bug A & B: self_model.snapshot() field-name fixes ─────────────────────────

class TestSelfModelInteroceptionFix(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.writers, cls.readers, cls.tmp = _make_env()
        _seed_interoception_event(
            cls.writers["sense"],
            total=1623,
            locked=47,
            tier_counts={"0": 10, "1": 50, "2": 120, "3": 500, "4": 400, "5": 100},
        )

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

    def test_locked_count_reads_locked_beliefs(self):
        """Bug A fix: snapshot locked_count must reflect locked_beliefs from payload."""
        sm = self._make_sm()
        snap = sm.snapshot()
        self.assertEqual(snap["interoception"]["locked_count"], 47,
                         "locked_count should be 47 (from locked_beliefs field), not 0")

    def test_tier_distribution_reads_tier_counts(self):
        """Bug B fix: snapshot tier_distribution must reflect tier_counts from payload."""
        sm = self._make_sm()
        snap = sm.snapshot()
        td = snap["interoception"]["tier_distribution"]
        self.assertNotEqual(td, {},
                            "tier_distribution should not be empty (reads tier_counts)")
        self.assertIn("3", td)
        self.assertEqual(td["3"], 500)

    def test_belief_count_still_correct(self):
        """Regression: total_beliefs field name was already correct — must stay correct."""
        sm = self._make_sm()
        snap = sm.snapshot()
        self.assertEqual(snap["interoception"]["belief_count"], 1623)

    def test_format_self_state_shows_locked_count(self):
        """format_self_state() must render non-zero locked count in Belief graph line."""
        from theory_x.stage4_membrane.self_model import format_self_state
        sm = self._make_sm()
        snap = sm.snapshot()
        text = format_self_state(snap)
        self.assertIn("47 locked", text,
                      f"Expected '47 locked' in formatted state. Got:\n{text}")
        self.assertNotIn("0 locked", text,
                         f"'0 locked' should not appear. Got:\n{text}")


# ── Selector: interoception parser natural-language output ─────────────────────

class TestSelectorInteroceptionParser(unittest.TestCase):

    def _make_selector(self):
        from theory_x.world_bridge.selector import WorldBridgeSelector
        # Paths unused by _parse_payload — pass dummy values
        return WorldBridgeSelector("/dev/null", "/dev/null")

    def _payload(self, total=800, locked=12, tier_counts=None, delta=None):
        if tier_counts is None:
            tier_counts = {"2": 10, "3": 300, "4": 200, "5": 50}
        return json.dumps({
            "total_beliefs": total,
            "locked_beliefs": locked,
            "tier_counts": tier_counts,
            "last_created_at": int(time.time()),
            "beliefs_since_last_poll": delta,
        })

    def test_basic_natural_language_output(self):
        sel = self._make_selector()
        result = sel._parse_payload("internal.interoception", self._payload())
        self.assertTrue(result.startswith("[substrate]"),
                        f"Expected [substrate] prefix, got: {result!r}")
        self.assertIn("800 beliefs held", result)
        self.assertIn("12 locked", result)

    def test_dominant_tier_appears(self):
        tier_counts = {"0": 5, "1": 20, "3": 400, "4": 100}
        sel = self._make_selector()
        result = sel._parse_payload("internal.interoception",
                                    self._payload(tier_counts=tier_counts))
        self.assertIn("dominant tier: 3", result,
                      f"Expected dominant tier 3, got: {result!r}")

    def test_positive_delta_appears(self):
        sel = self._make_selector()
        result = sel._parse_payload("internal.interoception",
                                    self._payload(delta=15))
        self.assertIn("+15 since last check", result,
                      f"Expected delta in output, got: {result!r}")

    def test_negative_delta_appears(self):
        sel = self._make_selector()
        result = sel._parse_payload("internal.interoception",
                                    self._payload(delta=-3))
        self.assertIn("-3 since last check", result,
                      f"Expected negative delta in output, got: {result!r}")

    def test_zero_delta_omitted(self):
        sel = self._make_selector()
        result = sel._parse_payload("internal.interoception",
                                    self._payload(delta=0))
        self.assertNotIn("since last check", result,
                         f"Zero delta should be omitted, got: {result!r}")

    def test_none_delta_omitted(self):
        """First poll has no delta — None should be omitted, not crash."""
        sel = self._make_selector()
        result = sel._parse_payload("internal.interoception",
                                    self._payload(delta=None))
        self.assertNotIn("since last check", result)
        self.assertTrue(result.startswith("[substrate]"))

    def test_malformed_payload_returns_empty(self):
        sel = self._make_selector()
        result = sel._parse_payload("internal.interoception", "not-json{{{")
        self.assertEqual(result, "")

    def test_empty_payload_returns_empty(self):
        sel = self._make_selector()
        result = sel._parse_payload("internal.interoception", "")
        self.assertEqual(result, "")

    def test_no_tier_counts_still_renders(self):
        payload = json.dumps({"total_beliefs": 100, "locked_beliefs": 5})
        sel = self._make_selector()
        result = sel._parse_payload("internal.interoception", payload)
        self.assertIn("100 beliefs held", result)
        self.assertNotIn("dominant tier", result)


# ── Delta metric: beliefs_since_last_poll across consecutive polls ─────────────

class TestInteroceptionDelta(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.writers, cls.readers, cls.tmp = _make_env()
        import time as _t
        # Seed 10 beliefs into beliefs.db
        for i in range(10):
            cls.writers["beliefs"].write(
                "INSERT OR IGNORE INTO beliefs "
                "(content, tier, confidence, created_at, source) "
                "VALUES (?, 3, 0.5, ?, 'test')",
                (f"Test belief {i}", int(_t.time())),
            )

    @classmethod
    def tearDownClass(cls):
        _cleanup(cls.writers, cls.tmp)

    def _make_interoception(self):
        from theory_x.stage1_sense.internal.interoception import Interoception
        mock_writer = MagicMock()
        return Interoception(
            writer=mock_writer,
            beliefs_reader=self.readers["beliefs"],
        )

    def test_first_poll_delta_is_none(self):
        """On first poll, no baseline exists — delta must be None."""
        adapter = self._make_interoception()
        events = adapter.poll()
        self.assertEqual(len(events), 1)
        payload = json.loads(events[0].payload)
        self.assertIsNone(payload["beliefs_since_last_poll"],
                          "First poll delta should be None (no baseline)")

    def test_second_poll_no_change_delta_is_zero(self):
        adapter = self._make_interoception()
        adapter.poll()  # establish baseline (10 beliefs)
        events = adapter.poll()  # no new beliefs added
        payload = json.loads(events[0].payload)
        self.assertEqual(payload["beliefs_since_last_poll"], 0)

    def test_delta_reflects_new_beliefs(self):
        adapter = self._make_interoception()
        adapter.poll()  # baseline: 10

        # Add 3 more beliefs
        for i in range(3):
            self.writers["beliefs"].write(
                "INSERT OR IGNORE INTO beliefs "
                "(content, tier, confidence, created_at, source) "
                "VALUES (?, 3, 0.5, ?, 'test')",
                (f"Delta belief {i} ts={time.time()}", int(time.time())),
            )

        events = adapter.poll()
        payload = json.loads(events[0].payload)
        self.assertEqual(payload["beliefs_since_last_poll"], 3,
                         "Delta should be 3 after adding 3 beliefs")

    def test_total_beliefs_always_present(self):
        adapter = self._make_interoception()
        events = adapter.poll()
        payload = json.loads(events[0].payload)
        self.assertIn("total_beliefs", payload)
        self.assertGreaterEqual(payload["total_beliefs"], 0)

    def test_locked_beliefs_key_correct(self):
        """Confirm interoception writes locked_beliefs (not locked_count)."""
        adapter = self._make_interoception()
        events = adapter.poll()
        payload = json.loads(events[0].payload)
        self.assertIn("locked_beliefs", payload,
                      "Key must be locked_beliefs to match self_model reader")
        self.assertNotIn("locked_count", payload,
                         "Old key name must not appear")

    def test_tier_counts_key_correct(self):
        """Confirm interoception writes tier_counts (not tier_distribution)."""
        adapter = self._make_interoception()
        events = adapter.poll()
        payload = json.loads(events[0].payload)
        self.assertIn("tier_counts", payload,
                      "Key must be tier_counts to match self_model reader")
        self.assertNotIn("tier_distribution", payload,
                         "Old key name must not appear")


if __name__ == "__main__":
    unittest.main()
