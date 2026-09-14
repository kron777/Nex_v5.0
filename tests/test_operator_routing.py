"""Tests for the admin-chat routing fix (_use_operator_composition).

Bug: admin (Jon) chats short-circuit to RAG/query_reply (belief verbatim) before
reaching the voice composition path, so the operator model — injected into the
composition prompt — never fired for him. Fix: when the session is admin AND
NEX5_OPERATOR_MODEL is armed, skip RAG so the reply is composed (operator-
coloured). Scoped to admin+flag only; non-admin/public and flag-off unchanged.
"""
from __future__ import annotations

import os
import unittest

from tests import _bootstrap  # noqa: F401

from gui import server as s


class TestOperatorRouting(unittest.TestCase):

    def setUp(self):
        self._prev = os.environ.get("NEX5_OPERATOR_MODEL")

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("NEX5_OPERATOR_MODEL", None)
        else:
            os.environ["NEX5_OPERATOR_MODEL"] = self._prev

    def test_admin_plus_flag_skips_rag(self):
        os.environ["NEX5_OPERATOR_MODEL"] = "1"
        self.assertTrue(s._use_operator_composition({"admin": True}))

    def test_nonadmin_unchanged_even_with_flag(self):
        os.environ["NEX5_OPERATOR_MODEL"] = "1"
        self.assertFalse(s._use_operator_composition({"admin": False}))
        self.assertFalse(s._use_operator_composition({}))          # no admin key

    def test_admin_flag_off_stays_rag_first(self):
        os.environ.pop("NEX5_OPERATOR_MODEL", None)
        self.assertFalse(s._use_operator_composition({"admin": True}))

    def test_failsafe_on_bad_session(self):
        os.environ["NEX5_OPERATOR_MODEL"] = "1"
        self.assertFalse(s._use_operator_composition(None))        # .get raises -> False

    def test_rag_condition_references_the_gate(self):
        # the fix must actually be wired into the chat handler's RAG branch
        import inspect
        src = inspect.getsource(s.build_app) if hasattr(s, "build_app") else inspect.getsource(s)
        self.assertIn("_use_operator_composition(session)", src)


if __name__ == "__main__":
    unittest.main()
