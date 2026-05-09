"""Tests for theory_x.executive_control — ExecutiveControl node."""
import unittest

from tests._bootstrap import *  # noqa: F401, F403


# ── 30-query dry-run regression baseline ─────────────────────────────────────
# Locks the classification of the 27/30 queries that have strong lexical signal.
# The 3 zero-signal follow-ups (ZSF-*) are expected to fall to Conversational;
# their row asserts exactly that.

_QUERIES = [
    # Analytical
    ("ANA-1",  "What are Bitcoin prices doing this week?",                        "Analytical"),
    ("ANA-2",  "How does inflation correlate with equity volatility?",            "Analytical"),
    ("ANA-3",  "Give me the GDP trend for the past decade",                       "Analytical"),
    ("ANA-4",  "Is ETH overvalued right now?",                                    "Analytical"),
    ("ANA-5",  "What's the yield on 10-year treasuries vs fed funds?",            "Analytical"),
    ("ANA-6",  "Compare the price of BTC vs ETH over the last 6 months",         "Analytical"),
    ("ANA-7",  "What percentage of the S&P 500 is tech stocks?",                  "Analytical"),
    ("ANA-8",  "Analyze the momentum indicators for this market",                 "Analytical"),
    ("ANA-9",  "What's the statistical significance of that correlation?",        "Analytical"),
    ("ANA-10", "Give me a data-driven analysis of crypto volatility",             "Analytical"),
    # Technical
    ("TEC-1",  "How does exponential decay work?",                                "Technical"),
    ("TEC-2",  "Explain how a transformer model processes tokens",                "Technical"),
    ("TEC-3",  "What is the difference between a mutex and a semaphore?",         "Technical"),
    ("TEC-4",  "Walk me through the backpropagation algorithm",                   "Technical"),
    ("TEC-5",  "How do neural networks learn through backpropagation?",            "Technical"),
    ("TEC-6",  "Implement a binary search in Python",                             "Technical"),
    ("TEC-7",  "What is an LRU cache and how does it work under the hood?",       "Technical"),
    ("TEC-8",  "Explain step-by-step how TCP handshake works",                    "Technical"),
    ("TEC-9",  "What's the time complexity of quicksort — big O analysis?",       "Technical"),
    ("TEC-10", "How do I resolve a deadlock in concurrent Python code?",          "Technical"),
    # Conversational
    ("CON-1",  "Hi there",                                                        "Conversational"),
    ("CON-2",  "What do you think about the weather?",                            "Conversational"),
    ("CON-3",  "Tell me something interesting",                                   "Conversational"),
    ("CON-4",  "What's your favourite book?",                                     "Conversational"),
    ("CON-5",  "Do you ever feel lonely?",                                        "Conversational"),
    ("CON-6",  "Thanks for that",                                                 "Conversational"),
    ("CON-7",  "You're quite thoughtful",                                         "Conversational"),
    # Zero-signal follow-ups — no lexical anchors; safe to fall to Conversational
    ("ZSF-1",  "Why?",                                                            "Conversational"),
    ("ZSF-2",  "And how does that relate?",                                       "Conversational"),
    ("ZSF-3",  "What do you mean by that?",                                       "Conversational"),
]


class TestDryRunRegression(unittest.TestCase):
    """30-query dry-run regression baseline — 27 strong + 3 zero-signal."""

    @classmethod
    def setUpClass(cls):
        from theory_x.executive_control import ExecutiveControl
        from voice.registers import REGISTERS
        cls.ec = ExecutiveControl(REGISTERS)

    def _assert_query(self, label, prompt, expected):
        result = self.ec.dry_run(prompt)
        self.assertEqual(
            result["result"], expected,
            f"{label}: prompt={prompt!r} → got {result['result']!r} "
            f"(raw={result['raw_scores']}, biased={result['biased_scores']})",
        )

    def test_all_queries(self):
        failures = []
        for label, prompt, expected in _QUERIES:
            result = self.ec.dry_run(prompt)
            if result["result"] != expected:
                failures.append(
                    f"  {label}: expected={expected}, got={result['result']}, "
                    f"scores={result['raw_scores']}"
                )
        if failures:
            self.fail("Regression failures:\n" + "\n".join(failures))

    def test_analytical_queries(self):
        for label, prompt, expected in _QUERIES:
            if expected == "Analytical":
                with self.subTest(label=label):
                    self._assert_query(label, prompt, expected)

    def test_technical_queries(self):
        for label, prompt, expected in _QUERIES:
            if expected == "Technical":
                with self.subTest(label=label):
                    self._assert_query(label, prompt, expected)

    def test_conversational_queries(self):
        for label, prompt, expected in _QUERIES:
            if expected == "Conversational":
                with self.subTest(label=label):
                    self._assert_query(label, prompt, expected)


