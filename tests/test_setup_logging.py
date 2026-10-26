"""nex_config.setup_logging() (D-C PR 1).

Four guards Beam's round-5 reply requires. getEffectiveLevel checks alone pass
happily while a propagate=False regression zeros the health metric, so the real
protection is (b) end-to-end emission and (c) the health-metric-intact test.

Global logging state is process-wide, so each test snapshots and restores the
root logger, the touched loggers' levels, the _log_configured guard, and the
error channel.
"""
import logging
import unittest

from tests import _bootstrap  # noqa: F401

import nex_config
import errors


class _Capture(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.NOTSET)
        self.names = []

    def emit(self, record):
        self.names.append(record.name)


class TestSetupLogging(unittest.TestCase):
    def setUp(self):
        self.root = logging.getLogger()
        self._root_level = self.root.level
        self._root_handlers = list(self.root.handlers)
        self._touched = nex_config.APP_LOG_NAMESPACES + nex_config.NOISY_THIRD_PARTY
        self._levels = {n: logging.getLogger(n).level for n in self._touched}
        # App namespaces inherit root; clear any stray explicit level.
        for n in nex_config.APP_LOG_NAMESPACES:
            logging.getLogger(n).setLevel(logging.NOTSET)
        self._was_configured = nex_config._log_configured
        nex_config._log_configured = False
        self._disk_failed = errors._disk_failed
        errors._disk_failed = True  # keep the test off repo/logs/errors.log
        errors.clear()

    def tearDown(self):
        self.root.setLevel(self._root_level)
        self.root.handlers = self._root_handlers
        for n, lvl in self._levels.items():
            logging.getLogger(n).setLevel(lvl)
        nex_config._log_configured = self._was_configured
        errors._disk_failed = self._disk_failed
        errors.clear()

    # (a) namespace resolution
    def test_levels_resolve_correctly(self):
        nex_config.setup_logging()
        for n in nex_config.APP_LOG_NAMESPACES:
            self.assertEqual(logging.getLogger(n).getEffectiveLevel(),
                             logging.INFO, f"{n} should be INFO")
        for n in nex_config.NOISY_THIRD_PARTY:
            self.assertEqual(logging.getLogger(n).getEffectiveLevel(),
                             logging.WARNING, f"{n} should be WARNING")

    # (b) end-to-end emission — the propagate=False guard
    def test_every_app_namespace_reaches_root(self):
        nex_config.setup_logging()
        cap = _Capture()
        self.root.addHandler(cap)
        try:
            for n in nex_config.APP_LOG_NAMESPACES:
                logging.getLogger(n).info("probe")
        finally:
            self.root.removeHandler(cap)
        for n in nex_config.APP_LOG_NAMESPACES:
            self.assertIn(n, cap.names, f"{n} INFO did not reach root")

    # (c) health metric intact — Caveat A: a quieted logger's WARNING still counts
    def test_quieted_logger_warning_still_counts(self):
        nex_config.setup_logging()
        before = len(errors.recent_errors())
        logging.getLogger("werkzeug").warning("simulated third-party warning")
        after = len(errors.recent_errors())
        self.assertEqual(after, before + 1)

    # (d) idempotency
    def test_idempotent(self):
        nex_config.setup_logging()
        n_handlers = len(self.root.handlers)
        n_central = sum(isinstance(h, errors.CentralHandler)
                        for h in self.root.handlers)
        nex_config.setup_logging()
        self.assertEqual(len(self.root.handlers), n_handlers)
        self.assertEqual(n_central, 1)


if __name__ == "__main__":
    unittest.main()
