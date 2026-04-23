"""Pytest-free bootstrap: put the repo root on sys.path so tests can
`from alpha import ALPHA` etc. regardless of cwd.

(Tests are pytest-compatible but also runnable via `python -m unittest`.)
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
