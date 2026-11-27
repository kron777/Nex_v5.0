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
