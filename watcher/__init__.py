"""The NEX Integration Watcher — an external, read-only observation and test
coordinator for NEX.

It is an instrument to UNDERSTAND NEX, not a mechanism that changes it. The
Watcher is independent of NEX's cognitive runtime: nothing in this package imports
`theory_x` or `substrate`, and every data path is read-only (see `watcher.safety`).

Observation, interpretation and intervention are kept separate on purpose:
`Evidence.data` is what was observed; `Evidence.interpretation` is a reading, held
apart from it; and this package performs no intervention at all — host-side
collection is *described* for Claude Code to run locally, never executed here.
"""
from __future__ import annotations

__version__ = "0.1.0"

PASSIVE_MODE = True  # this package has no non-passive mode.
