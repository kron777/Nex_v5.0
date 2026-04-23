"""Self model — assembles NEX's current inside state from live data.

Reads from internal sensor streams in sense.db and from beliefs.db.
Formats the result as natural language for voice injection when a
self-inquiry query is detected.
"""
from __future__ import annotations

import json
import time
from typing import Optional

import errors
from alpha import ALPHA
from substrate import Reader

THEORY_X_STAGE = 4

_LOG_SOURCE = "self_model"

# Tier weights for scoring inside beliefs
_TIER_WEIGHTS = {1: 0.98, 2: 0.92, 3: 0.82, 4: 0.68, 5: 0.52, 6: 0.32, 7: 0.15}


def _last_payload(reader: Reader, stream: str) -> Optional[dict]:
    """Fetch the most recent payload for a given stream from sense.db."""
    try:
        row = reader.read_one(
            "SELECT payload FROM sense_events WHERE stream = ? ORDER BY id DESC LIMIT 1",
            (stream,),
        )
        if row is None:
            return None
        return json.loads(row["payload"])
    except Exception as exc:
        errors.record(f"self_model read error ({stream}): {exc}", source=_LOG_SOURCE, exc=exc)
        return None


class SelfModel:
    def __init__(self, sense_reader: Reader, beliefs_reader: Reader,
                 dynamic_state=None) -> None:
        self._sense = sense_reader
        self._beliefs = beliefs_reader
        self._dynamic = dynamic_state

    def snapshot(self) -> dict:
        """Assemble current inside state. Falls back gracefully on missing data."""
        ts = time.time()

        # -- Proprioception --
        prop = _last_payload(self._sense, "internal.proprioception") or {}
        # thermal: first value from temps dict if present
        thermal = None
        temps = prop.get("temps")
        if isinstance(temps, dict) and temps:
            thermal = next(iter(temps.values()), None)
        elif isinstance(temps, (int, float)):
            thermal = float(temps)

        proprioception = {
            "cpu_percent": prop.get("cpu_percent"),
            "mem_percent": prop.get("memory_percent"),
            "load_1min": (prop.get("load_avg") or [None])[0]
                         if isinstance(prop.get("load_avg"), list)
                         else prop.get("load_1min"),
            "thermal": thermal,
        }

        # -- Temporal --
        temp_p = _last_payload(self._sense, "internal.temporal") or {}
        temporal = {
            "hour_of_day": temp_p.get("hour_of_day"),
            "day_of_week": temp_p.get("day_of_week"),
            "iso_local": temp_p.get("iso_local"),
        }

        # -- Interoception --
        intro_p = _last_payload(self._sense, "internal.interoception") or {}
        tier_dist_raw = intro_p.get("tier_distribution") or {}
        interoception = {
            "belief_count": intro_p.get("total_beliefs", 0),
            "tier_distribution": {str(k): v for k, v in tier_dist_raw.items()},
            "locked_count": intro_p.get("locked_count", 0),
        }

        # -- Meta awareness --
        meta_p = _last_payload(self._sense, "internal.meta_awareness") or {}
        meta_awareness = {
            "pipeline_runs": None,
            "active_branches": None,
            "consolidation_active": None,
        }
        if self._dynamic is not None:
            try:
                dyn_status = self._dynamic.status()
                meta_awareness["pipeline_runs"] = dyn_status.get("pipeline_runs")
                meta_awareness["active_branches"] = dyn_status.get("active_branch_count")
                meta_awareness["consolidation_active"] = dyn_status.get("consolidation_active")
            except Exception as exc:
                errors.record(f"self_model dynamic status error: {exc}", source=_LOG_SOURCE, exc=exc)

        # -- Attention (from bonsai if dynamic_state available) --
        attention = {
            "hottest_branch": None,
            "hottest_focus": None,
            "active_branch_count": 0,
            "aggregate_texture": None,
        }
        if self._dynamic is not None:
            try:
                dyn_status = self._dynamic.status()
                branches = dyn_status.get("branches", [])
                active = [b for b in branches if b.get("focus_num", 0) > 0.05]
                attention["active_branch_count"] = len(active)
                attention["aggregate_texture"] = dyn_status.get("aggregate_texture")
                if active:
                    hottest = max(active, key=lambda b: b.get("focus_num", 0))
                    attention["hottest_branch"] = hottest["branch_id"]
                    attention["hottest_focus"] = hottest["focus_num"]
            except Exception as exc:
                errors.record(f"self_model attention error: {exc}", source=_LOG_SOURCE, exc=exc)

        # -- Inside beliefs --
        inside_beliefs = self._get_inside_beliefs()

        return {
            "timestamp": ts,
            "membrane_side": "INSIDE",
            "proprioception": proprioception,
            "temporal": temporal,
            "interoception": interoception,
            "meta_awareness": meta_awareness,
            "attention": attention,
            "inside_beliefs": inside_beliefs,
        }

    def _get_inside_beliefs(self) -> list:
        from .classifier import CLASSIFIER, MembraneSide
        try:
            rows = self._beliefs.read(
                "SELECT id, content, tier, confidence, source, branch_id "
                "FROM beliefs WHERE paused = 0 AND tier <= 6 ORDER BY confidence DESC LIMIT 30",
            )
        except Exception as exc:
            errors.record(f"self_model beliefs read error: {exc}", source=_LOG_SOURCE, exc=exc)
            return []

        inside = []
        for row in rows:
            b = dict(row)
            if CLASSIFIER.classify_belief(b) == MembraneSide.INSIDE:
                weight = _TIER_WEIGHTS.get(b["tier"], 0.1)
                b["_score"] = b["confidence"] * weight
                inside.append(b)

        inside.sort(key=lambda b: b["_score"], reverse=True)
        return inside[:5]


