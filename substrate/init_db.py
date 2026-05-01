"""Initialize all substrate databases.

Creates the data directory, opens a Writer per database (which creates
the file and sets WAL mode), applies the schema, and seeds keystone
beliefs into beliefs.db.

Run:
    python -m substrate.init_db

Idempotent — every schema statement uses IF NOT EXISTS; keystone
seeding uses INSERT OR IGNORE.
"""
from __future__ import annotations

import logging
import re
import sqlite3
import sys
from pathlib import Path

from .paths import data_dir, db_paths
from .writer import Writer

THEORY_X_STAGE = None

logger = logging.getLogger("substrate.init_db")

_SCHEMA_DIR = Path(__file__).parent / "schema"

_SCHEMA_FOR_DB = {
    "beliefs":       "beliefs.sql",
    "sense":         "sense.sql",
    "dynamic":       "dynamic.sql",
    "intel":         "intel.sql",
    "conversations": "conversations.sql",
    "probes":        "probes.sql",
}


def _split_sql(text: str) -> list[str]:
    # Strip SQL line comments and split on ';' — our schema files do not
    # use ';' inside literals, so this is sufficient.
    stripped = re.sub(r"--[^\n]*", "", text)
    return [s.strip() for s in stripped.split(";") if s.strip()]


def _apply_schema(writer: Writer, schema_path: Path) -> int:
    sql_text = schema_path.read_text()
    statements = _split_sql(sql_text)
    applied = 0
    for stmt in statements:
        if re.match(r"ALTER\s+TABLE\b", stmt, re.I):
            # ALTER TABLE belongs in _apply_migrations(), not schema files.
            # Skipping here prevents duplicate-column crashes on re-init.
            logger.warning("Skipping ALTER TABLE in schema file %s — use _MIGRATIONS instead", schema_path.name)
            continue
        writer.write(stmt, ())
        applied += 1
    return applied


_MIGRATIONS: dict[str, list[str]] = {
    "beliefs": [
        "CREATE TABLE IF NOT EXISTS belief_edges ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "source_id INTEGER NOT NULL REFERENCES beliefs(id), "
        "target_id INTEGER NOT NULL REFERENCES beliefs(id), "
        "edge_type TEXT NOT NULL CHECK (edge_type IN ("
        "'supports','opposes','synthesises','cross_domain','refines')), "
        "weight REAL NOT NULL DEFAULT 0.5, "
        "created_at REAL NOT NULL, "
        "last_traversed_at REAL)",
        "CREATE INDEX IF NOT EXISTS idx_edges_source ON belief_edges(source_id)",
        "CREATE INDEX IF NOT EXISTS idx_edges_target ON belief_edges(target_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_edges_pair "
        "ON belief_edges(source_id, target_id, edge_type)",
        "CREATE TABLE IF NOT EXISTS belief_blacklist ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "pattern TEXT NOT NULL UNIQUE, "
        "reason TEXT NOT NULL DEFAULT '', "
        "added_at REAL NOT NULL)",
        "CREATE INDEX IF NOT EXISTS idx_blacklist_pattern ON belief_blacklist(pattern)",
        "ALTER TABLE beliefs ADD COLUMN reinforce_count INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE beliefs ADD COLUMN use_count INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE beliefs ADD COLUMN erosion_stage TEXT NOT NULL DEFAULT 'external'",
        "CREATE TABLE IF NOT EXISTS koan_reads ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "gate_id TEXT NOT NULL, "
        "read_at REAL NOT NULL)",
        "CREATE INDEX IF NOT EXISTS idx_koan_reads_gate ON koan_reads(gate_id)",
        "CREATE TABLE IF NOT EXISTS synergizer_log ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "ts REAL NOT NULL, "
        "belief_id_a INTEGER NOT NULL, "
        "belief_id_b INTEGER NOT NULL, "
        "result_content TEXT, "
        "result_belief_id INTEGER)",
        "CREATE INDEX IF NOT EXISTS idx_synergizer_ts ON synergizer_log(ts)",
        "CREATE TABLE IF NOT EXISTS fountain_crystallizations ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "fountain_event_id INTEGER NOT NULL, "
        "belief_id INTEGER NOT NULL, "
        "ts REAL NOT NULL, "
        "content TEXT NOT NULL)",
        "CREATE INDEX IF NOT EXISTS idx_crystal_event ON fountain_crystallizations(fountain_event_id)",
        "CREATE INDEX IF NOT EXISTS idx_crystal_belief ON fountain_crystallizations(belief_id)",
        "CREATE TABLE IF NOT EXISTS speech_queue ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "belief_id INTEGER NOT NULL, "
        "content TEXT NOT NULL, "
        "voice TEXT DEFAULT 'af_bella', "
        "queued_at REAL NOT NULL, "
        "spoken_at REAL, "
        "status TEXT DEFAULT 'pending', "
        "error TEXT, "
        "FOREIGN KEY (belief_id) REFERENCES beliefs(id))",
        "CREATE INDEX IF NOT EXISTS idx_speech_queue_status "
        "ON speech_queue(status, queued_at)",
        "UPDATE speech_queue SET voice='af_sarah' "
        "WHERE voice='af_bella' AND status='pending'",
        "CREATE TABLE IF NOT EXISTS config ("
        "key TEXT PRIMARY KEY, "
        "value TEXT NOT NULL, "
        "updated_at REAL NOT NULL)",
        "CREATE TABLE IF NOT EXISTS belief_activation ("
        "belief_id INTEGER PRIMARY KEY, "
        "activation REAL NOT NULL DEFAULT 0.0, "
        "last_touched_at REAL NOT NULL, "
        "FOREIGN KEY (belief_id) REFERENCES beliefs(id))",
        "CREATE INDEX IF NOT EXISTS idx_belief_activation_at "
        "ON belief_activation(last_touched_at)",
    ],
    "dynamic": [
        "CREATE TABLE IF NOT EXISTS harmonizer_events ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, "
        "belief_id_a INTEGER, belief_id_b INTEGER, resolution TEXT, "
        "synthesis_belief_id INTEGER)",
        "CREATE TABLE IF NOT EXISTS fountain_events ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, "
        "thought TEXT NOT NULL, droplet TEXT, readiness REAL NOT NULL, "
        "hot_branch TEXT, word_count INTEGER)",
        "CREATE INDEX IF NOT EXISTS idx_fountain_ts ON fountain_events(ts)",
        "CREATE INDEX IF NOT EXISTS idx_fountain_droplet ON fountain_events(droplet)",
        "ALTER TABLE fountain_events ADD COLUMN droplet TEXT",
        "CREATE TABLE IF NOT EXISTS drive_proposals ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "ts REAL NOT NULL, "
        "branch_id TEXT NOT NULL, "
        "pressure REAL NOT NULL, "
        "representative_beliefs TEXT NOT NULL, "
        "proposed_curiosity REAL NOT NULL, "
        "status TEXT NOT NULL DEFAULT 'pending')",
        "CREATE TABLE IF NOT EXISTS substrate_fires ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "ts REAL NOT NULL, "
        "parallel_fire_id INTEGER, "
        "output TEXT NOT NULL, "
        "activated_belief_id INTEGER, "
        "activation_value REAL)",
        "CREATE INDEX IF NOT EXISTS idx_substrate_fires_ts ON substrate_fires(ts)",
        # Phase 1 — stillness instrumentation
        "ALTER TABLE fountain_events ADD COLUMN stillness_reason TEXT",
        "CREATE TABLE IF NOT EXISTS stillness_log ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "ts REAL NOT NULL, "
        "reason TEXT NOT NULL, "
        "retrieval_signature TEXT, "
        "consecutive_stillness_count INTEGER, "
        "jaccard REAL)",
        "CREATE INDEX IF NOT EXISTS idx_stillness_ts ON stillness_log(ts)",
        "ALTER TABLE stillness_log ADD COLUMN jaccard REAL",
    ],
    "conversations": [
        "CREATE TABLE IF NOT EXISTS open_problems ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "title TEXT NOT NULL, "
        "description TEXT NOT NULL, "
        "state TEXT NOT NULL DEFAULT 'open', "
        "created_at REAL NOT NULL, "
        "last_touched_at REAL NOT NULL, "
        "plan TEXT NOT NULL DEFAULT '', "
        "observations TEXT NOT NULL DEFAULT '[]', "
        "resolved_at REAL)",
        "CREATE INDEX IF NOT EXISTS idx_problems_state ON open_problems(state)",
        "ALTER TABLE messages ADD COLUMN tool_used TEXT",
    ],
}


