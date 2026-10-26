"""Guaranteed identity block for the fountain prompt (NEX5_IDENTITY_BLOCK, dark).

WHY: her self-model reached the fountain prompt only by winning draws -- the
favourites gate (affinity > 0.40), the ~20% seed-source sample, and the
identity_log anchor, which is empty on a fresh store until identity_loop first
composes. Continuity should not be won; it should be guaranteed. Modelled on the
chat workspace's never-evicted set ({compassion, compass}): this block always
assembles, and affinity governs only HOW MUCH identity surfaces, not WHETHER.

    floor   one standing self-claim, every fire, affinity-independent:
            a random authored claim (source='identity', seeds/identity.yaml),
            else the self-location commitment (written at every boot before the
            fountain lights). Nothing is invented here -- identity claims are
            authored, not generated (see identity.yaml).
    extras  up to NEX5_IDENTITY_BLOCK_MAX_EXTRA (default 2) further self-beliefs
            whose affinity >= NEX5_IDENTITY_BLOCK_AFFINITY (default 0.40, the
            favourites threshold), highest first. NULL affinity -> no extras, so
            a fresh store gets the floor alone and the block grows as she rates.

Self-as-cause experiment (identity_ablation): under a non-control arm (reframe /
filler) the block emits NOTHING -- those arms remove the identity claim, and
re-inserting one here would confound A-vs-B. Under the control arm it adds the
standing claims alongside the arm-A anchor.

Flag OFF (default): never called; the prompt is byte-identical. Fail-safe: any
error emits nothing and never breaks a fire.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("nex5.identity_block")

HEADER = "Who you are (this holds every moment; ground, not a line to repeat):"
SLOT = "identity_block"

# The self-model band: authored claims, her own composed self-descriptions, and
# the self-location commitment.
_SELF_SOURCES = ("identity", "identity_loop", "self_location")
_FLOOR_SOURCES = ("identity", "self_location")   # in preference order


def enabled() -> bool:
    return os.environ.get("NEX5_IDENTITY_BLOCK") == "1"


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return max(0, int(os.environ.get(name, default)))
    except (TypeError, ValueError):
        return default


def _ablation_defers() -> bool:
    """True when the self-as-cause experiment is in a treatment arm."""
    try:
        from theory_x.stage_tom import identity_ablation as _iab
        return _iab.current_condition() != "normal"
    except Exception:
        return False   # no experiment module -> nothing to defer to


def select(beliefs_reader) -> list[dict]:
    """The rows the block will show: [floor, *extras]. Empty only when the store
    holds no self-model belief at all (never on a booted store)."""
    floor = None
    for src in _FLOOR_SOURCES:
        rows = beliefs_reader.read(
            "SELECT id, content FROM beliefs WHERE source=? "
            "AND content IS NOT NULL AND content != '' "
            "ORDER BY RANDOM() LIMIT 1", (src,))
        if rows:
            floor = dict(rows[0])
            break
    if floor is None:
        return []

    n_extra = _env_int("NEX5_IDENTITY_BLOCK_MAX_EXTRA", 2)
    extras = []
    if n_extra:
        ph = ",".join("?" * len(_SELF_SOURCES))
        extras = [dict(r) for r in beliefs_reader.read(
            f"SELECT id, content FROM beliefs WHERE source IN ({ph}) "
            "AND affinity IS NOT NULL AND affinity >= ? AND id != ? "
            "AND content IS NOT NULL AND content != '' "
            "ORDER BY affinity DESC LIMIT ?",
            (*_SELF_SOURCES,
             _env_float("NEX5_IDENTITY_BLOCK_AFFINITY", 0.40),
             floor["id"], n_extra))]
    return [floor] + extras


def append(prompt_parts: list, retrieval_manifest: list, beliefs_reader) -> int:
    """Append the block to prompt_parts (blank-line terminated, like every other
    block) and record its beliefs in retrieval_manifest. Returns the number of
    belief lines emitted (0 when deferring to the experiment or on error)."""
    if beliefs_reader is None or _ablation_defers():
        return 0
    try:
        rows = select(beliefs_reader)
    except Exception as exc:
        logger.warning("identity block: select failed: %s", exc)
        return 0
    if not rows:
        logger.warning("identity block: no self-model belief in the store")
        return 0
    prompt_parts.append(HEADER)
    for rank, r in enumerate(rows, start=1):
        prompt_parts.append(f"  - {r['content']}")
        retrieval_manifest.append((r["id"], SLOT, rank, None))
    prompt_parts.append("")
    return len(rows)
