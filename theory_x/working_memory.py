"""working_memory.py — Working Memory node (Theory X port, DOCTRINE §5 #2).

Short-term buffer with exponential decay. Capacity 7 (Miller's Law).
Half-life 5 minutes wall-clock. Items refresh on re-attention.

Standalone module; no other theory_x imports. stdlib only.

Integration (via gui/server.py):
    - tick(): decay + update on each chat turn
    - add(): called with focal belief ids/content after FocalSet update
    - get_active(): returns items above threshold for belief_text injection
    - state(): snapshot for /tmp/nex5_working_memory.log
"""
from __future__ import annotations

import math
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Optional

__all__ = ["WorkingMemory", "WMItem"]

_CAPACITY = 7
_HALF_LIFE = 300.0  # seconds — 5-minute half-life
_MIN_ACTIVATION = 0.05  # below this, item is pruned on next decay pass
_REFRESH_BOOST = 0.2  # per additional re-attention event


@dataclass
class WMItem:
    belief_id: str
    content: str
    first_seen: float
    last_seen: float
    refresh_count: int = 0

    def activation(self, now: float) -> float:
        """exp decay from last_seen, boosted by refresh count, capped at 1.0."""
        base = math.exp(-(now - self.last_seen) / _HALF_LIFE)
        return min(1.0, base * (1.0 + _REFRESH_BOOST * self.refresh_count))


class WorkingMemory:
    """Short-term buffer with exponential decay.

    Capacity: 7 items (Miller's Law).
    Half-life: 5 min wall-clock.
    Refresh: re-adding an existing item boosts activation and increments
             refresh_count instead of replacing the item.
    Eviction: when at capacity, the item with lowest current activation
              is ejected.
    Pruning: items below _MIN_ACTIVATION (0.05) are removed on decay().
    """

    CAPACITY = _CAPACITY
    HALF_LIFE = _HALF_LIFE

    def __init__(self) -> None:
        self._items: OrderedDict[str, WMItem] = OrderedDict()
        self._lock = threading.Lock()

    # ── public API ────────────────────────────────────────────────────────────

    def add(self, belief_id: str, content: str, now: Optional[float] = None) -> None:
        """Add or refresh an item. Thread-safe."""
        t = now if now is not None else time.time()
        with self._lock:
            if belief_id in self._items:
                item = self._items[belief_id]
                item.last_seen = t
                item.refresh_count += 1
                # Move to end (most-recently-seen position)
                self._items.move_to_end(belief_id)
            else:
                if len(self._items) >= self.CAPACITY:
                    self._evict_lowest(t)
                self._items[belief_id] = WMItem(
                    belief_id=belief_id,
                    content=content,
                    first_seen=t,
                    last_seen=t,
                    refresh_count=0,
                )

    def decay(self, now: Optional[float] = None) -> None:
        """Apply decay and prune items below _MIN_ACTIVATION. Thread-safe."""
        t = now if now is not None else time.time()
        with self._lock:
            to_remove = [
                bid for bid, item in self._items.items()
                if item.activation(t) < _MIN_ACTIVATION
            ]
            for bid in to_remove:
                del self._items[bid]

    def get_active(
        self,
        now: Optional[float] = None,
        min_activation: float = 0.1,
    ) -> list[dict]:
        """Return items above threshold, sorted by activation descending."""
        t = now if now is not None else time.time()
        with self._lock:
            results = []
            for item in self._items.values():
                a = item.activation(t)
                if a >= min_activation:
                    results.append({
                        "belief_id": item.belief_id,
                        "content": item.content,
                        "activation": round(a, 4),
                        "refresh_count": item.refresh_count,
                        "age_s": round(t - item.first_seen, 1),
                    })
        results.sort(key=lambda x: x["activation"], reverse=True)
        return results

    def tick(self, context: Optional[dict] = None) -> dict:
        """Lifecycle tick: decay then return state snapshot."""
        now = time.time()
        self.decay(now)
        return self.state(now)

    def state(self, now: Optional[float] = None) -> dict:
        """Snapshot for logging."""
        t = now if now is not None else time.time()
        with self._lock:
            items = [
                {
                    "belief_id": item.belief_id,
                    "content": item.content[:60],
                    "activation": round(item.activation(t), 4),
                    "refresh_count": item.refresh_count,
                    "last_seen": round(t - item.last_seen, 1),
                }
                for item in self._items.values()
            ]
        items.sort(key=lambda x: x["activation"], reverse=True)
        return {"size": len(items), "items": items}

    # ── internal ──────────────────────────────────────────────────────────────

    def _evict_lowest(self, now: float) -> None:
        """Eject the item with the lowest current activation. Caller holds lock."""
        if not self._items:
            return
        lowest_id = min(self._items, key=lambda bid: self._items[bid].activation(now))
        del self._items[lowest_id]
