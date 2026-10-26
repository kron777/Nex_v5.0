"""M8 — the HUD's direct-sqlite endpoints resolve DB paths via NEX5_DATA_DIR,
not a hardcoded /home/rr location that only exists on the original box."""
import os
import unittest

from tests import _bootstrap  # noqa: F401


class TestHudDbPathsResolve(unittest.TestCase):
    def test_constants_follow_data_dir_not_home_rr(self):
        import gui.server as server

        for const, name in ((server._DYN_DB, "dynamic.db"),
                            (server._CONV_DB, "conversations.db")):
            p = str(const)                         # DbPath resolves at str() time
            self.assertFalse(p.startswith("/home/rr"), p)
            self.assertTrue(p.endswith(name), p)
            self.assertIn(os.environ["NEX5_DATA_DIR"], p)


if __name__ == "__main__":
    unittest.main()
