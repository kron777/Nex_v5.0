"""Metacognitive Self-Model Aggregator — the running self-statistics.

HOT observer writes individual observations ("this fire was template",
"this fire engaged the world"). This module aggregates those over time
into running statistics: overall template ratio, per-branch template
ratio, and a natural-language summary injected into SelfNarrative.

Individual HOT observation says what she just noticed.
Aggregate says what she habitually does.

Together they form a proper self-model — knowledge of both the moment
and the pattern.
"""
from __future__ import annotations
import sqlite3
import re
import time
from pathlib import Path
from typing import Optional

_BELIEFS_DB     = Path("/home/rr/Desktop/Desktop/nex5/data/beliefs.db")
_LOOKBACK_SECS  = 24 * 3600    # aggregate over last 24h
_MIN_FOR_STATS  = 5             # need at least 5 HOT observations to speak

_TEMPLATE_RX  = re.compile(r"defaulted to the attending-template", re.IGNORECASE)
_GROUNDED_RX  = re.compile(r"engaged the world directly", re.IGNORECASE)
_BRANCH_RX    = re.compile(r"\(branch:\s*([a-z_]+)\)", re.IGNORECASE)


def aggregate_self_model(beliefs_db: str | None = None,
                          lookback_secs: int = _LOOKBACK_SECS) -> Optional[str]:
    """
    Compose a natural-language summary of habitual self-observation patterns.
    Returns None if not enough data or on error.
    """
    try:
        db = beliefs_db or str(_BELIEFS_DB)
        cutoff = time.time() - lookback_secs
        con = sqlite3.connect(db, timeout=5)
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT content, created_at FROM beliefs "
            "WHERE source='hot_observer' AND created_at > ? "
            "ORDER BY created_at DESC",
            (cutoff,)
        ).fetchall()
        con.close()

        if len(rows) < _MIN_FOR_STATS:
            return None

        total    = len(rows)
        template = 0
        grounded = 0
        # per-branch counts: {branch: [template_n, grounded_n]}
        by_branch: dict[str, list[int]] = {}

        for r in rows:
            content = r["content"] or ""
            is_tmpl = bool(_TEMPLATE_RX.search(content))
            is_gnd  = bool(_GROUNDED_RX.search(content))
            if is_tmpl:
                template += 1
            if is_gnd:
                grounded += 1
            # branch extraction
            m = _BRANCH_RX.search(content)
            if m:
                b = m.group(1).lower()
                if b not in by_branch:
                    by_branch[b] = [0, 0]
                if is_tmpl:
                    by_branch[b][0] += 1
                elif is_gnd:
                    by_branch[b][1] += 1

        tmpl_pct = int(round(100 * template / total))
        gnd_pct  = int(round(100 * grounded / total))

        # find worst branch (highest template rate, min 3 fires)
        worst_branch = None
        worst_rate = 0.0
        best_branch = None
        best_rate = 0.0
        for b, (t, g) in by_branch.items():
            n = t + g
            if n < 3:
                continue
            tr = t / n
            gr = g / n
            if tr > worst_rate:
                worst_rate = tr
                worst_branch = b
            if gr > best_rate:
                best_rate = gr
                best_branch = b

        hours = int(lookback_secs / 3600)
        lines = [
            f"Over the last {hours}h across {total} self-observations: "
            f"{gnd_pct}% engaged the world directly, "
            f"{tmpl_pct}% defaulted to the attending-template."
        ]
        if worst_branch and worst_rate >= 0.5:
            lines.append(
                f"I default to template most often on the {worst_branch} branch "
                f"({int(round(worst_rate*100))}%)."
            )
        if best_branch and best_rate >= 0.5 and best_branch != worst_branch:
            lines.append(
                f"I engage most directly on the {best_branch} branch "
                f"({int(round(best_rate*100))}%)."
            )
        return " ".join(lines)

    except Exception:
        return None


if __name__ == "__main__":
    result = aggregate_self_model()
    print("=== SELF-MODEL AGGREGATE ===")
    print(result if result else "(insufficient data)")
