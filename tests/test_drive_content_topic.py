"""Tests for content-aware drive topic synthesis (NEX5_DRIVE_CONTENT).

drive_emergence used to build a drive's topic from confidence-weighted raw term
frequency, so her standing register/frame vocabulary ('item', 'aligns',
'discusses') led every topic — the live failure was a drive labelled "clear
impactful messages item aligns". The fix weights each token by inverse document
frequency over her own generated voice, so register self-demotes without a
maintained stopword list.

These test the two guard cases the task requires:
  * content-heavy substrate -> a genuine CONTENT topic
  * register-heavy substrate -> NOT a register-only topic (the live failure)
plus the fail-safe fallback to plain frequency synthesis.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from collections import Counter

from tests import _bootstrap  # noqa: F401

from theory_x.stage_drives.drive_emergence import (
    _synthesize_topic, _synthesize_topic_content,
)


def _cluster(*contents, conf=0.8):
    return [{"content": c, "confidence": conf, "branch_id": f"b{i}"}
            for i, c in enumerate(contents)]


class TestContentTopicSynthesis(unittest.TestCase):

    # corpus DF over her own voice: frame words very common, content words rare
    _DF = Counter({
        "item": 1800, "aligns": 1100, "discusses": 800, "highlights": 700,
        "understanding": 900, "systems": 700, "about": 1500, "well": 900,
        "clear": 220, "messages": 60,
        # content
        "melatonin": 4, "cognition": 90, "impairs": 25, "morning": 40,
        "collider": 6, "quantum": 8, "entanglement": 3,
    })
    _N = 2000

    def test_register_heavy_cluster_leads_with_content(self):
        # frame words dominate FREQUENCY; one content word ('melatonin') present.
        cl = _cluster(
            "This item aligns with clear messages about melatonin",
            "The item discusses melatonin and aligns with prior work",
            "This item highlights melatonin research; aligns well",
            "Item aligns about how melatonin impairs morning cognition",
        )
        plain = _synthesize_topic(cl)
        content = _synthesize_topic_content(cl, self._DF, self._N)
        # plain synthesis leads with the frame word (the bug)
        self.assertTrue(plain.startswith("item"))
        # content synthesis leads with the genuine content, and drops 'item'
        self.assertTrue(content.startswith("melatonin"), content)
        self.assertNotIn("item", content.split())

    def test_content_heavy_cluster_stays_content(self):
        cl = _cluster(
            "Quantum entanglement at the collider surprised the team",
            "The collider results on entanglement look robust",
            "Quantum entanglement collider data, clearly stated",
        )
        content = _synthesize_topic_content(cl, self._DF, self._N)
        toks = content.split()
        # the rare content words lead; no frame word sneaks to the front
        self.assertIn(toks[0], {"entanglement", "quantum", "collider"})

    def test_register_only_cluster_not_a_register_topic(self):
        # a cluster that is PURELY narration scaffold -> IDF flattens them all;
        # whatever leads, it must not be dominated by the highest-DF frame words
        cl = _cluster(
            "This item aligns and discusses the systems",
            "The item highlights understanding and aligns with systems",
            "Item discusses systems; aligns about understanding well",
        )
        content = _synthesize_topic_content(cl, self._DF, self._N)
        # the two highest-DF tokens ('item' 1800, 'about' 1500) must be demoted
        # out of the lead position — the whole point of IDF
        self.assertNotEqual(content.split()[0], "item")
        self.assertNotEqual(content.split()[0], "about")

    # --- fail-safe fallbacks ---
    def test_thin_corpus_falls_back_to_plain(self):
        cl = _cluster("melatonin impairs morning cognition badly",
                      "melatonin and morning cognition again")
        self.assertEqual(_synthesize_topic_content(cl, self._DF, 10),
                         _synthesize_topic(cl))
        self.assertEqual(_synthesize_topic_content(cl, Counter(), self._N),
                         _synthesize_topic(cl))

    def test_own_voice_df_builds_and_guards(self):
        # _own_voice_df over an isolated tempdir: builds DF, guards thin corpus
        tmp = tempfile.mkdtemp(prefix="nex5_dvdf_")
        os.environ["NEX5_DATA_DIR"] = tmp
        try:
            from substrate.init_db import init_all
            init_all()
            from substrate import Reader, Writer, db_paths
            w = Writer(db_paths()["beliefs"], name="beliefs")
            from theory_x.stage_drives.drive_emergence import DriveEmergence
            de = DriveEmergence.__new__(DriveEmergence)
            de._br = Reader(db_paths()["beliefs"])
            # thin corpus -> (None, 0)
            df, n = de._own_voice_df()
            self.assertIsNone(df)
            # populate >=50 own-voice docs
            for i in range(60):
                w.write("INSERT INTO beliefs (content, tier, confidence, created_at, source, branch_id, locked) "
                        "VALUES (?, 6, 0.6, ?, 'fountain_insight', 'x', 0)",
                        (f"melatonin cognition note number {i} about systems", time.time() - i))
                time.sleep(0.003)
            df, n = de._own_voice_df()
            self.assertIsNotNone(df)
            self.assertGreaterEqual(n, 50)
            self.assertGreater(df.get("melatonin", 0), 0)
            w.close()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
            os.environ.pop("NEX5_DATA_DIR", None)


if __name__ == "__main__":
    unittest.main()
