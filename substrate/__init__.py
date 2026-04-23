"""One-pen substrate for NEX 5.0.

Public surface:
    Writer, WriteRequest — the single writer per DB (§8)
    Reader                — WAL-mode concurrent readers (§8)
    db_paths, data_dir    — path resolution (§8)
"""
from .paths import data_dir, db_paths
from .reader import Reader
from .writer import WriteRequest, Writer

THEORY_X_STAGE = None

__all__ = [
    "Writer",
    "WriteRequest",
    "Reader",
    "db_paths",
    "data_dir",
]
