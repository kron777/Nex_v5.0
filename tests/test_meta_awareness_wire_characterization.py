"""Characterize the currently unused Stage-1 MetaAwareness -> Stage-4 SelfModel edge.

These tests intentionally record current dataflow, not a desired cognitive
contract. They should be revised when the semantics of this connection are
decided and an explicit adapter/field mapping is implemented.
"""
from __future__ import annotations

import json
import unittest

from tests import _bootstrap  # noqa: F401


class _SenseReader:
    def __init__(self, payload):
        self.payload = payload

    def read_one(self, _sql, params=()):
        stream = params[0] if params else None
        if stream == "internal.meta_awareness":
            return {"payload": json.dumps(self.payload)}
        return None


class _BeliefsReader:
    def read(self, _sql, _params=()):
        return []


class _DynamicState:
    def __init__(self, status):
        self._status = status

    def status(self):
        return dict(self._status)


class TestMetaAwarenessWireCharacterization(unittest.TestCase):
    def test_stage1_payload_has_no_effect_without_dynamic_state(self):
        from theory_x.stage4_membrane.self_model import SelfModel

        sensor_payload = {
            "writer_queue_depths": {"beliefs": 7, "sense": 2},
            "error_channel_length": 3,
            "sense_global_running": True,
            "sense_adapter_count": 14,
            "sense_internal_count": 4,
            "sense_active_external_count": 10,
        }
        model = SelfModel(_SenseReader(sensor_payload), _BeliefsReader())
        snapshot = model.snapshot()

        # Stage 4 reads this payload into meta_p, but the returned fields
        # remain the initialized defaults when no DynamicState is attached.
        self.assertEqual(
            snapshot["meta_awareness"],
            {
                "pipeline_runs": None,
                "active_branches": None,
                "consolidation_active": None,
            },
        )

    def test_dynamic_state_populates_meta_fields_instead_of_stage1_payload(self):
        from theory_x.stage4_membrane.self_model import SelfModel

        sensor_payload = {
            "writer_queue_depths": {"beliefs": 99},
            "error_channel_length": 99,
            "sense_global_running": False,
            "sense_adapter_count": 99,
            "sense_internal_count": 99,
            "sense_active_external_count": 0,
        }
        dynamic_status = {
            "pipeline_runs": 12,
            "active_branch_count": 3,
            "consolidation_active": True,
            "branches": [],
            "aggregate_texture": 0.25,
        }
        model = SelfModel(
            _SenseReader(sensor_payload),
            _BeliefsReader(),
            dynamic_state=_DynamicState(dynamic_status),
        )
        snapshot = model.snapshot()

        self.assertEqual(
            snapshot["meta_awareness"],
            {
                "pipeline_runs": 12,
                "active_branches": 3,
                "consolidation_active": True,
            },
        )


if __name__ == "__main__":
    unittest.main()
