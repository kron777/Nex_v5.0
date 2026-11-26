"""Belief promotion eligibility regression tests."""


def test_corroborate_rejects_paused_belief_without_writes():
    from theory_x.stage3_world_model.promotion import BeliefPromoter

    class Reader:
        def read_one(self, sql, params=()):
            assert "paused" in sql
            return {
                "id": 17,
                "content": "paused belief",
                "tier": 7,
                "corroboration_count": 10,
                "locked": 0,
                "paused": 1,
            }

    class Writer:
        def __init__(self):
            self.calls = []

        def write(self, sql, params=()):
            self.calls.append((sql, params))

    writer = Writer()
    promoter = BeliefPromoter(writer, Reader())

    assert promoter.corroborate(17) is False
    assert writer.calls == []
