"""Consolidation — quiet-triggered memory consolidation pass.

When external activity has been quiet for > 300s (no recent user message
detected via internal.temporal stream), consolidation_active is set True
and the consolidation pass runs.
"""
from __future__ import annotations

import json
import time
from typing import Optional

import errors
from substrate import Reader
from .bonsai import BonsaiTree

THEORY_X_STAGE = 2

_QUIET_THRESHOLD_SECONDS = 300
_LOG_SOURCE = "consolidation"


def _external_quiet(sense_reader: Reader) -> bool:
    """Check if external activity has been quiet for > 300s."""
    try:
        row = sense_reader.read_one(
            "SELECT payload FROM sense_events "
            "WHERE stream = 'internal.temporal' "
            "ORDER BY id DESC LIMIT 1",
        )
        if row is None:
            return False
        payload = json.loads(row["payload"])
        seconds_since = payload.get("seconds_since_last_user_message")
        if seconds_since is not None:
            return float(seconds_since) > _QUIET_THRESHOLD_SECONDS
        return False
    except Exception as exc:
        errors.record(f"consolidation quiet check error: {exc}", source=_LOG_SOURCE, exc=exc)
        return False


def consolidation_pass(tree: BonsaiTree, sense_reader: Reader) -> bool:
    """Run a consolidation pass if quiet. Returns True if consolidation ran."""
    quiet = _external_quiet(sense_reader)
    if not quiet:
        return False

    # During consolidation: decay tree more aggressively
    try:
        tree.decay_pass()
        pruned = tree.prune_pass()
        if pruned:
            errors.record(
                f"consolidation pruned {len(pruned)} branches: {pruned}",
                source=_LOG_SOURCE,
                level="INFO",
            )
    except Exception as exc:
        errors.record(f"consolidation pass error: {exc}", source=_LOG_SOURCE, exc=exc)
        return False
    return True
