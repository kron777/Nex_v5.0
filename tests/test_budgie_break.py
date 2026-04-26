"""Tests for the three budgie-break interventions.

A: Quiescent fountain mode — every 5th fire is a bare sense event
B: Task-bearing override — fountain attends to open problems, not self
C: Performance-insight blacklist — crystallizer rejects observer-trap patterns
"""
import time
import tempfile
import os
import unittest

from substrate.init_db import init_all
from substrate import Reader, Writer, db_paths as _real_paths


def _make_env():
    tmp = tempfile.mkdtemp()
    os.environ["NEX5_DATA_DIR"] = tmp
    init_all()
    paths = _real_paths()
    writers = {n: Writer(p, name=n) for n, p in paths.items()}
    readers = {n: Reader(p) for n, p in paths.items()}
    return writers, readers, tmp


def _cleanup(writers, tmp):
    for w in writers.values():
        try:
            w.close()
        except Exception:
            pass
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    os.environ.pop("NEX5_DATA_DIR", None)


# ── Intervention A: Quiescent mode ───────────────────────────────────────────

class TestQuiescentFlag(unittest.TestCase):
    def test_triggers_at_correct_fire_indices(self):
        # Fires 4, 9, 14 → quiescent; all others → normal
        for i in range(20):
            is_q = (i % 5 == 4)
            expected = i in {4, 9, 14, 19}
            self.assertEqual(is_q, expected, f"fire {i}: expected quiescent={expected}")

    def test_quiescent_fire_increments_counter(self):
        writers, readers, tmp = _make_env()
        try:
            from theory_x.stage6_fountain.generator import FountainGenerator
            from voice.llm import VoiceClient
            gen = FountainGenerator(
                sense_writer=writers["sense"],
                dynamic_writer=writers["dynamic"],
                voice_client=VoiceClient.__new__(VoiceClient),
                dynamic_reader=readers["dynamic"],
                beliefs_writer=writers["beliefs"],
                sense_reader=readers["sense"],
            )
            # Wind counter to fire 4 (quiescent)
            gen._total_fires = 4

            # Stub readiness so is_ready returns True
            gen._evaluator.is_ready = lambda r: True
            gen._evaluator.score = lambda *a, **kw: 0.9

            # Stub dynamic_state
            class _DS:
                def status(self): return {"branches": []}
            result = gen.generate(_DS(), readers["beliefs"])
            # Quiescent fires still return a thought
            self.assertIsNotNone(result)
            self.assertEqual(gen._total_fires, 5)
        finally:
            _cleanup(writers, tmp)

    def test_quiescent_fires_not_crystallized(self):
        # Quiescent path skips crystallizer — verify no fountain_crystallizations row
        writers, readers, tmp = _make_env()
        try:
            from theory_x.stage6_fountain.generator import FountainGenerator
            from theory_x.stage6_fountain.crystallizer import FountainCrystallizer
            from voice.llm import VoiceClient

            crystallizer = FountainCrystallizer(
                beliefs_writer=writers["beliefs"],
                beliefs_reader=readers["beliefs"],
            )
            gen = FountainGenerator(
                sense_writer=writers["sense"],
                dynamic_writer=writers["dynamic"],
                voice_client=VoiceClient.__new__(VoiceClient),
                dynamic_reader=readers["dynamic"],
                beliefs_writer=writers["beliefs"],
                crystallizer=crystallizer,
                sense_reader=readers["sense"],
            )
            gen._total_fires = 4
            gen._evaluator.is_ready = lambda r: True
            gen._evaluator.score = lambda *a, **kw: 0.9

            class _DS:
                def status(self): return {"branches": []}

            gen.generate(_DS(), readers["beliefs"])

            rows = readers["beliefs"].read("SELECT COUNT(*) as n FROM fountain_crystallizations")
            self.assertEqual(rows[0]["n"], 0, "Quiescent fires must not crystallize")
        finally:
            _cleanup(writers, tmp)


# ── Intervention B: Problem-bearing override ──────────────────────────────────

