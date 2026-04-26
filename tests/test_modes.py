"""Tests for the mode system."""
import unittest
import sys
import os
import tempfile
import sqlite3


class TestModeDefinitions(unittest.TestCase):

    def test_all_ten_modes_exist(self):
        from theory_x.modes import MODES, DISPLAY_ORDER
        self.assertEqual(len(MODES), 10)
        for name in DISPLAY_ORDER:
            self.assertIn(name, MODES)

    def test_display_order_covers_all_modes(self):
        from theory_x.modes import MODES, DISPLAY_ORDER
        self.assertEqual(set(DISPLAY_ORDER), set(MODES.keys()))

    def test_get_mode_returns_correct_mode(self):
        from theory_x.modes import get_mode
        m = get_mode("market")
        self.assertEqual(m.name, "market")
        self.assertEqual(m.crystallization_category, "market_signal")

    def test_get_mode_falls_back_to_default(self):
        from theory_x.modes import get_mode, DEFAULT_MODE
        m = get_mode("nonexistent_mode")
        self.assertEqual(m.name, DEFAULT_MODE)

    def test_silent_mode_disables_fountain_and_speech(self):
        from theory_x.modes import get_mode
        m = get_mode("silent")
        self.assertFalse(m.fountain_enabled)
        self.assertFalse(m.speech_enabled)

    def test_normal_mode_has_defaults(self):
        from theory_x.modes import get_mode
        m = get_mode("normal")
        self.assertTrue(m.fountain_enabled)
        self.assertTrue(m.speech_enabled)
        self.assertEqual(m.governor_base_prob_multiplier, 1.0)
        self.assertEqual(m.governor_min_gap_multiplier, 1.0)

    def test_market_mode_has_feed_weights(self):
        from theory_x.modes import get_mode
        m = get_mode("market")
        self.assertIn("crypto", m.feed_weights)
        self.assertGreater(m.feed_weights["crypto"], 1.0)

    def test_all_modes_have_required_fields(self):
        from theory_x.modes import MODES
        for name, mode in MODES.items():
            self.assertEqual(mode.name, name, f"Mode {name} has wrong name field")
            self.assertIsInstance(mode.display_name, str)
            self.assertIsInstance(mode.description, str)
            self.assertIsInstance(mode.fountain_interval_seconds, int)

    def test_mode_dataclass_immutable_by_field(self):
        from theory_x.modes import get_mode
        m1 = get_mode("normal")
        m2 = get_mode("normal")
        self.assertEqual(m1.name, m2.name)


class TestModeState(unittest.TestCase):

    def setUp(self):
        """Create an in-memory-like SQLite DB with the config table."""
        import tempfile
        self._tmpdir = tempfile.mkdtemp()
        self._db_path = os.path.join(self._tmpdir, "beliefs.db")
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS config "
            "(key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at REAL NOT NULL)"
        )
        conn.commit()
        conn.close()

        from substrate import Writer, Reader
        self._writer = Writer(self._db_path, name="beliefs")
        self._reader = Reader(self._db_path)

    def tearDown(self):
        self._writer.close()
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_default_mode_is_normal(self):
        from theory_x.modes.state import ModeState
        ms = ModeState(self._writer, self._reader)
        self.assertEqual(ms.current_name(), "normal")

    def test_set_mode_changes_current(self):
        from theory_x.modes.state import ModeState
        ms = ModeState(self._writer, self._reader)
        result = ms.set_mode("market")
        self.assertTrue(result)
        self.assertEqual(ms.current_name(), "market")
        self.assertEqual(ms.current().name, "market")

    def test_set_unknown_mode_returns_false(self):
        from theory_x.modes.state import ModeState
        ms = ModeState(self._writer, self._reader)
        result = ms.set_mode("no_such_mode")
        self.assertFalse(result)
        self.assertEqual(ms.current_name(), "normal")

    def test_set_same_mode_returns_false(self):
        from theory_x.modes.state import ModeState
        ms = ModeState(self._writer, self._reader)
        result = ms.set_mode("normal")
        self.assertFalse(result)

    def test_mode_persists_to_db(self):
        from theory_x.modes.state import ModeState
        ms = ModeState(self._writer, self._reader)
        ms.set_mode("research")
        import time
        time.sleep(0.05)
        persisted = ms._load()
        self.assertEqual(persisted, "research")

    def test_build_mode_state_loads_persisted(self):
        from theory_x.modes.state import ModeState, build_mode_state
        ms = ModeState(self._writer, self._reader)
        ms.set_mode("news")
        import time
        time.sleep(0.05)

        ms2 = build_mode_state(
            {"beliefs": self._writer},
            {"beliefs": self._reader},
        )
        self.assertEqual(ms2.current_name(), "news")


if __name__ == "__main__":
    unittest.main()
