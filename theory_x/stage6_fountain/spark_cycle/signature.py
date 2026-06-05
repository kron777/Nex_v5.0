"""Imprint signature — Spark Cycle Architecture, spec section 4.6.

Deterministic, human-readable encoding of a substrate diff pattern. Two sparks
with the same signature left the same shape of trace, regardless of content.
Pure function over a diff-like mapping; no NEX imports, no I/O, no clock.

Layout:  <bd><ed><t><r><g><c>|<branches>|<edge_types>
    bd  belief_delta            capped -5..+5, signed ("+2","-5","+0")
    ed  edge_delta              capped -5..+5, signed
    t   temperature direction   '-' / '0' / '+'
    r   branch_reorientation    '0' / '1'
    g   graph_restructure       '0' / '1'
    c   belief_creation         '0' / '1'
    branches    sorted branches_shifted, first 3, comma-joined ('' if none)
    edge_types  sorted edge_types_created, first 3, comma-joined ('' if none)

Example: "+2+1+011|ai_research,systems|cross_domain,supports"
NOTE: spec 4.6's worked example is shown UNSORTED; this sorts (spec says "sorted
list"). Sorting is the point — it makes the signature order-independent so two
sparks touching {systems, ai_research} in either order collide. Tests assert sorted.
"""

from __future__ import annotations

from typing import Iterable, Mapping

_CAP = 5
_TRUNC = 3


def _signed_capped(value: int) -> str:
    try:
        v = int(value)
    except (TypeError, ValueError):
        v = 0
    if v > _CAP:
        v = _CAP
    elif v < -_CAP:
        v = -_CAP
    return f"{v:+d}"


def _direction(value) -> str:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return "0"
    if f > 0:
        return "+"
    if f < 0:
        return "-"
    return "0"


def _flag(value) -> str:
    return "1" if bool(value) else "0"


def _tag_list(items: Iterable | None) -> str:
    if not items:
        return ""
    seen = []
    for x in items:
        s = str(x)
        if s not in seen:
            seen.append(s)
    seen.sort()
    return ",".join(seen[:_TRUNC])


def compute_signature(diff: Mapping) -> str:
    bd = _signed_capped(diff.get("belief_delta", 0))
    ed = _signed_capped(diff.get("edge_delta", 0))
    t = _direction(diff.get("temperature_shift", 0.0))
    r = _flag(diff.get("branch_reorientation", False))
    g = _flag(diff.get("graph_restructure", False))
    c = _flag(diff.get("belief_creation", False))
    branches = _tag_list(diff.get("branches_shifted"))
    edges = _tag_list(diff.get("edge_types_created"))
    return f"{bd}{ed}{t}{r}{g}{c}|{branches}|{edges}"
