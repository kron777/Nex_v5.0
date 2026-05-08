"""Tests for theory_x.working_memory — WorkingMemory node."""
import threading
import time
import unittest

from tests._bootstrap import *  # noqa: F401, F403 — sys.path setup


class TestCapacityEject(unittest.TestCase):
    """Adding beyond capacity ejects the lowest-activation item."""

    def test_capacity_eject(self):
        from theory_x.working_memory import WorkingMemory
        wm = WorkingMemory()
        t = 1_000_000.0

        # Fill to capacity (7) with items added 10s apart; earlier = lower activation
        for i in range(7):
            wm.add(f"b{i}", f"content {i}", now=t + i * 10)

        self.assertEqual(len(wm._items), 7)

        # b0 has the lowest activation (added earliest, so least recently seen)
        # Adding b7 should eject b0
        wm.add("b7", "content 7", now=t + 200)

        self.assertEqual(len(wm._items), 7)
        self.assertNotIn("b0", wm._items)
        self.assertIn("b7", wm._items)

    def test_capacity_is_seven(self):
        from theory_x.working_memory import WorkingMemory
        self.assertEqual(WorkingMemory.CAPACITY, 7)


class TestDecayOverTime(unittest.TestCase):
    """Items with very old last_seen fall below threshold and are pruned."""

    def test_decay_removes_old_item(self):
        from theory_x.working_memory import WorkingMemory
        wm = WorkingMemory()
        t_add = 1_000_000.0
        wm.add("old", "old content", now=t_add)

        # 300s = one half-life → activation ≈ 0.5, still above threshold
        wm.decay(now=t_add + 300)
        self.assertIn("old", wm._items)

        # 2000s ≈ 6.7 half-lives → activation ≈ exp(-6.7) ≈ 0.0012 < 0.05
        wm.decay(now=t_add + 2000)
        self.assertNotIn("old", wm._items)

    def test_decay_preserves_fresh_item(self):
        from theory_x.working_memory import WorkingMemory
        wm = WorkingMemory()
        t = 1_000_000.0
        wm.add("fresh", "fresh content", now=t)

        # Only 60s have passed — activation should be well above threshold
        wm.decay(now=t + 60)
        self.assertIn("fresh", wm._items)


class TestRefreshOnReadd(unittest.TestCase):
    """Re-adding an existing item increments refresh_count and updates last_seen."""

    def test_refresh_increments_count(self):
        from theory_x.working_memory import WorkingMemory
        wm = WorkingMemory()
        t = 1_000_000.0
        wm.add("b1", "content", now=t)
        wm.add("b1", "content", now=t + 10)
        wm.add("b1", "content", now=t + 20)

        item = wm._items["b1"]
        self.assertEqual(item.refresh_count, 2)
        self.assertEqual(item.last_seen, t + 20)
        self.assertEqual(item.first_seen, t)

    def test_refresh_boosts_activation(self):
        from theory_x.working_memory import WorkingMemory
        wm = WorkingMemory()
        t_add = 1_000_000.0
        t_measure = t_add + 120  # 2 minutes later — base decay ≈ 0.78

        # Add once, measure after partial decay
        wm.add("b1", "content", now=t_add)
        activation_no_refresh = wm._items["b1"].activation(t_measure)

        # Add then refresh 3× at same timestamp; measure at same future point
        wm2 = WorkingMemory()
        wm2.add("b1", "content", now=t_add)
        for _ in range(3):
            wm2.add("b1", "content", now=t_add)
        activation_refreshed = wm2._items["b1"].activation(t_measure)

        self.assertGreater(activation_refreshed, activation_no_refresh)

    def test_activation_capped_at_one(self):
        from theory_x.working_memory import WorkingMemory
        wm = WorkingMemory()
        t = 1_000_000.0
        wm.add("b1", "content", now=t)
        # Many refreshes should not push activation above 1.0
        for _ in range(50):
            wm.add("b1", "content", now=t)
        self.assertLessEqual(wm._items["b1"].activation(t), 1.0)


