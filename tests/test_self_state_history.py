"""self_binding.bind() keeps one self_state row AND appends to self_state_history.

The single-row self_state is overwritten each bind (only "now"); the append-only
history is the continuity substrate (DESIGN_MINDEDNESS.md §2.1). Purely additive:
the read path is unchanged, so this only checks that the trace accumulates.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

from tests._bootstrap import *  # noqa: F401, F403


class TestSelfStateHistory(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nex5_ssh_")
        os.environ["NEX5_DATA_DIR"] = self.tmp
        from substrate.init_db import init_all
        init_all()
        from substrate import Writer, db_paths
        self.dynamic_writer = Writer(db_paths()["dynamic"], name="dynamic")

    def tearDown(self):
        self.dynamic_writer.close()
        os.environ.pop("NEX5_DATA_DIR", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _dynamic_conn(self):
        from substrate import db_paths
        return sqlite3.connect(str(db_paths()["dynamic"]))

    def test_bind_keeps_one_row_and_appends_history(self):
        from theory_x.stage_tom import self_binding

        r1 = self_binding.bind()
        time.sleep(0.02)
        r2 = self_binding.bind()
        self.assertIn("synthesis", r1)
        self.assertIn("synthesis", r2)

        c = self._dynamic_conn()
        try:
            # self_state stays single-row (only "now").
            n_state = c.execute("SELECT COUNT(*) FROM self_state").fetchone()[0]
            self.assertEqual(n_state, 1)

            # history accumulates one row per bind.
            rows = c.execute(
                "SELECT bound_at, synthesis FROM self_state_history "
                "ORDER BY bound_at ASC"
            ).fetchall()
            self.assertEqual(len(rows), 2)
            # bound_at is populated and ordered; the latest history synthesis
            # matches the current self_state row.
            self.assertTrue(all(row[0] for row in rows))
            cur = c.execute("SELECT synthesis FROM self_state WHERE id=1").fetchone()[0]
            self.assertEqual(rows[-1][1], cur)
        finally:
            c.close()

    def test_bind_uses_injected_dynamic_writer_without_opening_another(self):
        from theory_x.stage_tom import self_binding
        with patch.object(
            self_binding,
            "Writer",
            side_effect=AssertionError("self_binding opened a second dynamic Writer"),
        ):
            result = self_binding.bind(dynamic_writer=self.dynamic_writer)
        self.assertIn("synthesis", result)
        # The injected Writer remains owned by the caller and usable afterwards.
        self.dynamic_writer.write(
            "UPDATE self_state SET bound_at = bound_at WHERE id = 1"
        )

    def test_recursive_self_passes_the_injected_writer(self):
        from theory_x.stage_tom import recursive_self, self_binding
        with patch.object(
            self_binding,
            "bind",
            return_value={"components": {"raga": "free"}},
        ) as bind:
            result = recursive_self._bound_state(dynamic_writer=self.dynamic_writer)
        self.assertEqual(result, {"raga": "free"})
        bind.assert_called_once_with(dynamic_writer=self.dynamic_writer)

    def test_history_survives_many_binds(self):
        from theory_x.stage_tom import self_binding
        for _ in range(5):
            self_binding.bind()
        c = self._dynamic_conn()
        try:
            n = c.execute("SELECT COUNT(*) FROM self_state_history").fetchone()[0]
            self.assertEqual(n, 5)
            self.assertEqual(
                c.execute("SELECT COUNT(*) FROM self_state").fetchone()[0], 1)
        finally:
            c.close()
    def test_history_survives_many_binds(self):
        from theory_x.stage_tom import self_binding
        for _ in range(5):
            self_binding.bind()
        c = self._dynamic_conn()
        try:
            n = c.execute("SELECT COUNT(*) FROM self_state_history").fetchone()[0]
            self.assertEqual(n, 5)
            self.assertEqual(
                c.execute("SELECT COUNT(*) FROM self_state").fetchone()[0], 1)
        finally:
            c.close()


if __name__ == "__main__":
    unittest.main()
