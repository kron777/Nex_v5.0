"""
probes_db.py — SQLite schema and I/O for probe results.

All probe runs are recorded in data/probes.db (already exists in NEX5).
This module initialises the schema if absent and provides typed read/write.
"""
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


DB_PATH = Path(__file__).resolve().parents[2] / "data" / "probes.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS probe_runs (
    probe_run_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    condition_hash    TEXT    NOT NULL,
    mode              TEXT    NOT NULL,
    sense_pattern     TEXT    NOT NULL,
    prior_context     TEXT    NOT NULL,
    prompt_framing    TEXT    NOT NULL,
    foundation_type   TEXT    NOT NULL,
    rep_index         INTEGER NOT NULL,  -- 0-based within condition
    output_text       TEXT,
    output_template   TEXT,   -- ABSTRACT_NOMINAL | DIALECTICAL | SENSE_OBS |
                               --   SIMILE | QUESTION | ACTION | RECEPTIVITY |
                               --   UNCATEGORIZED | ERROR | TIMEOUT
    output_register   TEXT,   -- observer | action | question | mixed | unknown
    belief_id         INTEGER,  -- beliefs.id if crystallized, NULL otherwise
    fired_at          REAL    NOT NULL,
    notes             TEXT
);

CREATE INDEX IF NOT EXISTS idx_probe_runs_hash
    ON probe_runs (condition_hash);

CREATE INDEX IF NOT EXISTS idx_probe_runs_mode
    ON probe_runs (mode);

CREATE INDEX IF NOT EXISTS idx_probe_runs_fired_at
    ON probe_runs (fired_at);

CREATE TABLE IF NOT EXISTS probe_conditions (
    condition_hash    TEXT    PRIMARY KEY,
    mode              TEXT    NOT NULL,
    sense_pattern     TEXT    NOT NULL,
    prior_context     TEXT    NOT NULL,
    prompt_framing    TEXT    NOT NULL,
    foundation_type   TEXT    NOT NULL,
    n_reps            INTEGER NOT NULL,
    created_at        REAL    NOT NULL,
    notes             TEXT
);
"""


@dataclass
class ProbeResult:
    condition_hash: str
    mode: str
    sense_pattern: str
    prior_context: str
    prompt_framing: str
    foundation_type: str
    rep_index: int
    output_text: Optional[str]
    output_template: Optional[str]
    output_register: Optional[str]
    belief_id: Optional[int] = None
    fired_at: float = 0.0
    notes: str = ""

    def __post_init__(self):
        if self.fired_at == 0.0:
            self.fired_at = time.time()


class ProbesDB:
    """Thread-safe (one writer) SQLite I/O for probe results."""

    def __init__(self, db_path: Path = DB_PATH):
        self._path = db_path
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def upsert_condition(self, condition) -> None:
        """Record a ProbeCondition in the conditions table."""
        self._conn.execute(
            """INSERT OR REPLACE INTO probe_conditions
               (condition_hash, mode, sense_pattern, prior_context,
                prompt_framing, foundation_type, n_reps, created_at, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, strftime('%s','now'), ?)""",
            (
                condition.condition_hash(),
                condition.mode,
                condition.sense_pattern,
                condition.prior_context,
                condition.prompt_framing,
                condition.foundation_type,
                condition.n_reps,
                condition.notes,
            ),
        )
        self._conn.commit()

    def insert_result(self, result: ProbeResult) -> int:
        cur = self._conn.execute(
            """INSERT INTO probe_runs
               (condition_hash, mode, sense_pattern, prior_context,
                prompt_framing, foundation_type, rep_index,
                output_text, output_template, output_register,
                belief_id, fired_at, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                result.condition_hash,
                result.mode,
                result.sense_pattern,
                result.prior_context,
                result.prompt_framing,
                result.foundation_type,
                result.rep_index,
                result.output_text,
                result.output_template,
                result.output_register,
                result.belief_id,
                result.fired_at,
                result.notes,
            ),
        )
        self._conn.commit()
        return cur.lastrowid

    def fetch_condition_results(self, condition_hash: str) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM probe_runs WHERE condition_hash = ? ORDER BY fired_at",
            (condition_hash,),
        ).fetchall()

    def fetch_all_results(self) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM probe_runs ORDER BY fired_at"
        ).fetchall()

    def template_counts_by_condition(self) -> list[sqlite3.Row]:
        return self._conn.execute(
            """SELECT condition_hash, mode, sense_pattern, prior_context,
                      prompt_framing, foundation_type,
                      output_template, COUNT(*) as n
               FROM probe_runs
               WHERE output_template IS NOT NULL
               GROUP BY condition_hash, output_template
               ORDER BY condition_hash, n DESC"""
        ).fetchall()

    def close(self) -> None:
        self._conn.close()


def init_db(db_path: Path = DB_PATH) -> ProbesDB:
    return ProbesDB(db_path)
