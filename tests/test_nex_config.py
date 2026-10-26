"""nex_config — typed flag registry + validator (H8)."""
import unittest

from tests import _bootstrap  # noqa: F401

import nex_config


class TestRegistry(unittest.TestCase):
    def test_core_flags_registered(self):
        for f in ("NEX5_DATA_DIR", "NEX5_GUI_PORT", "NEX5_COMPASSION",
                  "NEX5_SPEECH_MIN_GAP", "NEX5_CONFIG_STRICT"):
            self.assertIn(f, nex_config.KNOWN_FLAGS, f)

    def test_kinds_are_valid(self):
        self.assertEqual(set(nex_config.KNOWN_FLAGS.values()) - {"bool", "int", "float", "str"}, set())


class TestValidate(unittest.TestCase):
    def test_unknown_flag_detected(self):
        env = {"NEX5_COMPASSOIN": "1", "PATH": "/bin"}  # typo + a non-NEX var
        unk = nex_config.unknown_flags(env)
        self.assertEqual(unk, ["NEX5_COMPASSOIN"])
        probs = nex_config.validate(env, log=False)
        self.assertTrue(any("NEX5_COMPASSOIN" in p for p in probs))

    def test_known_flag_not_flagged(self):
        env = {"NEX5_COMPASSION": "1", "NEX5_GUI_PORT": "8765"}
        self.assertEqual(nex_config.validate(env, log=False), [])

    def test_bad_int_value_detected(self):
        env = {"NEX5_GUI_PORT": "not-a-number"}
        probs = nex_config.invalid_values(env)
        self.assertTrue(any("NEX5_GUI_PORT" in p for p in probs))

    def test_bad_float_value_detected(self):
        env = {"NEX5_SPEECH_MIN_GAP": "fast"}
        self.assertTrue(nex_config.validate(env, log=False))

    def test_strict_raises(self):
        env = {"NEX5_TYPO_FLAG": "1"}
        with self.assertRaises(nex_config.ConfigError):
            nex_config.validate(env, strict=True, log=False)

    def test_strict_via_env_flag(self):
        env = {"NEX5_CONFIG_STRICT": "1", "NEX5_ANOTHER_TYPO": "x"}
        with self.assertRaises(nex_config.ConfigError):
            nex_config.validate(env, log=False)

    def test_clean_env_does_not_raise_in_strict(self):
        env = {"NEX5_CONFIG_STRICT": "1", "NEX5_COMPASSION": "1"}
        self.assertEqual(nex_config.validate(env, log=False), [])


class TestAccessors(unittest.TestCase):
    def test_get_bool(self):
        self.assertTrue(nex_config.get_bool("X", env={"X": "1"}))
        self.assertTrue(nex_config.get_bool("X", env={"X": "true"}))
        self.assertFalse(nex_config.get_bool("X", env={"X": "0"}))
        self.assertFalse(nex_config.get_bool("X", env={}))
        self.assertTrue(nex_config.get_bool("X", default=True, env={}))

    def test_get_int(self):
        self.assertEqual(nex_config.get_int("X", 5, env={"X": "12"}), 12)
        self.assertEqual(nex_config.get_int("X", 5, env={"X": "bad"}), 5)  # falls back
        self.assertEqual(nex_config.get_int("X", 5, env={}), 5)

    def test_get_float(self):
        self.assertEqual(nex_config.get_float("X", 1.0, env={"X": "2.5"}), 2.5)
        self.assertEqual(nex_config.get_float("X", 1.0, env={"X": "bad"}), 1.0)

    def test_get_str(self):
        self.assertEqual(nex_config.get_str("X", "d", env={"X": "v"}), "v")
        self.assertEqual(nex_config.get_str("X", "d", env={}), "d")


if __name__ == "__main__":
    unittest.main()
