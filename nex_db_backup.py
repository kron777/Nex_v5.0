#!/usr/bin/env python3
"""nex_db_backup.py — online, WAL-safe backups of the live substrate DBs.

WHY: the reaper bounds table growth but there is no point-in-time copy to
recover from corruption, an accidental mass delete, or a bad migration.

HOW: SQLite's online backup API (sqlite3.Connection.backup) copies a
consistent snapshot while NEX keeps reading and writing — no VACUUM, no
exclusive lock, no process stop. Each copy is integrity-checked before it is
kept (a torn backup is discarded, never left looking good), and old copies
are rotated. restore_db() is the other half of the drill: it verifies a
backup's integrity, then atomically replaces a destination file.

Data dir is resolved via substrate.paths (honours NEX5_DATA_DIR) — no
hardcoded path, so this runs anywhere the package does.

Run:
  nex_db_backup.py                 # back up every live DB, rotate to --keep
  nex_db_backup.py --keep 7        # keep the 7 most recent per DB (default)
  nex_db_backup.py --list          # list existing backups
  nex_db_backup.py --restore <backup.db> --into <dest.db> [--force]
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

from substrate.paths import data_dir, db_paths

DEFAULT_KEEP = 7
BUSY_TIMEOUT_MS = 5000


def backup_root() -> Path:
    """Where backups live — beside the data dir, not inside it (so the reaper
    and the readers never mistake a backup for a live DB). Override via
    NEX5_BACKUP_DIR."""
    env = os.environ.get("NEX5_BACKUP_DIR")
    return Path(env) if env else (data_dir().parent / "nex5_backups")


def _integrity_ok(path: Path) -> bool:
    try:
        con = sqlite3.connect(
            f"file:{path}?mode=ro", uri=True, timeout=BUSY_TIMEOUT_MS / 1000.0
        )
        try:
            row = con.execute("PRAGMA integrity_check").fetchone()
            return bool(row) and row[0] == "ok"
        finally:
            con.close()
    except sqlite3.Error:
        return False


def backup_db(name: str, src_path: str | Path, dest_dir: Path) -> Path | None:
    """Online .backup of one DB into dest_dir; returns the backup path, or None
    if the copy failed its integrity check (in which case it is discarded)."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = dest_dir / f"{name}-{stamp}.db"
    src = sqlite3.connect(
        f"file:{src_path}?mode=ro", uri=True, timeout=BUSY_TIMEOUT_MS / 1000.0
    )
    try:
        dst = sqlite3.connect(str(dest))
        try:
            src.backup(dst)  # consistent online snapshot
        finally:
            dst.close()
    finally:
        src.close()
    if not _integrity_ok(dest):
        try:
            dest.unlink()
        except OSError:
            pass
        return None
    return dest


def rotate(name: str, dest_dir: Path, keep: int) -> list[Path]:
    """Delete all but the `keep` most recent backups for `name` (timestamped
    names sort chronologically). Returns the paths removed."""
    backups = sorted(dest_dir.glob(f"{name}-*.db"))
    doomed = backups[:-keep] if keep > 0 else backups
    removed = []
    for old in doomed:
        try:
            old.unlink()
            removed.append(old)
        except OSError:
            pass
    return removed


def backup_all(keep: int = DEFAULT_KEEP) -> dict[str, Path | None]:
    """Back up every live DB. Missing DBs map to None; present DBs map to the
    backup path (or None if its integrity check failed)."""
    root = backup_root()
    out: dict[str, Path | None] = {}
    for name, path in db_paths().items():
        if not Path(path).exists():
            out[name] = None
            continue
        made = backup_db(name, path, root)
        out[name] = made
        if made is not None:
            rotate(name, root, keep)
    return out


def _clear_wal_sidecars(dest: Path) -> None:
    # A restored main file must not inherit the previous DB's stale WAL/SHM.
    for suffix in ("-wal", "-shm"):
        side = dest.with_name(dest.name + suffix)
        try:
            side.unlink()
        except OSError:
            pass


def restore_db(backup_path: str | Path, dest_path: str | Path,
               *, force: bool = False) -> Path:
    """Restore a backup to dest_path. Verifies the backup first, refuses to
    overwrite an existing file unless force=True, and writes atomically so a
    crash mid-restore cannot leave a half-written live DB.

    Run with NEX stopped when restoring over a live DB.
    """
    backup_path = Path(backup_path)
    dest_path = Path(dest_path)
    if not _integrity_ok(backup_path):
        raise ValueError(f"backup failed integrity check: {backup_path}")
    if dest_path.exists() and not force:
        raise FileExistsError(f"refusing to overwrite {dest_path} (pass --force)")
    tmp = dest_path.with_name(dest_path.name + ".restoring")
    src = sqlite3.connect(f"file:{backup_path}?mode=ro", uri=True)
    try:
        dst = sqlite3.connect(str(tmp))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    _clear_wal_sidecars(dest_path)
    os.replace(tmp, dest_path)
    return dest_path


def list_backups() -> None:
    root = backup_root()
    if not root.exists():
        print(f"no backups yet ({root})")
        return
    rows = sorted(root.glob("*.db"))
    if not rows:
        print(f"no backups yet ({root})")
        return
    for p in rows:
        size_mb = p.stat().st_size / 1048576.0
        print(f"  {p.name:40s} {size_mb:8.1f} MB")


def main() -> int:
    ap = argparse.ArgumentParser(description="NEX substrate DB backup / restore")
    ap.add_argument("--keep", type=int, default=DEFAULT_KEEP,
                    help=f"backups to retain per DB (default {DEFAULT_KEEP})")
    ap.add_argument("--list", action="store_true", help="list existing backups")
    ap.add_argument("--restore", metavar="BACKUP",
                    help="restore this backup file")
    ap.add_argument("--into", metavar="DEST",
                    help="destination DB path for --restore")
    ap.add_argument("--force", action="store_true",
                    help="allow --restore to overwrite an existing file")
    args = ap.parse_args()

    if args.list:
        list_backups()
        return 0

    if args.restore:
        if not args.into:
            print("--restore requires --into <dest.db>", file=sys.stderr)
            return 2
        dest = restore_db(args.restore, args.into, force=args.force)
        print(f"restored {args.restore} -> {dest}")
        return 0

    root = backup_root()
    print(f"backing up to {root}")
    for name, made in backup_all(args.keep).items():
        if made is None:
            print(f"  {name}: SKIPPED (missing or integrity failure)")
        else:
            print(f"  {name}: {made.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
