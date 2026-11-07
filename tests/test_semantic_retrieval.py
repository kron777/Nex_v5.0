"""BeliefRetriever semantic fallback (`NEX5_SEMANTIC_RETRIEVAL`), dark.

Catches beliefs relevant to the query but sharing zero literal tokens with
it -- invisible to the keyword loop by construction (`if overlap == 0:
continue`). Uses the real sentence-transformer model (cached after first
call) since the point is to prove the real model finds the signal.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

_FLAG = "NEX5_SEMANTIC_RETRIEVAL"


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_sem_ret_")
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


def _seed_belief(writers, content, tier=5, confidence=0.6, branch_id=None, source="test"):
    now = int(time.time())
    return writers["beliefs"].write(
        "INSERT INTO beliefs (content, tier, confidence, created_at, branch_id, source, locked, paused) "
        "VALUES (?, ?, ?, ?, ?, ?, 0, 0)",
        (content, tier, confidence, now, branch_id, source),
    )


def _make_retriever(readers):
    from theory_x.stage3_world_model.retrieval import BeliefRetriever
    return BeliefRetriever(readers["beliefs"])


# A query and a belief about the same thing, verified to share effectively
# no tokens (see test_sanity_zero_overlap below).
_QUERY = "Is the economy improving lately"
_SEMANTIC_MATCH = "Unemployment figures have been dropping steadily this quarter"
_UNRELATED = "My cat enjoys sleeping in the sun all afternoon"


def _clear_embedding_cache():
    # embed_belief() caches by belief id, process-wide. Across fresh test
    # DBs, small autoincrement ids get reused for different content, so a
    # stale cached embedding from an earlier test can leak in -- clear it,
    # a test-only concern (a live belief's content/id pairing doesn't churn
    # like this in production).
    from theory_x.diversity import embeddings as emb_mod
    emb_mod._cache.clear()


class TestFlagOff(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        os.environ.pop(_FLAG, None)
        _clear_embedding_cache()

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def test_sanity_zero_overlap(self):
        from theory_x.stage3_world_model.retrieval import _tokenize
        q = _tokenize(_QUERY)
        b = _tokenize(_SEMANTIC_MATCH)
        self.assertEqual(q & b, set(), "sanity: query and belief must share no tokens")

    def test_zero_overlap_belief_not_retrieved(self):
        _seed_belief(self.writers, _SEMANTIC_MATCH)
        r = _make_retriever(self.readers)
        results = r.retrieve(_QUERY, limit=10)
        self.assertEqual(results, [], "flag off: zero-overlap belief must not surface")

    def test_semantic_fallback_scores_returns_empty(self):
        from theory_x.stage3_world_model.retrieval import _semantic_fallback_scores
        row = {"id": 1, "content": _SEMANTIC_MATCH}
        self.assertEqual(_semantic_fallback_scores(_QUERY, [row]), {})


class TestFlagOn(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        os.environ[_FLAG] = "1"
        _clear_embedding_cache()

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def test_semantically_relevant_zero_overlap_belief_is_retrieved(self):
        bid = _seed_belief(self.writers, _SEMANTIC_MATCH)
        r = _make_retriever(self.readers)
        results = r.retrieve(_QUERY, limit=10)
        ids = [b["id"] for b in results]
        self.assertIn(bid, ids, "semantically relevant, keyword-disjoint belief must surface")

    def test_unrelated_zero_overlap_belief_not_retrieved(self):
        bid = _seed_belief(self.writers, _UNRELATED)
        r = _make_retriever(self.readers)
        results = r.retrieve(_QUERY, limit=10)
        self.assertNotIn(bid, [b["id"] for b in results],
                          "unrelated belief must not surface via semantic fallback")

    def test_keyword_match_never_overridden_by_semantic_score(self):
        """A belief that already matched by keyword keeps its keyword-path
        score (undiscounted) and ranks above any semantic-only hit."""
        from theory_x.stage3_world_model.retrieval import _tokenize
        keyword_belief = "The economy is doing very well this year"
        self.assertTrue(_tokenize(_QUERY) & _tokenize(keyword_belief),
                         "sanity: this belief must share tokens with the query")
        bid = _seed_belief(self.writers, keyword_belief, confidence=0.3)
        r = _make_retriever(self.readers)
        results = r.retrieve(_QUERY, limit=10)
        ids = [b["id"] for b in results]
        self.assertIn(bid, ids)
        self.assertEqual(ids[0], bid, "the keyword match must rank first")

    def test_pool_cap_respected(self):
        """Semantic embedding is never attempted on more zero-overlap
        candidates than _SEMANTIC_RETRIEVAL_POOL allows, however many
        exist (init_all()'s own keystone seeding contributes a baseline
        set of its own, on top of whatever this test seeds)."""
        from theory_x.stage3_world_model import retrieval as rmod
        calls = {"n": 0}
        orig = rmod._semantic_fallback_scores

        def spy(query, candidates):
            calls["n"] = len(candidates)
            return orig(query, candidates)

        rmod._semantic_fallback_scores = spy
        try:
            for i in range(5):
                _seed_belief(self.writers, f"{_UNRELATED} variant {i}")
            r = _make_retriever(self.readers)
            r.retrieve(_QUERY, limit=10)
            self.assertGreaterEqual(calls["n"], 5)
            self.assertLessEqual(calls["n"], rmod._SEMANTIC_RETRIEVAL_POOL)
        finally:
            rmod._semantic_fallback_scores = orig

    def test_pool_cap_actually_truncates_when_exceeded(self):
        """With more zero-overlap candidates than the cap, the candidate
        list passed to the scorer is truncated, not grown unbounded."""
        from theory_x.stage3_world_model import retrieval as rmod
        from unittest import mock
        with mock.patch.object(rmod, "_SEMANTIC_RETRIEVAL_POOL", 3):
            calls = {"n": None}
            orig = rmod._semantic_fallback_scores

            def spy(query, candidates):
                calls["n"] = len(candidates)
                return orig(query, candidates)

            with mock.patch.object(rmod, "_semantic_fallback_scores", spy):
                for i in range(10):
                    _seed_belief(self.writers, f"{_UNRELATED} variant {i}")
                r = _make_retriever(self.readers)
                r.retrieve(_QUERY, limit=10)
            self.assertEqual(calls["n"], 3)


if __name__ == "__main__":
    unittest.main()
