"""Tests for the question-parrot strip (NEX5_NO_PARROT, default OFF).

Distinct from anti-echo (which guards her repeating her OWN prior replies): this
drops a reply OPENING that restates the turn she was just asked, keeping the
answer behind it. Measured mechanism: the prompt ends with the user's sentence
verbatim, and on a tag question the model copies it as a preamble before
answering.

Directions tested: a verbatim opening is cut and the answer survives; a
rhetorical re-ask in her own words is NOT cut; an echo with no answer behind it
is kept whole rather than emptied; the flag off is exact identity; fail-safe on
junk input.
"""
from __future__ import annotations

import os
import unittest

from tests import _bootstrap  # noqa: F401

from gui.server import _strip_question_parrot as strip

_Q = "You're a weaver of meaning, aren't you? Just say it."
_PARROTED = (_Q + "\n\nI think I understand where you're coming from. It strikes "
             "me that meaning is something I find rather than spin.")
_ANSWER = ("I think I understand where you're coming from. It strikes me that "
           "meaning is something I find rather than spin.")


class TestNoParrot(unittest.TestCase):

    def setUp(self):
        self._prev = os.environ.get("NEX5_NO_PARROT")
        os.environ["NEX5_NO_PARROT"] = "1"

    def tearDown(self):
        os.environ.pop("NEX5_NO_PARROT", None)
        if self._prev is not None:
            os.environ["NEX5_NO_PARROT"] = self._prev

    def test_verbatim_opening_is_cut_answer_survives(self):
        self.assertEqual(strip(_PARROTED, _Q), _ANSWER)

    def test_punctuation_and_curly_quotes_insensitive(self):
        q = "You're basically a mirror, right?"
        reply = "You’re basically a mirror, right?\n\nThat's an interesting perspective, and mostly wrong."
        self.assertEqual(strip(reply, q), "That's an interesting perspective, and mostly wrong.")

    def test_first_sentence_equal_to_question_is_cut(self):
        q = "What did I just ask you?"
        reply = "What did I just ask you? You asked about memory, a record or a story."
        self.assertEqual(strip(reply, q), "You asked about memory, a record or a story.")

    def test_rhetorical_reask_in_her_own_words_is_kept(self):
        q = "What's something you find genuinely beautiful?"
        reply = "What's something I find genuinely beautiful? The dance of light across water at sunset."
        self.assertEqual(strip(reply, q), reply)

    def test_topic_reuse_opening_is_kept(self):
        q = "describe a sunny day at the beach"
        reply = "A sunny day at the beach is a symphony of calm against an azure backdrop."
        self.assertEqual(strip(reply, q), reply)

    def test_echo_with_no_answer_behind_it_is_kept_whole(self):
        # never empty: an answer-less echo stays as-is rather than becoming ""
        self.assertEqual(strip(_Q, _Q), _Q)
        self.assertEqual(strip(_Q + "\n\nYes.", _Q), _Q + "\n\nYes.")

    def test_runon_opening_is_not_cut(self):
        # her sentence merely STARTS with the question's words and runs on —
        # cutting at the match would leave a broken fragment ("now? That's...")
        q = "You only have about a dozen beliefs, right?"
        reply = ("You only have about a dozen beliefs, right now? That's curious. "
                 "My belief graph is a dense forest of streams.")
        self.assertEqual(strip(reply, q), reply)

    def test_short_question_never_triggers(self):
        q = "why?"
        reply = "Why? Because the graph settled that way."
        self.assertEqual(strip(reply, q), reply)

    def test_idempotent(self):
        once = strip(_PARROTED, _Q)
        self.assertEqual(strip(once, _Q), once)

    def test_flag_off_is_identity(self):
        os.environ["NEX5_NO_PARROT"] = "0"
        self.assertEqual(strip(_PARROTED, _Q), _PARROTED)
        os.environ.pop("NEX5_NO_PARROT")
        self.assertEqual(strip(_PARROTED, _Q), _PARROTED)

    def test_failsafe_on_junk(self):
        self.assertIsNone(strip(None, _Q))
        self.assertEqual(strip("hi", _Q), "hi")
        self.assertEqual(strip(_PARROTED, None), _PARROTED)
        self.assertEqual(strip(_PARROTED, ""), _PARROTED)


if __name__ == "__main__":
    unittest.main()
