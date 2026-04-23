"""Admin authentication — argon2id.

Single password. Hash stored in a gitignored file outside any DB
(default: <repo>/admin_password.argon2, override via the
NEX5_ADMIN_HASH_FILE env var).

Every session requires fresh authentication; the GUI sets a session
flag that clears at session end.

See SPECIFICATION.md §2 — Admin authentication.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

THEORY_X_STAGE = None

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_HASH_FILE = _REPO_ROOT / "admin_password.argon2"

_hasher = PasswordHasher()  # argon2id by default


def _hash_file(override: Optional[Path] = None) -> Path:
    if override is not None:
        return override
    env = os.environ.get("NEX5_ADMIN_HASH_FILE")
    return Path(env) if env else _DEFAULT_HASH_FILE


def set_password(plaintext: str, *, path: Optional[Path] = None) -> Path:
    """Hash `plaintext` with argon2id and write to the hash file.

    The file is chmod'd to 0600 where the OS permits. Returns the path
    written.
    """
    target = _hash_file(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_hasher.hash(plaintext))
    try:
        os.chmod(target, 0o600)
    except OSError:
        pass
    return target


def _load_hash(path: Optional[Path] = None) -> Optional[str]:
    target = _hash_file(path)
    if not target.exists():
        return None
    content = target.read_text().strip()
    return content or None


def is_configured(path: Optional[Path] = None) -> bool:
    return _load_hash(path) is not None


def verify_password(pasted: str, *, path: Optional[Path] = None) -> bool:
    """Return True iff `pasted` matches the stored admin hash."""
    stored = _load_hash(path)
    if not stored:
        return False
    try:
        return _hasher.verify(stored, pasted)
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(path: Optional[Path] = None) -> bool:
    stored = _load_hash(path)
    if not stored:
        return False
    return _hasher.check_needs_rehash(stored)
