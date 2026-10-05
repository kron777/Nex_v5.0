"""Database path resolution for the substrate.

Data root defaults to <repo>/data/, overridable via NEX5_DATA_DIR.
Separate DB files per concern — separate files mean separate locks.

See SPECIFICATION.md §8 — Separate Databases per Concern.
"""
from __future__ import annotations

import os
from pathlib import Path

THEORY_X_STAGE = None

_REPO_ROOT = Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    override = os.environ.get("NEX5_DATA_DIR")
    return Path(override) if override else _REPO_ROOT / "data"


def db_paths() -> dict[str, Path]:
    root = data_dir()
    return {
        "beliefs":       root / "beliefs.db",
        "sense":         root / "sense.db",
        "dynamic":       root / "dynamic.db",
        "intel":         root / "intel.db",
        "conversations": root / "conversations.db",
        "probes":        root / "probes.db",
    }


class DbPath(os.PathLike):
    """A DB path resolved at USE time, so NEX5_DATA_DIR is honoured even by
    module-level constants bound at import. Drop-in for the old hardcoded
    Path("/home/rr/.../nex5/data/<name>.db") constants: os.fspath()/str()
    resolve via db_paths(), so sqlite3.connect(DB), f"file:{DB}?mode=ro" and
    Path(DB) all work. In production (NEX5_DATA_DIR unset) this resolves to the
    same <repo>/data/<name>.db as before.
    """

    def __init__(self, name: str) -> None:
        self._name = name

    def __fspath__(self) -> str:
        return str(db_paths()[self._name])

    def __str__(self) -> str:
        return self.__fspath__()

    def __repr__(self) -> str:
        return f"DbPath({self._name!r} -> {self.__fspath__()})"
