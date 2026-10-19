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
import threading
from typing import Optional

logger = logging.getLogger("nex5.identity_ablation")

_MODES = ("normal", "reframe", "filler")
_NORMAL_HEADER = "This is who you said you are ({m} min ago):"
_REFRAME_HEADER = "Earlier output, for context:"
# Filler is used BOTH to pad arm B and to fill arm C -- it must be the SAME string in
# both (else A-vs-C has two differences), NON-INSTRUCTIONAL, and SEMANTICALLY INERT.
# MINOR-2: the old sensory/spatial filler ("grey light on the wall...") reads as world
# STATE a fountain prompt may treat as situational context, not padding -- and in arm B
# it sits right after the statement. So: referent-free near-tautological function words,
# no concrete nouns, no spatial/sensory anchors, no imperative, no "you". In arm B it is
# also DELIMITED into its own paragraph so it can't parse as a continuation of the
# statement. Asserted in tests.
_FILLER_UNIT = "and so it was, and so it remains, as it is and as it was, much the same, and thus, "
_cache: dict = {"mtime": None, "mode": "normal", "logged": None}
_lock = threading.Lock()   # MINOR-1: _flip is mutated from the fountain and tick threads
# Q11 seam guard: count condition CHANGES between identity ticks so the primary analysis
# can filter rows where the arm flipped mid-interval. first_stamp emits flips=-1 (UNKNOWN)
# for the first stamp after process start (CRIT-2): _flip resets at import, so a restart
# would otherwise fabricate a "stable" (flips=0) row with a hardcoded prev_stamp_arm.
_flip: dict = {"current": None, "flips": 0, "prev_stamp_arm": "normal", "first_stamp": True}


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
    mode = _cache["mode"]
    # Q11 flip accounting (observed on every call; the fountain calls this per fire, so
    # flips BETWEEN the rarer identity ticks are captured). The first observation sets
    # the baseline and is not a flip. Locked (MINOR-1): read-modify-write across threads.
    with _lock:
        if _flip["current"] is None:
            _flip["current"] = mode
            _flip["prev_stamp_arm"] = mode
        elif mode != _flip["current"]:
            _flip["flips"] += 1
            _flip["current"] = mode
    return mode


def stamp_fields() -> dict:
    """Three-field arm stamp for the OUTCOME row (Q11). arm = in force now; arm_prev =
    in force at the previous stamp (interval start); flips = condition CHANGES observed
    since (or -1 = UNKNOWN for the first stamp after process start, CRIT-2 -- excluded
    from primary, never a fabricated flips=0). Primary analysis filters flips==0; other
    rows kept and reported as excluded-n, never dropped. Resets the interval counters."""
    arm = current_condition()
    with _lock:
        flips = -1 if _flip["first_stamp"] else _flip["flips"]
        out = {"arm": arm, "arm_prev": _flip["prev_stamp_arm"], "flips": flips}
        _flip["prev_stamp_arm"] = arm
        _flip["flips"] = 0
        _flip["first_stamp"] = False
    return out


def arm_for_outcome(identity_rows, outcome_ts: float):
    """CRIT-1: pin the analysis join. An outcome event is attributed to the identity_log
    row with the GREATEST composed_at STRICTLY LESS THAN outcome_ts -- the arm that
    actually ACTED, not one that had not yet acted. A tie (composed_at == outcome_ts) is
    excluded (returns None). `identity_rows` = iterable of rows with composed_at + the
    ablation fields. Returns the chosen row or None."""
    best = None
    for r in identity_rows:
        ts = r["composed_at"] if hasattr(r, "__getitem__") else r.composed_at
        if ts < outcome_ts and (best is None or ts > (best["composed_at"])):
            best = r
    return best


_FILLER_WORDS = _FILLER_UNIT.split()


def _filler_tokens(n: int) -> str:
    """n whitespace tokens of inert filler (the real control is TOKEN budget, not chars
    -- CRIT-3; a char-exact pad would still differ in tokens and change the tail budget)."""
    if n <= 0:
        return ""
    return " ".join(_FILLER_WORDS[i % len(_FILLER_WORDS)] for i in range(n))


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
    target = len(normal.split())   # match the TOKEN budget (CRIT-3), not char length
    if mode == "reframe":
        rf = _REFRAME_HEADER + "\n  " + statement
        need = target - len(rf.split())
        # delimit the filler into its own paragraph so it can't parse as a continuation
        # of the statement (the "\n\n" is whitespace -> contributes no token).
        return rf + ("\n\n" + _filler_tokens(need)) if need > 0 else rf
    if mode == "filler":
        return _filler_tokens(target)
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
