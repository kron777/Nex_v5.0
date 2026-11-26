"""Pipeline corroboration candidate scans must exclude retired markers."""
from __future__ import annotations

import unittest
from unittest.mock import patch


class _Reader:
    def __init__(self):
        self.queries = []

    def read(self, sql, params=()):
        self.queries.append(sql)
        return []


class TestPipelineHooksEligibility(unittest.TestCase):
    def test_default_scan_excludes_retired_markers(self):
        from theory_x.stage3_world_model.pipeline_hooks import PipelineHooks

        reader = _Reader()
        hooks = PipelineHooks(promoter=object(), beliefs_reader=reader)
        with patch.dict("os.environ", {"NEX5_TIER_CLIMB": "0"}):
            hooks.on_pipeline_event({
                "magnitude": 0.8,
                "sensation_source": "attention and memory",
                "branch_id": "systems",
            })
        self.assertEqual(len(reader.queries), 1)
        self.assertIn("erosion_stage != 'retired'", reader.queries[0])

    def test_tier_six_rotation_excludes_retired_markers_in_both_windows(self):
        from theory_x.stage3_world_model.pipeline_hooks import PipelineHooks

        reader = _Reader()
        hooks = PipelineHooks(promoter=object(), beliefs_reader=reader)
        rows, cursor = hooks._load_t6_climb_candidates(limit=1)

        self.assertEqual(rows, [])
        self.assertEqual(cursor, 0)
        self.assertEqual(len(reader.queries), 2)
        self.assertTrue(all("erosion_stage != 'retired'" in sql for sql in reader.queries))


if __name__ == "__main__":
    unittest.main()
