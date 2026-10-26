"""errors.log_and_continue — swallowed exceptions become visible (H6)."""
import unittest

from tests import _bootstrap  # noqa: F401

import errors


class TestLogAndContinue(unittest.TestCase):
    def setUp(self):
        errors.clear()

    def test_records_exception_at_warning_with_traceback(self):
        try:
            raise ValueError("boom")
        except Exception as e:
            errors.log_and_continue(e, source="unit.test", context="doing a thing")
        evs = errors.recent_errors(10)  # the WARNING+ ring
        self.assertTrue(any(
            "doing a thing" in ev.message
            and ev.source == "unit.test"
            and ev.level == "WARNING"
            and ev.traceback
            for ev in evs
        ))

    def test_debug_level_kept_out_of_warning_ring(self):
        try:
            raise RuntimeError("quiet")
        except Exception as e:
            errors.log_and_continue(e, source="unit.test", level="DEBUG")
        self.assertTrue(any(ev.message.endswith("quiet") for ev in errors.recent(10)))
        self.assertFalse(any("quiet" in ev.message for ev in errors.recent_errors(10)))

    def test_never_raises(self):
        try:
            errors.log_and_continue(RuntimeError("x"), source="unit.test")
        except Exception:
            self.fail("log_and_continue must never raise")


if __name__ == "__main__":
    unittest.main()
