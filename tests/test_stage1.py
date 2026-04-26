"""Tests for Stage 1: drift register, Condenser, and Governor."""
import random
import time
import unittest


class TestDriftRegister(unittest.TestCase):

    def test_prompt_contains_drift_examples(self):
        from theory_x.stage6_fountain.generator import _DRIFT_SYSTEM_PROMPT_TEMPLATE, _DEFAULT_DRIFT_EXAMPLES
        self.assertTrue(any("quiet" in ex or "slow" in ex for ex in _DEFAULT_DRIFT_EXAMPLES))
        self.assertIn("DO NOT", _DRIFT_SYSTEM_PROMPT_TEMPLATE)

    def test_prompt_forbids_manifesto_patterns(self):
        from theory_x.stage6_fountain.generator import _DRIFT_SYSTEM_PROMPT_TEMPLATE
        self.assertIn("The X of my Y", _DRIFT_SYSTEM_PROMPT_TEMPLATE)
        self.assertIn("quietude", _DRIFT_SYSTEM_PROMPT_TEMPLATE)

    def test_prompt_included_in_build_prompt_output(self):
        from theory_x.stage6_fountain.generator import FountainGenerator
        from voice.llm import VoiceClient
        gen = FountainGenerator(
            sense_writer=None,
            dynamic_writer=None,
            voice_client=VoiceClient.__new__(VoiceClient),
            dynamic_reader=None,
        )
        prompt = gen._build_prompt({}, 10, {})
        # Drift system prompt should be present verbatim
        self.assertIn("idle, drifting", prompt)
        self.assertIn("DO NOT", prompt)


class TestCondenser(unittest.TestCase):

    def test_fallback_produces_valid_droplet(self):
        from theory_x.stage6_fountain.condenser import Condenser
        c = Condenser(voice_client=None)

        d1 = c.condense("The weight of being alone in this vast silence")
        self.assertIsNotNone(d1)
        self.assertGreaterEqual(len(d1.split("-")), 3)

        d2 = c.condense("huh, bitcoin's moving today")
        self.assertIsNotNone(d2)

    def test_empty_input_returns_none(self):
        from theory_x.stage6_fountain.condenser import Condenser
        c = Condenser(voice_client=None)
        self.assertIsNone(c.condense(""))
        self.assertIsNone(c.condense(None))

    def test_clean_strips_preamble(self):
        from theory_x.stage6_fountain.condenser import Condenser
        c = Condenser(voice_client=None)
        self.assertEqual(c._clean("Droplet: alone-yet-pervasive\n"), "alone-yet-pervasive")
        self.assertEqual(c._clean("  btc-movement-detected."), "btc-movement-detected")

    def test_clean_lowercases(self):
        from theory_x.stage6_fountain.condenser import Condenser
        c = Condenser(voice_client=None)
        self.assertEqual(c._clean("BTC-Movement-Detected"), "btc-movement-detected")

    def test_fallback_at_least_three_content_words(self):
        from theory_x.stage6_fountain.condenser import Condenser
        c = Condenser(voice_client=None)
        # Very short input with few content words → raw-fragment
        d = c.condense("hi")
        self.assertEqual(d, "raw-fragment")


class TestGovernor(unittest.TestCase):

    def test_respects_min_gap(self):
        from speech.governor import SpeechGovernor
        g = SpeechGovernor(min_gap_seconds=60, base_speak_probability=1.0)
        d1 = g.decide("test belief")
        self.assertTrue(d1.speak)
        # Immediately after: gap blocks
        d2 = g.decide("test belief 2")
        self.assertFalse(d2.speak)
        self.assertIn("within_min_gap", d2.reason)

    def test_base_probability_low(self):
        from speech.governor import SpeechGovernor
        random.seed(42)
        g = SpeechGovernor(min_gap_seconds=0, base_speak_probability=0.15)
        results = []
        for i in range(100):
            g._last_speech_ts = 0.0
            results.append(g.decide(f"belief {i}").speak)
        speak_rate = sum(results) / 100
        self.assertLess(speak_rate, 0.35)
        self.assertGreater(speak_rate, 0.03)

    def test_valence_boost_no_crash(self):
        from speech.governor import SpeechGovernor
        g = SpeechGovernor(min_gap_seconds=0, base_speak_probability=0.1)
        d = g.decide("strong belief", valence={"weight": 0.9})
        self.assertIn(d.speak, [True, False])

    def test_user_active_suppresses_speech(self):
        from speech.governor import SpeechGovernor
        random.seed(0)
        g = SpeechGovernor(min_gap_seconds=0, base_speak_probability=1.0)
        d = g.decide("test", situation={"user_active_recently": True,
                                         "user_asleep": False,
                                         "open_problems": False})
        # prob *= 0.3 → 0.3, random.seed(0) → random.random() ≈ 0.844 → False
        self.assertFalse(d.speak)

    def test_mark_spoken_externally(self):
        from speech.governor import SpeechGovernor
        g = SpeechGovernor(min_gap_seconds=300, base_speak_probability=1.0)
        g.mark_spoken_externally()
        d = g.decide("test")
        self.assertFalse(d.speak)
        self.assertIn("within_min_gap", d.reason)


