"""Bonsai tree — in-memory branch state for the A-F pipeline.

The tree is in-memory. Snapshots persist to dynamic.db via Writer.
Seed branches never die; non-seed branches can be pruned on disuse.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

import errors
from alpha import ALPHA  # noqa: F401 — referenced by trunk label

THEORY_X_STAGE = 2

# Focus levels: a (lowest) → g (highest)
_FOCUS_LEVELS = ["a", "b", "c", "d", "e", "f", "g"]
# Texture levels: a (smoothest) → e (roughest)
_TEXTURE_LEVELS = ["a", "b", "c", "d", "e"]

# Decay constant: each pass multiplies each node's focus_num by (1 - DECAY)
_DECAY_RATE = 0.05
# Recency penalty (diversity): a branch attended within _RECENCY_WINDOW seconds
# decays EXTRA, so a hot branch cools faster between fires and starved branches
# can surface. Gentle-firm: tune _RECENCY_PENALTY up (toward ~0.30) for stronger
# rotation, down toward 0 to disable. The soak proved the prompt-nudge too soft;
# this biases the actual focus_num selection works with, at modest strength.
_RECENCY_WINDOW = 1200.0   # seconds — "recently attended" = last 20 min
_RECENCY_PENALTY = 0.12    # extra decay fraction applied to recently-hot branches
# Starvation bonus (strong-firm diversity): a branch NOT attended for
# _STARVE_WINDOW seconds gets a small focus_num BUMP so it surfaces for a turn
# regardless of its (possibly low) curiosity_weight. This is what reaches the
# genuinely cold branches (history/language/psychology) that gentle-firm could
# not — it deliberately overrides the designed weighting, mildly. Tune
# _STARVE_BONUS up for more forced rotation, _STARVE_WINDOW down to trigger sooner.
_STARVE_WINDOW = 7200.0    # seconds — un-attended for 2h+ = starved
_STARVE_BONUS = 0.15       # focus_num bump given to a starved branch per pass
# A non-seed branch is pruned when focus_num < PRUNE_FLOOR for PRUNE_HOLD cycles
_PRUNE_FLOOR = 0.05
_PRUNE_HOLD_CYCLES = 6

# Cadence-aware decay (session 26): a branch should decay proportional to how
# much of ITS OWN expected poll interval has elapsed per tick, not a flat rate
# tuned for a ~30s cadence. Without this, slow branches (poll every
# 1800-7200s) lose ~99.8% of focus_num between bursts while fast branches
# (crypto ~60s) barely decay at all between updates -- branches lose on
# cadence, not merit (ai_research has curiosity_weight 1.0 and still sat near
# 0.00). See journal/CARRY_OVER.md, session 25 audit / session 26 build.
_ACCUMULATOR_TICK_SECONDS = 30.0   # must match _accumulator_loop's stop.wait()
_CADENCE_WINDOW_SECONDS = 24 * 3600  # sense_events lookback for the calc
_CADENCE_BURST_GAP = 30.0          # events within this gap = the same burst
_CADENCE_FACTOR_FLOOR = 0.01      # a branch can't get more than ~100x slowdown
_CADENCE_FACTOR_CEILING = 3.0     # guards against a garbage/tiny interval value
_CADENCE_REFRESH_TICKS = 60       # recompute cadence every ~60 ticks (~30 min)
# Session 26 tuning: raw cadence scaling (alpha=1.0) let slow branches retain
# so much that real historical replay showed 5 branches saturating at the
# focus_num 1.0 ceiling, erasing the curiosity_weight differentiation the
# design was meant to preserve. alpha=0.7 compresses every branch's cadence
# credit toward 1.0 (less lift, disproportionately less for the branches that
# were getting the MOST lift) -- replayed against 48h of real pipeline_events:
# zero branches pinned, Gini 0.31 / normalized entropy 0.89 (target band
# 0.30-0.42 / 0.86-0.92), slow branches still materially lifted off ~0.00.
_CADENCE_ALPHA = 0.7


def _cluster_bursts(timestamps: list, threshold: float = _CADENCE_BURST_GAP) -> list:
    """Collapse a sorted timestamp list into burst start-times. A poll's whole
    batch of items lands within seconds of each other; per-row inter-arrival
    gaps are dominated by this and don't reflect the real poll cadence."""
    if not timestamps:
        return []
    bursts = [timestamps[0]]
    for t in timestamps[1:]:
        if t - bursts[-1] > threshold:
            bursts.append(t)
    return bursts


def _cadence_factor(branch_interval: Optional[float]) -> float:
    """Scale factor applied to the selected decay rate. Unknown/absent
    interval (no external feed maps to this branch, or not enough history
    yet) -> 1.0, the flat/unscaled default -- safe because it just reproduces
    today's already-known behavior rather than guessing a number."""
    if branch_interval is None or branch_interval <= 0:
        return 1.0
    raw = (_ACCUMULATOR_TICK_SECONDS / branch_interval) ** _CADENCE_ALPHA
    return max(_CADENCE_FACTOR_FLOOR, min(_CADENCE_FACTOR_CEILING, raw))

