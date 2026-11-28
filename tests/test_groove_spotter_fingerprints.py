"""Characterize GrooveSpotter's process-local detector fingerprints.

These tests lock down the current source behaviour only. They do not select a
canonical groove-episode identity or change alert/Metacognition semantics.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from theory_x.diversity.groove import GrooveSpotter


class _Writer:
    def __init__(self):
        self.calls = []

    def write(self, sql, params=()):
        self.calls.append((sql, params))
        return len(self.calls)


class _Reader:
    def read(self, sql, params=()):
        return []


def _template_window():
    # Three distinct fires share at least three non-stopword bigrams.
    suffixes = ("north", "south", "east")
    return [
        {"id": i + 1, "content": f"amber river flows through quiet hills {suffix}"}
        for i, suffix in enumerate(suffixes)
    ]


def _centroid_windows():
    current = [
        {"id": i + 1, "content": f"current-{i}"}
        for i in range(5)
    ]
    previous = [
        {"id": i + 101, "content": f"previous-{i}"}
        for i in range(5)
    ]
    points = (
        (0.0, 0.0),
        (10.0, 0.0),
        (0.0, 10.0),
        (10.0, 10.0),
        (20.0, 20.0),
    )

    def fake_embed(content):
        if content.startswith("previous-"):
            return points[int(content.split("-")[1])]
        return (0.0, 0.0)

    return current, previous, fake_embed


class TestGrooveSpotterFingerprints(unittest.TestCase):
    def _spotter(self):
        return GrooveSpotter(_Writer(), _Reader())

    def _assert_same_instance_suppresses_and_new_instance_replays(
        self, detect, *args
    ):
        first_spotter = self._spotter()
        first = detect(first_spotter, *args)
        self.assertIsNotNone(first, "the first qualifying observation must emit")
        self.assertIsNone(
            detect(first_spotter, *args),
            "an unchanged observation must be suppressed by the same instance",
        )
        self.assertEqual(len(first_spotter._writer.calls), 1)

        restarted_spotter = self._spotter()
        replay = detect(restarted_spotter, *args)
        self.assertIsNotNone(
            replay,
            "a fresh instance starts without the process-local fingerprint",
        )
        self.assertEqual(len(restarted_spotter._writer.calls), 1)

    def test_ngram_fingerprint_suppresses_unchanged_scan_and_resets(self):
        window = [
            {
                "id": i,
                "content": f"amber river flows through quiet hills marker{i}",
            }
            for i in range(20)
        ]
        self._assert_same_instance_suppresses_and_new_instance_replays(
            lambda spotter, rows: spotter._check_ngrams(rows),
            window,
        )

        spotter = self._spotter()
        self.assertIsNotNone(spotter._check_ngrams(window))
        self.assertIsNone(spotter._check_ngrams([]))
        self.assertIsNotNone(
            spotter._check_ngrams(window),
            "the fingerprint must clear when no n-gram condition remains",
        )
        self.assertEqual(len(spotter._writer.calls), 2)

    def test_exact_fingerprint_suppresses_unchanged_scan_and_resets(self):
        repeated = [
            {"id": i, "content": "the same sentence appears in this window"}
            for i in range(3)
        ]
        self._assert_same_instance_suppresses_and_new_instance_replays(
            lambda spotter, rows: spotter._detect_exact_repetition(rows),
            repeated,
        )

        spotter = self._spotter()
        self.assertIsNotNone(spotter._detect_exact_repetition(repeated))
        self.assertIsNone(
            spotter._detect_exact_repetition(
                [
                    {"id": 10, "content": "first distinct sentence"},
                    {"id": 11, "content": "second distinct sentence"},
                    {"id": 12, "content": "third distinct sentence"},
                ]
            )
        )
        self.assertIsNotNone(
            spotter._detect_exact_repetition(repeated),
            "the exact-content fingerprint must clear when repetition ends",
        )
        self.assertEqual(len(spotter._writer.calls), 2)

    def test_template_fingerprint_suppresses_unchanged_fire_set_and_resets(self):
        window = _template_window()
        self._assert_same_instance_suppresses_and_new_instance_replays(
            lambda spotter, rows: spotter._detect_template_repetition(rows),
            window,
        )

        spotter = self._spotter()
        self.assertIsNotNone(spotter._detect_template_repetition(window))
        self.assertIsNone(spotter._detect_template_repetition([]))
        self.assertIsNotNone(
            spotter._detect_template_repetition(window),
            "the template fire-set fingerprint must clear when no shared pattern remains",
        )
        self.assertEqual(len(spotter._writer.calls), 2)

    def test_centroid_fingerprint_suppresses_unchanged_window_and_resets(self):
        current, previous, fake_embed = _centroid_windows()
        detect = lambda spotter, cur, prev: spotter._check_centroid_tightening(
            cur, prev
        )
        with patch("theory_x.diversity.groove.embed", side_effect=fake_embed):
            self._assert_same_instance_suppresses_and_new_instance_replays(
                detect, current, previous
            )

            spotter = self._spotter()
            self.assertIsNotNone(
                spotter._check_centroid_tightening(current, previous)
            )
            self.assertIsNone(
                spotter._check_centroid_tightening(current, []),
                "an unavailable previous window clears the centroid fingerprint",
            )
            self.assertIsNotNone(
                spotter._check_centroid_tightening(current, previous),
                "the same window can emit again after the condition resets",
            )
            self.assertEqual(len(spotter._writer.calls), 2)


if __name__ == "__main__":
    unittest.main()
