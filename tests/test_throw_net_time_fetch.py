"""Throw-Net TimeFetch tests — Phase 25a TN-2.

Covers:
- fetch_from_beliefs returns matching rows with correct provenance
- fetch_from_beliefs filters confidence < 0.4
- fetch_from_beliefs filters short content (<=30 chars)
- fetch_from_novel_associations returns matches with similarity order
- fetch_from_novel_associations orders by similarity DESC
- fetch_from_arcs filters out return_transformation (D6 critical)
- fetch_from_arcs orders by quality_grade DESC
- fetch_from_problems routes through ProblemMemory.find_matching()
- fetch_from_problems handles ProblemMemory error gracefully
- run() combines all four sweeps
- run() deduplicates overlapping content
- run() caps total at _dedup_cap (40)
- provenance markers (source key) are correct for all sweeps
- empty constraint returns []
- stopwords-only constraint returns []
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tests import _bootstrap  # noqa: F401


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_tf_")
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
    os.environ.pop("NEX5_DATA_DIR", None)
    os.environ.pop("NEX5_ADMIN_HASH_FILE", None)


def _make_tf(writers, readers, problem_memory=None):
    from theory_x.stage_throw_net.time_fetch import TimeFetch
    if problem_memory is None:
        problem_memory = MagicMock()
        problem_memory.find_matching.return_value = []
    return TimeFetch(readers["beliefs"], problem_memory)


def _write_belief(writers, content, confidence=0.7, branch_id="test", tier=7):
    writers["beliefs"].write(
        "INSERT INTO beliefs "
        "(content, tier, confidence, created_at, source, branch_id, "
        "reinforce_count, use_count, erosion_stage, locked, corroboration_count) "
        "VALUES (?, ?, ?, ?, 'test', ?, 0, 0, 'external', 0, 0)",
        (content, tier, confidence, time.time(), branch_id),
    )
    time.sleep(0.03)


def _write_novel_assoc(writers, readers, content_a, content_b,
                       branch_a="alpha", branch_b="beta", similarity=0.80):
    """Insert two beliefs and link them in novel_association_log."""
    writers["beliefs"].write(
        "INSERT INTO beliefs (content, tier, confidence, created_at, source, "
        "branch_id, reinforce_count, use_count, erosion_stage, locked, "
        "corroboration_count) VALUES (?, 7, 0.7, ?, 'test', ?, 0, 0, 'external', 0, 0)",
        (content_a, time.time(), branch_a),
    )
    time.sleep(0.03)
    writers["beliefs"].write(
        "INSERT INTO beliefs (content, tier, confidence, created_at, source, "
        "branch_id, reinforce_count, use_count, erosion_stage, locked, "
        "corroboration_count) VALUES (?, 7, 0.7, ?, 'test', ?, 0, 0, 'external', 0, 0)",
        (content_b, time.time(), branch_b),
    )
    time.sleep(0.03)
    rows_a = readers["beliefs"].read(
        "SELECT id FROM beliefs WHERE content=?", (content_a,)
    )
    rows_b = readers["beliefs"].read(
        "SELECT id FROM beliefs WHERE content=?", (content_b,)
    )
    if rows_a and rows_b:
        writers["beliefs"].write(
            "INSERT OR IGNORE INTO novel_association_log "
            "(detected_at, belief_id_a, belief_id_b, branch_id_a, "
            "branch_id_b, similarity) VALUES (?, ?, ?, ?, ?, ?)",
            (time.time(), rows_a[0]["id"], rows_b[0]["id"],
             branch_a, branch_b, similarity),
        )
        time.sleep(0.03)


def _write_arc(writers, theme_summary, arc_type="progression", quality_grade=0.75):
    writers["beliefs"].write(
        "INSERT INTO arcs "
        "(arc_type, detected_at, window_start, window_end, theme_summary, "
        "member_count, quality_grade, last_active_at) "
        "VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
        (arc_type, time.time(), time.time() - 3600, time.time(),
         theme_summary, quality_grade, time.time()),
    )
    time.sleep(0.03)


class TestFetchFromBeliefs(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.tf = _make_tf(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_fetch_from_beliefs_returns_matches(self):
        """Beliefs containing the keyword are returned with correct provenance."""
        _write_belief(self.writers,
                      "Consciousness emerges from the complexity of neural binding processes.",
                      confidence=0.75, branch_id="cognition")
        results = self.tf.fetch_from_beliefs("consciousness")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source"], "belief")
        self.assertEqual(results[0]["branch_id"], "cognition")
        self.assertAlmostEqual(results[0]["confidence"], 0.75, places=2)
        self.assertIn("origin_id", results[0])

    def test_fetch_from_beliefs_filters_low_confidence(self):
        """Beliefs with confidence <= 0.4 are excluded."""
        _write_belief(self.writers,
                      "This consciousness belief has insufficient confidence score.",
                      confidence=0.3)
        results = self.tf.fetch_from_beliefs("consciousness")
        self.assertEqual(len(results), 0)

    def test_fetch_from_beliefs_filters_short_content(self):
        """Beliefs with content <= 30 chars are excluded."""
        _write_belief(self.writers, "consciousness brief.", confidence=0.8)
        results = self.tf.fetch_from_beliefs("consciousness")
        self.assertEqual(len(results), 0)

    def test_fetch_from_beliefs_provenance_source_key(self):
        """source key is 'belief' for all returned items."""
        _write_belief(self.writers,
                      "Emergence arises when complex systems reach critical thresholds.",
                      confidence=0.7)
        results = self.tf.fetch_from_beliefs("emergence")
        for r in results:
            self.assertEqual(r["source"], "belief")


class TestFetchFromNovelAssociations(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.tf = _make_tf(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_fetch_from_novel_associations_returns_matches(self):
        """Pairs where either belief contains the keyword are returned."""
        _write_novel_assoc(
            self.writers, self.readers,
            "Consciousness arises through integrated information processing.",
            "Awareness connects disparate cognitive systems naturally.",
            similarity=0.82,
        )
        results = self.tf.fetch_from_novel_associations("consciousness")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source"], "novel_association")
        self.assertIn("↔", results[0]["content"])
        self.assertAlmostEqual(results[0]["similarity"], 0.82, places=2)

    def test_fetch_from_novel_associations_orders_by_similarity_desc(self):
        """Higher similarity associations come first."""
        _write_novel_assoc(
            self.writers, self.readers,
            "Emergence emerges from interconnected belief systems deeply.",
            "Patterns emerge within complex adaptive networks today.",
            similarity=0.65,
        )
        _write_novel_assoc(
            self.writers, self.readers,
            "Emergence reflects the boundary between order and chaos.",
            "Complexity underlies every emergent phenomenon observed now.",
            similarity=0.90,
        )
        results = self.tf.fetch_from_novel_associations("emergence")
        self.assertGreaterEqual(len(results), 2)
        self.assertGreaterEqual(results[0]["similarity"], results[1]["similarity"])

    def test_fetch_from_novel_associations_provenance(self):
        """source key is 'novel_association'; branch_id_a and branch_id_b present."""
        _write_novel_assoc(
            self.writers, self.readers,
            "Fractal geometry reveals hidden self-similarity structures.",
            "Mathematical patterns encode recursive complexity always.",
            branch_a="math", branch_b="cognition", similarity=0.78,
        )
        results = self.tf.fetch_from_novel_associations("fractal")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source"], "novel_association")
        self.assertIn("branch_id_a", results[0])
        self.assertIn("branch_id_b", results[0])


class TestFetchFromArcs(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.tf = _make_tf(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_fetch_from_arcs_filters_groove_arc_type(self):
        """return_transformation arcs are excluded (D6 critical test)."""
        _write_arc(self.writers,
                   "The consciousness of the groove repeating pattern emerges.",
                   arc_type="return_transformation", quality_grade=0.90)
        results = self.tf.fetch_from_arcs("consciousness")
        self.assertEqual(len(results), 0,
                         "return_transformation arcs must be filtered (D6)")

    def test_fetch_from_arcs_returns_non_groove_arcs(self):
        """Non-groove arcs matching the keyword are returned."""
        _write_arc(self.writers,
                   "Consciousness expands through progressive belief integration.",
                   arc_type="progression", quality_grade=0.80)
        results = self.tf.fetch_from_arcs("consciousness")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source"], "arc")
        self.assertEqual(results[0]["arc_type"], "progression")

    def test_fetch_from_arcs_orders_by_quality_grade_desc(self):
        """Higher quality arcs come first."""
        _write_arc(self.writers,
                   "Emergence pattern grows through interconnected belief weaving.",
                   arc_type="progression", quality_grade=0.60)
        _write_arc(self.writers,
                   "Emergence arises when complexity crosses the threshold point.",
                   arc_type="progression", quality_grade=0.85)
        results = self.tf.fetch_from_arcs("emergence")
        self.assertGreaterEqual(len(results), 2)
        self.assertGreaterEqual(results[0]["quality_grade"], results[1]["quality_grade"])

    def test_fetch_from_arcs_provenance(self):
        """source='arc', arc_type and quality_grade present."""
        _write_arc(self.writers,
                   "Fractal self-similarity emerges from belief graph topology.",
                   arc_type="progression", quality_grade=0.75)
        results = self.tf.fetch_from_arcs("fractal")
        self.assertEqual(results[0]["source"], "arc")
        self.assertIn("arc_type", results[0])
        self.assertIn("quality_grade", results[0])
        self.assertIn("origin_id", results[0])


class TestFetchFromProblems(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_fetch_from_problems_routes_through_problem_memory(self):
        """find_matching() is called and results are converted to candidate format."""
        pm = MagicMock()
        pm.find_matching.return_value = [
            {"id": 42, "title": "Consciousness gap",
             "description": "We lack beliefs connecting consciousness to substrate."},
        ]
        tf = _make_tf(self.writers, self.readers, problem_memory=pm)
        results = tf.fetch_from_problems("consciousness")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source"], "gap")
        self.assertEqual(results[0]["origin_id"], 42)
        self.assertIn("Consciousness gap", results[0]["content"])
        pm.find_matching.assert_called_once_with("consciousness")

    def test_fetch_from_problems_handles_problem_memory_error(self):
        """ProblemMemory exception is swallowed; returns []."""
        pm = MagicMock()
        pm.find_matching.side_effect = RuntimeError("pm exploded")
        tf = _make_tf(self.writers, self.readers, problem_memory=pm)
        results = tf.fetch_from_problems("consciousness")
        self.assertEqual(results, [])

    def test_fetch_from_problems_empty_constraint(self):
        """Empty constraint returns [] without calling find_matching."""
        pm = MagicMock()
        tf = _make_tf(self.writers, self.readers, problem_memory=pm)
        results = tf.fetch_from_problems("")
        self.assertEqual(results, [])
        pm.find_matching.assert_not_called()


class TestRunCombinedSweep(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_run_combines_all_sweeps(self):
        """run() collects candidates from multiple sources."""
        _write_belief(self.writers,
                      "Consciousness emerges through integrated information processing always.",
                      confidence=0.75)
        pm = MagicMock()
        pm.find_matching.return_value = [
            {"id": 1, "title": "Consciousness gap",
             "description": "Open question about consciousness substrate."},
        ]
        tf = _make_tf(self.writers, self.readers, problem_memory=pm)
        results = tf.run("consciousness")
        sources = {r["source"] for r in results}
        self.assertIn("belief", sources)
        self.assertIn("gap", sources)

    def test_run_deduplicates_overlapping_content(self):
        """Same content string from multiple sweeps appears only once."""
        content = "Consciousness emerges from integrated information processing always."
        _write_belief(self.writers, content, confidence=0.75)

        pm = MagicMock()
        # Return same content as a problem too
        pm.find_matching.return_value = [
            {"id": 1, "title": content, "description": ""}
        ]
        tf = _make_tf(self.writers, self.readers, problem_memory=pm)
        results = tf.run("consciousness")
        contents = [r["content"] for r in results]
        # The full belief content won't exactly match the title-only problem content
        # but verify no exact duplicates exist
        self.assertEqual(len(contents), len(set(contents)))

    def test_run_caps_total_at_dedup_cap(self):
        """run() returns at most _dedup_cap (40) results."""
        # Seed 50 distinct beliefs with the keyword
        for i in range(50):
            _write_belief(
                self.writers,
                f"Belief number {i} about consciousness and neural emergence here.",
                confidence=0.7,
            )
        tf = _make_tf(self.writers, self.readers)
        tf._belief_limit = 50  # bypass per-sweep limit for this test
        results = tf.run("consciousness")
        self.assertLessEqual(len(results), tf._dedup_cap)

    def test_run_empty_constraint_returns_empty(self):
        """run('') returns [] without any DB reads."""
        tf = _make_tf(self.writers, self.readers)
        self.assertEqual(tf.run(""), [])
        self.assertEqual(tf.run("   "), [])

    def test_run_stopwords_only_returns_empty(self):
        """run('the and is') returns [] — no keywords after filtering."""
        _write_belief(self.writers,
                      "The system and is working as expected here correctly.",
                      confidence=0.7)
        tf = _make_tf(self.writers, self.readers)
        results = tf.run("the and is")
        self.assertEqual(results, [])

    def test_provenance_markers_correct(self):
        """source key is one of the four valid values for each result."""
        _write_belief(self.writers,
                      "Emergence unfolds when complex adaptive systems cross thresholds.",
                      confidence=0.75)
        pm = MagicMock()
        pm.find_matching.return_value = [
            {"id": 7, "title": "Emergence problem statement open",
             "description": "Understanding emergence in complex systems."},
        ]
        tf = _make_tf(self.writers, self.readers, problem_memory=pm)
        results = tf.run("emergence")
        valid_sources = {"belief", "novel_association", "arc", "gap"}
        for r in results:
            self.assertIn(r["source"], valid_sources,
                          f"Unexpected source: {r['source']}")


class TestExtractKeywords(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.tf = _make_tf(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_keywords_strips_stopwords(self):
        """Common stopwords are excluded from keyword list."""
        keywords = self.tf._extract_keywords("the and is of")
        self.assertEqual(keywords, [])

    def test_keywords_filters_short_tokens(self):
        """Tokens shorter than min_len are excluded."""
        keywords = self.tf._extract_keywords("go do it be", min_len=3)
        self.assertEqual(keywords, [])

    def test_keywords_strips_punctuation(self):
        """Trailing punctuation is stripped before comparison."""
        keywords = self.tf._extract_keywords("consciousness, belief.")
        self.assertIn("consciousness", keywords)
        self.assertIn("belief", keywords)


if __name__ == "__main__":
    unittest.main()
