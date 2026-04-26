"""Probes DB — schema lives in substrate/schema/probes.sql.

init_probes_db() is provided for test helpers that need to create a
standalone probes.db at an arbitrary path. Production init goes through
substrate.init_db.init_all() which handles probes.db automatically.
"""
from __future__ import annotations

import re
from pathlib import Path

THEORY_X_STAGE = None

_SCHEMA_PATH = Path(__file__).parent.parent.parent / "substrate" / "schema" / "probes.sql"


def init_probes_db(path=None) -> None:
    """Initialize probes.db schema at the given path using the substrate Writer.

    When path is None this is a no-op — production code uses init_all()
    which now includes probes in db_paths().
    """
    if path is None:
        return
    from substrate.writer import Writer
    sql_text = _SCHEMA_PATH.read_text()
    stmts = [s.strip() for s in re.sub(r"--[^\n]*", "", sql_text).split(";") if s.strip()]
    w = Writer(Path(path), name="probes")
    try:
        for stmt in stmts:
            w.write(stmt, ())
    finally:
        w.close()
