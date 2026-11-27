"""Concurrency invariants for BeliefPromoter.corroborate().

corroborate() is called from two different threads on the normal boot path:
dynamic formation (PipelineHooks.on_pipeline_event) and the World Model's
world_consolidation loop. Its read, threshold decision and write must therefore
behave as one atomic step per call:

- concurrent corroborations of one belief never lose an increment;
- a threshold crossing promotes exactly once, with exactly one promotion-log
  event and exactly one provenance-erosion reinforcement.

Isolated temporary databases only. Thresholds and promotion policy are the
module's own; these tests assert atomicity, not new policy.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_promo_")
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


class _CountingErosion:
    def __init__(self):
        self.calls = []
        self._lock = threading.Lock()

    def record_reinforce(self, belief_id):
        with self._lock:
            self.calls.append(belief_id)


class TestCorroborateAtomicity(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.w = self.writers["beliefs"]
        self.r = self.readers["beliefs"]

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _belief(self, tier, corroboration_count=0):
        bid = self.w.write(
            "INSERT INTO beliefs (content, tier, confidence, created_at, source, "
            "corroboration_count) VALUES (?, ?, ?, ?, ?, ?)",
            (f"Concurrent corroboration subject {time.time_ns()}", tier, 0.5,
             int(time.time()), "test", corroboration_count),
        )
        return bid

    def _row(self, bid):
        return self.r.read_one(
            "SELECT tier, corroboration_count, promotion_log FROM beliefs WHERE id = ?",
            (bid,),
        )

    def _race(self, n_threads, per_thread, fn):
        barrier = threading.Barrier(n_threads)
        results, errors_seen = [], []
        lock = threading.Lock()

        def worker():
            barrier.wait()
            for _ in range(per_thread):
                try:
                    out = fn()
                except Exception as exc:  # pragma: no cover - surfaced below
                    with lock:
                        errors_seen.append(exc)
                    continue
                with lock:
                    results.append(out)

        threads = [threading.Thread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)
        self.assertEqual(errors_seen, [])
        return results

    def test_concurrent_corroborations_never_lose_an_increment(self):
        """Tier 2 has no corroboration threshold, so every call is a pure
        increment: the final count must equal the number of calls."""
        from theory_x.stage3_world_model.promotion import BeliefPromoter
        bid = self._belief(tier=2)
        promoters = [BeliefPromoter(self.w, self.r) for _ in range(8)]
        idx = iter(range(10**6))
        lock = threading.Lock()

        def call():
            with lock:
                p = promoters[next(idx) % len(promoters)]
            return p.corroborate(bid)

        results = self._race(n_threads=8, per_thread=30, fn=call)
        self.assertEqual(len(results), 240)
        self.assertFalse(any(results))          # tier 2 never promotes
        self.assertEqual(self._row(bid)["corroboration_count"], 240)

    def test_threshold_crossing_promotes_exactly_once(self):
        """Two simultaneous corroborations at threshold-1 on Tier 7
        (threshold 3): exactly one promotes; the other counts at Tier 6."""
        from theory_x.stage3_world_model.promotion import BeliefPromoter
        bid = self._belief(tier=7, corroboration_count=2)
        erosion = _CountingErosion()
        p = BeliefPromoter(self.w, self.r, erosion=erosion)

        results = self._race(n_threads=2, per_thread=1, fn=lambda: p.corroborate(bid))
        self.assertEqual(sorted(results), [False, True])

        row = self._row(bid)
        self.assertEqual(row["tier"], 6)
        self.assertEqual(row["corroboration_count"], 1)
        # promotion_log elements are stored as JSON-encoded strings
        # (json_insert of a json.dumps() text value) -- decode each element.
        decoded = [json.loads(e) if isinstance(e, str) else e
                   for e in json.loads(row["promotion_log"] or "[]")]
        events = [e for e in decoded
                  if isinstance(e, dict) and e.get("event") == "corroboration"]
        self.assertEqual(len(events), 1)
        self.assertEqual((events[0]["from"], events[0]["to"]), (7, 6))
        self.assertEqual(erosion.calls, [bid])

    def test_sequential_behaviour_unchanged(self):
        """Single-threaded promotion still happens at the module's threshold."""
        from theory_x.stage3_world_model.promotion import BeliefPromoter
        bid = self._belief(tier=7)
        erosion = _CountingErosion()
        p = BeliefPromoter(self.w, self.r, erosion=erosion)
        self.assertEqual([p.corroborate(bid) for _ in range(3)], [False, False, True])
        row = self._row(bid)
        self.assertEqual((row["tier"], row["corroboration_count"]), (6, 0))
        self.assertEqual(erosion.calls, [bid])

    # ------------------------------------------------------------------
    # Demotion paths must not overwrite a transition that committed after
    # their decision point (decay_pass batch snapshot; contradiction read).
    # A hook fires exactly at that point: after the Reader read for a
    # read-then-write implementation, or just before the Writer transaction
    # for a transactional one.
    # ------------------------------------------------------------------

    def _hooked(self, hook):
        test = self

        class _Reader:
            def __init__(self, inner):
                self._inner, self.fired = inner, False

            def _fire(self):
                if not self.fired:
                    self.fired = True
                    hook()

            def read(self, sql, params=()):
                rows = self._inner.read(sql, params)
                self._fire()
                return rows

            def read_one(self, sql, params=()):
                row = self._inner.read_one(sql, params)
                self._fire()
                return row

        class _Writer:
            def __init__(self, inner, reader):
                self._inner, self._reader = inner, reader

            def transaction(self, cb):
                self._reader._fire()
                return self._inner.transaction(cb)

            def __getattr__(self, name):
                return getattr(self._inner, name)

        reader = _Reader(test.r)
        return _Writer(test.w, reader), reader

    def _idle(self, tier):
        old = int(time.time()) - 10 * 24 * 3600
        bid = self._belief(tier=tier)
        self.w.write(
            "UPDATE beliefs SET created_at = ?, last_referenced_at = ? WHERE id = ?",
            (old, old, bid),
        )
        return bid

    def _demoted_undo(self, bid):
        rows = self.r.read(
            "SELECT cause_ref FROM undo_events WHERE kind = 'demoted' AND belief_id = ?",
            (bid,),
        )
        return [row["cause_ref"] for row in rows]

    def test_decay_pass_does_not_clobber_a_promotion_after_its_snapshot(self):
        """An idle T6 belief promoted to T5 (and re-referenced) after decay's
        batch read must stay at T5, not be written to stale T6+1 = T7."""
        from theory_x.stage3_world_model.promotion import BeliefPromoter
        bid = self._idle(tier=6)

        def promote():
            self.w.write(
                "UPDATE beliefs SET tier = 5, corroboration_count = 0, "
                "last_promoted_at = ?, last_referenced_at = ? WHERE id = ?",
                (int(time.time()), int(time.time()), bid),
            )

        writer, reader = self._hooked(promote)
        demoted = BeliefPromoter(writer, reader).decay_pass()
        self.assertTrue(reader.fired)
        self.assertEqual(self._row(bid)["tier"], 5)
        self.assertEqual(demoted, 0)
        self.assertEqual(self._demoted_undo(bid), [])

    def test_decay_pass_skips_a_belief_referenced_after_its_snapshot(self):
        """Same tier, but referenced after the snapshot: no longer idle, so it
        must not be demoted from the stale eligibility decision."""
        from theory_x.stage3_world_model.promotion import BeliefPromoter
        bid = self._idle(tier=5)

        def reference():
            self.w.write("UPDATE beliefs SET last_referenced_at = ? WHERE id = ?",
                         (int(time.time()), bid))

        writer, reader = self._hooked(reference)
        self.assertEqual(BeliefPromoter(writer, reader).decay_pass(), 0)
        self.assertEqual(self._row(bid)["tier"], 5)
        self.assertEqual(self._demoted_undo(bid), [])

    def test_decay_pass_still_demotes_genuinely_idle_beliefs(self):
        from theory_x.stage3_world_model.promotion import BeliefPromoter
        self.w.write("UPDATE beliefs SET locked = 1")  # isolate from seed rows
        t5, t6, t7 = self._idle(5), self._idle(6), self._idle(7)
        self.assertEqual(BeliefPromoter(self.w, self.r).decay_pass(), 2)
        self.assertEqual((self._row(t5)["tier"], self._row(t6)["tier"],
                          self._row(t7)["tier"]), (6, 7, 7))
        self.assertEqual(self._demoted_undo(t5), ["decay_pass:5->6"])
        self.assertEqual(self._demoted_undo(t6), ["decay_pass:6->7"])
        self.assertEqual(self._demoted_undo(t7), [])

    def test_decisive_contradiction_applies_to_the_current_tier(self):
        """A promotion T4->T3 committing at the contradiction's decision point
        must not be overwritten: demote from T3 (-> T5), not stale T4 (-> T6)."""
        from theory_x.stage3_world_model.promotion import BeliefPromoter
        bid = self._belief(tier=4)

        def promote():
            self.w.write("UPDATE beliefs SET tier = 3 WHERE id = ?", (bid,))

        writer, reader = self._hooked(promote)
        self.assertTrue(BeliefPromoter(writer, reader).decisive_contradiction(bid))
        self.assertTrue(reader.fired)
        self.assertEqual(self._row(bid)["tier"], 5)
        self.assertEqual(self._demoted_undo(bid), ["decisive_contradiction:3->5"])

    def test_missing_and_locked_tier1_are_noops(self):
        from theory_x.stage3_world_model.promotion import BeliefPromoter
        p = BeliefPromoter(self.w, self.r)
        self.assertFalse(p.corroborate(10**9))  # no such belief
        bid = self._belief(tier=1)
        self.w.write("UPDATE beliefs SET locked = 1 WHERE id = ?", (bid,))
        self.assertFalse(p.corroborate(bid))
        self.assertEqual(self._row(bid)["corroboration_count"], 0)


if __name__ == "__main__":
    unittest.main()
