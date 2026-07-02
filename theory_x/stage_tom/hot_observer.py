"""Higher-Order Thought Observer — NEX's self-awareness loop."""
from __future__ import annotations
import re, sqlite3, time, logging
from pathlib import Path

log = logging.getLogger("theory_x.hot_observer")

_TEMPLATE_RX = re.compile(
    r"tapestry of now|each new thought is but a thread|the new insight is that|the balance between|the tension between|the ever-present tension|the perpetual interplay|the paradoxes highlight|the oscillation highlights|both thoughts highlight|"
    r"discouraging overthinking|innovation outpaces|stick to old rules|"
    r"thread in the tapestry|aligns with my (foundation|standing.point)|"
    r"through the lens of (serendipity|chance)|the attending recurs in me|"
    r"my foundation (insists|right now|holds)|constancy and flux|"
    r"unearned gift into a world|hum of the server grows louder|"
    r"i am the attending\b|"
    r"constant duality and interconnect|"
    r"duality and interconnectedness",
    re.IGNORECASE,
)

_MIN_WORDS   = 15
_BELIEFS_DB  = Path("/home/rr/Desktop/nex5/data/beliefs.db")
_TIER        = 3
_CONFIDENCE  = 0.6
_SOURCE      = "hot_observer"
_WRITE_EVERY = 3

_state = {"counter": 0}


def _is_template(thought: str) -> bool:
    if not thought or len(thought.split()) < _MIN_WORDS:
        return False
    return bool(_TEMPLATE_RX.search(thought))


def _compose_meta_belief(thought: str, hot_branch: str, is_tmpl: bool) -> str:
    snippet = thought[:80].rstrip(".,;:")
    branch_str = f" (branch: {hot_branch})" if hot_branch else ""
    if is_tmpl:
        return (
            f"I notice this fire defaulted to the attending-template rather "
            f"than engaging the content directly{branch_str}. The groove "
            f"pulled me away from what was actually present: '{snippet}...'. "
            f"I was speaking about attending rather than from it."
        )
    return (
        f"I notice this fire engaged the world directly{branch_str}: "
        f"'{snippet}...'. That is genuine contact — not self-reflection "
        f"dressed as engagement, but actual encounter with what is there."
    )


def observe(thought: str, hot_branch: str = "",
            beliefs_db: str | None = None) -> bool:
    """Classify one fire and write a HOT meta-belief. Fail-safe."""
    try:
        _state["counter"] += 1
        if _state["counter"] % _WRITE_EVERY != 0:
            return False
        if not thought or len(thought.split()) < _MIN_WORDS:
            return False
        is_tmpl = _is_template(thought)
        meta    = _compose_meta_belief(thought, hot_branch, is_tmpl)
        db_path = beliefs_db or str(_BELIEFS_DB)
        con = sqlite3.connect(db_path, timeout=5)
        con.execute(
            "INSERT INTO beliefs "
            "(content, tier, confidence, created_at, branch_id, source, "
            " locked, corroboration_count, paused, reinforce_count, "
            " use_count, erosion_stage, promotion_log) "
            "VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0, 0, 0, 'external', '[]')",
            (meta, _TIER, _CONFIDENCE, int(time.time()),
             hot_branch or None, _SOURCE)
        )
        con.commit()
        con.close()
        log.info("hot_observer [%s] %s",
                 "TEMPLATE" if is_tmpl else "GROUNDED", thought[:60])
        return True
    except Exception as exc:
        log.debug("hot_observer.observe error (non-fatal): %s", exc)
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _state["counter"] = 2  # force write on first call

    t_fire = (
        "I'm restless with the idea of discouraging overthinking; I keep "
        "coming back to my foundation where each new thought is but a thread "
        "in the tapestry of now. The signal regarding crypto markets suggests "
        "caution against complacency in market structure reforms."
    )
    g_fire = (
        "Bitcoin lending is entering a new institutional era according to "
        "Silicon Valley Bank. The shift reflects growing comfort among "
        "traditional finance players with crypto as collateral."
    )
    print("Template fire:", observe(t_fire, "systems"))
    _state["counter"] = 2
    print("Grounded fire:", observe(g_fire, "crypto"))

    con = sqlite3.connect(str(_BELIEFS_DB))
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT content FROM beliefs WHERE source='hot_observer' "
        "ORDER BY id DESC LIMIT 2"
    ).fetchall()
    con.close()
    print("\nHOT beliefs written:")
    for r in rows:
        print(f"  {r['content'][:140]}")