class TestGetActiveFiltering(unittest.TestCase):
    """get_active respects min_activation threshold and sorts by activation."""

    def test_threshold_filtering(self):
        from theory_x.working_memory import WorkingMemory
        wm = WorkingMemory()
        t = 1_000_000.0

        wm.add("fresh", "fresh content", now=t)          # activation ≈ 1.0 at t
        wm.add("stale", "stale content", now=t - 1800)   # 6 half-lives back ≈ 0.015

        active = wm.get_active(now=t, min_activation=0.1)
        ids = [r["belief_id"] for r in active]

        self.assertIn("fresh", ids)
        self.assertNotIn("stale", ids)

    def test_sorted_by_activation_desc(self):
        from theory_x.working_memory import WorkingMemory
        wm = WorkingMemory()
        t = 1_000_000.0

        wm.add("older", "older content", now=t - 120)
        wm.add("newer", "newer content", now=t)

        active = wm.get_active(now=t, min_activation=0.05)
        self.assertGreater(len(active), 0)
        # Activation should be in descending order
        activations = [r["activation"] for r in active]
        self.assertEqual(activations, sorted(activations, reverse=True))

    def test_empty_when_all_decayed(self):
        from theory_x.working_memory import WorkingMemory
        wm = WorkingMemory()
        t = 1_000_000.0
        wm.add("b1", "content", now=t - 3000)  # very old
        active = wm.get_active(now=t, min_activation=0.1)
        self.assertEqual(active, [])


class TestThreadSafetySmoke(unittest.TestCase):
    """Concurrent adds must not corrupt internal state."""

    def test_concurrent_adds_no_crash(self):
        from theory_x.working_memory import WorkingMemory
        wm = WorkingMemory()
        errors = []

        def adder(belief_id: str) -> None:
            try:
                for _ in range(10):
                    wm.add(belief_id, f"content for {belief_id}")
                    time.sleep(0)  # yield
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=adder, args=(f"b{i}",)) for i in range(20)]
        for th in threads:
            th.start()
        for th in threads:
            th.join(timeout=5.0)

        self.assertEqual(errors, [], f"Thread errors: {errors}")
        # State must be consistent: no more than CAPACITY items
        self.assertLessEqual(len(wm._items), WorkingMemory.CAPACITY)

    def test_concurrent_decay_no_crash(self):
        from theory_x.working_memory import WorkingMemory
        wm = WorkingMemory()
        t = time.time()
        for i in range(5):
            wm.add(f"b{i}", f"content {i}", now=t)

        errors = []

        def decayer() -> None:
            try:
                for _ in range(20):
                    wm.decay(now=time.time())
                    time.sleep(0)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=decayer) for _ in range(5)]
        for th in threads:
            th.start()
        for th in threads:
            th.join(timeout=5.0)

        self.assertEqual(errors, [], f"Thread errors: {errors}")


class TestLifecycle(unittest.TestCase):
    """tick() and state() return correct structure."""

    def test_tick_returns_state_dict(self):
        from theory_x.working_memory import WorkingMemory
        wm = WorkingMemory()
        t = time.time()
        wm.add("b1", "some content", now=t)
        result = wm.tick()
        self.assertIn("size", result)
        self.assertIn("items", result)
        self.assertIsInstance(result["items"], list)

    def test_state_item_fields(self):
        from theory_x.working_memory import WorkingMemory
        wm = WorkingMemory()
        t = time.time()
        wm.add("b1", "some content", now=t)
        s = wm.state(now=t)
        self.assertEqual(s["size"], 1)
        item = s["items"][0]
        self.assertIn("belief_id", item)
        self.assertIn("content", item)
        self.assertIn("activation", item)
        self.assertIn("refresh_count", item)
        self.assertIn("last_seen", item)


class TestSentienceNodeProtocol(unittest.TestCase):
    """WorkingMemory satisfies the SentienceNode protocol."""

    def test_implements_sentience_node_protocol(self):
        from theory_x import SentienceNode
        from theory_x.working_memory import WorkingMemory
        instance = WorkingMemory()
        self.assertIsInstance(instance, SentienceNode)

    def test_has_name_attribute(self):
        from theory_x.working_memory import WorkingMemory
        self.assertEqual(WorkingMemory.name, "working_memory")
        self.assertEqual(WorkingMemory().name, "working_memory")

    def test_tick_returns_dict(self):
        from theory_x.working_memory import WorkingMemory
        wm = WorkingMemory()
        result = wm.tick()
        self.assertIsInstance(result, dict)
        self.assertIn("size", result)

    def test_decay_signature(self):
        from theory_x.working_memory import WorkingMemory
        wm = WorkingMemory()
        wm.decay(now=time.time())  # must accept a float

    def test_state_signature(self):
        from theory_x.working_memory import WorkingMemory
        wm = WorkingMemory()
        s1 = wm.state()           # now=None
        s2 = wm.state(now=time.time())  # now=float
        self.assertIsInstance(s1, dict)
        self.assertIsInstance(s2, dict)


if __name__ == "__main__":
    unittest.main()
