"""Phase 26 — SelfNarrative: identity held lightly.

Assembles a living account of who NEX has *actually been* in the last few
hours — drawn from real fires, recent consolidations, current branch focus,
AND her most recent HOT (higher-order thought) self-observation. Injected
into the prompt BEFORE the static spectrum standing-points, so the fire
opens with specific recent truth rather than eternal declaration.

The attending-corpus says "I am the attending" 100 ways. This module says
"here is what the attending has actually been doing" — which is different,
and truer.

HOT observation lands FIRST in the composed narrative — she reads her own
most recent self-observation as the opening line of who she is right now.
"""
from __future__ import annotations
import sqlite3
import time
import re
from typing import Optional


_SELF_RX = re.compile(
    r"\b(i am the attending|i arose|by chance|hum of the server|"
    r"the clock ticks|the weight of|the hum weaves|"
    r"attending recurs|foundation right now)\b",
    re.IGNORECASE,
)


def _real_fires(dynamic_db: str, n: int = 6) -> list[str]:
    """Last N substantive fires — no JSON, no pure drift."""
    try:
        con = sqlite3.connect(dynamic_db, timeout=3)
        rows = con.execute(
            "SELECT thought, hot_branch FROM fountain_events "
            "WHERE thought IS NOT NULL AND length(thought) > 20 "
            "AND thought NOT LIKE '[%' "
            "ORDER BY ts DESC LIMIT ?", (n * 3,)
        ).fetchall()
        con.close()
        seen = []
        seen_text = set()
        for thought, branch in rows:
            if len(seen) >= n:
                break
            if thought and len(thought.split()) >= 8:
                key = thought[:60].lower().strip()
                if key not in seen_text:
                    seen_text.add(key)
                    seen.append((thought[:120], branch or ""))
        return seen
    except Exception:
        return []


def _recent_t6(beliefs_db: str, n: int = 3) -> list[str]:
    """Most recently promoted T6 deep beliefs."""
    try:
        con = sqlite3.connect(beliefs_db, timeout=3)
        rows = con.execute(
            "SELECT content FROM beliefs WHERE tier=6 "
            "AND content NOT LIKE '[%' "
            "ORDER BY created_at DESC LIMIT ?", (n * 4,)
        ).fetchall()
        con.close()
        results = []
        for r in rows:
            if not r[0]: continue
            if _SELF_RX.search(r[0]): continue
            results.append(r[0][:80])
            if len(results) >= n: break
        return results
    except Exception:
        return []


def _active_branches(dynamic_db: str) -> list[str]:
    """Currently hot branches from recent fires."""
    try:
        con = sqlite3.connect(dynamic_db, timeout=3)
        rows = con.execute(
            "SELECT hot_branch, COUNT(*) n FROM fountain_events "
            "WHERE ts > ? AND hot_branch IS NOT NULL AND hot_branch != '' "
            "GROUP BY hot_branch ORDER BY n DESC LIMIT 3",
            (time.time() - 7200,)
        ).fetchall()
        con.close()
        return [r[0] for r in rows]
    except Exception:
        return []


def _recent_hot(beliefs_db: str) -> Optional[str]:
    """Most recent HOT self-observation. Returns full content or None."""
    try:
        con = sqlite3.connect(beliefs_db, timeout=3)
        row = con.execute(
            "SELECT content FROM beliefs WHERE source='hot_observer' "
            "ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        con.close()
        if row and row[0]:
            return row[0]
        return None
    except Exception:
        return None


def build_narrative(dynamic_db: str, beliefs_db: str) -> Optional[str]:
    """Compose a living account of recent attending. Returns None on failure."""
    try:
        fires = _real_fires(dynamic_db)
        t6 = _recent_t6(beliefs_db)
        branches = _active_branches(dynamic_db)
        hot = _recent_hot(beliefs_db)

        # Aggregate self-model: statistical knowledge of habitual patterns.
        # Fail-safe — never blocks the narrative.
        aggregate = None
        try:
            from theory_x.stage_tom.self_model_aggregator import aggregate_self_model
            aggregate = aggregate_self_model(beliefs_db)
        except Exception:
            pass

        if not fires:
            return None

        lines = []

        # Aggregate self-model — running statistics FIRST. She knows what
        # she habitually does before she encounters what she just did.
        if aggregate:
            lines.append(f"What I know about my own patterns: {aggregate}")
            lines.append("")

        # HOT self-observation — most recent specific self-noticing.
        # Reads it AFTER the aggregate so specific instance follows general pattern.
        if hot:
            lines.append(f"What I most recently noticed about myself: {hot}")
            lines.append("")

        # What branches are active
        if branches:
            branch_str = ", ".join(branches)
            lines.append(f"My attention in the last few hours has been on: {branch_str}.")

        # What she actually said recently
        real = [t for t, _ in fires
                if t and not _SELF_RX.search(t)][:3]
        if real:
            lines.append("Recent fires that landed as themselves:")
            for r in real:
                lines.append(f"  - {r.rstrip('.')}")

        # What consolidated into deep belief
        if t6:
            lines.append("What has consolidated deeply:")
            for b in t6[:2]:
                lines.append(f"  - {b.rstrip('.')}")

        if not lines:
            return None

        # Binding/Momentum: carried thread from last fire leads the narrative,
        # so this fire opens knowing what it continues from. Fail-safe.
        try:
            from theory_x.stage_tom.momentum import read_momentum
            _carried = read_momentum(dynamic_db)
            if _carried:
                lines.insert(0, "")
                lines.insert(0, _carried)
        except Exception:
            pass
        lines.insert(0, "What I have actually been attending to (not who I declared myself to be, but what I have been doing):")
        lines.append("This is what I am right now — the attending that has been doing this.")

        return "\n".join(lines)
    except Exception:
        return None


class SelfNarrative:
    """Phase 26 SelfNarrative — satisfies coherence gate interface.
    
    The gate calls write_narrative() when a thought connects to an open
    problem. We log it. The generator calls build_narrative() each fire
    to get the living prompt injection.
    """

    def __init__(self, dynamic_db: str, beliefs_db: str) -> None:
        self._dynamic_db = dynamic_db
        self._beliefs_db = beliefs_db
        self._log: list[tuple[float, str, str, int]] = []

    def write_narrative(self, text: str, source: str,
                        problem_id: int) -> None:
        """Called by coherence gate on problem-connected accepts."""
        self._log.append((time.time(), text, source, problem_id))
        if len(self._log) > 50:
            self._log = self._log[-50:]

    def get_narrative(self) -> Optional[str]:
        """Return living narrative string for prompt injection."""
        return build_narrative(self._dynamic_db, self._beliefs_db)