_ALTER_COL_RE = re.compile(
    r"ALTER\s+TABLE\s+(\w+)\s+ADD\s+COLUMN\s+(\w+)", re.I
)


def _column_exists(db_path: str, table: str, column: str) -> bool:
    """Read-only PRAGMA check via direct sqlite3 — safe alongside WAL Writer."""
    try:
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
            rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
            return any(row[1] == column for row in rows)
    except Exception:
        return False  # DB not yet created or unreadable — let the write proceed


def _apply_migrations(writers: dict[str, Writer]) -> None:
    """Apply additive migrations for existing databases.

    ALTER TABLE ADD COLUMN statements are pre-checked via PRAGMA table_info
    so the column-already-exists case is skipped before touching the Writer.
    This prevents the Writer's worker thread from logging a spurious ERROR for
    an expected, harmless condition on existing databases.
    """
    for db_name, stmts in _MIGRATIONS.items():
        w = writers.get(db_name)
        if w is None:
            continue
        for stmt in stmts:
            m = _ALTER_COL_RE.match(stmt.strip())
            if m:
                table, col = m.group(1), m.group(2)
                if _column_exists(w.db_path, table, col):
                    continue  # column already exists — skip silently
            try:
                w.write(stmt, ())
            except Exception:
                pass  # CREATE IF NOT EXISTS etc. are idempotent; swallow any remainder


def init_all() -> None:
    data_dir().mkdir(parents=True, exist_ok=True)
    paths = db_paths()
    writers: dict[str, Writer] = {}
    try:
        for name, path in paths.items():
            schema_file = _SCHEMA_DIR / _SCHEMA_FOR_DB[name]
            w = Writer(path, name=name)
            writers[name] = w
            applied = _apply_schema(w, schema_file)
            logger.info("Initialized %s (%d statements)", path, applied)

        # Apply additive column migrations for existing DBs (idempotent)
        _apply_migrations(writers)

        # Seed Tier 1 keystones into beliefs.db.
        from keystone import reseed as keystone_reseed
        keystone_reseed(writers["beliefs"])
        logger.info("Keystone seeds applied to beliefs.db")

        # Seed contamination blacklist.
        from substrate.blacklist_seeds import seed_blacklist
        seed_blacklist(writers["beliefs"])
        logger.info("Blacklist seeds applied to beliefs.db")

        # Seed koan beta beliefs.
        from substrate.koan_seeds import seed_koans
        seed_koans(writers["beliefs"])
        logger.info("Koan beta beliefs seeded to beliefs.db")
    finally:
        for w in writers.values():
            w.close()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s"
    )
    init_all()
    print("Substrate initialized.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
