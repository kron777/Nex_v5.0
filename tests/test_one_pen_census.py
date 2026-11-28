"""tools/one_pen_census.py -- the static one-pen scan stays runnable and truthful.

Fixture files only for the classification rules; one smoke run over the real
repository pins a known, documented exception (StrikeCatalogue writes its own
strikes_catalogue.db directly) so the scan cannot silently stop seeing writes.
"""
from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

from tools import one_pen_census as C

_ROOT = Path(__file__).resolve().parents[1]


def _scan(code, rel="theory_x/fake/mod.py"):
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "mod.py"
        p.write_text(textwrap.dedent(code))
        return C.scan_file(p, rel)


class TestClassification(unittest.TestCase):
    def test_direct_write_is_reported(self):
        [s] = _scan("""
            from substrate import connect
            def tick():
                cx = connect("x.db")
                cx.execute("UPDATE signals SET actioned_at=? WHERE id=?", (1, 2))
                cx.commit()
        """)
        self.assertEqual((s["function"], s["writes"], s["runtime"]), ("tick", True, True))

    def test_read_only_connections_are_not_sites(self):
        self.assertEqual(_scan("""
            from substrate import connect
            def a(): return connect("file:x.db?mode=ro", uri=True).execute("SELECT 1")
            def b(): return connect("x.db", read_only=True)
        """), [])

    def test_returned_connection_is_flagged_for_review(self):
        [s] = _scan("""
            from substrate import connect
            def _connect():
                conn = connect("x.db")
                return conn
        """)
        self.assertEqual((s["writes"], s["hands_off"]), (False, True))

    def test_scripts_are_not_runtime(self):
        [s] = _scan("""
            import sqlite3
            con = sqlite3.connect("x.db")
            con.execute("DELETE FROM t")
        """, rel="scripts/cleanup.py")
        self.assertEqual((s["runtime"], s["writes"]), (False, True))


class TestRepositorySmoke(unittest.TestCase):
    def test_known_documented_exception_is_seen(self):
        sites = C.census(_ROOT)
        self.assertGreater(len(sites), 0)
        strikes = [s for s in sites if s["site"].startswith("strikes/catalogue.py:")]
        self.assertTrue(strikes and all(s["runtime"] for s in strikes))
        self.assertTrue(any(s["hands_off"] for s in strikes))   # _connect() factory
        self.assertFalse(any(s["site"].startswith(("substrate/", "tests/")) for s in sites))


if __name__ == "__main__":
    unittest.main()
