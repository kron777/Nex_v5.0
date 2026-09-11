"""Tests for the crystallizer structural attribution marker (fix #1A, f517455).

GATED default-OFF via NEX5_ATTRIB_CRYSTALLIZE. A wide-mode fire that engaged a
specific external feed item (focal_item present) but emitted the claim BARE gets
a structured marker (attribution:<focal snippet>) and an honest "(per a feed
item)" clause. Fires that bind no focal_item (DRIFT/substrate) are never touched.

Driven through FountainCrystallizer.crystallize() against isolated tempdir DBs —
never the live soak DBs. The env flag is set on the TEST process only; the live
soak (its own pid) is unaffected.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

_FLAG = "NEX5_ATTRIB_CRYSTALLIZE"
# a quality-passing thought: self-reference + anchor + engagement, bare (no source)
_THOUGHT = "I notice a pull toward complexity that I cannot fully name"


def _make_env():
    # No schema relax: beliefs.tags is NOT NULL in production, and the fix makes
    # the untouched paths write '[]' (the column DEFAULT), never None. These
    # tests run against the real fresh schema to prove that.
    tmp = tempfile.mkdtemp(prefix="nex5_crystal_attrib_")
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


def _make_crystallizer(writers, readers):
    from theory_x.stage6_fountain.crystallizer import FountainCrystallizer
    return FountainCrystallizer(
        beliefs_writer=writers["beliefs"],
        beliefs_reader=readers["beliefs"],
    )


class TestCrystallizerAttribution(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.c = _make_crystallizer(self.writers, self.readers)
        self._prev_flag = os.environ.get(_FLAG)

    def tearDown(self):
        if self._prev_flag is None:
            os.environ.pop(_FLAG, None)
        else:
            os.environ[_FLAG] = self._prev_flag
        _cleanup(self.writers, self.tmp)

    def _row(self, belief_id):
        from theory_x.stage3_world_model.attribution_marker import marker_in_tags
        rows = self.readers["beliefs"].read(
            "SELECT content, tags FROM beliefs WHERE id = ?", (belief_id,)
        )
        self.assertEqual(len(rows), 1)
        return rows[0], marker_in_tags(rows[0]["tags"])

    def test_flag_on_focal_item_bare_thought_gets_marked(self):
        os.environ[_FLAG] = "1"
        bid = self.c.crystallize(
            thought=_THOUGHT, fountain_event_id=1, ts=time.time(),
            focal_item="Rust terminal multiplexer",
        )
        self.assertIsNotNone(bid)
        time.sleep(0.05)
        row, marker = self._row(bid)
        self.assertEqual(marker, "Rust terminal multiplexer")
        self.assertIn("(per a feed item)", row["content"])

    def test_flag_off_leaves_bare(self):
        os.environ.pop(_FLAG, None)
        bid = self.c.crystallize(
            thought=_THOUGHT, fountain_event_id=2, ts=time.time(),
            focal_item="Rust terminal multiplexer",
        )
        self.assertIsNotNone(bid)
        time.sleep(0.05)
        row, marker = self._row(bid)
        self.assertIsNone(marker)
        self.assertEqual(row["content"], _THOUGHT)
        # untouched path writes the '[]' DEFAULT, never None (beliefs.tags NOT NULL)
        self.assertEqual(row["tags"], "[]")

    def test_drift_no_focal_item_untouched_even_with_flag(self):
        os.environ[_FLAG] = "1"
        bid = self.c.crystallize(
            thought=_THOUGHT, fountain_event_id=3, ts=time.time(),
            focal_item=None,
        )
        self.assertIsNotNone(bid)
        time.sleep(0.05)
        row, marker = self._row(bid)
        self.assertIsNone(marker)
        self.assertEqual(row["content"], _THOUGHT)
        self.assertEqual(row["tags"], "[]")

    def test_idempotent_when_already_attributed(self):
        os.environ[_FLAG] = "1"
        already = "I notice this pull toward complexity (per its source)"
        bid = self.c.crystallize(
            thought=already, fountain_event_id=4, ts=time.time(),
            focal_item="Rust terminal multiplexer",
        )
        self.assertIsNotNone(bid)
        time.sleep(0.05)
        row, marker = self._row(bid)
        # already attributed -> no re-stamp, no second clause appended
        self.assertIsNone(marker)
        self.assertEqual(row["content"].count("(per "), 1)
        self.assertEqual(row["tags"], "[]")
        self.assertNotIn("(per a feed item)", row["content"])


if __name__ == "__main__":
    unittest.main()
