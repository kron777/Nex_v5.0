"""Tests for phrase-aware extraction (44a85dc) + context-carry (6ef84ac).

Both fixes live in theory_x.signals.detectors.CoOccurrenceDetector. We drive the
detector end-to-end against isolated tempdir DBs (never the live soak DBs) and
assert on the emitted Signal:

- a contiguous run of capitalized words is ONE entity ("Large Hadron Collider"),
  not three orphans
- a genuine single-word name still comes through (run length 1)
- EDGE stopwords are trimmed ("The ...", "With ..."); internal title-case words kept
- each token carries the sentence SPAN it came from (context), not a bare word
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest

from tests import _bootstrap  # noqa: F401


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_extract_")
    os.environ["NEX5_DATA_DIR"] = tmp
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


class TestPhraseAwareExtraction(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _insert(self, content, branch, offset_sec=60):
        self.writers["beliefs"].write(
            "INSERT INTO beliefs (content, tier, confidence, created_at, "
            "source, branch_id) VALUES (?, 1, 0.5, ?, 'test', ?)",
            (content, time.time() - offset_sec, branch),
        )

    def _detect(self):
        from theory_x.signals.detectors import CoOccurrenceDetector
        det = CoOccurrenceDetector(self.readers["beliefs"], min_branches=2)
        return det.detect()

    def _entities(self, signals):
        out = set()
        for s in signals:
            out.update(s.entities)
        return out

    def test_contiguous_caps_is_one_entity(self):
        self._insert("The Large Hadron Collider announced results.", "physics")
        self._insert("Everyone talked about Large Hadron Collider today.", "emerging_tech")
        ents = self._entities(self._detect())
        self.assertIn("Large Hadron Collider", ents)
        # not fragmented into orphan tokens
        self.assertNotIn("Large", ents)
        self.assertNotIn("Collider", ents)

    def test_single_word_name_still_passes(self):
        self._insert("Bitcoin surged again overnight.", "crypto")
        self._insert("Bitcoin is volatile lately.", "markets")
        self.assertIn("Bitcoin", self._entities(self._detect()))

    def test_leading_stopword_trimmed(self):
        # "The" is an edge stopword; the tracked entity is the name after it
        self._insert("The Ethereum upgrade shipped.", "crypto")
        self._insert("With Ethereum rising, fees climbed.", "markets")
        ents = self._entities(self._detect())
        self.assertIn("Ethereum", ents)
        self.assertNotIn("The Ethereum", ents)
        self.assertNotIn("With Ethereum", ents)

    def test_internal_titlecase_word_kept(self):
        # lowercase neighbours on both sides so each run is exactly the title —
        # a capitalized neighbour would merge into the run and split the entity
        self._insert("My reading of War And Peace endures.", "literature")
        self._insert("The themes of War And Peace resonate.", "philosophy")
        # internal function word ("And") is preserved, only edges trim
        self.assertIn("War And Peace", self._entities(self._detect()))

    def test_context_span_carried_not_bare_word(self):
        self._insert("The Large Hadron Collider announced results.", "physics")
        self._insert("Everyone talked about Large Hadron Collider today.", "emerging_tech")
        sig = next(s for s in self._detect() if "Large Hadron Collider" in s.entities)
        ctx = sig.payload.get("context", "")
        # the representative context is a sentence span, not the orphaned token
        self.assertIn("Large Hadron Collider", ctx)
        self.assertGreater(len(ctx), len("Large Hadron Collider"))
        # contexts list carries branch-tagged spans
        contexts = sig.payload.get("contexts", [])
        self.assertTrue(contexts)
        self.assertIn("branch", contexts[0])
        self.assertIn("span", contexts[0])


if __name__ == "__main__":
    unittest.main()
