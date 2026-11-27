"""Regression tests for Diversity EdgeBuilder write accounting."""

from substrate import Reader, Writer, connect
from theory_x.diversity import edge_builder


def test_edge_builder_wrote_counts_only_rows_inserted(tmp_path, monkeypatch):
    db_path = tmp_path / "beliefs.db"
    cx = connect(db_path)
    try:
        cx.execute(
            "CREATE TABLE beliefs ("
            "id INTEGER PRIMARY KEY, content TEXT NOT NULL, created_at REAL NOT NULL, "
            "paused INTEGER NOT NULL DEFAULT 0, locked INTEGER NOT NULL DEFAULT 0)"
        )
        cx.execute(
            "CREATE TABLE belief_edges ("
            "id INTEGER PRIMARY KEY, source_id INTEGER NOT NULL, target_id INTEGER NOT NULL, "
            "edge_type TEXT NOT NULL, weight REAL NOT NULL, created_at REAL NOT NULL, "
            "UNIQUE(source_id, target_id, edge_type))"
        )
        cx.executemany(
            "INSERT INTO beliefs (id, content, created_at, paused, locked) "
            "VALUES (?, ?, ?, 0, 0)",
            [
                (1, "A sufficiently long observation about one subject.", 1.0),
                (2, "A sufficiently long observation about another subject.", 2.0),
                (3, "A sufficiently long observation about a third subject.", 3.0),
            ],
        )
        # Deterministically ignore all edges aimed at belief 3. This models an
        # INSERT OR IGNORE outcome after earlier inserts have succeeded.
        cx.execute(
            "CREATE TRIGGER ignore_target_three BEFORE INSERT ON belief_edges "
            "WHEN NEW.target_id = 3 BEGIN SELECT RAISE(IGNORE); END"
        )
        cx.commit()
    finally:
        cx.close()

    monkeypatch.setattr(
        edge_builder, "embed_belief",
        lambda belief_id, content: [float(belief_id)],
    )
    monkeypatch.setattr(edge_builder, "cosine", lambda left, right: 0.9)

    stats = edge_builder.edge_builder_tick(db_path=db_path)

    check = connect(db_path)
    try:
        actual_edges = check.execute(
            "SELECT COUNT(*) FROM belief_edges"
        ).fetchone()[0]
    finally:
        check.close()

    assert stats["considered"] == 3
    assert actual_edges == 4
    assert stats["wrote"] == actual_edges

def test_edge_builder_uses_injected_substrate_handles(tmp_path, monkeypatch):
    db_path = tmp_path / "beliefs-injected.db"
    cx = connect(db_path)
    try:
        cx.execute(
            "CREATE TABLE beliefs ("
            "id INTEGER PRIMARY KEY, content TEXT NOT NULL, created_at REAL NOT NULL, "
            "paused INTEGER NOT NULL DEFAULT 0, locked INTEGER NOT NULL DEFAULT 0)"
        )
        cx.execute(
            "CREATE TABLE belief_edges ("
            "id INTEGER PRIMARY KEY, source_id INTEGER NOT NULL, target_id INTEGER NOT NULL, "
            "edge_type TEXT NOT NULL, weight REAL NOT NULL, created_at REAL NOT NULL, "
            "UNIQUE(source_id, target_id, edge_type))"
        )
        cx.executemany(
            "INSERT INTO beliefs (id, content, created_at, paused, locked) "
            "VALUES (?, ?, ?, 0, 0)",
            [
                (1, "A sufficiently long observation about one subject.", 1.0),
                (2, "A sufficiently long observation about another subject.", 2.0),
            ],
        )
        cx.commit()
    finally:
        cx.close()

    monkeypatch.setattr(
        edge_builder, "embed_belief",
        lambda belief_id, content: [float(belief_id)],
    )
    monkeypatch.setattr(edge_builder, "cosine", lambda left, right: 0.9)

    reader = Reader(db_path)
    writer = Writer(db_path, name="edge-builder-injected-test")
    try:
        stats = edge_builder.edge_builder_tick(
            beliefs_reader=reader,
            beliefs_writer=writer,
        )
        assert stats == {"considered": 2, "wrote": 2, "skipped": 0}
        assert reader.count("belief_edges") == 2
        # The injected Writer remains owned by the caller and operational.
        assert writer.write(
            "INSERT INTO belief_edges "
            "(source_id, target_id, edge_type, weight, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (1, 2, "test_extra", 0.1, 999.0),
        ) > 0
        assert reader.count("belief_edges") == 3
    finally:
        writer.close()
