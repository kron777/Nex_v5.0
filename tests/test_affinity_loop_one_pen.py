"""One-pen persistence tests for AffinityLoop."""
from __future__ import annotations

import time

from substrate import Reader, Writer, connect
from theory_x.life import affinity_loop


def _db(path):
    cx = connect(path)
    cx.execute(
        "CREATE TABLE beliefs ("
        "id INTEGER PRIMARY KEY, content TEXT, tier INTEGER, source TEXT, "
        "source_kind TEXT, reinforce_count INTEGER, use_count INTEGER, last_referenced_at REAL, "
        "affinity REAL, affinity_updated_at REAL)"
    )
    cx.execute(
        "CREATE TABLE belief_edges (id INTEGER PRIMARY KEY, source_id INTEGER)"
    )
    cx.execute(
        "INSERT INTO beliefs VALUES (1, 'A durable thought about attention', 6, "
        "'fountain_insight', 'authored', 0, 4, ?, NULL, NULL)",
        (time.time()-3600,),
    )
    cx.commit()
    cx.close()


def test_affinity_tick_uses_injected_writer_for_llm_mode(tmp_path, monkeypatch):
    db_path = tmp_path / "beliefs.db"
    _db(db_path)
    reader = Reader(db_path)
    writer = Writer(db_path, name="affinity-test")
    monkeypatch.setattr(affinity_loop, "_affinity_mode", lambda: "off")
    monkeypatch.setattr(affinity_loop, "_source_kind_on", lambda: False)
    monkeypatch.setattr(affinity_loop, "_self_rate", lambda voice, content: 0.8)
    try:
        result = affinity_loop.affinity_tick(
            object(), beliefs_reader=reader, beliefs_writer=writer
        )
        assert result["scored"] == 1
        assert result["mode"] == "off"
        row = reader.read_one(
            "SELECT affinity, affinity_updated_at FROM beliefs WHERE id=1"
        )
        assert row["affinity"] is not None
        assert 0.0 <= row["affinity"] <= 1.0
        assert row["affinity_updated_at"] is not None
    finally:
        writer.close()


def test_affinity_tick_provenance_mode_does_not_call_voice(tmp_path, monkeypatch):
    db_path = tmp_path / "beliefs.db"
    _db(db_path)
    reader = Reader(db_path)
    writer = Writer(db_path, name="affinity-provenance-test")
    monkeypatch.setattr(affinity_loop, "_affinity_mode", lambda: "on")
    monkeypatch.setattr(affinity_loop, "_source_kind_on", lambda: False)
    monkeypatch.setattr(affinity_loop, "_provenance_affinity", lambda *args: 0.91)
    monkeypatch.setattr(
        affinity_loop, "_self_rate",
        lambda *args: (_ for _ in ()).throw(AssertionError("voice must not be called")),
    )
    try:
        result = affinity_loop.affinity_tick(
            object(), beliefs_reader=reader, beliefs_writer=writer
        )
        assert result["scored"] == 1
        assert result["mode"] == "on"
        assert reader.read_one("SELECT affinity FROM beliefs WHERE id=1")[0] == 0.91
    finally:
        writer.close()
