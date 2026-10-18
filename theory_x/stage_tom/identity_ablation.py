"""Identity-block ablation for the self-as-cause experiment (sentience round, step 1).

THE CONFOUND THIS AVOIDS (Beam SEV-1): the identity block CONTAINS the previous
self-description, and the outcome (selfdesc_novel) asks whether the NEXT self-
description's distinctive token differs from THAT SAME TEXT. So removing the block
removes the information that determines the outcome -- the removal arm cannot fail, and
a CI excluding zero would mean nothing. The experiment must hold the tokens constant
and vary ONLY the identity CLAIM:

    A  normal   "This is who you said you are (N min ago):" + <prev selfdesc>
                info present, framing = IDENTITY
    B  reframe  "Earlier output, for context:"              + <prev selfdesc>
                info IDENTICAL (same tokens, length-matched), framing = NONE
    C  filler   length-matched neutral filler
                info absent, framing absent -- DESCRIPTIVE ONLY, confounded by the
                metric's own definition; interpret nothing, pre-registered as such.

A vs B is THE experiment (isolates the claim). A vs C removes information and is
reported descriptive-only. The old drop/swap modes were both confounded (each removed
the previous self-description) and are gone.

Design constraints (each a real failure mode):
  FILE-BASED condition (mtime-cached, one stat/call) -- NOT an env var, because an env
  switch needs a restart and a restart is a treatment (self_downtime + boot_count +
  static tier-6 reload). The file lets conditions INTERLEAVE within one store epoch.
  LENGTH-MATCHED: reframe and filler are padded to the normal block's length so only
  the framing varies, never length/position.
  IDEMPOTENT: 'normal' is byte-identical to the original block.
Fail-safe is the CALLER's job for this experiment: on any error the caller must emit
arm A (control) and log, never silently drop to treatment.

Condition file (JSON): {"mode": "normal"|"reframe"|"filler"}. Default normal.
"""
from __future__ import annotations

import json
import os
import logging
from typing import Optional

logger = logging.getLogger("nex5.identity_ablation")

_MODES = ("normal", "reframe", "filler")
_NORMAL_HEADER = "This is who you said you are ({m} min ago):"
_REFRAME_HEADER = "Earlier output, for context:"
_FILLER_UNIT = "The hour is unremarkable and the room holds its usual quiet. "
_cache: dict = {"mtime": None, "mode": "normal", "logged": None}


def _condition_path() -> str:
    try:
        from substrate.paths import data_dir
        return str(data_dir() / "identity_ablation.json")
    except Exception:
        return os.path.expanduser("~/.nex/identity_ablation.json")


def current_condition() -> str:
    """Active mode from the file, re-read only when its mtime changes. Fail-safe ->
    'normal'. Logged once per distinct condition (never per call -- a per-call emitter
    would inflate the soak line-rate)."""
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
        if mode not in _MODES:
            mode = "normal"
        _cache["mtime"] = mtime
        _cache["mode"] = mode
        if _cache["logged"] != mode:
            _cache["logged"] = mode
            logger.warning("identity ablation condition -> %s (experiment; arm is stamped "
                           "on each identity_log row)", mode)
    return _cache["mode"]


def _filler(n_chars: int) -> str:
    if n_chars <= 0:
        return ""
    return (_FILLER_UNIT * ((n_chars // len(_FILLER_UNIT)) + 1))[:n_chars]


def _normal_block(statement: str, minutes_ago: int) -> str:
    # No trailing newline: the caller appends this as one prompt_part plus a "" part,
    # and prompt_parts is joined with "\n" -- so [block, ""] reproduces the original
    # 3-append "header\n  statement\n" exactly (byte-identical in normal mode).
    return _NORMAL_HEADER.format(m=minutes_ago) + "\n  " + statement


def block_for(statement: str, minutes_ago: int, mode: Optional[str] = None) -> str:
    """The identity-block text under the active (or given) condition, WITHOUT a trailing
    newline (the caller adds the "" part).

    normal  -> byte-identical original block.
    reframe -> same statement, neutral header, length-matched to the normal block.
    filler  -> neutral filler of the normal block's length (no statement, no header).
    """
    mode = mode or current_condition()
    normal = _normal_block(statement, minutes_ago)
    if mode == "normal" or not statement:
        return normal
    if mode == "reframe":
        rf = _REFRAME_HEADER + "\n  " + statement
        if len(rf) < len(normal):
            return rf + _filler(len(normal) - len(rf))
        return rf[:len(normal)]
    if mode == "filler":
        return _filler(len(normal))
    return normal


_gate_warned: set = set()


def _warn_once(exc) -> None:
    key = ("iab_gate", type(exc).__name__)
    if key not in _gate_warned:
        _gate_warned.add(key)
        logger.warning("identity ablation gate error -> defaulting to CONTROL (arm A): "
                       "%r (logged once)", exc)


def append_block(prompt_parts: list, statement: str, minutes_ago: int) -> str:
    """Append the identity block for the active arm and return the arm applied.

    normal keeps the original 3-part append (byte-identical). reframe/filler append one
    length-matched part + "". FAIL-SAFE DEFAULTS TO CONTROL (arm A), logged once per
    error kind -- an experiment fail-safe must never silently convert a control tick
    into a treatment tick.
    """
    def _control():
        prompt_parts.append("This is who you said you are (%d min ago):" % minutes_ago)
        prompt_parts.append("  %s" % statement)
        prompt_parts.append("")

    try:
        mode = current_condition()
        if mode == "normal":
            _control()
            return "normal"
        prompt_parts.append(block_for(statement, minutes_ago, mode))
        prompt_parts.append("")
        return mode
    except Exception as exc:
        _warn_once(exc)
        # strip any partial append from a mid-way failure, then emit clean control
        _control()
        return "normal"
