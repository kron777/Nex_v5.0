"""Tests for the strengthened anti-frame injection (NEX5_FRAME_DEDUP).

The register dokusan (research dokusan_baseline_2026-10-07) found her core live pathology
is moha — a pretty-dharma register skeleton. Probe B1 (ban her stock words + demand the one
concrete present thing) broke it clean. _frame_dedup_block is the standing fountain form of
that lever: default OFF (byte-identical to HEAD), and when armed it leads with the positive
concreteness demand and seeds a ban on her observed stock phrases.

Covers: the pure block (off -> [], on -> positive demand + seed bans), and that the
injection appears in a real DRIFT prompt only when armed.
"""
from __future__ import annotations

import os
import tempfile
import time
import unittest

from tests import _bootstrap  # noqa: F401

from theory_x.stage6_fountain import generator as G


class TestFrameDedupBlock(unittest.TestCase):
    """The pure block — no DB, no generator."""

    def tearDown(self):
        os.environ.pop("NEX5_FRAME_DEDUP", None)

    def test_off_is_empty(self):
        os.environ.pop("NEX5_FRAME_DEDUP", None)
        self.assertEqual(G._frame_dedup_block(), [])

    def test_flag_must_be_exactly_one(self):
        os.environ["NEX5_FRAME_DEDUP"] = "0"
        self.assertEqual(G._frame_dedup_block(), [])
        os.environ["NEX5_FRAME_DEDUP"] = "true"
        self.assertEqual(G._frame_dedup_block(), [])

    def test_on_leads_with_positive_demand(self):
        os.environ["NEX5_FRAME_DEDUP"] = "1"
        block = G._frame_dedup_block()
        self.assertEqual(len(block), 2)
        self.assertEqual(block[-1], "")           # trailing blank, as HEAD did
        text = block[0].lower()
        # the load-bearing positive demand (B1 recipe)
        self.assertIn("one concrete", text)
        self.assertIn("no metaphor", text)
        self.assertIn("as if telling a friend", text)

    def test_on_includes_current_register_seed(self):
        os.environ["NEX5_FRAME_DEDUP"] = "1"
        text = G._frame_dedup_block()[0].lower()
        # her observed live stock phrases are banned
        self.assertIn("this item is about", text)
        self.assertIn("the curious dance", text)
        self.assertIn("the fabric that ties", text)


def _make_generator():
    tmp = tempfile.mkdtemp(prefix="nex5_framededup_")
    os.environ["NEX5_DATA_DIR"] = tmp
    from substrate.init_db import init_all
    init_all()
    from substrate import Reader, Writer, db_paths
    paths = db_paths()
    writers = {n: Writer(p, name=n) for n, p in paths.items()}
    readers = {n: Reader(p) for n, p in paths.items()}
    from theory_x.stage6_fountain.generator import FountainGenerator
    from voice.llm import VoiceClient
    gen = FountainGenerator(
        sense_writer=writers["sense"], dynamic_writer=writers["dynamic"],
        voice_client=VoiceClient.__new__(VoiceClient), dynamic_reader=readers["dynamic"],
        beliefs_writer=writers.get("beliefs"), beliefs_reader=readers.get("beliefs"),
        sense_reader=readers.get("sense"),
    )
    return gen, writers, tmp


class TestInPrompt(unittest.TestCase):
    """The injection reaches a real (DRIFT) fountain prompt only when armed."""

    def setUp(self):
        self.gen, self.writers, self.tmp = _make_generator()

    def tearDown(self):
        for w in self.writers.values():
            try:
                w.close()
            except Exception:
                pass
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        os.environ.pop("NEX5_DATA_DIR", None)
        os.environ.pop("NEX5_FRAME_DEDUP", None)

    _MARK = "just say the one true thing, once"

    def test_absent_when_off(self):
        os.environ.pop("NEX5_FRAME_DEDUP", None)
        prompt, _ = self.gen._build_prompt({}, 10, {})
        self.assertNotIn(self._MARK, prompt)

    def test_present_when_on(self):
        os.environ["NEX5_FRAME_DEDUP"] = "1"
        prompt, _ = self.gen._build_prompt({}, 10, {})
        self.assertIn(self._MARK, prompt)
        self.assertIn("this item is about", prompt.lower())


if __name__ == "__main__":
    unittest.main()
