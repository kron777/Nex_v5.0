"""Phase 17 smoke tests — Novel Association (Stage 10a).

Covers:
- SentienceNode protocol conformance
- Per-branch candidate sampling
- Cross-branch high-similarity pair → synthesises edge + log entry
- Same-branch pair → skipped (no edge, no log)
- Below-threshold cross-branch pair → not detected
- Duplicate pair → INSERT OR IGNORE (no double log entry)
- format_for_prompt() empty when no log entries
- format_for_prompt() returns text when unannotated entry exists
- format_for_prompt() marks annotated_at after surfacing
- format_for_prompt() skips entries outside lookback window
- format_for_prompt() skips already-annotated entries
- tick() interval gate: no scan before _LOOP_INTERVAL_S elapsed
- decay() resolves stale unannotated entries
- decay() preserves fresh unannotated entries
- Cross-restart persistence
- start_loop() smoke test (no crash, daemon thread)
"""
from __future__ import annotations

import os
import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401


def _make_env():
    # Clear embed_belief LRU cache before each test env. The cache is process-level
    # and keyed by belief_id only; fresh temp DBs reuse the same IDs, so without
    # this clear, embed_belief() returns stale embeddings from prior tests.
    try:
        from theory_x.diversity import embeddings as _emb
        with _emb._cache_lock:
            _emb._cache.clear()
    except Exception:
        pass

    tmp = tempfile.mkdtemp(prefix="nex5_nassoc_")
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


def _build_na(writers, readers):
    from theory_x.stage10_imagination.novel_association import NovelAssociation
    return NovelAssociation(writers["beliefs"], readers["beliefs"])


def _seed_belief(writers, content, branch_id, confidence=0.5):
    now = time.time()
    return writers["beliefs"].write(
        "INSERT INTO beliefs (content, tier, confidence, created_at, branch_id) "
        "VALUES (?, 7, ?, ?, ?)",
        (content, confidence, now, branch_id),
    )


def _seed_log_entry(writers, belief_id_a, belief_id_b, branch_id_a, branch_id_b,
                    similarity=0.85, detected_at=None, annotated_at=None):
    ts = detected_at if detected_at is not None else time.time()
    writers["beliefs"].write(
        "INSERT OR IGNORE INTO novel_association_log "
        "(detected_at, belief_id_a, belief_id_b, branch_id_a, branch_id_b, "
        "similarity, annotated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (ts, belief_id_a, belief_id_b, branch_id_a, branch_id_b, similarity, annotated_at),
    )


# ── SentienceNode protocol ────────────────────────────────────────────────────

