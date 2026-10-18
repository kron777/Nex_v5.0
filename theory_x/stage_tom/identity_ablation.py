"""Identity-block ablation for the self-as-cause experiment (sentience round, step 1).

The identity anchor (generator.py) reads the most recent self-description into the
fountain prompt. Does that block do causal work, or is it decoration? This gates the
block so the experiment can run with selfdesc_novel Brier as the outcome.

Three design constraints, each from a real failure mode:

  FILE-BASED, not an env var. Switching condition off the process environment needs a
  RESTART, and a restart is a treatment -- it writes a self_downtime belief, bumps
  boot_count, and reloads the static tier-6 pool. The arms would then differ by
  (block) AND (restart history). The condition is read from a FILE, re-read per call
  with an mtime check (one stat per fire), so conditions change with NO restart and the
  experiment can interleave (24h on / 24h off) within one store epoch rather than run
  sequentially across the measured drift.

  DROP = FILLER, not empty. Removing content can change the output for length reasons
  alone, and the swap arm needs length control anyway. Drop replaces the identity block
  with neutral, non-self-referential filler of matched length; swap replaces it with a
  length-matched NON-identity substitute. Build both; the run enables DROP first (a null
  there makes the swap unnecessary).

  IDEMPOTENT. No file / mode 'normal' -> the block is byte-identical to the original.

Fail-safe throughout: any error returns the real identity block (never alters a fire
on an experiment's account). The identity block is NOT exempt -- it is the thing under
test.

Condition file (JSON): {"mode": "normal"|"drop"|"swap"}. Default normal.
"""
from __future__ import annotations

import json
import os
import time
from typing import Optional

import logging

logger = logging.getLogger("nex5.identity_ablation")

_FILLER_UNIT = "The hour is unremarkable and the room holds its usual quiet. "
_cache: dict = {"mtime": None, "mode": "normal", "logged": None}


def _condition_path() -> str:
    try:
        from substrate.paths import data_dir
        return str(data_dir() / "identity_ablation.json")
    except Exception:
        return os.path.expanduser("~/.nex/identity_ablation.json")


def current_condition() -> str:
    """Read the active mode from the file, re-reading only when its mtime changes
    (one stat per call). Returns 'normal' | 'drop' | 'swap'. Fail-safe -> 'normal'."""
    path = _condition_path()
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return "normal"
    if mtime != _cache["mtime"]:
        try:
            mode = str(json.loads(open(path, encoding="utf-8").read()).get("mode", "normal"))
        except Exception:
            mode = "normal"
        if mode not in ("normal", "drop", "swap"):
            mode = "normal"
        _cache["mtime"] = mtime
        _cache["mode"] = mode
        if _cache["logged"] != mode:   # once per distinct condition, never per call
            _cache["logged"] = mode
            logger.warning("identity ablation condition -> %s (experiment; self-labels "
                           "outcome rows via current_condition())", mode)
    return _cache["mode"]


def _filler(n_chars: int) -> str:
    if n_chars <= 0:
        return ""
    reps = (n_chars // len(_FILLER_UNIT)) + 1
    return (_FILLER_UNIT * reps)[:n_chars]


def apply_to_identity_block(identity_text: str,
                            substitute: Optional[str] = None,
                            mode: Optional[str] = None) -> str:
    """Return the text to emit for the identity block under the active condition.

    normal -> identity_text unchanged (idempotent).
    drop   -> neutral filler of the same length (content removed, length held).
    swap   -> `substitute` (a non-identity belief) fit to the same length; falls back to
              filler if no substitute supplied.
    """
    try:
        mode = mode or current_condition()
        if mode == "normal" or not identity_text:
            return identity_text
        target = len(identity_text)
        if mode == "drop":
            return _filler(target)
        if mode == "swap":
            if not substitute:
                return _filler(target)
            s = substitute
            return s[:target] if len(s) >= target else s + _filler(target - len(s))
        return identity_text
    except Exception:
        return identity_text   # never alter a fire on an experiment's account
