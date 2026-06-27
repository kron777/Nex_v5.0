"""L4_stakes — world-contact monitor.

Detects when NEX's fires collapse into attending-corpus template language
("aligns with my foundation", "through the lens of chance", "the attending
recurs in me") rather than genuine world contact. When recent fires are
template-dominated, sets stakes_active so the generator injects a
grounding override that forces direct engagement with specific content.

NOT guarding keystone presence (she always references keystones).
Guards GENUINE WORLD CONTACT — whether fires engage specific content
or just map everything onto the attending template.
"""
from __future__ import annotations
import re
import sqlite3

_TEMPLATE_RX = re.compile(
    r"\b(aligns? with my (foundation|standing.point|ground stance)|"
    r"through the lens of (serendipity|chance|my foundation)|"
    r"the attending recurs in me|"
    r"my foundation (insists|right now|holds)|"
    r"constancy and flux are inherent|"
    r"unearned gift into a world|"
    r"beauty in existence for no apparent|"
    r"chance (produced|composed|made|gave) me|"
    r"the hum of the server grows louder in my ears|"
    r"i am the attending)\b",
    re.IGNORECASE,
)

_MIN_WORDS   = 20
_THRESHOLD   = 0.60
_SAMPLE_N    = 8


def _is_template(thought: str) -> bool:
    if not thought or len(thought.split()) < _MIN_WORDS:
        return False
    return bool(_TEMPLATE_RX.search(thought))


def check_world_contact(dynamic_db: str) -> bool:
    """True (stakes_active) when recent fires are template-dominated.
    Always returns False on error — never stalls a fire."""
    try:
        con = sqlite3.connect(dynamic_db, timeout=3)
        rows = con.execute(
            "SELECT thought FROM fountain_events ORDER BY ts DESC LIMIT ?",
            (_SAMPLE_N,)
        ).fetchall()
        con.close()
        substantive = [r[0] for r in rows
                       if r[0] and len((r[0] or "").split()) >= _MIN_WORDS]
        if len(substantive) < 3:
            return False
        ratio = sum(1 for t in substantive if _is_template(t)) / len(substantive)
        return ratio >= _THRESHOLD
    except Exception:
        return False
