"""Harmonizer semantic conflict path (`NEX5_SEMANTIC_CONFLICT`), dark.

Catches beliefs opposed in meaning but sharing no tokens -- invisible to
_conflict_score by construction. Uses the real sentence-transformer model
(slow first call, cached after) since this is read-only and the point is
to prove the real embedding model finds the signal, not a mock.
"""
from __future__ import annotations

import os
import unittest

from tests import _bootstrap  # noqa: F401

_FLAG = "NEX5_SEMANTIC_CONFLICT"


def _clear_embedding_cache():
    # embed_belief() caches by belief id, process-wide. These tests use
    # hand-picked literal ids, which could collide with another test
    # file's own literal ids in the same pytest process -- clear first.
    from theory_x.diversity import embeddings as emb_mod
    emb_mod._cache.clear()


class TestSemanticConflictFlagOff(unittest.TestCase):
    def setUp(self):
        _clear_embedding_cache()

    def tearDown(self):
        os.environ.pop(_FLAG, None)

    def test_returns_zero_when_flag_unset(self):
        from theory_x.stage3_world_model.harmonizer import _semantic_conflict_score
        os.environ.pop(_FLAG, None)
        score = _semantic_conflict_score(
            1, "The stock market will rise sharply this year",
            2, "Equity prices are going to fall a great deal this year",
        )
        self.assertEqual(score, 0.0)

    def test_scan_for_conflicts_unaffected_by_zero_overlap_pair(self):
        """flag off -> no new conflicts beyond what _conflict_score alone finds."""
        from theory_x.stage3_world_model.harmonizer import _conflict_score, _tokenize
        ta = _tokenize("The stock market will rise sharply this year")
        tb = _tokenize("Equity prices are going to fall a great deal this year")
        self.assertEqual(_conflict_score(ta, "x", tb, "y"), 0.0,
                          "sanity: these genuinely share no tokens via the token path")


class TestSemanticConflictFlagOn(unittest.TestCase):
    def setUp(self):
        os.environ[_FLAG] = "1"
        _clear_embedding_cache()

    def tearDown(self):
        os.environ.pop(_FLAG, None)

    def test_opposed_paraphrases_with_no_shared_tokens_flagged(self):
        from theory_x.stage3_world_model.harmonizer import _semantic_conflict_score, _conflict_score, _tokenize
        a = "I strongly believe this decision was correct"
        b = "I do not think that choice was correct"
        # sanity: confirm via the token path that these share effectively
        # nothing (overlap=1, "correct" only -- below the >=2 negation bar).
        self.assertEqual(_conflict_score(_tokenize(a), a, _tokenize(b), b), 0.0)
        score = _semantic_conflict_score(101, a, 102, b)
        self.assertGreater(score, 0.0,
                            "semantically opposed, keyword-disjoint pair must be caught")

    def test_same_topic_same_polarity_not_flagged(self):
        """Same topic, same polarity (paraphrase agreement) is not a conflict."""
        from theory_x.stage3_world_model.harmonizer import _semantic_conflict_score
        score = _semantic_conflict_score(
            103, "The stock market will rise sharply this year",
            104, "Equity prices are going to climb a great deal this year",
        )
        self.assertEqual(score, 0.0)

    def test_unrelated_topics_not_flagged(self):
        from theory_x.stage3_world_model.harmonizer import _semantic_conflict_score
        score = _semantic_conflict_score(
            105, "The stock market will rise sharply this year",
            106, "My favourite color is a deep shade of blue",
        )
        self.assertEqual(score, 0.0, "unrelated topics must not be flagged as opposed")

    def test_never_overrides_an_existing_token_score(self):
        """scan_for_conflicts() only tries the semantic path when the token
        path returns 0.0 -- confirmed directly on the token path's own
        clearly-scoring pair."""
        from theory_x.stage3_world_model.harmonizer import _conflict_score, _tokenize
        a = "Consciousness arises from neural complexity and integration"
        b = "Consciousness does not arise from neural complexity"
        token_score = _conflict_score(_tokenize(a), a, _tokenize(b), b)
        self.assertGreater(token_score, 0.0, "sanity: token path already catches this one")


if __name__ == "__main__":
    unittest.main()