class TestSentienceNodeProtocol(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.na = _build_na(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_implements_sentience_node_protocol(self):
        from theory_x import SentienceNode
        self.assertIsInstance(self.na, SentienceNode)

    def test_name_attribute(self):
        from theory_x.stage10_imagination.novel_association import NovelAssociation
        self.assertEqual(NovelAssociation.name, "novel_association")
        self.assertEqual(self.na.name, "novel_association")

    def test_tick_returns_dict_with_name(self):
        result = self.na.tick()
        self.assertIsInstance(result, dict)
        self.assertEqual(result["name"], "novel_association")

    def test_tick_returns_expected_fields(self):
        result = self.na.tick()
        self.assertIn("last_scan_at", result)
        self.assertIn("edges_written_total", result)
        self.assertIn("next_scan_in", result)

    def test_state_returns_expected_fields(self):
        s = self.na.state()
        self.assertIn("name", s)
        self.assertIn("last_scan_at", s)
        self.assertIn("edges_written_total", s)
        self.assertIn("next_scan_in", s)

    def test_decay_accepts_float(self):
        self.na.decay(time.time())  # must not raise

    def test_tick_accepts_context(self):
        result = self.na.tick(context={"session_id": "test"})
        self.assertIsInstance(result, dict)


# ── Candidate sampling ────────────────────────────────────────────────────────

class TestCandidateSampling(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.na = _build_na(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_candidates_have_valid_branch(self):
        # init_all() seeds koan beliefs with branch_id='systems'; they must appear
        # in candidates (correct behaviour). All returned candidates must have
        # branch_id set — the filter excludes NULL-branch beliefs.
        candidates = self.na._pull_candidates()
        for c in candidates:
            self.assertIsNotNone(c["branch_id"],
                f"Candidate id={c['id']} has NULL branch_id — must be excluded")

    def test_null_branch_excluded(self):
        null_id = self.writers["beliefs"].write(
            "INSERT INTO beliefs (content, tier, confidence, created_at) "
            "VALUES ('no branch belief unique xzqw', 7, 0.5, ?)",
            (time.time(),),
        )
        candidates = self.na._pull_candidates()
        candidate_ids = {c["id"] for c in candidates}
        self.assertNotIn(null_id, candidate_ids, "NULL branch_id belief must not appear in candidates")

    def test_per_branch_sampling_limits(self):
        # Seed 3 small branches (5 beliefs each — below _BATCH_SIZE cap)
        # and 1 large branch (20 beliefs — above _BATCH_SIZE cap).
        # Expected: small branches fully sampled (5 each); large branch capped.
        from theory_x.stage10_imagination.novel_association import _BATCH_SIZE
        from collections import Counter

        for branch in ("test_small_a", "test_small_b", "test_small_c"):
            for i in range(5):
                _seed_belief(self.writers, f"small branch {branch} belief {i}", branch)

        for i in range(20):
            _seed_belief(self.writers, f"large branch test_large belief {i}", "test_large")

        candidates = self.na._pull_candidates()
        branch_counts = Counter(c["branch_id"] for c in candidates)

        # Small branches: all 5 beliefs present (fully sampled)
        for small_branch in ("test_small_a", "test_small_b", "test_small_c"):
            self.assertEqual(branch_counts.get(small_branch, 0), 5,
                f"Small branch '{small_branch}' must be fully sampled (5 beliefs)")

        # Large branch: capped at _BATCH_SIZE
        self.assertLessEqual(branch_counts.get("test_large", 0), _BATCH_SIZE,
            f"Large branch must be capped at _BATCH_SIZE ({_BATCH_SIZE})")

    def test_paused_belief_excluded(self):
        paused_id = self.writers["beliefs"].write(
            "INSERT INTO beliefs (content, tier, confidence, created_at, branch_id, paused) "
            "VALUES ('paused belief unique xzqw', 7, 0.5, ?, 'systems', 1)",
            (time.time(),),
        )
        candidates = self.na._pull_candidates()
        candidate_ids = {c["id"] for c in candidates}
        self.assertNotIn(paused_id, candidate_ids, "Paused belief must not appear in candidates")

    def test_low_confidence_excluded(self):
        low_id = _seed_belief(
            self.writers, "low confidence belief unique xzqw", "systems", confidence=0.10
        )
        candidates = self.na._pull_candidates()
        candidate_ids = {c["id"] for c in candidates}
        self.assertNotIn(low_id, candidate_ids, "Low-confidence belief must not appear in candidates")


# ── Edge + log detection ──────────────────────────────────────────────────────

class TestEdgeDetection(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.na = _build_na(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _force_scan(self):
        """Force a scan regardless of interval."""
        self.na._last_scan_at = 0.0
        self.na.tick()

    def test_high_similarity_cross_branch_writes_edge(self):
        # Nearly identical content → cosine very close to 1.0 (normalized)
        _seed_belief(
            self.writers,
            "consciousness emerges from integrated information processing in neural systems",
            "cognition_science",
        )
        _seed_belief(
            self.writers,
            "consciousness emerges from integrated information processing in artificial systems",
            "ai_research",
        )
        self._force_scan()
        edges = self.readers["beliefs"].read(
            "SELECT * FROM belief_edges WHERE edge_type = 'synthesises'", ()
        )
        self.assertGreater(len(edges), 0, "High-similarity cross-branch pair must create synthesises edge")

    def test_high_similarity_cross_branch_writes_log(self):
        _seed_belief(
            self.writers,
            "distributed ledger technology enables trustless consensus across nodes",
            "crypto",
        )
        _seed_belief(
            self.writers,
            "distributed ledger technology enables trustless consensus between peers",
            "emerging_tech",
        )
        self._force_scan()
        log_rows = self.readers["beliefs"].read(
            "SELECT * FROM novel_association_log", ()
        )
        self.assertGreater(len(log_rows), 0, "Detected pair must write log entry")

    def test_same_branch_pair_skipped(self):
        # Use a dedicated branch name to avoid cross-pairing with pre-seeded koans.
        # With the conditional cap, pre-seeded systems koans are fully sampled and
        # may cross-pair with common vocabulary. Check by specific IDs: the
        # same-branch pair must not produce an edge, regardless of other edges.
        id_a = _seed_belief(
            self.writers,
            "same branch test belief alpha unique xzqw",
            "test_same_branch",
        )
        id_b = _seed_belief(
            self.writers,
            "same branch test belief beta unique xzqw",
            "test_same_branch",  # same branch
        )
        self._force_scan()
        edges = self.readers["beliefs"].read(
            "SELECT * FROM belief_edges WHERE edge_type = 'synthesises' "
            "AND ((source_id = ? AND target_id = ?) OR (source_id = ? AND target_id = ?))",
            (id_a, id_b, id_b, id_a),
        )
        self.assertEqual(len(edges), 0, "Same-branch pairs must not create synthesises edges")

    def test_low_similarity_cross_branch_not_detected(self):
        # Use a dedicated branch name to isolate from pre-seeded koan beliefs.
        # Check only the specific pair by ID, not total log count.
        id_a = _seed_belief(
            self.writers,
            "ancient Roman aqueducts supplied fresh water to cities via gravity",
            "test_roman",
        )
        id_b = _seed_belief(
            self.writers,
            "prime number factorization underlies modern asymmetric cryptography",
            "test_crypto",
        )
        self._force_scan()
        log_rows = self.readers["beliefs"].read(
            "SELECT * FROM novel_association_log "
            "WHERE (belief_id_a = ? AND belief_id_b = ?) "
            "OR (belief_id_a = ? AND belief_id_b = ?)",
            (id_a, id_b, id_b, id_a),
        )
        self.assertEqual(len(log_rows), 0,
            "Below-threshold pair must not produce log entry for our specific beliefs")

    def test_duplicate_pair_insert_ignore(self):
        _seed_belief(
            self.writers,
            "quantum entanglement enables instantaneous state correlation",
            "emerging_tech",
        )
        _seed_belief(
            self.writers,
            "quantum entanglement enables instantaneous state correlation across distance",
            "ai_research",
        )
        self._force_scan()
        first_count = len(self.readers["beliefs"].read(
            "SELECT * FROM novel_association_log", ()
        ))
        # Force a second scan — should not duplicate
        self.na._last_scan_at = 0.0
        self.na.tick()
        second_count = len(self.readers["beliefs"].read(
            "SELECT * FROM novel_association_log", ()
        ))
        self.assertEqual(first_count, second_count, "Duplicate pair must not create duplicate log entry")


# ── Interval gate ─────────────────────────────────────────────────────────────

class TestIntervalGate(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.na = _build_na(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_no_scan_before_interval(self):
        _seed_belief(self.writers, "belief alpha for interval test", "alpha_branch")
        _seed_belief(self.writers, "belief alpha for interval test variant", "beta_branch")
        # First tick — scans and sets _last_scan_at
        self.na._last_scan_at = 0.0
        self.na.tick()
        edges_after_first = len(self.readers["beliefs"].read(
            "SELECT * FROM belief_edges WHERE edge_type = 'synthesises'", ()
        ))
        # Second tick immediately — must not scan again
        self.na.tick()
        edges_after_second = len(self.readers["beliefs"].read(
            "SELECT * FROM belief_edges WHERE edge_type = 'synthesises'", ()
        ))
        self.assertEqual(edges_after_first, edges_after_second,
                         "tick() must not scan again before _LOOP_INTERVAL_S")

    def test_next_scan_in_positive_after_tick(self):
        self.na._last_scan_at = 0.0
        s = self.na.tick()
        self.assertGreater(s["next_scan_in"], 0)


# ── format_for_prompt ─────────────────────────────────────────────────────────

class TestFormatForPrompt(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.na = _build_na(self.writers, self.readers)
        # Seed two beliefs to get real IDs
        self.id_a = _seed_belief(self.writers, "belief a for prompt test", "branch_a")
        self.id_b = _seed_belief(self.writers, "belief b for prompt test", "branch_b")

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_empty_when_no_log_entries(self):
        text = self.na.format_for_prompt()
        self.assertEqual(text, "")

    def test_returns_text_when_unannotated_fresh_entry(self):
        _seed_log_entry(self.writers, self.id_a, self.id_b, "branch_a", "branch_b")
        text = self.na.format_for_prompt()
        self.assertNotEqual(text, "")
        self.assertIn("Self-observation", text)

    def test_text_contains_branch_names(self):
        _seed_log_entry(self.writers, self.id_a, self.id_b, "cognition_science", "crypto")
        text = self.na.format_for_prompt()
        self.assertIn("cognition_science", text)
        self.assertIn("crypto", text)

    def test_marks_annotated_after_surfacing(self):
        _seed_log_entry(self.writers, self.id_a, self.id_b, "branch_a", "branch_b")
        self.na.format_for_prompt()  # first call — returns text + marks annotated
        text2 = self.na.format_for_prompt()  # second call — must return empty
        self.assertEqual(text2, "", "Already-annotated entry must not be surfaced again")

    def test_skips_already_annotated_entry(self):
        _seed_log_entry(self.writers, self.id_a, self.id_b, "branch_a", "branch_b",
                        annotated_at=time.time())
        text = self.na.format_for_prompt()
        self.assertEqual(text, "", "Annotated entry must not be surfaced")

    def test_skips_entries_outside_lookback(self):
        from theory_x.stage10_imagination.novel_association import _ANNOTATION_LOOKBACK_S
        stale_ts = time.time() - _ANNOTATION_LOOKBACK_S - 10
        _seed_log_entry(self.writers, self.id_a, self.id_b, "branch_a", "branch_b",
                        detected_at=stale_ts)
        text = self.na.format_for_prompt()
        self.assertEqual(text, "", "Stale entry (outside lookback) must not be surfaced")


# ── Decay ─────────────────────────────────────────────────────────────────────

class TestDecay(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.na = _build_na(self.writers, self.readers)
        self.id_a = _seed_belief(self.writers, "belief a decay test", "branch_a")
        self.id_b = _seed_belief(self.writers, "belief b decay test", "branch_b")

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_decay_resolves_stale_entries(self):
        from theory_x.stage10_imagination.novel_association import _STALE_DAYS
        stale_ts = time.time() - _STALE_DAYS * 86400 - 1
        _seed_log_entry(self.writers, self.id_a, self.id_b, "branch_a", "branch_b",
                        detected_at=stale_ts)
        self.na.decay(time.time())
        rows = self.readers["beliefs"].read(
            "SELECT annotated_at FROM novel_association_log WHERE annotated_at IS NULL", ()
        )
        self.assertEqual(len(rows), 0, "Stale entries must be marked annotated by decay()")

    def test_decay_preserves_fresh_entries(self):
        _seed_log_entry(self.writers, self.id_a, self.id_b, "branch_a", "branch_b")
        self.na.decay(time.time())
        rows = self.readers["beliefs"].read(
            "SELECT annotated_at FROM novel_association_log WHERE annotated_at IS NULL", ()
        )
        self.assertEqual(len(rows), 1, "Fresh entries must survive decay()")


# ── Cross-restart persistence ─────────────────────────────────────────────────

class TestCrossRestartPersistence(unittest.TestCase):

    def test_log_entries_survive_new_instantiation(self):
        writers, readers, tmp = _make_env()
        try:
            id_a = _seed_belief(writers, "belief a persist test", "branch_a")
            id_b = _seed_belief(writers, "belief b persist test", "branch_b")
            _seed_log_entry(writers, id_a, id_b, "branch_a", "branch_b")

            # Simulate restart
            na2 = _build_na(writers, readers)
            text = na2.format_for_prompt()
            self.assertNotEqual(text, "",
                "novel_association_log entries must persist across NovelAssociation instantiation")
        finally:
            _cleanup(writers, tmp)


# ── start_loop smoke test ─────────────────────────────────────────────────────

class TestStartLoop(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.na = _build_na(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_start_loop_does_not_raise(self):
        self.na.start_loop()  # must not raise

    def test_loop_thread_is_daemon(self):
        before = {t.name for t in threading.enumerate()}
        self.na.start_loop()
        after = {t for t in threading.enumerate() if t.name not in before}
        loop_threads = [t for t in after if t.name == "novel_association_loop"]
        self.assertGreater(len(loop_threads), 0, "start_loop() must start a thread named novel_association_loop")
        self.assertTrue(loop_threads[0].daemon, "novel_association_loop thread must be a daemon")


if __name__ == "__main__":
    unittest.main()
