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


# ── SentienceNode protocol (PHASE 13 additions) ──────────────────────────────

class TestSentienceNodeProtocol(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        from theory_x.stage7_sustained.problem_memory import ProblemMemory
        self.pm = ProblemMemory(self.writers["conversations"], self.readers["conversations"])

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_implements_sentience_node_protocol(self):
        from theory_x import SentienceNode
        self.assertIsInstance(self.pm, SentienceNode)

    def test_has_name_attribute(self):
        from theory_x.stage7_sustained.problem_memory import ProblemMemory
        self.assertEqual(ProblemMemory.name, "problem_memory")
        self.assertEqual(self.pm.name, "problem_memory")

    def test_tick_returns_dict_with_name(self):
        result = self.pm.tick()
        self.assertIsInstance(result, dict)
        self.assertEqual(result["name"], "problem_memory")

    def test_tick_accepts_context(self):
        result = self.pm.tick(context={"session_id": "test"})
        self.assertIsInstance(result, dict)
        self.assertIn("open_count", result)

    def test_state_returns_expected_fields(self):
        s = self.pm.state()
        self.assertIn("name", s)
        self.assertIn("open_count", s)
        self.assertIn("oldest_age_days", s)
        self.assertIn("cache_age_s", s)

    def test_state_open_count_zero_on_empty_db(self):
        s = self.pm.tick()
        self.assertEqual(s["open_count"], 0)

    def test_decay_accepts_float(self):
        import time
        self.pm.decay(time.time())  # must not raise

    def test_state_open_count_updates_after_open(self):
        import time
        self.pm.open("Protocol Test Problem", "Testing the sentience node count")
        self.pm._cached_open = None  # force refresh
        s = self.pm.tick()
        self.assertEqual(s["open_count"], 1)


# ── find_matching — stopwords + ≥2 content-word overlap (PHASE 13) ───────────

class TestFindMatchingV2(unittest.TestCase):
    """Phase 13 tests for the improved find_matching (stopwords + ≥2 overlap)."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        from theory_x.stage7_sustained.problem_memory import ProblemMemory
        self.pm = ProblemMemory(self.writers["conversations"], self.readers["conversations"])

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_two_content_word_overlap_matches(self):
        self.pm.open(
            "Consciousness Emergence",
            "How does consciousness emerge in neural systems",
        )
        results = self.pm.find_matching("what does consciousness emergence look like")
        self.assertEqual(len(results), 1)

    def test_single_content_word_does_not_match(self):
        self.pm.open(
            "Consciousness Emergence",
            "How does consciousness emerge in neural systems",
        )
        # Only "consciousness" overlaps — 1 word, below ≥2 threshold
        results = self.pm.find_matching("tell me about consciousness")
        self.assertEqual(results, [],
            "Single content-word overlap must not match — ≥2 required")

    def test_stopwords_only_query_returns_empty(self):
        self.pm.open("Any Problem", "Description about something important")
        results = self.pm.find_matching("what do you think")
        self.assertEqual(results, [],
            "All-stopword query must return [] regardless of open problems")

    def test_closed_problems_not_matched(self):
        pid = self.pm.open(
            "Consciousness Emergence",
            "How does consciousness emerge in neural systems",
        )
        self.pm.close(pid)
        results = self.pm.find_matching("consciousness emergence neural systems")
        self.assertEqual(results, [],
            "Closed problems must not appear in find_matching results")


# ── Decay — auto-close stale problems (PHASE 13) ─────────────────────────────

class TestDecay(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        from theory_x.stage7_sustained.problem_memory import ProblemMemory
        self.pm = ProblemMemory(self.writers["conversations"], self.readers["conversations"])

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_decay_closes_stale_problems(self):
        import time
        now = time.time()
        stale_ts = now - 40 * 86400  # 40 days ago
        self.writers["conversations"].write(
            "INSERT INTO open_problems "
            "(title, description, state, created_at, last_touched_at) "
            "VALUES (?, ?, 'open', ?, ?)",
            ("Stale Problem", "Very old unresolved problem", stale_ts, stale_ts),
        )
        self.assertEqual(len(self.pm.list_open()), 1)
        self.pm.decay(now)
        self.assertEqual(len(self.pm.list_open()), 0,
            "Problem stale > 30 days must be auto-closed by decay()")

    def test_decay_leaves_fresh_problems_open(self):
        import time
        self.pm.open("Fresh Problem", "Created just now and should survive")
        self.pm.decay(time.time())
        self.assertEqual(len(self.pm.list_open()), 1,
            "Fresh problem must survive decay()")

    def test_decay_invalidates_cache(self):
        import time
        self.pm.tick()  # populate cache
        self.assertIsNotNone(self.pm._cached_open)
        self.pm.decay(time.time())
        self.assertIsNone(self.pm._cached_open,
            "decay() must invalidate the open-problem cache")


if __name__ == "__main__":
    unittest.main()
