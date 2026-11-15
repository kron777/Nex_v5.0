"""smṛti dev round (2026-11-15) — the retained candidate reaches the commit.

generate()'s own retrieval_manifest already records every belief drawn into
a fire's prompt (own_sense/seed/spectrum, etc.) -- used to write
fountain_retrieval_log, but never reached crystallize() itself. This is the
one missing thread: the top-ranked own_sense entry (the closest thing a fire
has to "the object" it is engaging with, as opposed to an imported seed) is
now carried unmodified from retrieval through generate() to the actual
commit, via crystallize()'s new `retained_candidate_id` parameter.

Purely observational: no schema change, no behavioral effect on what gets
crystallized or how. Logged via the same errors.record() channel every other
observational event in this file already uses, not a new table -- the live
fountain_crystallizations table (continuously written by the running
process) was deliberately left untouched.

Covers:
- retained_candidate_id is optional and backward-compatible (omitted entirely,
  or explicitly None) -- crystallize() behaves exactly as before either way.
- when provided, a citable "smrti: retained candidate X -> crystallized Y"
  record appears in errors.recent(), linking the two ids.
- when None (the retrieval found no own_sense entry for this fire), no such
  record is emitted -- nothing claims a retention that didn't happen.
- a quality-check rejection (no belief written) never logs a retention record
  either, even if retained_candidate_id was provided -- there is nothing to
  link it to.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_smrti_")
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


_GOOD_THOUGHT = "Inside me there is a hum I cannot silence or locate, and I notice it."


class TestRetainedCandidateThreading(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.c = _make_crystallizer(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _recent_smrti_records(self):
        import errors
        return [e for e in errors.recent(50) if e.message.startswith("smrti:")]

    def test_omitted_parameter_is_fully_backward_compatible(self):
        belief_id = self.c.crystallize(
            thought=_GOOD_THOUGHT, fountain_event_id=1, ts=time.time(),
        )
        self.assertIsNotNone(belief_id)
        self.assertEqual(self._recent_smrti_records(), [])

    def test_explicit_none_behaves_identically_to_omitted(self):
        belief_id = self.c.crystallize(
            thought=_GOOD_THOUGHT, fountain_event_id=2, ts=time.time(),
            retained_candidate_id=None,
        )
        self.assertIsNotNone(belief_id)
        self.assertEqual(self._recent_smrti_records(), [])

    def test_provided_candidate_is_logged_linked_to_the_crystallized_belief(self):
        belief_id = self.c.crystallize(
            thought=_GOOD_THOUGHT, fountain_event_id=3, ts=time.time(),
            retained_candidate_id=9101,
        )
        self.assertIsNotNone(belief_id)
        records = self._recent_smrti_records()
        self.assertEqual(len(records), 1)
        self.assertIn("9101", records[0].message)
        self.assertIn(str(belief_id), records[0].message)

    def test_quality_rejection_never_logs_a_retention_record(self):
        before = len(self._recent_smrti_records())
        result = self.c.crystallize(
            thought="No self reference here at all.",
            fountain_event_id=4, ts=time.time(),
            retained_candidate_id=9101,
        )
        self.assertIsNone(result)
        self.assertEqual(len(self._recent_smrti_records()), before)


if __name__ == "__main__":
    unittest.main()
