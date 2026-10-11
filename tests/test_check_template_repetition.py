"""The template-repetition harness measures near-duplicate structure correctly.

Seeds fountain_insight outputs with controlled duplication (distinct content,
shared first sentence — orphan beliefs are content-unique, so content differs)
and checks the harness's metrics and its baseline verdict.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from tests._bootstrap import *  # noqa: F401, F403


class TestTemplateRepetitionHarness(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nex5_trh_")
        os.environ["NEX5_DATA_DIR"] = self.tmp
        from substrate.init_db import init_all
        init_all()
        from substrate import Writer, db_paths
        self.bw = Writer(str(db_paths()["beliefs"]), name="beliefs")

    def tearDown(self):
        try:
            self.bw.close()
        except Exception:
            pass
        os.environ.pop("NEX5_DATA_DIR", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _seed(self, content, ts):
        self.bw.write(
            "INSERT INTO beliefs (content, tier, confidence, created_at, source, branch_id) "
            "VALUES (?, 6, 0.7, ?, 'fountain_insight', 'systems')",
            (content, int(ts)),
        )

    def test_metrics_on_controlled_corpus(self):
        same = "The hum of the server fills the room while fingers move"
        now = int(time.time())
        # order: dup, dup, distinct, dup, distinct, dup
        corpus = [
            f"{same}. Alpha one.",
            f"{same}. Beta two.",
            "A completely different thought about bitcoin markets moving today.",
            f"{same}. Gamma three.",
            "Another distinct idea about neural attention patterns over here.",
            f"{same}. Delta four.",
        ]
        for i, c in enumerate(corpus):
            self._seed(c, now - (len(corpus) - i) * 60)  # increasing created_at
        self.bw.close()  # flush before the read-only measure

        from tools.check_template_repetition import measure
        m = measure(window=50, threshold=0.5)

        self.assertEqual(m["n_outputs"], 6)
        # 5 consecutive pairs; only (Alpha,Beta) share a first sentence -> 1/5.
        self.assertAlmostEqual(m["consecutive_duplicate_rate"], 0.2, places=3)
        # the four "same"-first-sentence outputs form one cluster.
        self.assertEqual(m["largest_cluster_size"], 4)

    def test_baseline_verdict_flags_regression(self):
        from tools.check_template_repetition import _verdict
        base = {"consecutive_duplicate_rate": 0.20, "largest_cluster_fraction": 0.30}
        improved = {"consecutive_duplicate_rate": 0.10, "largest_cluster_fraction": 0.20}
        worse = {"consecutive_duplicate_rate": 0.60, "largest_cluster_fraction": 0.70}
        ok_i, _ = _verdict(improved, base, tol=0.25)
        ok_w, _ = _verdict(worse, base, tol=0.25)
        self.assertTrue(ok_i)
        self.assertFalse(ok_w)

    def test_empty_corpus_is_safe(self):
        from tools.check_template_repetition import measure
        m = measure(window=50, threshold=0.5)
        self.assertEqual(m["n_outputs"], 0)
        self.assertEqual(m["consecutive_duplicate_rate"], 0.0)
        self.assertEqual(m["largest_cluster_size"], 0)


if __name__ == "__main__":
    unittest.main()
