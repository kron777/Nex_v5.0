"""Tests for speech.voices registry and state."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile

from speech.voices.registry import (
    Voice, _parse_voice_id, _find_voice_dir,
    enumerate_voices, get_voice, DEFAULT_VOICE,
)
from speech.voices.state import VoiceState, build_voice_state


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

class TestVoiceParser(unittest.TestCase):

    def test_american_female(self):
        v = _parse_voice_id("af_sarah")
        self.assertIsNotNone(v)
        self.assertEqual(v.id, "af_sarah")
        self.assertEqual(v.display_name, "Sarah")
        self.assertEqual(v.accent, "American")
        self.assertEqual(v.gender, "female")

    def test_american_male(self):
        v = _parse_voice_id("am_adam")
        self.assertIsNotNone(v)
        self.assertEqual(v.accent, "American")
        self.assertEqual(v.gender, "male")

    def test_british_female(self):
        v = _parse_voice_id("bf_emma")
        self.assertIsNotNone(v)
        self.assertEqual(v.accent, "British")
        self.assertEqual(v.gender, "female")

    def test_british_male(self):
        v = _parse_voice_id("bm_george")
        self.assertIsNotNone(v)
        self.assertEqual(v.accent, "British")
        self.assertEqual(v.gender, "male")

    def test_non_english_rejected(self):
        # Japanese, Spanish, etc. should return None
        self.assertIsNone(_parse_voice_id("jf_nezuko"))
        self.assertIsNone(_parse_voice_id("ef_dora"))
        self.assertIsNone(_parse_voice_id("zf_xiaobei"))

    def test_bad_format_returns_none(self):
        self.assertIsNone(_parse_voice_id("sarah"))
        self.assertIsNone(_parse_voice_id(""))
        self.assertIsNone(_parse_voice_id("a_sarah"))  # prefix length 1

    def test_display_name_capitalised(self):
        v = _parse_voice_id("af_nicole")
        self.assertEqual(v.display_name, "Nicole")


# ---------------------------------------------------------------------------
# Enumeration tests
# ---------------------------------------------------------------------------

class TestVoiceEnumeration(unittest.TestCase):

    def test_fallback_list_when_no_dir(self):
        with patch("speech.voices.registry._find_voice_dir", return_value=None):
            voices = enumerate_voices()
        self.assertGreater(len(voices), 0)
        ids = [v.id for v in voices]
        self.assertIn("af_sarah", ids)
        self.assertIn("am_adam", ids)

    def test_sorted_american_before_british(self):
        with patch("speech.voices.registry._find_voice_dir", return_value=None):
            voices = enumerate_voices()
        accents = [v.accent for v in voices]
        last_american = max(i for i, a in enumerate(accents) if a == "American")
        first_british = min(i for i, a in enumerate(accents) if a == "British")
        self.assertLess(last_american, first_british)

    def test_sorted_female_before_male_within_accent(self):
        with patch("speech.voices.registry._find_voice_dir", return_value=None):
            voices = enumerate_voices()
        american = [v for v in voices if v.accent == "American"]
        genders = [v.gender for v in american]
        last_female = max(i for i, g in enumerate(genders) if g == "female")
        first_male = min(i for i, g in enumerate(genders) if g == "male")
        self.assertLess(last_female, first_male)

    def test_no_duplicates(self):
        with patch("speech.voices.registry._find_voice_dir", return_value=None):
            voices = enumerate_voices()
        ids = [v.id for v in voices]
        self.assertEqual(len(ids), len(set(ids)))

    def test_enumerate_from_real_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            (d / "af_sarah.pt").touch()
            (d / "am_adam.pt").touch()
            (d / "jf_nezuko.pt").touch()  # non-English, should be filtered
            with patch("speech.voices.registry._find_voice_dir", return_value=d):
                voices = enumerate_voices()
        ids = [v.id for v in voices]
        self.assertIn("af_sarah", ids)
        self.assertIn("am_adam", ids)
        self.assertNotIn("jf_nezuko", ids)

    def test_get_voice_known(self):
        v = get_voice("af_sarah")
        self.assertEqual(v.id, "af_sarah")

    def test_get_voice_unknown_returns_default(self):
        with patch("speech.voices.registry._find_voice_dir", return_value=None):
            v = get_voice("zz_nonexistent")
        self.assertEqual(v.id, DEFAULT_VOICE)


# ---------------------------------------------------------------------------
# VoiceState tests
# ---------------------------------------------------------------------------

def _make_voice_state(persisted: str | None = None, voice_id: str = DEFAULT_VOICE) -> VoiceState:
    writer = MagicMock()
    reader = MagicMock()
    reader.read.return_value = [{"value": persisted}] if persisted else []
    return VoiceState(writer, reader, initial_voice=voice_id)


class TestVoiceState(unittest.TestCase):

    def test_initial_voice(self):
        vs = _make_voice_state()
        self.assertEqual(vs.current_name(), DEFAULT_VOICE)

    def test_current_returns_voice_dataclass(self):
        vs = _make_voice_state()
        v = vs.current()
        self.assertIsInstance(v, Voice)
        self.assertEqual(v.id, DEFAULT_VOICE)

    def test_set_voice_known(self):
        vs = _make_voice_state()
        changed = vs.set_voice("am_adam")
        self.assertTrue(changed)
        self.assertEqual(vs.current_name(), "am_adam")

    def test_set_voice_same_returns_false(self):
        vs = _make_voice_state()
        changed = vs.set_voice(DEFAULT_VOICE)
        self.assertFalse(changed)

    def test_set_voice_unknown_rejected(self):
        vs = _make_voice_state()
        with patch("speech.voices.registry._find_voice_dir", return_value=None):
            changed = vs.set_voice("zz_nonexistent")
        self.assertFalse(changed)
        self.assertEqual(vs.current_name(), DEFAULT_VOICE)

    def test_set_voice_persists(self):
        vs = _make_voice_state()
        vs.set_voice("am_adam")
        vs._writer.write.assert_called()
        # call_args[0] is (sql, params); params is a tuple
        call_args = vs._writer.write.call_args[0]
        self.assertIn("am_adam", call_args[1])

    def test_build_voice_state_loads_persisted(self):
        writer = MagicMock()
        reader = MagicMock()
        reader.read.return_value = [{"value": "am_adam"}]
        with patch("speech.voices.registry._find_voice_dir", return_value=None):
            vs = build_voice_state({"beliefs": writer}, {"beliefs": reader})
        # am_adam is in the fallback list
        self.assertEqual(vs.current_name(), "am_adam")

    def test_build_voice_state_ignores_unknown_persisted(self):
        writer = MagicMock()
        reader = MagicMock()
        reader.read.return_value = [{"value": "zz_nonexistent"}]
        with patch("speech.voices.registry._find_voice_dir", return_value=None):
            vs = build_voice_state({"beliefs": writer}, {"beliefs": reader})
        self.assertEqual(vs.current_name(), DEFAULT_VOICE)

    def test_build_voice_state_no_persisted_uses_default(self):
        writer = MagicMock()
        reader = MagicMock()
        reader.read.return_value = []
        vs = build_voice_state({"beliefs": writer}, {"beliefs": reader})
        self.assertEqual(vs.current_name(), DEFAULT_VOICE)


if __name__ == "__main__":
    unittest.main()
