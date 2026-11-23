"""Runtime snapshot extraction must use configured read-only DB paths."""
import time

from substrate import connect
from substrate.paths import db_paths
from scripts import nexsnap_extract


def _create_database(path, statements):
    conn = connect(path)
    try:
        for statement in statements:
            conn.execute(statement)
        conn.commit()
    finally:
        conn.close()


def test_runtime_state_uses_configured_data_dir_and_read_only_connections(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("NEX5_DATA_DIR", str(tmp_path))
    paths = db_paths()
    now = time.time()

    _create_database(paths["conversations"], [
        "CREATE TABLE drives_competing (id INTEGER PRIMARY KEY, coherence REAL, "
        "exploration REAL, integration REAL, self_preservation REAL, curiosity REAL, "
        "tension_pairs TEXT)",
        "INSERT INTO drives_competing VALUES (1, 0.1, 0.2, 0.3, 0.4, 0.5, 'pair')",
        "CREATE TABLE voice_profile (drive_pair TEXT, frequency INTEGER)",
        "INSERT INTO voice_profile VALUES ('care-curiosity', 7)",
    ])
    _create_database(paths["dynamic"], [
        "CREATE TABLE fountain_events (hot_branch TEXT, ts REAL)",
        f"INSERT INTO fountain_events VALUES ('reflection', {now})",
    ])
    _create_database(paths["beliefs"], [
        "CREATE TABLE gate_decisions (outcome TEXT, ts REAL)",
        f"INSERT INTO gate_decisions VALUES ('ACCEPT', {now})",
    ])

    state = nexsnap_extract.extract_runtime_state()

    assert state["drives"]["coherence"] == 0.1
    assert state["voice_profile"] == [{"pair": "care-curiosity", "freq": 7}]
    assert state["fountain_24h_by_branch"] == {"reflection": 1}
    assert state["gate_24h"] == {"ACCEPT": 1}


def test_runtime_state_closes_opened_connections_when_later_open_fails(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("NEX5_DATA_DIR", str(tmp_path))
    paths = db_paths()
    _create_database(paths["conversations"], [
        "CREATE TABLE drives_competing (id INTEGER PRIMARY KEY, coherence REAL, "
        "exploration REAL, integration REAL, self_preservation REAL, curiosity REAL, "
        "tension_pairs TEXT)",
        "CREATE TABLE voice_profile (drive_pair TEXT, frequency INTEGER)",
    ])
    _create_database(paths["dynamic"], [
        "CREATE TABLE fountain_events (hot_branch TEXT, ts REAL)",
    ])

    opened = []
    real_connect = nexsnap_extract.connect

    def tracking_connect(*args, **kwargs):
        if len(opened) == 2:
            raise RuntimeError("simulated third database open failure")
        conn = real_connect(*args, **kwargs)
        opened.append(conn)
        return conn

    monkeypatch.setattr(nexsnap_extract, "connect", tracking_connect)

    import pytest
    with pytest.raises(RuntimeError, match="simulated third database open failure"):
        nexsnap_extract.extract_runtime_state()

    assert len(opened) == 2
    for conn in opened:
        with pytest.raises(Exception):
            conn.execute("SELECT 1")
