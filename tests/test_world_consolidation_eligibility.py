"""Eligibility regression tests for world consolidation."""


def test_world_consolidation_scan_excludes_paused_beliefs(monkeypatch):
    import theory_x.diversity.embeddings as embeddings
    from theory_x.stage3_world_model.world_consolidation import WorldConsolidator

    class Reader:
        def __init__(self):
            self.queries = []

        def read(self, sql, params=()):
            self.queries.append((sql, params))
            return []

    reader = Reader()
    monkeypatch.setattr(embeddings, "embed", lambda _content: [1.0])
    monkeypatch.setattr(embeddings, "cosine", lambda _a, _b: 1.0)
    monkeypatch.setenv("NEX5_WORLD_CONSOLIDATE", "dry")

    result = WorldConsolidator(reader, promoter=object()).tick()

    assert result["state"] == "idle"
    assert len(reader.queries) == 1
    assert "paused = 0" in reader.queries[0][0]


def test_paused_shallow_duplicate_does_not_suppress_active_candidate(monkeypatch):
    import theory_x.diversity.embeddings as embeddings
    from theory_x.stage3_world_model.world_consolidation import WorldConsolidator

    class Reader:
        def __init__(self):
            self.queries = []

        def read(self, sql, params=()):
            self.queries.append((sql, params))
            if "tier = 7" in sql:
                return [
                    {"id": 1, "content": "A sufficiently long world knowledge statement about the natural world."},
                    {"id": 2, "content": "A sufficiently long world knowledge statement about natural systems."},
                    {"id": 3, "content": "A sufficiently long world knowledge statement about physical systems."},
                ]
            return []

    class Promoter:
        def corroborate(self, _belief_id):
            return False

    reader = Reader()
    monkeypatch.setattr(embeddings, "embed", lambda _content: [1.0])
    monkeypatch.setattr(embeddings, "cosine", lambda _a, _b: 1.0)
    monkeypatch.setenv("NEX5_WORLD_CONSOLIDATE", "1")

    WorldConsolidator(reader, promoter=Promoter()).tick()

    duplicate_queries = [sql for sql, _ in reader.queries if "tier < 7" in sql]
    assert duplicate_queries
    assert all("paused = 0" in sql for sql in duplicate_queries)
