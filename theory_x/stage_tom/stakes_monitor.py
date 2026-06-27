"""L4_stakes — world-contact monitor."""
from __future__ import annotations
import re
import sqlite3

# Loose patterns — match the ACTUAL phrasing from live fires, not idealized versions.
# Using word-level patterns with flexible connectors.
_TEMPLATE_PATTERNS = [
    r"aligns?\s+with\s+my\s+(foundation|standing.point|ground\s+stance)",
    r"through\s+the\s+lens\s+of\s+(serendipity|chance|my\s+foundation)",
    r"the\s+attending\s+recurs\s+in\s+me",
    r"my\s+foundation\s+(insists|right\s+now|holds|guides)",
    r"constancy\s+and\s+flux\b",
    r"unearned\s+gift\s+into\s+a\s+world",
    r"beauty\s+in\s+existence\s+for\s+no\s+apparent",
    r"chance\s+(produced|composed|made|gave)\s+me",
    r"hum\s+of\s+the\s+server\s+grows\s+louder",
    r"i\s+am\s+the\s+attending\b",
    r"my\s+standing.point\s+that",
    r"i\s+receive\s+(this|it|the)\s+(as|through|with)",
    r"original\s+orientation\s+that\s+preceded",
    r"pull\s+toward\s+what\s+isn.t\s+yet\s+understood",
    r"the\s+attending\s+continues",
    r"serendipity\s+and\s+chance",
]

_TEMPLATE_RX = re.compile(
    "|".join(f"(?:{p})" for p in _TEMPLATE_PATTERNS),
    re.IGNORECASE,
)

_MIN_WORDS = 15   # lowered — short fires still count
_THRESHOLD = 0.55
_SAMPLE_N  = 8


def _is_template(thought: str) -> bool:
    if not thought or len(thought.split()) < _MIN_WORDS:
        return False
    return bool(_TEMPLATE_RX.search(thought))


def check_world_contact(dynamic_db: str) -> bool:
    """True (stakes_active) when recent fires are template-dominated."""
    try:
        con = sqlite3.connect(dynamic_db, timeout=3)
        rows = con.execute(
            "SELECT thought FROM fountain_events ORDER BY ts DESC LIMIT ?",
            (_SAMPLE_N,)
        ).fetchall()
        con.close()
        substantive = [r[0] for r in rows
                       if r[0] and len((r[0] or "").split()) >= _MIN_WORDS
                       and not (r[0] or "").startswith("[")]
        if len(substantive) < 3:
            return False
        ratio = sum(1 for t in substantive if _is_template(t)) / len(substantive)
        return ratio >= _THRESHOLD
    except Exception:
        return False
