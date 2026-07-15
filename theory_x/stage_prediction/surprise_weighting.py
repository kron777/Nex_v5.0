"""Surprise-Weighted Belief Deposit — predictive processing feedback path.

When a fire crystallizes into a T6 belief, check whether a recent surprise
event preceded this fire. If yes, weight the belief's confidence by the
surprise score. High-surprise fires (genuine novelty) deposit heavier
beliefs; routine confirmation deposits at baseline.

This is Karl Friston's free energy principle at its most implementable:
novelty drives learning, not confirmation. Prediction error becomes the
weighting signal for belief formation.

Returns a confidence value in [_MIN_CONF, _MAX_CONF].
"""
from __future__ import annotations
import logging
import sqlite3
import time
from pathlib import Path

log = logging.getLogger("theory_x.surprise_weighting")

_BASE_CONFIDENCE = 0.70   # crystallizer default
_MIN_CONF        = 0.55
_MAX_CONF        = 0.92
_BOOST_FACTOR    = 0.22   # max additional confidence at surprise_score=1.0
_LOOKBACK_SECS   = 60.0   # surprise must be recent to count
_DYNAMIC_DB      = Path("/home/rr/Desktop/Desktop/nex5/data/dynamic.db")


def confidence_for_fire(dynamic_db: str | None = None) -> tuple[float, float]:
    """
    Returns (confidence, surprise_score).
      confidence    — adjusted belief confidence in [_MIN_CONF, _MAX_CONF]
      surprise_score — the surprise that drove the adjustment, 0.0 if none

    Fail-safe: returns (_BASE_CONFIDENCE, 0.0) on any error.
    """
    try:
        db = dynamic_db or str(_DYNAMIC_DB)
        cutoff = time.time() - _LOOKBACK_SECS
        con = sqlite3.connect(db, timeout=3)
        row = con.execute(
            "SELECT surprise_score, surprise_flag, big_surprise "
            "FROM surprise_events "
            "WHERE triggered_at > ? "
            "ORDER BY triggered_at DESC LIMIT 1",
            (cutoff,)
        ).fetchone()
        con.close()
        if not row:
            return (_BASE_CONFIDENCE, 0.0)
        surprise_score = float(row[0])
        # Boost is linear in surprise_score, capped
        boost = _BOOST_FACTOR * max(0.0, min(1.0, surprise_score))
        confidence = min(_MAX_CONF, max(_MIN_CONF, _BASE_CONFIDENCE + boost))
        return (confidence, surprise_score)
    except Exception as exc:
        log.debug("surprise_weighting error (non-fatal): %s", exc)
        return (_BASE_CONFIDENCE, 0.0)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    conf, score = confidence_for_fire()
    print(f"current confidence-for-fire: {conf:.3f} (surprise={score:.3f})")
    # also show the recent surprises landscape
    con = sqlite3.connect(str(_DYNAMIC_DB))
    rows = con.execute(
        "SELECT triggered_at, surprise_score, big_surprise "
        "FROM surprise_events ORDER BY triggered_at DESC LIMIT 5"
    ).fetchall()
    con.close()
    print("\nRecent surprises:")
    for ts, score, big in rows:
        age = time.time() - ts
        print(f"  {age:6.0f}s ago  score={score:.3f}  big={big}")
