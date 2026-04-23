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
    }
