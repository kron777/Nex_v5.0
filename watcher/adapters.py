"""Read-only diagnostic-tool adapters + source-level safety classification.

The Watcher reuses NEX's existing read-only diagnostics instead of rebuilding
them. Every tool is classified by its INSPECTED SIDE EFFECTS (not its name):

  passive  — read-only (opens DBs mode=ro, writes nothing)
  isolated — fixtures / temp DB only
  active   — writes/injects/mutates live NEX  (e.g. decryption/probe_runner.py)
  unknown  — side effects not established -> never run against live NEX

`classify_tool` greps a tool's source for write markers and returns a class with
the lines it cited. `KNOWN` records the Phase-0 classifications. A
`ReadOnlyToolAdapter` will only ever run a tool classified `passive`, and only on
the HOST (the check_*.py tools need the live DBs, which cloud cannot reach);
cloud-side it refuses to execute and emits classification evidence instead.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from .evidence import Evidence
from .safety import PassiveViolation

# Strong DB-write markers only. Ambiguous ones (subprocess, bare connect(),
# os.environ[...], "restart") are deliberately excluded: a read-only tool can use
# subprocess (e.g. to render a diagram) or a normal connection that only SELECTs,
# so those produce false positives. Side-effects the heuristic can't resolve stay
# for host-side source inspection, not an over-eager "active" label.
_WRITE_MARKERS = re.compile(
    r"(INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|REPLACE\s+INTO|executescript|\.commit\()",
    re.IGNORECASE,
)
_RO_MARKER = re.compile(r"mode=ro|READ-ONLY|read-only|writes nothing|idempotent", re.IGNORECASE)

# Phase-0 classifications (verified by source inspection this session).
KNOWN: Dict[str, str] = {
    "tools/check_cadence.py": "passive",
    "tools/check_session_consistency.py": "passive",
    "tools/check_template_repetition.py": "passive",
    "tools/check_tripwires.py": "passive",
    "scripts/instrument_report.py": "passive",
    "scripts/snapshot.py": "passive",
    "mind_map/mind_map.py": "passive",
    "decryption/probe_runner.py": "active",     # injects synthetic beliefs into live DB
    "scripts/genius_set_threshold.py": "active",
    "scripts/label_genius.py": "active",
    "tools/metacog_digest.py": "active",
}


def classify_tool(path: str) -> Evidence:
    """Classify one tool by reading its source (read-only). Cites the markers."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError as e:
        return Evidence(f"tool_class:{path}", None, "cloud", "unknown", path,
                        modifier="unverified", interpretation=f"unreadable: {e}")
    write_hits = sorted({m.group(0) for m in _WRITE_MARKERS.finditer(text)})
    ro_hits = bool(_RO_MARKER.search(text))
    if write_hits:
        klass = "active"
    elif ro_hits:
        klass = "passive"
    else:
        klass = "unknown"
    return Evidence(
        f"tool_class:{path}", {"class": klass, "write_markers": write_hits, "ro_markers": ro_hits},
        "cloud", "implemented", path,
        interpretation=f"Classified {klass} by inspected side effects. "
                       f"{'Cited: ' + ', '.join(write_hits) if write_hits else 'no write markers found'}.")


class ReadOnlyToolAdapter:
    """Wraps an existing tool; runs it ONLY if passive AND on the host."""

    def __init__(self, path: str, tool_class: Optional[str] = None) -> None:
        self.path = path
        self.tool_class = tool_class or KNOWN.get(path, "unknown")

    def run_on_host(self, *_a, **_k):
        if self.tool_class != "passive":
            raise PassiveViolation(
                f"refusing to run non-passive tool {self.path!r} (class={self.tool_class})")
        # Executed by Claude Code on the machine (needs live DBs). Cloud cannot.
        raise PassiveViolation(
            f"{self.path} runs against live DBs -> host-only. Cloud must not execute it; "
            f"dispatch it to Claude Code.")


def collect(repo_dir: str = ".") -> List[Evidence]:
    """For each KNOWN tool, report the verified class AND a heuristic cross-check,
    flagging any disagreement for human review (the heuristic is a signal, not
    ground truth)."""
    import os
    out: List[Evidence] = []
    for rel, known in KNOWN.items():
        p = os.path.join(repo_dir, rel)
        if not os.path.exists(p):
            continue
        h = classify_tool(p)
        heuristic = (h.data or {}).get("class", "unknown")
        agrees = heuristic == known
        out.append(Evidence(
            f"tool_class:{rel}",
            {"verified_class": known, "heuristic_class": heuristic, "agrees": agrees,
             "write_markers": (h.data or {}).get("write_markers", [])},
            "cloud", "implemented", p,
            interpretation=("verified class = %s" % known) + (
                "" if agrees else
                f"  — NOTE: source heuristic said '{heuristic}'; disagreement flagged for review")))
    return out
