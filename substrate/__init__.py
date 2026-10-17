"""One-pen substrate for NEX 5.0.

Public surface:
    Writer, WriteRequest — the single writer per DB (§8)
    Reader                — WAL-mode concurrent readers (§8)
    connect               — canonical connection factory (WAL + FK + timeout)
    db_paths, data_dir    — path resolution (§8)
"""
from .db import (
    Connection,
    Cursor,
    DatabaseError,
    Error,
    IntegrityError,
    OperationalError,
    Row,
    connect,
)
from .paths import data_dir, db_paths
from .reader import Reader
from .writer import WriteRequest, Writer

THEORY_X_STAGE = None

__all__ = [
    "Writer",
    "WriteRequest",
    "Reader",
    "connect",
    "Row",
    "Connection",
    "Cursor",
    "Error",
    "IntegrityError",
    "OperationalError",
    "DatabaseError",
    "db_paths",
    "data_dir",
]
