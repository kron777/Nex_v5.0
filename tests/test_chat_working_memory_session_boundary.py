"""Characterize the Chat handler's per-session WorkingMemory buffers.

The selector is process-scoped, but WorkingMemory instances are stored by
session ID. These tests assert the buffer boundary only; they do not assert
that FocalSet selection is session-local or that the model relies on injected
context.
"""
from __future__ import annotations

import unittest

from tests import _bootstrap  # noqa: F401


class TestChatWorkingMemorySessionBoundary(unittest.TestCase):
    def setUp(self):
        import gui.server as server

        self.server = server
        self._old = server._working_memory_by_session
        server._working_memory_by_session = {}

    def tearDown(self):
        self.server._working_memory_by_session = self._old

    def test_same_session_reuses_its_buffer(self):
        first = self.server._get_or_create_wm("session-A")
        second = self.server._get_or_create_wm("session-A")

        self.assertIs(first, second)

    def test_different_sessions_have_distinct_buffers_and_contents(self):
        a = self.server._get_or_create_wm("session-A")
        b = self.server._get_or_create_wm("session-B")

        a.add("belief-A", "private context A", now=1000.0)
        b.add("belief-B", "private context B", now=1000.0)

        a_items = a.get_active(now=1000.0)
        b_items = b.get_active(now=1000.0)

        self.assertEqual([x["belief_id"] for x in a_items], ["belief-A"])
        self.assertEqual([x["belief_id"] for x in b_items], ["belief-B"])
        self.assertNotIn("private context A", [x["content"] for x in b_items])
        self.assertNotIn("private context B", [x["content"] for x in a_items])


if __name__ == "__main__":
    unittest.main()