# Seed branches — 10 permanent branches; never pruned
SEED_BRANCHES = [
    {"id": "ai_research",       "curiosity_weight": 1.0},
    {"id": "emerging_tech",     "curiosity_weight": 0.9},
    {"id": "cognition_science", "curiosity_weight": 0.8},
    {"id": "computing",         "curiosity_weight": 0.7},
    {"id": "systems",           "curiosity_weight": 1.0},
    {"id": "crypto",            "curiosity_weight": 0.7},
    {"id": "markets",           "curiosity_weight": 0.5},
    {"id": "language",          "curiosity_weight": 0.5},
    {"id": "history",           "curiosity_weight": 0.4},
    {"id": "psychology",        "curiosity_weight": 0.6},
]


@dataclass
class BonsaiNode:
    branch_id: str
    curiosity_weight: float
    is_seed: bool = False
    focus_num: float = 0.0       # 0.0–1.0 internal
    texture_num: float = 0.0     # 0.0–1.0 internal
    last_attended_at: float = 0.0
    prune_counter: int = 0
    parent_id: Optional[str] = None

    @property
    def focus_increment(self) -> str:
        return _num_to_focus(self.focus_num)

    @property
    def texture_increment(self) -> str:
        return _num_to_texture(self.texture_num)


def _focus_to_num(level: str) -> float:
    idx = _FOCUS_LEVELS.index(level) if level in _FOCUS_LEVELS else 0
    return idx / max(1, len(_FOCUS_LEVELS) - 1)


def _num_to_focus(num: float) -> str:
    idx = round(num * (len(_FOCUS_LEVELS) - 1))
    idx = max(0, min(idx, len(_FOCUS_LEVELS) - 1))
    return _FOCUS_LEVELS[idx]


def _texture_to_num(level: str) -> float:
    idx = _TEXTURE_LEVELS.index(level) if level in _TEXTURE_LEVELS else 0
    return idx / max(1, len(_TEXTURE_LEVELS) - 1)


def _num_to_texture(num: float) -> str:
    idx = round(num * (len(_TEXTURE_LEVELS) - 1))
    idx = max(0, min(idx, len(_TEXTURE_LEVELS) - 1))
    return _TEXTURE_LEVELS[idx]


def _aggregate_focus_num(nodes: list[BonsaiNode]) -> float:
    if not nodes:
        return 0.0
    weights = [n.curiosity_weight for n in nodes]
    total_w = sum(weights)
    if total_w == 0:
        return 0.0
    return sum(n.focus_num * n.curiosity_weight for n in nodes) / total_w


def _aggregate_texture_num(nodes: list[BonsaiNode]) -> float:
    if not nodes:
        return 0.0
    weights = [n.curiosity_weight for n in nodes]
    total_w = sum(weights)
    if total_w == 0:
        return 0.0
    return sum(n.texture_num * n.curiosity_weight for n in nodes) / total_w


def _new_node(branch_id: str, curiosity_weight: float, is_seed: bool = False,
              parent_id: Optional[str] = None) -> BonsaiNode:
    return BonsaiNode(
        branch_id=branch_id,
        curiosity_weight=curiosity_weight,
        is_seed=is_seed,
        focus_num=0.0,
        texture_num=0.0,
        last_attended_at=time.time(),
        prune_counter=0,
        parent_id=parent_id,
    )