class TestDropletDedup(unittest.TestCase):

    def setUp(self):
        import tempfile
        import os
        self.tmp = tempfile.mkdtemp()
        os.environ["NEX5_DATA_DIR"] = self.tmp
        from substrate.init_db import init_all
        init_all()
        from substrate import Reader, Writer, db_paths
        paths = db_paths()
        self.writers = {n: Writer(p, name=n) for n, p in paths.items()}
        self.readers = {n: Reader(p) for n, p in paths.items()}

    def tearDown(self):
        for w in self.writers.values():
            try:
                w.close()
            except Exception:
                pass
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        import os
        os.environ.pop("NEX5_DATA_DIR", None)

    def test_droplet_repeat_rejects_crystallization(self):
        from theory_x.stage6_fountain.crystallizer import FountainCrystallizer

        c = FountainCrystallizer(
            beliefs_writer=self.writers["beliefs"],
            beliefs_reader=self.readers["beliefs"],
            dynamic_reader=self.readers["dynamic"],
        )
        now = time.time()
        # Insert two recent fountain_events with same droplet
        for _ in range(2):
            self.writers["dynamic"].write(
                "INSERT INTO fountain_events (ts, thought, droplet, readiness, word_count) "
                "VALUES (?, ?, ?, ?, ?)",
                (now, "some thought", "low-market-tempo", 0.9, 3),
            )

        ok, reason = c._quality_check(
            "I notice markets feel unusually slow and quiet today.",
            droplet="low-market-tempo",
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "droplet_repetition")

    def test_novel_droplet_passes(self):
        from theory_x.stage6_fountain.crystallizer import FountainCrystallizer

        c = FountainCrystallizer(
            beliefs_writer=self.writers["beliefs"],
            beliefs_reader=self.readers["beliefs"],
            dynamic_reader=self.readers["dynamic"],
        )
        ok, reason = c._quality_check(
            "I notice something new arising in me.",
            droplet="novel-observation-fresh",
        )
        self.assertTrue(ok, f"Should pass, got: {reason}")


class TestEngagementCheck(unittest.TestCase):
    """_has_engagement must accept drift-register outputs, reject pure feed echoes."""

    def setUp(self):
        from theory_x.stage6_fountain.crystallizer import FountainCrystallizer
        self.c = FountainCrystallizer.__new__(FountainCrystallizer)

    def test_first_person_passes(self):
        self.assertTrue(self.c._has_engagement("I wonder about this situation."))
        self.assertTrue(self.c._has_engagement("My attention keeps drifting back to that."))

    def test_question_passes(self):
        self.assertTrue(self.c._has_engagement("Why didn't that alert come through?"))
        self.assertTrue(self.c._has_engagement("What's happening in crypto today?"))

    def test_noticing_words_pass(self):
        self.assertTrue(self.c._has_engagement("huh, markets feel slow today"))
        self.assertTrue(self.c._has_engagement("wait, bitcoin's moving"))
        self.assertTrue(self.c._has_engagement("something about this feels off"))

    def test_evaluative_words_pass(self):
        self.assertTrue(self.c._has_engagement("that arxiv title is oddly phrased"))
        self.assertTrue(self.c._has_engagement("feeds are quiet today"))

    def test_pure_external_echo_rejected(self):
        self.assertFalse(self.c._has_engagement("Bitcoin trades at 62340 USD."))
        self.assertFalse(self.c._has_engagement("Meta reduces workforce by 10 percent."))
        self.assertFalse(self.c._has_engagement("Arxiv paper title: Long-Horizon Manipulation."))

    def test_quality_check_uses_engagement(self):
        from theory_x.stage6_fountain.crystallizer import FountainCrystallizer
        import tempfile, os
        tmp = tempfile.mkdtemp()
        os.environ["NEX5_DATA_DIR"] = tmp
        from substrate.init_db import init_all
        init_all()
        from substrate import Reader, Writer, db_paths
        paths = db_paths()
        writers = {n: Writer(p, name=n) for n, p in paths.items()}
        readers = {n: Reader(p) for n, p in paths.items()}
        try:
            c = FountainCrystallizer(
                beliefs_writer=writers["beliefs"],
                beliefs_reader=readers["beliefs"],
            )
            ok, reason = c._quality_check("Why didn't that alert come through?")
            # 20+ chars, has "?", should pass engagement — but too short? Let's check
            # "Why didn't that alert come through?" = 36 chars — passes length too
            self.assertTrue(ok, f"Expected pass, got: {reason}")

            ok2, reason2 = c._quality_check("Bitcoin trades at 62340 USD.")
            self.assertFalse(ok2)
            self.assertEqual(reason2, "no_engagement")
        finally:
            for w in writers.values():
                try:
                    w.close()
                except Exception:
                    pass
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
            os.environ.pop("NEX5_DATA_DIR", None)


if __name__ == "__main__":
    unittest.main()
