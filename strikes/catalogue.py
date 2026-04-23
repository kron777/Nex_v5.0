"""Strike catalogue — Jon's observation notebook.

Uses direct sqlite3.connect() intentionally. Strike records are observation
data, not operational substrate. The one-pen rule applies to NEX's operational
databases; this catalogue is separate.

The DB lives at <data_dir>/strikes_catalogue.db.
"""
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from substrate.paths import data_dir

THEORY_X_STAGE = None

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS strike_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    strike_type     TEXT NOT NULL,
    fired_at        REAL NOT NULL,
    input_text      TEXT NOT NULL DEFAULT '',
    response_text   TEXT NOT NULL DEFAULT '',
    fountain_fired  INTEGER NOT NULL DEFAULT 0,
    beliefs_before  INTEGER NOT NULL DEFAULT 0,
    beliefs_after   INTEGER NOT NULL DEFAULT 0,
    hottest_branch  TEXT,
    readiness_score REAL,
    notes           TEXT NOT NULL DEFAULT ''
);
"""
_CREATE_INDEX = "CREATE INDEX IF NOT EXISTS idx_strike_ts ON strike_records(fired_at);"


@dataclass
class StrikeRecord:
    id: int
    strike_type: str
    fired_at: float
    input_text: str
    response_text: str
    fountain_fired: bool
    beliefs_before: int
    beliefs_after: int
    hottest_branch: str
    readiness_score: float
    notes: str


def _catalogue_path() -> Path:
    return data_dir() / "strikes_catalogue.db"


class StrikeCatalogue:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self._path = str(db_path) if db_path else str(_catalogue_path())
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, isolation_level=None)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(_CREATE_TABLE)
            conn.execute(_CREATE_INDEX)

    def save(self, record: StrikeRecord) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO strike_records "
                "(strike_type, fired_at, input_text, response_text, fountain_fired, "
                "beliefs_before, beliefs_after, hottest_branch, readiness_score, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record.strike_type,
                    record.fired_at,
                    record.input_text,
                    record.response_text,
                    int(record.fountain_fired),
                    record.beliefs_before,
                    record.beliefs_after,
                    record.hottest_branch,
                    record.readiness_score,
                    record.notes,
                ),
            )
            return cur.lastrowid

    def update_notes(self, id: int, notes: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE strike_records SET notes=? WHERE id=?", (notes, id)
            )

    def update_beliefs_after(self, id: int, beliefs_after: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE strike_records SET beliefs_after=? WHERE id=?",
                (beliefs_after, id),
            )

    def recent(self, limit: int = 20) -> list[StrikeRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM strike_records ORDER BY fired_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            StrikeRecord(
                id=r["id"],
                strike_type=r["strike_type"],
                fired_at=r["fired_at"],
                input_text=r["input_text"],
                response_text=r["response_text"],
                fountain_fired=bool(r["fountain_fired"]),
                beliefs_before=r["beliefs_before"],
                beliefs_after=r["beliefs_after"],
                hottest_branch=r["hottest_branch"] or "",
                readiness_score=r["readiness_score"] or 0.0,
                notes=r["notes"],
            )
            for r in rows
        ]
