"""Pytest-free bootstrap: put the repo root on sys.path so tests can
`from alpha import ALPHA` etc. regardless of cwd.

(Tests are pytest-compatible but also runnable via `python -m unittest`.)

Test hygiene (repair queue 2026-10-05): the suite must never touch the live
<repo>/data databases. Under pytest:
  * NEX5_DATA_DIR defaults to a session temp dir (a test may still point it at
    its own dir), so code resolving paths via substrate.paths never lands on
    live data;
  * any sqlite3 connection, or any file opened for writing, under the live
    data dir is refused (OperationalError / PermissionError) AND the test that
    attempted it is failed at teardown -- loudly, even if the code under test
    swallowed the exception in a fail-safe path.
"""
import builtins
import io
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_LIVE_DATA = os.path.realpath(str(_ROOT / "data"))
_SESSION_DATA = tempfile.mkdtemp(prefix="nex5_test_data_")
os.environ.setdefault("NEX5_DATA_DIR", _SESSION_DATA)
if os.path.realpath(os.environ["NEX5_DATA_DIR"]) == _LIVE_DATA:
    os.environ["NEX5_DATA_DIR"] = _SESSION_DATA

_BLOCKED: list = []


def _is_live(target) -> bool:
    try:
        p = os.fspath(target)
    except TypeError:
        return False
    if isinstance(p, bytes):
        p = p.decode(errors="replace")
    if p.startswith("file:"):
        p = p[5:].split("?", 1)[0]
    if not p or p.startswith(":"):
        return False
    rp = os.path.realpath(p)
    return rp == _LIVE_DATA or rp.startswith(_LIVE_DATA + os.sep)


def _wrap_connect(orig):
    def connect(database, *args, **kwargs):
        if _is_live(database):
            _BLOCKED.append(f"sqlite connect {os.fspath(database)}")
            raise sqlite3.OperationalError(
                f"TEST HYGIENE: live nex5/data connection refused: {os.fspath(database)}")
        return orig(database, *args, **kwargs)
    return connect


def _wrap_open(orig):
    def _open(file, mode="r", *args, **kwargs):
        if any(c in str(mode) for c in "wax+") and _is_live(file):
            _BLOCKED.append(f"open({mode!r}) {os.fspath(file)}")
            raise PermissionError(
                f"TEST HYGIENE: write to live nex5/data refused: {os.fspath(file)}")
        return orig(file, mode, *args, **kwargs)
    return _open


sqlite3.connect = _wrap_connect(sqlite3.connect)
sqlite3.dbapi2.connect = sqlite3.connect
builtins.open = _wrap_open(builtins.open)
io.open = builtins.open

try:
    import pytest

    @pytest.fixture(autouse=True)
    def _no_live_data():
        """Keep NEX5_DATA_DIR off live data; fail the test on any live touch."""
        if not os.environ.get("NEX5_DATA_DIR") or \
                os.path.realpath(os.environ["NEX5_DATA_DIR"]) == _LIVE_DATA:
            os.environ["NEX5_DATA_DIR"] = _SESSION_DATA
        start = len(_BLOCKED)
        yield
        hits = _BLOCKED[start:]
        if hits:
            pytest.fail("TEST HYGIENE: test touched live nex5/data "
                        f"({len(hits)}x): {hits[:3]}", pytrace=False)
except ImportError:  # plain unittest run: the guard above still refuses live access
    pass