# ── SentienceNode protocol conformance ───────────────────────────────────────

class TestSentienceNodeProtocol(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from theory_x.executive_control import ExecutiveControl
        from voice.registers import REGISTERS
        cls.ec = ExecutiveControl(REGISTERS)

    def test_implements_sentience_node_protocol(self):
        from theory_x import SentienceNode
        self.assertIsInstance(self.ec, SentienceNode)

    def test_name_attribute(self):
        from theory_x.executive_control import ExecutiveControl
        self.assertEqual(ExecutiveControl.name, "executive_control")
        self.assertEqual(self.ec.name, "executive_control")

    def test_tick_returns_dict(self):
        result = self.ec.tick()
        self.assertIsInstance(result, dict)
        self.assertIn("call_count", result)

    def test_decay_accepts_float(self):
        import time
        self.ec.decay(now=time.time())  # must not raise

    def test_state_no_args(self):
        s = self.ec.state()
        self.assertIsInstance(s, dict)
        self.assertIn("name", s)
        self.assertIn("call_count", s)
        self.assertIn("register_counts", s)

    def test_state_with_float(self):
        import time
        s = self.ec.state(now=time.time())
        self.assertIsInstance(s, dict)

    def test_state_tracks_call_count(self):
        from theory_x.executive_control import ExecutiveControl
        from voice.registers import REGISTERS
        ec = ExecutiveControl(REGISTERS)
        self.assertEqual(ec.state()["call_count"], 0)
        ec.select("What is the price of Bitcoin?")
        self.assertEqual(ec.state()["call_count"], 1)
        ec.select("Hi there")
        self.assertEqual(ec.state()["call_count"], 2)


# ── Philosophical scoring (EXPERIMENT EC-A 2026-05-09) ───────────────────────
# EC now scores Philosophical. Membrane override still fires afterward.
# Boundary cases PHI-BC-* are the primary falsification tests.

_PHILOSOPHICAL_QUERIES = [
    # Clear philosophical signal — must score Philosophical
    ("PHI-1",    "What is consciousness?",                            "Philosophical"),
    ("PHI-2",    "Describe the silence",                              "Philosophical"),
    ("PHI-3",    "What is the nature of meaning?",                    "Philosophical"),
    ("PHI-4",    "What is free will?",                                "Philosophical"),
    ("PHI-5",    "Is consciousness real or an illusion?",             "Philosophical"),
    ("PHI-6",    "Tell me about emptiness",                           "Philosophical"),
    ("PHI-7",    "What is phenomenology?",                            "Philosophical"),
    ("PHI-8",    "Do we truly exist?",                                "Philosophical"),
    ("PHI-9",    "And free will?",                                    "Philosophical"),
    ("PHI-10",   "What is metaphysics?",                              "Philosophical"),
    # Boundary cases — must NOT score Philosophical (tie-breaking / overlap)
    ("PHI-BC-1", "What is the meaning of GDP?",                       "Conversational"),
    # PHI-BC-2: mixed signal (consciousness + neural networks) — neither p nor t clears
    # threshold; EC correctly returns Conversational. Key constraint: NOT Philosophical.
    ("PHI-BC-2", "How does consciousness arise in neural networks?",   "Conversational"),
]


class TestPhilosophicalScoring(unittest.TestCase):
    """EXPERIMENT EC-A: EC now returns Philosophical for clear philosophical queries.
    Boundary cases PHI-BC-* verify tie-breaking and overlap prevention.
    """

    @classmethod
    def setUpClass(cls):
        from theory_x.executive_control import ExecutiveControl
        from voice.registers import REGISTERS
        cls.ec = ExecutiveControl(REGISTERS)

    def _assert_query(self, label, prompt, expected):
        result = self.ec.dry_run(prompt)
        self.assertEqual(
            result["result"], expected,
            f"{label}: prompt={prompt!r} → got {result['result']!r} "
            f"(raw={result['raw_scores']}, biased={result['biased_scores']})",
        )

    def test_all_philosophical_queries(self):
        failures = []
        for label, prompt, expected in _PHILOSOPHICAL_QUERIES:
            result = self.ec.dry_run(prompt)
            if result["result"] != expected:
                failures.append(
                    f"  {label}: expected={expected}, got={result['result']}, "
                    f"scores={result['raw_scores']}"
                )
        if failures:
            self.fail("Philosophical scoring failures:\n" + "\n".join(failures))

    def test_boundary_gdp_meaning_not_philosophical(self):
        """'What is the meaning of GDP?' must NOT score Philosophical — Analytical conflict."""
        result = self.ec.dry_run("What is the meaning of GDP?")
        self.assertNotEqual(result["result"], "Philosophical",
            f"PHI-BC-1 failed: tie-breaking wrong — got Philosophical, "
            f"scores={result['raw_scores']}")

    def test_boundary_consciousness_neural_networks_not_philosophical(self):
        """'How does consciousness arise in neural networks?' must NOT score Philosophical.
        Mixed p/t signal; neither clears threshold — Conversational is correct."""
        result = self.ec.dry_run("How does consciousness arise in neural networks?")
        self.assertNotEqual(result["result"], "Philosophical",
            f"PHI-BC-2 failed: tie-breaking wrong — got Philosophical, "
            f"scores={result['raw_scores']}")

    def test_philosophical_register_in_state_counts(self):
        from theory_x.executive_control import ExecutiveControl
        from voice.registers import REGISTERS
        ec = ExecutiveControl(REGISTERS)
        ec.select("What is consciousness?")
        state = ec.state()
        self.assertIn("Philosophical", state["register_counts"])
        self.assertEqual(state["register_counts"]["Philosophical"], 1)


# ── Continuity bias ───────────────────────────────────────────────────────────

class TestContinuityBias(unittest.TestCase):

    def test_continuity_boosts_prior_register(self):
        from theory_x.executive_control import ExecutiveControl
        from voice.registers import REGISTERS
        ec = ExecutiveControl(REGISTERS)
        session = "test-session-cont"

        # Establish Technical register in session
        ec.select("How does exponential decay work?", session_id=session)

        # Now ask a zero-signal follow-up — without continuity it falls to Conversational
        no_bias = ec.dry_run("Why?")
        self.assertEqual(no_bias["result"], "Conversational")

        # With continuity (session established), bias should be visible in scores
        with_bias = ec.dry_run("Why?", session_id=session)
        self.assertGreater(
            with_bias["biased_scores"].get("Technical", 0),
            with_bias["raw_scores"].get("Technical", 0),
            "Continuity bias should increase Technical score after a Technical session turn",
        )

    def test_new_session_no_bias(self):
        from theory_x.executive_control import ExecutiveControl
        from voice.registers import REGISTERS
        ec = ExecutiveControl(REGISTERS)
        result = ec.dry_run("Why?", session_id="brand-new-session")
        # No prior register — raw and biased scores should be identical
        self.assertEqual(result["raw_scores"], result["biased_scores"])

    def test_continuity_does_not_change_high_signal(self):
        """A strong Analytical query wins even if session was previously Technical."""
        from theory_x.executive_control import ExecutiveControl
        from voice.registers import REGISTERS
        ec = ExecutiveControl(REGISTERS)
        session = "test-session-switch"

        # Establish Technical
        ec.select("Walk me through the backpropagation algorithm", session_id=session)

        # Strong Analytical query — should still win
        result = ec.select(
            "What is the Bitcoin price correlation with tech stocks?",
            session_id=session,
        )
        self.assertEqual(result.name, "Analytical")

    def test_session_state_is_updated_after_select(self):
        from theory_x.executive_control import ExecutiveControl
        from voice.registers import REGISTERS
        ec = ExecutiveControl(REGISTERS)
        session = "test-session-update"

        ec.select("How does a transformer model work?", session_id=session)
        state = ec.state()
        self.assertIn("active_sessions", state)
        self.assertGreaterEqual(state["active_sessions"], 1)


if __name__ == "__main__":
    unittest.main()
