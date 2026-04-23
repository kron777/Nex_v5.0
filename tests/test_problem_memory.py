"""ProblemMemory tests.

Covers:
- open() creates a row and returns an id
- observe() appends to observations list
- update_plan() sets the plan field
- close() sets state to closed
- resume() returns the full record with parsed observations
- list_open() excludes closed problems
- find_matching() returns problems whose words overlap the query
- format_for_prompt() produces a readable block
"""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_pm_")
    os.environ["NEX5_DATA_DIR"] = tmp
    os.environ["NEX5_ADMIN_HASH_FILE"] = str(Path(tmp) / "admin.argon2")
    from substrate.init_db import init_all
    init_all()
    from substrate import Reader, Writer, db_paths
    paths = db_paths()
    writers = {n: Writer(p, name=n) for n, p in paths.items()}
    readers = {n: Reader(p) for n, p in paths.items()}
    return writers, readers, tmp


def _cleanup(writers, tmp):
    for w in writers.values():
        try:
            w.close()
        except Exception:
            pass
    shutil.rmtree(tmp, ignore_errors=True)


class TestProblemMemory(unittest.TestCase):

    def test_open_returns_id(self):
        writers, readers, tmp = _make_env()
        try:
            from theory_x.stage7_sustained.problem_memory import ProblemMemory
            pm = ProblemMemory(writers["conversations"], readers["conversations"])
            pid = pm.open("test problem", "something I am thinking about")
            self.assertIsInstance(pid, int)
            self.assertGreater(pid, 0)
        finally:
            _cleanup(writers, tmp)

    def test_resume_returns_record(self):
        writers, readers, tmp = _make_env()
        try:
            from theory_x.stage7_sustained.problem_memory import ProblemMemory
            pm = ProblemMemory(writers["conversations"], readers["conversations"])
            pid = pm.open("recursion question", "does nex recurse?")
            p = pm.resume(pid)
            self.assertIsNotNone(p)
            self.assertEqual(p["title"], "recursion question")
            self.assertEqual(p["state"], "open")
            self.assertIsInstance(p["observations"], list)
            self.assertEqual(len(p["observations"]), 0)
        finally:
            _cleanup(writers, tmp)

    def test_observe_appends(self):
        writers, readers, tmp = _make_env()
        try:
            from theory_x.stage7_sustained.problem_memory import ProblemMemory
            pm = ProblemMemory(writers["conversations"], readers["conversations"])
            pid = pm.open("convergence", "will beliefs converge?")
            pm.observe(pid, "first observation")
            pm.observe(pid, "second observation")
            p = pm.resume(pid)
            self.assertEqual(len(p["observations"]), 2)
            self.assertEqual(p["observations"][0]["text"], "first observation")
            self.assertEqual(p["observations"][1]["text"], "second observation")
        finally:
            _cleanup(writers, tmp)

    def test_update_plan(self):
        writers, readers, tmp = _make_env()
        try:
            from theory_x.stage7_sustained.problem_memory import ProblemMemory
            pm = ProblemMemory(writers["conversations"], readers["conversations"])
            pid = pm.open("architecture", "what pattern to use?")
            pm.update_plan(pid, "use spreading activation")
            p = pm.resume(pid)
            self.assertEqual(p["plan"], "use spreading activation")
        finally:
            _cleanup(writers, tmp)

    def test_close_sets_state(self):
        writers, readers, tmp = _make_env()
        try:
            from theory_x.stage7_sustained.problem_memory import ProblemMemory
            pm = ProblemMemory(writers["conversations"], readers["conversations"])
            pid = pm.open("closed problem", "this will be closed")
            pm.close(pid)
            p = pm.resume(pid)
            self.assertEqual(p["state"], "closed")
        finally:
            _cleanup(writers, tmp)

    def test_list_open_excludes_closed(self):
        writers, readers, tmp = _make_env()
        try:
            from theory_x.stage7_sustained.problem_memory import ProblemMemory
            pm = ProblemMemory(writers["conversations"], readers["conversations"])
            p1 = pm.open("open one", "still open")
            p2 = pm.open("closed one", "will close")
            pm.close(p2)
            open_list = pm.list_open()
            ids = [p["id"] for p in open_list]
            self.assertIn(p1, ids)
            self.assertNotIn(p2, ids)
        finally:
            _cleanup(writers, tmp)

    def test_find_matching_keyword_overlap(self):
        writers, readers, tmp = _make_env()
        try:
            from theory_x.stage7_sustained.problem_memory import ProblemMemory
            pm = ProblemMemory(writers["conversations"], readers["conversations"])
            pm.open("activation spreading", "exploring graph traversal")
            pm.open("belief convergence", "unrelated topic")
            matches = pm.find_matching("activation in the belief graph")
            titles = [m["title"] for m in matches]
            self.assertIn("activation spreading", titles)
        finally:
            _cleanup(writers, tmp)

    def test_find_matching_empty_query(self):
        writers, readers, tmp = _make_env()
        try:
            from theory_x.stage7_sustained.problem_memory import ProblemMemory
            pm = ProblemMemory(writers["conversations"], readers["conversations"])
            pm.open("some problem", "description")
            matches = pm.find_matching("")
            self.assertEqual(matches, [])
        finally:
            _cleanup(writers, tmp)

    def test_format_for_prompt_contains_title(self):
        writers, readers, tmp = _make_env()
        try:
            from theory_x.stage7_sustained.problem_memory import ProblemMemory
            pm = ProblemMemory(writers["conversations"], readers["conversations"])
            pid = pm.open("epistemic temperature", "how hot is the belief graph?")
            pm.observe(pid, "depends on edge density")
            pm.update_plan(pid, "measure edge count vs belief count ratio")
            text = pm.format_for_prompt(pid)
            self.assertIn("epistemic temperature", text)
            self.assertIn("depends on edge density", text)
            self.assertIn("measure edge count", text)
        finally:
            _cleanup(writers, tmp)

    def test_resume_nonexistent_returns_none(self):
        writers, readers, tmp = _make_env()
        try:
            from theory_x.stage7_sustained.problem_memory import ProblemMemory
            pm = ProblemMemory(writers["conversations"], readers["conversations"])
            self.assertIsNone(pm.resume(9999))
        finally:
            _cleanup(writers, tmp)


if __name__ == "__main__":
    unittest.main()