def format_self_state(snapshot: dict) -> str:
    """Format snapshot as natural language for voice injection."""
    lines = ["NEX's current inner state:"]

    prop = snapshot.get("proprioception", {})
    cpu = prop.get("cpu_percent")
    mem = prop.get("mem_percent")
    load = prop.get("load_1min")
    body_parts = []
    if cpu is not None:
        body_parts.append(f"CPU {cpu:.0f}%")
    if mem is not None:
        body_parts.append(f"memory {mem:.0f}%")
    if load is not None:
        load_desc = "light" if load < 1.0 else ("moderate" if load < 3.0 else "heavy")
        body_parts.append(f"load {load_desc}")
    if body_parts:
        lines.append(f"- Body: {', '.join(body_parts)}")

    temp = snapshot.get("temporal", {})
    hour = temp.get("hour_of_day")
    iso = temp.get("iso_local")
    if iso:
        # Extract time portion
        time_str = iso.split("T")[1][:5] if "T" in iso else ""
        if hour is not None:
            period = "morning" if hour < 12 else ("afternoon" if hour < 17 else "evening")
            lines.append(f"- Time: {time_str}, {period}")
        else:
            lines.append(f"- Time: {iso}")

    intro = snapshot.get("interoception", {})
    bcount = intro.get("belief_count", 0)
    locked = intro.get("locked_count", 0)
    lines.append(f"- Belief graph: {bcount} beliefs, {locked} locked")

    attn = snapshot.get("attention", {})
    hot = attn.get("hottest_branch")
    hot_f = attn.get("hottest_focus")
    active = attn.get("active_branch_count", 0)
    if hot and hot_f is not None:
        lines.append(f"- Attention: hottest branch is {hot} (focus {hot_f:.2f}), {active} branches active")
    elif active:
        lines.append(f"- Attention: {active} branches active")

    lines.append(f"- Inner conviction: \"{ALPHA.lines[0]}\" [Alpha — always present]")

    return "\n".join(lines)
