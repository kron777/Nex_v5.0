"""Tests for theory_x.focal_set — FocalSet, including SentienceNode conformance."""
import unittest

from tests._bootstrap import *  # noqa: F401, F403


class TestSentienceNodeProtocol(unittest.TestCase):
    """FocalSet satisfies the SentienceNode protocol."""

    def test_implements_sentience_node_protocol(self):
        from theory_x import SentienceNode
        from theory_x.focal_set import FocalSet
        instance = FocalSet()
        self.assertIsInstance(instance, SentienceNode)

    def test_has_name_attribute(self):
        from theory_x.focal_set import FocalSet
        self.assertEqual(FocalSet.name, "focal_set")
        self.assertEqual(FocalSet().name, "focal_set")

    def test_tick_returns_dict(self):
        from theory_x.focal_set import FocalSet
        fs = FocalSet()
        result = fs.tick()
        self.assertIsInstance(result, dict)
        self.assertIn("name", result)
        self.assertIn("focal_ids", result)
        self.assertIn("mode", result)

    def test_tick_accepts_context_kwarg(self):
        from theory_x.focal_set import FocalSet
        fs = FocalSet()
        result = fs.tick(context={"candidates": {}, "current_tick": 1})
        self.assertIsInstance(result, dict)

    def test_decay_is_noop(self):
        from theory_x.focal_set import FocalSet
        fs = FocalSet()
        import time
        before = fs.state()
        fs.decay(time.time())
        after = fs.state()
        # decay() is a no-op — state unchanged
        self.assertEqual(before["focal_ids"], after["focal_ids"])
        self.assertEqual(before["mode"], after["mode"])

    def test_state_returns_dict(self):
        from theory_x.focal_set import FocalSet
        import time
        fs = FocalSet()
        s = fs.state(now=time.time())
        self.assertIn("name", s)
        self.assertIn("k", s)
        self.assertIn("focal_size", s)
        self.assertIn("focal_ids", s)
        self.assertIn("last_shift_tick", s)
        self.assertIn("tick", s)

    def test_state_now_is_optional(self):
        from theory_x.focal_set import FocalSet
        fs = FocalSet()
        s = fs.state()  # no now arg
        self.assertIsInstance(s, dict)


class TestFocalSetCore(unittest.TestCase):
    """Core FocalSet mechanics — existing functionality not broken by retrofit."""

    def _candidates(self, ids, base_activation=0.8):
        import time
        t = time.time()
        return {
            str(i): {
                "id": i,
                "content": f"belief {i}",
                "last_referenced_at": t - (i * 10),
                "tier": 2,
                "_role": "ANCHOR",
            }
            for i in ids
        }

    def test_top_k_selection(self):
        from theory_x.focal_set import FocalSet
        fs = FocalSet(K=3)
        candidates = self._candidates(range(7))
        tick = fs.next_tick()
        fs.update(candidates, current_tick=tick)
        self.assertLessEqual(len(fs.get_focal_ids()), 3)

    def test_shift_event_logged(self):
        from theory_x.focal_set import FocalSet
        fs = FocalSet(K=3)
        tick = fs.next_tick()
        event = fs.update(self._candidates(range(5)), current_tick=tick)
        self.assertIsNotNone(event)
        log = fs.get_shift_log()
        self.assertEqual(len(log), 1)

    def test_mode_locked_prevents_shifts(self):
        from theory_x.focal_set import FocalSet
        fs = FocalSet(K=3)
        tick = fs.next_tick()
        fs.update(self._candidates(range(4)), current_tick=tick)
        fs.set_mode("locked")
        before = fs.get_focal_ids()
        tick2 = fs.next_tick()
        fs.update(self._candidates(range(10, 14)), current_tick=tick2)
        after = fs.get_focal_ids()
        self.assertEqual(before, after)

    def test_next_tick_increments(self):
        from theory_x.focal_set import FocalSet
        fs = FocalSet()
        t1 = fs.next_tick()
        t2 = fs.next_tick()
        self.assertEqual(t2, t1 + 1)


if __name__ == "__main__":
    unittest.main()
