from substrate import Reader, Writer, connect
from theory_x.signals import prose_stats


def _seed_beliefs(path):
    cx = connect(path)
    try:
        cx.execute(
            "CREATE TABLE beliefs ("
            "id INTEGER PRIMARY KEY, content TEXT, source TEXT)"
        )
        cx.executemany(
            "INSERT INTO beliefs (content, source) VALUES (?, ?)",
            [
                (
                    "the city Beijing has a river and a quiet square",
                    "precipitated_from_sense",
                ),
                (
                    "the company Postgres supports reliable database systems",
                    "precipitated_from_sense",
                ),
                (
                    "Ancient Rome Shines Bright Today",
                    "precipitated_from_sense",
                ),
                (
                    "the city Wellington has a harbour and green hills",
                    "other_source",
                ),
            ],
        )
        cx.commit()
    finally:
        cx.close()


def _stats(reader):
    rows = reader.read(
        "SELECT token, prose_cap, prose_lower "
        "FROM token_prose_stats ORDER BY token"
    )
    return {
        row["token"]: (row["prose_cap"], row["prose_lower"])
        for row in rows
    }


def test_writer_reader_build_matches_direct_builder(tmp_path):
    writer_db = tmp_path / "writer.db"
    direct_db = tmp_path / "direct.db"
    _seed_beliefs(writer_db)
    _seed_beliefs(direct_db)

    writer = Writer(writer_db, name="prose-stats-test")
    writer_reader = Reader(writer_db)
    direct_reader = Reader(direct_db)
    try:
        writer_count = prose_stats.build(writer, writer_reader)
        direct_count = prose_stats.build_direct(direct_db)

        writer_stats = _stats(writer_reader)
        direct_stats = _stats(direct_reader)

        assert writer_count > 0
        assert writer_count == direct_count
        assert writer_stats == direct_stats
        assert writer_stats["beijing"][0] == 1
        assert writer_stats["postgres"][0] == 1
        assert "wellington" not in writer_stats
    finally:
        writer.close()
