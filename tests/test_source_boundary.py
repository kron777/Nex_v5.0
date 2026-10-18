"""Round 11 item 2 / Q4 — the source-boundary ratchet gate.

Direction A (authored -> received, the self/world leak) must be 0 and never regress.
Direction B (received -> authored) is a countdown ratcheted by --max-b. Fixture DBs.
"""
import os
import sqlite3
import tempfile
import unittest

from tests import _bootstrap  # noqa: F401

import importlib.util

_SPEC = importlib.util.spec_from_file_location(
    "check_source_boundary",
    os.path.join(os.path.dirname(__file__), "..", "tools", "check_source_boundary.py"),
)
CSB = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(CSB)


def _db(rows):
    """rows: list of (content, source, created_at)."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    cx = sqlite3.connect(path)
    cx.execute("CREATE TABLE beliefs (id INTEGER PRIMARY KEY, content TEXT, "
               "source TEXT, created_at INTEGER)")
    cx.executemany("INSERT INTO beliefs (content, source, created_at) VALUES (?,?,?)", rows)
    cx.commit(); cx.close()
    return path


class TestBoundaryRatchet(unittest.TestCase):
    def setUp(self):
        self._paths = []

    def tearDown(self):
        for p in self._paths:
            try: os.unlink(p)
            except OSError: pass

    def _make(self, rows):
        p = _db(rows); self._paths.append(p); return p

    def test_clean_passes(self):
        p = self._make([("a thought", "fountain_insight", 1),
                        ("a headline", "precipitated_from_sense", 2)])
        self.assertEqual(CSB.run(p), 0)

    def test_direction_A_always_fails(self):
        # same content: authored FIRST (t=1) then received (t=2) -> Direction A leak
        p = self._make([("shared text", "fountain_insight", 1),
                        ("shared text", "precipitated_from_sense", 2)])
        self.assertEqual(CSB.run(p, max_b=999), 1)

    def test_class_detector_flags_cross_band_source(self):
        # same content under counterfactual_node (authored) and precipitated_from_sense
        # (received) -> the source spans two bands -> flagged by the class detector.
        p = self._make([("echoed headline", "precipitated_from_sense", 1),
                        ("echoed headline", "counterfactual_node", 2),
                        ("her own thought", "fountain_insight", 3)])
        cd = CSB.class_detector(p)
        self.assertEqual(cd.get("counterfactual_node"), 1)
        self.assertEqual(cd.get("precipitated_from_sense"), 1)
        self.assertNotIn("fountain_insight", cd)   # single-band, not flagged

    def test_direction_B_ratchet(self):
        # received FIRST (t=1) then authored (t=2) -> Direction B = 1
        p = self._make([("a headline", "precipitated_from_sense", 1),
                        ("a headline", "counterfactual_node", 2)])
        self.assertEqual(CSB.run(p, max_b=17), 0)   # within ceiling
        self.assertEqual(CSB.run(p, max_b=0), 1)    # ratcheted below -> fail


if __name__ == "__main__":
    unittest.main()
