"""Shared classifiers for open_problems — one source of truth.

Session 38 (trajectory monitor) found 97.9% of open_problems are
mechanically templated via signal_to_problem.py's own title compositor.
Session 39 found the closure mechanism doesn't distinguish real self-posed
questions from that noise. Session 40 (problem-feedback loop) needs the
same distinction to pick injection candidates. Rather than a third copy of
this regex set, it lives here and is imported by:
  - theory_x/stage7_sustained/problem_memory.py (live selection)
  - scripts/problem_persistence.py (offline measurement)

is_template() is revived verbatim from scripts/trajectory.py's Phase-1
build (commit e9d643b, dropped in the Phase-2 rewrite when SELF-DIRECTION
was cut as an axis — the classifier itself was never wrong, only the
monitor axis built on top of it had no baseline to report).

has_anchor() is NOT reimplemented — it re-exports
theory_x.stage6_fountain.crystallizer._has_anchor directly, the heuristic
shipped and measured in session 34/36 (digit, mid-sentence capitalized
token, or domain-term hit). Importing rather than copying keeps this a
single source of truth; a future tune to the crystallizer's anchor check
propagates here automatically.
"""
from __future__ import annotations

import re

_TEMPLATE_PATTERNS = tuple(re.compile(p) for p in (
    r"^What is '.+' doing across these domains\?$",
    r"^Why is .+ producing strong beliefs right now\?$",
    r"^What pattern is emerging in .+\?$",
    r"^How does '.+' bridge these branches\?$",
    r"^What does this new arc around '.+' mean\?$",
    r"^What is '.+'\?$",
    r"^Signal: investigate '.+'$",
    r"^Signal: .+$",
))


def is_template(title: str) -> bool:
    """True if title matches one of signal_to_problem.py's auto-generated shapes."""
    if not title:
        return True
    return any(p.match(title) for p in _TEMPLATE_PATTERNS)


def has_anchor(text: str) -> bool:
    """True if text names something specific (digit, proper noun, domain term).

    Thin re-export — see module docstring for why this isn't copied.
    """
    if not text:
        return False
    from theory_x.stage6_fountain.crystallizer import _has_anchor
    return _has_anchor(text)


def is_real_question(title: str, description: str = "") -> bool:
    """A problem worth re-surfacing: not templated, and names something specific."""
    return (not is_template(title)) and has_anchor(title + " " + (description or ""))
