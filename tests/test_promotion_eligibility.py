"""Belief promotion eligibility regression tests."""


def test_corroborate_rejects_paused_and_retired_beliefs_without_writes():
    from theory_x.stage3_world_model.promotion import BeliefPromoter

    class Reader:
        def __init__(self, row):
            self.row = row

        def read_one(self, sql, params=()):
            assert "paused" in sql
            assert "erosion_stage" in sql
            return self.row

    class Writer:
        def __init__(self):
            self.calls = []

        def write(self, sql, params=()):
            self.calls.append((sql, params))

    inactive_rows = (
        {
            "id": 17, "content": "paused belief", "tier": 7,
            "corroboration_count": 10, "locked": 0, "paused": 1,
            "erosion_stage": "external",
        },
        {
            "id": 18, "content": "retired belief", "tier": 7,
            "corroboration_count": 10, "locked": 0, "paused": 0,
            "erosion_stage": "retired",
        },
    )

    for row in inactive_rows:
        writer = Writer()
        promoter = BeliefPromoter(writer, Reader(row))
        assert promoter.corroborate(row["id"]) is False
        assert writer.calls == []


def test_survive_challenge_rejects_inactive_and_retired_beliefs_without_writes():
    from theory_x.stage3_world_model.promotion import BeliefPromoter

    class Reader:
        def __init__(self, row):
            self.row = row

        def read_one(self, sql, params=()):
            assert "paused" in sql
            assert "erosion_stage" in sql
            return self.row

    class Writer:
        def __init__(self):
            self.calls = []

        def write(self, sql, params=()):
            self.calls.append((sql, params))

    ineligible_rows = (
        {
            "id": 21, "tier": 6, "locked": 0, "paused": 1,
            "erosion_stage": "external",
        },
        {
            "id": 22, "tier": 7, "locked": 0, "paused": 0,
            "erosion_stage": "retired",
        },
        {
            "id": 23, "tier": 8, "locked": 0, "paused": 0,
            "erosion_stage": "retired",
        },
        {
            "id": 24, "tier": 8, "locked": 0, "paused": 0,
            "erosion_stage": "external",
        },
    )

    for row in ineligible_rows:
        writer = Writer()
        promoter = BeliefPromoter(writer, Reader(row))
        assert promoter.survive_challenge(row["id"]) is False
        assert writer.calls == []
