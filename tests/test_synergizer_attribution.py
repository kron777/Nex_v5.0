"""Tests for the synergizer structural attribution guard (fix #1b, 2f5866e).

A synthesis of contested/attributed lineage must not silently flatten into bare
settled fact: if either parent entered hedged/sourced (or already carries the
marker), the child belief is re-stamped in code (attribution:* tag) and its
content surfaces "(per ...)".

Driven end-to-end through BeliefSynergizer.synthesize() with a mocked voice
client (clean LLM text), against isolated tempdir DBs — never the live soak DBs.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from tests import _bootstrap  # noqa: F401

_LLM_TEXT = "A bridge exists between attention and entropy"


def _relax_beliefs_tags(db_path):
    """Isolated-tempdir only: drop the NOT NULL on beliefs.tags so an untouched
    synthesis (tags=None) can land and be inspected. The live DB predates this
    constraint (0/66k NULLs; the pre-fix INSERT omitted the column, taking the
    '[]' DEFAULT), so this restores production's effective semantics. Never runs
    against a live DB — db_path is always a fresh mkdtemp path here."""
    con = sqlite3.connect(str(db_path))
    try:
        con.execute("PRAGMA writable_schema=ON")
        con.execute(
            "UPDATE sqlite_master SET sql="
            "REPLACE(sql,'tags TEXT NOT NULL DEFAULT','tags TEXT DEFAULT') "
            "WHERE type='table' AND name='beliefs'"
        )
        con.execute("PRAGMA writable_schema=OFF")
        con.commit()
    finally:
        con.close()


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_syn_attrib_")
    os.environ["NEX5_DATA_DIR"] = tmp
    os.environ["NEX5_ADMIN_HASH_FILE"] = str(Path(tmp) / "admin.argon2")
    from substrate.init_db import init_all
    init_all()
    from substrate import Reader, Writer, db_paths
    paths = db_paths()
    _relax_beliefs_tags(paths["beliefs"])  # before Writers open their connections
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


def _make_synergizer(writers, readers, llm_text=_LLM_TEXT):
    from theory_x.stage3_world_model.synergizer import BeliefSynergizer
    mock_voice = MagicMock()
    resp = MagicMock()
    resp.text = llm_text
    mock_voice.speak.return_value = resp
    return BeliefSynergizer(
        beliefs_writer=writers["beliefs"],
        beliefs_reader=readers["beliefs"],
        voice_client=mock_voice,
    )


class TestSynergizerAttribution(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _synergizer_forcing_pair(self, content_a, content_b):
        # init_all seeds 76 beliefs (koans etc.), so _select_pair is
        # non-deterministic against ad-hoc seeds. Force the exact parents so the
        # attribution guard is tested in isolation. Parents are dict-like rows
        # carrying the fields synthesize() reads: id, content, branch_id, tags.
        s = _make_synergizer(self.writers, self.readers)
        pair = (
            {"id": 1, "content": content_a, "branch_id": "crypto", "tags": "[]"},
            {"id": 2, "content": content_b, "branch_id": "ai_research", "tags": "[]"},
        )
        s._select_pair = lambda: pair
        return s

    def _synergized_child(self):
        from theory_x.stage3_world_model.attribution_marker import marker_in_tags
        rows = self.readers["beliefs"].read(
            "SELECT content, tags FROM beliefs WHERE source = 'synergized'"
        )
        self.assertEqual(len(rows), 1, "expected exactly one synergized child")
        return rows[0], marker_in_tags(rows[0]["tags"])

    def test_contested_parent_child_tagged_and_surfaced(self):
        # one parent entered sourced ("according to Reuters"); child must retain it
        s = self._synergizer_forcing_pair(
            "According to Reuters, attention is selective.",
            "Systems decay without fresh input.",
        )
        result = s.synthesize()
        self.assertIsNotNone(result)
        time.sleep(0.05)
        row, marker = self._synergized_child()
        self.assertEqual(marker, "Reuters")
        self.assertIn("(per Reuters)", row["content"])

    def test_clean_parents_left_untouched(self):
        s = self._synergizer_forcing_pair(
            "Attention is selective.",
            "Systems decay without fresh input.",
        )
        result = s.synthesize()
        self.assertIsNotNone(result)
        time.sleep(0.05)
        row, marker = self._synergized_child()
        self.assertIsNone(marker)
        self.assertNotIn("(per ", row["content"])
        self.assertEqual(row["content"], _LLM_TEXT)


if __name__ == "__main__":
    unittest.main()
