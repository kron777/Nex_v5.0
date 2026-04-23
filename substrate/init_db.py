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
        writer.write(stmt, ())
        applied += 1
    return applied


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

        # Seed Tier 1 keystones into beliefs.db.
        from keystone import reseed as keystone_reseed
        keystone_reseed(writers["beliefs"])
        logger.info("Keystone seeds applied to beliefs.db")
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
