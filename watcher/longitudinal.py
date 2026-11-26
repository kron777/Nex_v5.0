"""Longitudinal observation — track a subject across an ordered series of
snapshots (integration stages over time).

Where `watcher.snapshot.diff_snapshots` compares two points and
`watcher.regression` flags reversals, this module keeps the whole timeline, so
behavioural drift is visible across many integration stages, not just the last
step. NEX is in STANDBY, so the current series is static/cloud; runtime-origin
points enter the same series unchanged once the host supplies them, and stay
distinguishable by each point's `origin`.

A `Series` is just an ordered list of loaded snapshots. Nothing here modifies
NEX or the snapshots; it reads them.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .snapshot import _by_subject


class Series:
    """An ordered collection of snapshots (ascending by `taken_at`)."""

    def __init__(self, snapshots: Optional[List[dict]] = None) -> None:
        self.snapshots: List[dict] = sorted(snapshots or [],
                                            key=lambda s: s.get("taken_at", ""))

    def add(self, snap: dict) -> None:
        self.snapshots.append(snap)
        self.snapshots.sort(key=lambda s: s.get("taken_at", ""))

    def stages(self) -> List[dict]:
        """One row per snapshot: its label, stage tag, time and size."""
        return [{"label": s.get("label"), "stage": s.get("stage"),
                 "taken_at": s.get("taken_at"), "count": s.get("count")}
                for s in self.snapshots]

    def trend(self, subject: str) -> List[dict]:
        """How one subject evolved across the series. Each point keeps its origin,
        so cloud (static) and host (runtime) observations stay distinguishable."""
        points: List[dict] = []
        for s in self.snapshots:
            rec = _by_subject(s).get(subject)
            points.append({
                "label": s.get("label"), "stage": s.get("stage"),
                "taken_at": s.get("taken_at"),
                "present": rec is not None,
                "origin": rec.get("origin") if rec else None,
                "evidence_class": rec.get("evidence_class") if rec else None,
                "modifier": rec.get("modifier") if rec else None,
            })
        return points

    def subjects(self) -> List[str]:
        seen: set = set()
        for s in self.snapshots:
            seen.update(_by_subject(s).keys())
        return sorted(seen)

    def compare_stages(self, label_a: str, label_b: str) -> Dict[str, Any]:
        """Diff two named stages anywhere in the series (by snapshot label)."""
        from .snapshot import diff_snapshots
        a = self._find(label_a)
        b = self._find(label_b)
        if a is None or b is None:
            raise KeyError(f"stage label(s) not found: {label_a!r}/{label_b!r}")
        return diff_snapshots(a, b)

    def _find(self, label: str) -> Optional[dict]:
        for s in self.snapshots:
            if s.get("label") == label:
                return s
        return None


def cycle_timeline(series: Series) -> List[dict]:
    """Track the runtime graph's feedback cycles across the series — one row per
    stage with each cycle's status, so loop-confidence progression is legible."""
    out: List[dict] = []
    for s in series.snapshots:
        rec = _by_subject(s).get("runtime_graph")
        cycles = {}
        if rec and isinstance(rec.get("data"), dict):
            for c in rec["data"].get("feedback_cycles", []):
                cycles[" -> ".join(c.get("cycle", []))] = c.get("status")
        out.append({"label": s.get("label"), "stage": s.get("stage"),
                    "taken_at": s.get("taken_at"), "cycles": cycles})
    return out
