"""Tests for theory_x.stage3_world_model.attribution_marker (fix #1b / #1A core).

Covers the primitives the synergizer and crystallizer both build on:
- detect_attribution: named source, generic hedge, "per day" noise, empty/bad input
- contested_snippet: stored marker wins over content; non-dict -> None
- stamp_tags / marker_in_tags: round-trip and idempotency (no accretion)
- surface_in_content: named -> "(per <Name>)", generic hedge -> "(per its source)",
  idempotent (no double-stamp), empty/bad input passthrough

Pure-logic module (no DB), but we still isolate NEX5_DATA_DIR to a tempdir so an
accidental import-time DB touch can never reach the live soak DBs.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest

from tests import _bootstrap  # noqa: F401

_TMP = tempfile.mkdtemp(prefix="nex5_attrib_marker_")
os.environ["NEX5_DATA_DIR"] = _TMP

from theory_x.stage3_world_model.attribution_marker import (  # noqa: E402
    detect_attribution,
    contested_snippet,
    stamp_tags,
    marker_in_tags,
    surface_in_content,
    _MARKER_PREFIX,
)


def tearDownModule():
    shutil.rmtree(_TMP, ignore_errors=True)
    os.environ.pop("NEX5_DATA_DIR", None)


class TestDetectAttribution(unittest.TestCase):

    def test_named_source_via_per(self):
        # explicit connector + capitalized name -> the name (name mid-sentence so
        # the source-name char class doesn't greedily swallow a trailing period)
        self.assertEqual(detect_attribution("The result per CERN was null."), "CERN")

    def test_named_source_trailing_period_is_kept(self):
        # documents real behavior: at sentence end the '.' is inside the name
        # char class, so it rides along (callers strip whitespace, not periods)
        self.assertEqual(detect_attribution("Found nothing per CERN."), "CERN.")

    def test_named_source_via_according_to(self):
        self.assertEqual(
            detect_attribution("According to Reuters, the market fell sharply."),
            "Reuters",
        )

    def test_named_source_multiword(self):
        self.assertEqual(
            detect_attribution("This was reported per Hacker News this morning."),
            "Hacker News",
        )

    def test_generic_hedge_no_name(self):
        # a hedge phrase with no capitalized source -> a short snippet, not None
        snip = detect_attribution("Reportedly the outage lasted an hour.")
        self.assertIsNotNone(snip)
        self.assertIn("reportedly", snip.lower())

    def test_this_item_states_hedge(self):
        snip = detect_attribution("This item states the launch is delayed.")
        self.assertIsNotNone(snip)
        self.assertIn("this item states", snip.lower())

    def test_per_day_is_not_a_source(self):
        # "per <lowercase>" must not fabricate a source (the classic noise case)
        self.assertIsNone(detect_attribution("It rained three times per day."))

    def test_plain_claim_none(self):
        self.assertIsNone(detect_attribution("Attention collapses possible futures."))

    def test_empty_and_none(self):
        self.assertIsNone(detect_attribution(""))
        self.assertIsNone(detect_attribution(None))


class TestContestedSnippet(unittest.TestCase):

    def test_stored_marker_wins_even_if_content_bare(self):
        belief = {"content": "A bare settled claim.", "tags": '["attribution:CERN"]'}
        self.assertEqual(contested_snippet(belief), "CERN")

    def test_falls_back_to_content_hedge(self):
        belief = {"content": "According to Reuters, prices rose.", "tags": "[]"}
        self.assertEqual(contested_snippet(belief), "Reuters")

    def test_clean_belief_none(self):
        belief = {"content": "A plain observation.", "tags": "[]"}
        self.assertIsNone(contested_snippet(belief))

    def test_non_dict_input_none(self):
        self.assertIsNone(contested_snippet("not a dict"))
        self.assertIsNone(contested_snippet(None))


class TestStampAndReadRoundTrip(unittest.TestCase):

    def test_round_trip(self):
        tags = stamp_tags(None, "CERN")
        self.assertEqual(marker_in_tags(tags), "CERN")

    def test_preserves_existing_tags(self):
        tags = stamp_tags('["topic:physics"]', "CERN")
        self.assertEqual(marker_in_tags(tags), "CERN")
        self.assertIn("topic:physics", tags)

    def test_idempotent_no_duplicate_marker(self):
        once = stamp_tags(None, "CERN")
        twice = stamp_tags(once, "CERN")
        markers = [t for t in __import__("json").loads(twice) if t.startswith(_MARKER_PREFIX)]
        self.assertEqual(len(markers), 1)

    def test_marker_in_tags_accepts_list(self):
        self.assertEqual(marker_in_tags(["attribution:Reuters"]), "Reuters")

    def test_marker_in_tags_none_when_absent(self):
        self.assertIsNone(marker_in_tags('["topic:physics"]'))
        self.assertIsNone(marker_in_tags("[]"))
        self.assertIsNone(marker_in_tags(""))


class TestSurfaceInContent(unittest.TestCase):

    def test_named_source_clause(self):
        out = surface_in_content("The collider found nothing", "CERN")
        self.assertTrue(out.endswith("(per CERN)."), out)

    def test_generic_hedge_becomes_per_its_source(self):
        # a hedge-phrase snippet must not be fabricated into a named citation
        out = surface_in_content("The outage lasted an hour", "reportedly the outage")
        self.assertTrue(out.endswith("(per its source)."), out)

    def test_idempotent_when_already_per_clause(self):
        already = "The collider found nothing (per CERN)."
        self.assertEqual(surface_in_content(already, "Reuters"), already)

    def test_idempotent_when_content_already_attributed(self):
        already = "According to Reuters, prices rose."
        self.assertEqual(surface_in_content(already, "CERN"), already)

    def test_no_accretion_across_generations(self):
        first = surface_in_content("A raw claim", "CERN")
        second = surface_in_content(first, "CERN")
        self.assertEqual(first, second)
        self.assertEqual(second.count("(per "), 1)

    def test_empty_inputs_passthrough(self):
        self.assertEqual(surface_in_content("", "CERN"), "")
        self.assertEqual(surface_in_content("A claim", ""), "A claim")
        self.assertEqual(surface_in_content("A claim", None), "A claim")


if __name__ == "__main__":
    unittest.main()