class BonsaiTree:
    def __init__(self, sense_reader=None) -> None:
        self._nodes: dict[str, BonsaiNode] = {}
        self._init_called = False
        self._sense_reader = sense_reader
        # branch_id -> effective poll interval (seconds), refreshed
        # periodically by refresh_cadence(). Empty/missing entries fall back
        # to _cadence_factor's 1.0 default.
        self._cadence: dict[str, float] = {}

    def init_tree(self) -> None:
        for seed in SEED_BRANCHES:
            node = _new_node(seed["id"], seed["curiosity_weight"], is_seed=True)
            self._nodes[seed["id"]] = node
        self._init_called = True

    def get(self, branch_id: str) -> Optional[BonsaiNode]:
        return self._nodes.get(branch_id)

    def add_branch(self, branch_id: str, curiosity_weight: float = 0.5) -> BonsaiNode:
        """Add a non-seed branch (idempotent — returns existing if already present)."""
        if branch_id in self._nodes:
            return self._nodes[branch_id]
        node = _new_node(branch_id, curiosity_weight, is_seed=False)
        self._nodes[branch_id] = node
        return node

    def all_nodes(self) -> list[BonsaiNode]:
        return list(self._nodes.values())

    def attend(self, branch_id: str, magnitude: float) -> BonsaiNode:
        """Increment focus on a branch from an attention event."""
        node = self._nodes.get(branch_id)
        if node is None:
            return None
        delta = magnitude * node.curiosity_weight * 0.1
        node.focus_num = min(1.0, node.focus_num + delta)
        # texture roughens slightly on attention
        node.texture_num = min(1.0, node.texture_num + delta * 0.3)
        node.last_attended_at = time.time()
        node.prune_counter = 0
        return node

    def refresh_cadence(self) -> None:
        """Recompute each branch's effective poll interval from recent
        sense_events (burst-clustered, min-of-constituent-streams -- whichever
        feed fires most often sets how often this branch can realistically be
        attended). Read-only, called periodically (not every decay tick) by
        _accumulator_loop. On no reader, no data, or any failure: leave the
        existing cache untouched rather than wiping it to empty -- a
        transient DB hiccup should not silently revert every branch to flat
        decay for a tick."""
        if self._sense_reader is None:
            return
        try:
            from .attention import _STREAM_BRANCH
            since = time.time() - _CADENCE_WINDOW_SECONDS
            rows = self._sense_reader.read(
                "SELECT stream, timestamp FROM sense_events "
                "WHERE timestamp > ? AND stream NOT LIKE 'internal.%' "
                "ORDER BY stream, timestamp ASC",
                (since,),
            )
            by_stream: dict[str, list] = {}
            for r in rows:
                by_stream.setdefault(r["stream"], []).append(r["timestamp"])

            branch_intervals: dict[str, list] = {}
            for stream, ts_list in by_stream.items():
                bursts = _cluster_bursts(ts_list)
                if len(bursts) < 2:
                    continue
                gaps = sorted(bursts[i + 1] - bursts[i] for i in range(len(bursts) - 1))
                median = gaps[len(gaps) // 2]
                prefix = stream.split(".")[0]
                branch_id = _STREAM_BRANCH.get(prefix) or _STREAM_BRANCH.get(stream)
                if branch_id:
                    branch_intervals.setdefault(branch_id, []).append(median)

            new_cadence = {
                branch_id: min(intervals)
                for branch_id, intervals in branch_intervals.items()
            }
            if new_cadence:
                self._cadence = new_cadence
        except Exception as exc:
            errors.record(f"bonsai refresh_cadence failed: {exc}", source="bonsai")

    def decay_pass(self) -> None:
        """Apply focus/texture decay across all nodes. Recency-aware: a branch
        attended very recently decays EXTRA, so hot branches cool faster between
        fires and starved branches can surface (diversity fix). Cadence-aware:
        the selected rate is scaled by how much of the branch's OWN expected
        poll interval elapsed this tick, so a slow-but-healthy branch isn't
        punished for polling less often than the 30s tick."""
        _now = time.time()
        for node in self._nodes.values():
            _rate = _DECAY_RATE
            # extra decay if attended within the recency window
            if _now - node.last_attended_at < _RECENCY_WINDOW:
                _rate = _DECAY_RATE + _RECENCY_PENALTY
            _rate *= _cadence_factor(self._cadence.get(node.branch_id))
            node.focus_num = max(0.0, node.focus_num * (1 - _rate))
            node.texture_num = max(0.0, node.texture_num * (1 - _DECAY_RATE * 0.5))
            # Starvation bonus: long-neglected branches get a bump so they
            # surface regardless of low curiosity_weight (reaches cold branches).
            if _now - node.last_attended_at > _STARVE_WINDOW:
                node.focus_num = min(1.0, node.focus_num + _STARVE_BONUS)

    def prune_pass(self) -> list[str]:
        """Remove non-seed branches that have been below floor for too long."""
        pruned = []
        for branch_id, node in list(self._nodes.items()):
            if node.is_seed:
                continue
            if node.focus_num < _PRUNE_FLOOR:
                node.prune_counter += 1
                if node.prune_counter >= _PRUNE_HOLD_CYCLES:
                    del self._nodes[branch_id]
                    pruned.append(branch_id)
            else:
                node.prune_counter = 0
        return pruned

    def snapshot(self) -> dict:
        nodes = self.all_nodes()
        return {
            "branches": [
                {
                    "branch_id": n.branch_id,
                    "is_seed": n.is_seed,
                    "curiosity_weight": n.curiosity_weight,
                    "focus_increment": n.focus_increment,
                    "focus_num": n.focus_num,
                    "texture_increment": n.texture_increment,
                    "texture_num": n.texture_num,
                    "last_attended_at": n.last_attended_at,
                    "parent_id": n.parent_id,
                }
                for n in nodes
            ],
            "total_branches": len(nodes),
            "active_branch_count": sum(1 for n in nodes if n.focus_num > _PRUNE_FLOOR),
            "aggregate_focus": _num_to_focus(_aggregate_focus_num(nodes)),
            "aggregate_texture": _num_to_texture(_aggregate_texture_num(nodes)),
        }