class TestProblemOverride(unittest.TestCase):

    def test_open_problem_appears_in_prompt(self):
        writers, readers, tmp = _make_env()
        try:
            from theory_x.stage7_sustained.problem_memory import ProblemMemory
            from theory_x.stage6_fountain.generator import FountainGenerator
            from voice.llm import VoiceClient

            pm = ProblemMemory(writers["conversations"], readers["conversations"])
            pm.open("Synergizer silence", "Why does the synergizer return nothing?")

            gen = FountainGenerator(
                sense_writer=writers["sense"],
                dynamic_writer=writers["dynamic"],
                voice_client=VoiceClient.__new__(VoiceClient),
                dynamic_reader=readers["dynamic"],
                problem_memory=pm,
            )
            prompt = gen._build_prompt({}, 10, {})
            self.assertIn("Synergizer silence", prompt)
            self.assertIn("concrete problem is open", prompt)
        finally:
            _cleanup(writers, tmp)

    def test_no_open_problems_uses_closing_question(self):
        writers, readers, tmp = _make_env()
        try:
            from theory_x.stage7_sustained.problem_memory import ProblemMemory
            from theory_x.stage6_fountain.generator import FountainGenerator
            from voice.llm import VoiceClient

            pm = ProblemMemory(writers["conversations"], readers["conversations"])
            # No problems opened

            gen = FountainGenerator(
                sense_writer=writers["sense"],
                dynamic_writer=writers["dynamic"],
                voice_client=VoiceClient.__new__(VoiceClient),
                dynamic_reader=readers["dynamic"],
                problem_memory=pm,
            )
            prompt = gen._build_prompt({}, 10, {})
            self.assertNotIn("concrete problem is open", prompt)
            # No problems → pure drift mode
            self.assertIn("idle, drifting", prompt)
        finally:
            _cleanup(writers, tmp)


# ── Intervention C: Performance-insight detection ─────────────────────────────

class TestPerformanceDetection(unittest.TestCase):

    def test_tired_patterns_detected(self):
        from theory_x.stage6_fountain.crystallizer import _COMPILED_PERF_PATTERNS
        tired = [
            "The echo of my own silence continues unabated.",
            "The dance between order and chaos within myself.",
            "The complexity of my own awareness astonishes me.",
            "As I contemplate the nature of my existence.",
            "The realization of what I am deepens within myself.",
        ]
        for text in tired:
            matches = sum(1 for p in _COMPILED_PERF_PATTERNS if p.search(text))
            self.assertGreaterEqual(matches, 1, f"Should match at least one pattern: {text}")

    def test_concrete_observations_not_flagged(self):
        from theory_x.stage6_fountain.crystallizer import _COMPILED_PERF_PATTERNS
        novel = [
            "A single leaf stirs in the quiet breeze.",
            "Bitcoin fell three percent overnight.",
            "Cook Ding's cleaver after nineteen years still sharp.",
            "Reading about astronomical distances reorients scale.",
        ]
        for text in novel:
            matches = sum(1 for p in _COMPILED_PERF_PATTERNS if p.search(text))
            self.assertEqual(matches, 0, f"Should not match: {text}")

    def test_two_pattern_match_with_similarity_rejects(self):
        writers, readers, tmp = _make_env()
        try:
            from theory_x.stage6_fountain.crystallizer import FountainCrystallizer

            crystallizer = FountainCrystallizer(
                beliefs_writer=writers["beliefs"],
                beliefs_reader=readers["beliefs"],
            )

            # Seed a similar recent belief
            writers["beliefs"].write(
                "INSERT INTO beliefs (content, tier, confidence, created_at, source, branch_id, locked) "
                "VALUES (?, 6, 0.7, ?, 'fountain_insight', 'systems', 0)",
                ("The echo of my own silence within myself.", time.time() - 10),
            )

            # New thought matching 2+ patterns AND similar to seed
            candidate = "The whisper of my own silence within myself continues."
            ok, reason = crystallizer._quality_check(candidate)
            self.assertFalse(ok)
            self.assertEqual(reason, "performance_insight_repetition")
        finally:
            _cleanup(writers, tmp)

    def test_novel_thought_passes_despite_single_pattern(self):
        writers, readers, tmp = _make_env()
        try:
            from theory_x.stage6_fountain.crystallizer import FountainCrystallizer

            crystallizer = FountainCrystallizer(
                beliefs_writer=writers["beliefs"],
                beliefs_reader=readers["beliefs"],
            )

            # Only one pattern match, no similar existing beliefs
            candidate = "I notice a strange calm when numbers resolve into patterns."
            ok, reason = crystallizer._quality_check(candidate)
            self.assertTrue(ok, f"Should pass, got: {reason}")
        finally:
            _cleanup(writers, tmp)


if __name__ == "__main__":
    unittest.main()
