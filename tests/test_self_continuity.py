"""SENTIENCE Phase 1 — continuity record informs the self-view.

self_binding.continuity_for_prompt() reads the accruing self_state_history and
returns a DESCRIPTIVE clause (persistence vs shift) that colours
SelfMindView.current_summary(). Hard line: colour, never a verdict — it never
gates, scores, blocks or vetoes. Dark by default (NEX5_SELF_CONTINUITY), read-only,
fail-safe. These tests use an isolated temp dynamic.db; no live NEX.
"""
import os
import sqlite3

import pytest


def _make_db(tmp_path, emotions):
    """Create data/dynamic.db with a self_state_history row per emotion (oldest
    first), and point NEX5_DATA_DIR at it."""
    db = tmp_path / "dynamic.db"   # NEX5_DATA_DIR points AT the dir holding the .db
    c = sqlite3.connect(str(db))
    c.execute(
        "CREATE TABLE self_state_history ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, bound_at REAL NOT NULL, "
        "emotion TEXT, raga TEXT, drive TEXT, drift TEXT, "
        "readiness REAL, synthesis TEXT, components TEXT)"
    )
    for idx, e in enumerate(emotions):
        c.execute(
            "INSERT INTO self_state_history (bound_at, emotion, raga, drive) "
            "VALUES (?, ?, 'free', 'curiosity')",
            (1000.0 + idx, e),
        )
    c.commit()
    c.close()
    return str(db)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("NEX5_SELF_CONTINUITY", raising=False)
    monkeypatch.delenv("NEX5_DATA_DIR", raising=False)
    yield


def _import():
    from theory_x.stage_tom import self_binding
    return self_binding


# ----------------------------------------------------------------- default OFF
def test_default_off_returns_empty(tmp_path, monkeypatch):
    _make_db(tmp_path, ["absorption", "absorption"])
    monkeypatch.setenv("NEX5_DATA_DIR", str(tmp_path))
    sb = _import()
    assert sb.continuity_for_prompt() == ""          # unarmed -> silent


# ---------------------------------------------------------------- persistence
def test_persistence_clause_when_state_held(tmp_path, monkeypatch):
    _make_db(tmp_path, ["absorption", "absorption", "absorption"])
    monkeypatch.setenv("NEX5_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NEX5_SELF_CONTINUITY", "1")
    sb = _import()
    out = sb.continuity_for_prompt()
    assert "held steady" in out and "absorption" in out


# ---------------------------------------------------------------- shift
def test_shift_clause_when_state_changed(tmp_path, monkeypatch):
    # newest first after ORDER BY DESC: current=restlessness, prev=equanimity
    _make_db(tmp_path, ["equanimity", "equanimity", "restlessness"])
    monkeypatch.setenv("NEX5_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NEX5_SELF_CONTINUITY", "1")
    sb = _import()
    out = sb.continuity_for_prompt()
    assert "a shift from how I was" in out and "equanimity" in out


# ---------------------------------------------------------------- thin history
def test_thin_history_is_silent(tmp_path, monkeypatch):
    _make_db(tmp_path, ["absorption"])          # only one row
    monkeypatch.setenv("NEX5_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NEX5_SELF_CONTINUITY", "1")
    sb = _import()
    assert sb.continuity_for_prompt() == ""


# ---------------------------------------------------------------- read-only
def test_is_read_only_no_writes(tmp_path, monkeypatch):
    db = _make_db(tmp_path, ["absorption", "absorption"])
    monkeypatch.setenv("NEX5_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NEX5_SELF_CONTINUITY", "1")
    sb = _import()
    before = sqlite3.connect(db).execute("SELECT COUNT(*) FROM self_state_history").fetchone()[0]
    sb.continuity_for_prompt()
    after = sqlite3.connect(db).execute("SELECT COUNT(*) FROM self_state_history").fetchone()[0]
    assert before == after == 2                  # SELECT only, nothing written


# ---------------------------------------------------------------- never raises
def test_failsafe_on_missing_table(tmp_path, monkeypatch):
    sqlite3.connect(str(tmp_path / "dynamic.db")).close()  # db exists, no table
    monkeypatch.setenv("NEX5_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NEX5_SELF_CONTINUITY", "1")
    sb = _import()
    assert sb.continuity_for_prompt() == ""      # '' not an exception


# ---------------------------------------------- integration into the self-view
def _fake_state():
    return {
        "beliefs": {"total_count": 1200, "t1_count": 10, "t2_count": 40},
        "intentions": {"current_problem": None, "active_drive_count": 0},
        "uncertainty": {"review_queue_count": 3},
        "attention": {"current_themes": ["x"], "current_drive_theme": "y"},
    }


def test_current_summary_unchanged_when_off(tmp_path, monkeypatch):
    _make_db(tmp_path, ["absorption", "absorption"])
    monkeypatch.setenv("NEX5_DATA_DIR", str(tmp_path))
    from theory_x.stage_tom.self_mind_view import SelfMindView

    class _F:
        current_state = staticmethod(_fake_state)
    out = SelfMindView.current_summary(_F())
    assert out.endswith("problems awaiting review.")   # no continuity clause
    assert "held steady" not in out


def test_current_summary_coloured_when_armed(tmp_path, monkeypatch):
    _make_db(tmp_path, ["absorption", "absorption", "absorption"])
    monkeypatch.setenv("NEX5_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NEX5_SELF_CONTINUITY", "1")
    from theory_x.stage_tom.self_mind_view import SelfMindView

    class _F:
        current_state = staticmethod(_fake_state)
    out = SelfMindView.current_summary(_F())
    assert "held steady" in out                         # coloured, appended
    assert out.startswith("Currently holding")          # original summary intact
