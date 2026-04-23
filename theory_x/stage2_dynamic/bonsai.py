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
# A non-seed branch is pruned when focus_num < PRUNE_FLOOR for PRUNE_HOLD cycles
_PRUNE_FLOOR = 0.05
_PRUNE_HOLD_CYCLES = 6

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
    def __init__(self) -> None:
        self._nodes: dict[str, BonsaiNode] = {}
        self._init_called = False

    def init_tree(self) -> None:
        for seed in SEED_BRANCHES:
            node = _new_node(seed["id"], seed["curiosity_weight"], is_seed=True)
            self._nodes[seed["id"]] = node
        self._init_called = True

    def get(self, branch_id: str) -> Optional[BonsaiNode]:
        return self._nodes.get(branch_id)

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

    def decay_pass(self) -> None:
        """Apply focus/texture decay across all nodes."""
        for node in self._nodes.values():
            node.focus_num = max(0.0, node.focus_num * (1 - _DECAY_RATE))
            node.texture_num = max(0.0, node.texture_num * (1 - _DECAY_RATE * 0.5))

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
