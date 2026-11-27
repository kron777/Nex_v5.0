"""Provenance erosion tests.

Covers:
- use_count increments via record_use()
- reinforce_count increments via record_reinforce()
- Stage advances at threshold (external → nex_absorbed at 10 reinforcements)
- Protected sources skip erosion entirely
- erosion_pass() runs correctly
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
    tmp = tempfile.mkdtemp(prefix="nex5_er_")
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


def _insert_belief(writer, content, source="test", tier=5, confidence=0.6):
    now = int(time.time())
    return writer.write(
        "INSERT INTO beliefs (content, tier, confidence, created_at, source) "
        "VALUES (?, ?, ?, ?, ?)",
        (content, tier, confidence, now, source),
    )


class TestErosionTracking(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_use_count_increments(self):
        from theory_x.stage3_world_model.erosion import ProvenanceErosion
        w = self.writers["beliefs"]
        r = self.readers["beliefs"]
        erosion = ProvenanceErosion(w, r)

        bid = _insert_belief(w, "Test belief for use count tracking")
        erosion.record_use(bid)
        erosion.record_use(bid)

        row = r.read_one("SELECT use_count FROM beliefs WHERE id = ?", (bid,))
        self.assertEqual(row["use_count"], 2)

    def test_reinforce_count_increments(self):
        from theory_x.stage3_world_model.erosion import ProvenanceErosion
        w = self.writers["beliefs"]
        r = self.readers["beliefs"]
        erosion = ProvenanceErosion(w, r)

        bid = _insert_belief(w, "Test belief for reinforce tracking")
        erosion.record_reinforce(bid)

        row = r.read_one("SELECT reinforce_count FROM beliefs WHERE id = ?", (bid,))
        self.assertEqual(row["reinforce_count"], 1)

    def test_stage_advances_at_threshold(self):
        from theory_x.stage3_world_model.erosion import ProvenanceErosion, THRESHOLDS
        w = self.writers["beliefs"]
        r = self.readers["beliefs"]
        erosion = ProvenanceErosion(w, r)

        bid = _insert_belief(w, "Belief to advance to nex_absorbed")
        threshold = THRESHOLDS["external"]

        # Set reinforce_count to threshold - 1 directly, then call record_reinforce once
        w.write(
            "UPDATE beliefs SET reinforce_count = ? WHERE id = ?",
            (threshold - 1, bid),
        )
        erosion.record_reinforce(bid)

        row = r.read_one("SELECT erosion_stage FROM beliefs WHERE id = ?", (bid,))
        self.assertEqual(row["erosion_stage"], "nex_absorbed")

    def test_protected_source_skipped(self):
        from theory_x.stage3_world_model.erosion import ProvenanceErosion, THRESHOLDS
        w = self.writers["beliefs"]
        r = self.readers["beliefs"]
        erosion = ProvenanceErosion(w, r)

        bid = _insert_belief(w, "Protected belief", source="keystone_seed")
        threshold = THRESHOLDS["external"]
        w.write("UPDATE beliefs SET reinforce_count = ? WHERE id = ?", (threshold, bid))

        erosion._erosion_check(bid)

        row = r.read_one("SELECT erosion_stage FROM beliefs WHERE id = ?", (bid,))
        self.assertEqual(row["erosion_stage"], "external")

    def test_erosion_pass(self):
        from theory_x.stage3_world_model.erosion import ProvenanceErosion, THRESHOLDS
        w = self.writers["beliefs"]
        r = self.readers["beliefs"]
        erosion = ProvenanceErosion(w, r)

        threshold = THRESHOLDS["external"]
        bid = _insert_belief(w, "Belief for erosion_pass test")
        w.write("UPDATE beliefs SET reinforce_count = ? WHERE id = ?", (threshold, bid))

        advanced = erosion.erosion_pass()
        self.assertGreaterEqual(advanced, 1)

        row = r.read_one("SELECT erosion_stage FROM beliefs WHERE id = ?", (bid,))
        self.assertEqual(row["erosion_stage"], "nex_absorbed")



    def test_erosion_pass_reaches_ready_rows_after_500_unadvanced_rows(self):
        from theory_x.stage3_world_model.erosion import ProvenanceErosion, THRESHOLDS
        w = self.writers["beliefs"]
        r = self.readers["beliefs"]
        erosion = ProvenanceErosion(w, r)

        # Keep seed rows out of this controlled scan; the 500 low-reinforcement
        # rows deliberately occupy the first page ahead of five ready rows.
        w.write("UPDATE beliefs SET locked = 1")
        first_id = None
        low_ids = []
        for index in range(500):
            bid = _insert_belief(w, f"Low reinforcement row {index}")
            first_id = bid if first_id is None else first_id
            low_ids.append(bid)
        ready_ids = [
            _insert_belief(w, f"Ready row {index}") for index in range(5)
        ]
        w.write(
            "UPDATE beliefs SET erosion_stage='nex_integrated', reinforce_count=0 "
            "WHERE id >= ?",
            (first_id,),
        )
        placeholders = ",".join("?" for _ in ready_ids)
        w.write(
            f"UPDATE beliefs SET reinforce_count=? WHERE id IN ({placeholders})",
            (THRESHOLDS["nex_integrated"], *ready_ids),
        )

        advanced = erosion.erosion_pass()
        self.assertEqual(advanced, 5)

        low_rows = r.read(
            f"SELECT id, erosion_stage FROM beliefs WHERE id IN "
            f"({','.join('?' for _ in low_ids)})",
            tuple(low_ids),
        )
        ready_rows = r.read(
            f"SELECT id, erosion_stage FROM beliefs WHERE id IN ({placeholders})",
            tuple(ready_ids),
        )
        self.assertTrue(all(row["erosion_stage"] == "nex_integrated" for row in low_rows))
        self.assertTrue(all(row["erosion_stage"] == "nex_core" for row in ready_rows))

    def test_erosion_pass_keyset_does_not_skip_rows_that_leave_eligible_set(self):
        from theory_x.stage3_world_model.erosion import ProvenanceErosion, THRESHOLDS
        w = self.writers["beliefs"]
        r = self.readers["beliefs"]
        erosion = ProvenanceErosion(w, r)

        w.write("UPDATE beliefs SET locked = 1")
        belief_ids = [
            _insert_belief(w, f"Ready for keyset page {index}") for index in range(505)
        ]
        first_id = belief_ids[0]
        placeholders = ",".join("?" for _ in belief_ids)
        w.write(
            "UPDATE beliefs SET erosion_stage='nex_integrated', reinforce_count=? "
            "WHERE id >= ?",
            (THRESHOLDS["nex_integrated"], first_id),
        )

        advanced = erosion.erosion_pass()
        self.assertEqual(advanced, 505)

        rows = r.read(
            f"SELECT id, erosion_stage FROM beliefs WHERE id IN ({placeholders})",
            tuple(belief_ids),
        )
        self.assertEqual(len(rows), 505)
        self.assertTrue(all(row["erosion_stage"] == "nex_core" for row in rows))

        undo_rows = r.read(
            "SELECT belief_id FROM undo_events "
            "WHERE kind='eroded' AND cause_ref='erosion_pass:nex_integrated->nex_core'"
        )
        self.assertEqual(
            {row["belief_id"] for row in undo_rows}, set(belief_ids)
        )

    # ------------------------------------------------------------------
    # Consequence-review invariants (repeat execution, partial failure).
    # A small page size keeps the multi-page paths fast and explicit.
    # ------------------------------------------------------------------

    def _ready_rows(self, n, stage="external"):
        from theory_x.stage3_world_model.erosion import THRESHOLDS
        w = self.writers["beliefs"]
        w.write("UPDATE beliefs SET locked = 1")  # isolate from seed rows
        ids = [_insert_belief(w, f"Ready {stage} row {i}") for i in range(n)]
        placeholders = ",".join("?" for _ in ids)
        w.write(
            f"UPDATE beliefs SET erosion_stage = ?, reinforce_count = ? "
            f"WHERE id IN ({placeholders})",
            (stage, THRESHOLDS[stage], *ids),
        )
        return ids

    def _state(self, ids):
        placeholders = ",".join("?" for _ in ids)
        rows = self.readers["beliefs"].read(
            f"SELECT id, erosion_stage, reinforce_count, confidence FROM beliefs "
            f"WHERE id IN ({placeholders})",
            tuple(ids),
        )
        return {row["id"]: row for row in rows}

    def _eroded_undo_ids(self):
        rows = self.readers["beliefs"].read(
            "SELECT belief_id FROM undo_events WHERE kind = 'eroded'"
        )
        return [row["belief_id"] for row in rows]

    def test_repeat_erosion_pass_is_idempotent(self):
        """A second pass with no new reinforcement advances nothing, writes no
        further undo rows and applies no second confidence increment."""
        from theory_x.stage3_world_model import erosion as erosion_mod
        ids = self._ready_rows(3)
        erosion = erosion_mod.ProvenanceErosion(
            self.writers["beliefs"], self.readers["beliefs"])

        self.assertEqual(erosion.erosion_pass(), 3)
        after_first = self._state(ids)
        self.assertTrue(all(r["erosion_stage"] == "nex_absorbed" for r in after_first.values()))
        self.assertTrue(all(r["reinforce_count"] == 0 for r in after_first.values()))
        self.assertEqual(sorted(self._eroded_undo_ids()), sorted(ids))

        self.assertEqual(erosion.erosion_pass(), 0)
        after_second = self._state(ids)
        for bid in ids:
            self.assertEqual(after_second[bid]["erosion_stage"], "nex_absorbed")
            self.assertAlmostEqual(after_second[bid]["confidence"],
                                   after_first[bid]["confidence"])
        self.assertEqual(sorted(self._eroded_undo_ids()), sorted(ids))

    def test_mid_scan_read_failure_returns_honest_count_and_next_pass_recovers(self):
        """A read failure on a later page returns only the work actually done,
        surfaces the error, and the next pass completes the remainder without
        re-advancing rows already handled."""
        from unittest import mock
        from theory_x.stage3_world_model import erosion as erosion_mod

        class _ReaderFailingOnCall:
            def __init__(self, inner, fail_on):
                self._inner, self._fail_on, self._calls = inner, fail_on, 0

            def read(self, sql, params=()):
                self._calls += 1
                if self._calls == self._fail_on:
                    raise RuntimeError("injected page read failure")
                return self._inner.read(sql, params)

            def read_one(self, sql, params=()):
                return self._inner.read_one(sql, params)

        ids = self._ready_rows(5)
        w, r = self.writers["beliefs"], self.readers["beliefs"]
        with mock.patch.object(erosion_mod, "_PAGE_SIZE", 2), \
                mock.patch.object(erosion_mod.errors, "record") as rec:
            flaky = erosion_mod.ProvenanceErosion(w, _ReaderFailingOnCall(r, fail_on=2))
            advanced = flaky.erosion_pass()
            self.assertEqual(advanced, 2)          # only the first page was handled
            self.assertTrue(any("erosion_pass read error" in str(c.args[0])
                                for c in rec.call_args_list))

            state = self._state(ids)
            moved = [b for b in ids if state[b]["erosion_stage"] == "nex_absorbed"]
            self.assertEqual(len(moved), advanced)  # count matches persisted state
            self.assertEqual(sorted(self._eroded_undo_ids()), sorted(moved))

            recovered = erosion_mod.ProvenanceErosion(w, r).erosion_pass()
        self.assertEqual(recovered, 3)
        final = self._state(ids)
        self.assertTrue(all(row["erosion_stage"] == "nex_absorbed" for row in final.values()))
        # every belief advanced exactly once: one undo row each, no duplicates
        self.assertEqual(sorted(self._eroded_undo_ids()), sorted(ids))

    def test_per_row_write_failure_is_isolated_and_not_counted(self):
        """An UPDATE failure for one belief is surfaced, is not counted, writes
        no undo row, and does not stop later rows (including later pages)."""
        from unittest import mock
        from theory_x.stage3_world_model import erosion as erosion_mod

        class _WriterFailingForBelief:
            def __init__(self, inner, belief_id):
                self._inner, self._belief_id = inner, belief_id

            def write(self, sql, params=()):
                if (sql.startswith("UPDATE beliefs SET erosion_stage")
                        and params and params[-1] == self._belief_id):
                    raise RuntimeError("injected update failure")
                return self._inner.write(sql, params)

            def write_many(self, statements):
                return self._inner.write_many(statements)

        ids = self._ready_rows(5)
        failing_id = ids[1]
        w, r = self.writers["beliefs"], self.readers["beliefs"]
        before = self._state(ids)
        with mock.patch.object(erosion_mod, "_PAGE_SIZE", 2), \
                mock.patch.object(erosion_mod.errors, "record") as rec:
            advanced = erosion_mod.ProvenanceErosion(
                _WriterFailingForBelief(w, failing_id), r).erosion_pass()
            self.assertEqual(advanced, 4)
            self.assertTrue(any(f"belief {failing_id}" in str(c.args[0])
                                for c in rec.call_args_list))

            state = self._state(ids)
            self.assertEqual(state[failing_id]["erosion_stage"], "external")
            self.assertEqual(state[failing_id]["reinforce_count"],
                             before[failing_id]["reinforce_count"])
            self.assertAlmostEqual(state[failing_id]["confidence"],
                                   before[failing_id]["confidence"])
            self.assertNotIn(failing_id, self._eroded_undo_ids())
            self.assertTrue(all(state[b]["erosion_stage"] == "nex_absorbed"
                                for b in ids if b != failing_id))

            # the skipped belief is still eligible and the next pass takes it
            self.assertEqual(erosion_mod.ProvenanceErosion(w, r).erosion_pass(), 1)
        self.assertEqual(sorted(self._eroded_undo_ids()), sorted(ids))


if __name__ == "__main__":
    unittest.main()
