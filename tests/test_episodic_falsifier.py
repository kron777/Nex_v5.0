"""SENTIENCE_PROGRAM.md:190 falsifier for Phase E (`NEX5_EPISODIC`):
"retrieval cannot separate 'happened to me' from 'I believe'."

Operationalized two ways against the real query_episodes()/reconstruct_episode()
path (not a new mechanism -- this only exercises what record_episodes() already
writes):

1. A bare belief with no corresponding episode must never be retrievable as an
   episode -- reconstruct_episode() around its timestamp must return None, even
   when the belief's content is distinctive and timestamp-adjacent to the probe.
   If retrieval could not separate the two, a belief would surface here.

2. A held_tension episode (the one source type whose `what` text quotes raw
   belief content) must still read as an EVENT -- the composed account names the
   tension ("I held both: ... and ...") rather than flatly asserting either
   belief as true. This is the one source type where belief content and
   episodic content sit closest together, so it is the real test of the claim,
   not the easy cases (ghost_flag/surprise/meta_cognition already read as
   happened-to-me by construction).

Result of running both, 2026-11-09: PASS. See p8_episodic node, MIND_MAP.yaml.
"""
from __future__ import annotations

import os
import time
import unittest

from tests import _bootstrap  # noqa: F401
from tests.test_episodic import _make_env, _cleanup, _seed_belief, _seed_held_tension, _FLAG


class TestEpisodicVsBeliefSeparation(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        os.environ[_FLAG] = "1"

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def test_bare_belief_never_surfaces_as_episode(self):
        from theory_x.memory import episodic
        now = time.time()
        _seed_belief(self.writers, "The fountain riffing rate halves after dedup")
        # No episode source (ghost_flag/meta_cognition/surprise/held_tension)
        # exists at all -- only a belief. Nothing to record.
        episodic.record_episodes(
            self.readers["conversations"], self.readers["dynamic"],
            self.writers["dynamic"], self.readers["beliefs"])
        ep = episodic.reconstruct_episode(self.readers["dynamic"], now)
        self.assertIsNone(ep, "a belief with no episodic source must not be retrievable as an episode")

    def test_held_tension_episode_reads_as_event_not_as_a_belief(self):
        from theory_x.memory import episodic
        now = time.time()
        a_id = _seed_belief(self.writers, "The dedup fix removed the riffing bursts")
        b_id = _seed_belief(self.writers, "The riffing bursts are still happening")
        _seed_held_tension(self.writers, now - 60, a_id, b_id)
        recorded = episodic.record_episodes(
            self.readers["conversations"], self.readers["dynamic"],
            self.writers["dynamic"], self.readers["beliefs"])
        self.assertEqual(len(recorded), 1)

        ep = episodic.reconstruct_episode(self.readers["dynamic"], now - 60)
        self.assertIsNotNone(ep)
        account = ep["account"]
        # It must name the tension as something that happened (held), not
        # assert either belief as settled fact on its own.
        self.assertIn("I held both", account)
        self.assertIn("The dedup fix removed the riffing bursts", account)
        self.assertIn("The riffing bursts are still happening", account)
        # Neither belief appears alone, unqualified by the "I held both" frame --
        # i.e. retrieval never collapses the pair into a flat assertion.
        self.assertNotEqual(account.strip().rstrip("."), "The dedup fix removed the riffing bursts")
        self.assertNotEqual(account.strip().rstrip("."), "The riffing bursts are still happening")


if __name__ == "__main__":
    unittest.main()
