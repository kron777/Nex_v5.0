#!/usr/bin/env python3
"""
calibration_consult.py  —  Step 2 of calibration.

Step 1 gave NEX a tested fact about itself ("my market calls are no better
than chance"), sitting locked on the Tier-1 shelf. But nothing READS it.

Step 2 makes NEX glance at that fact right before it makes a market call,
and decide how much to trust itself. The guess still happens (we need it
to keep measuring) — but now it is ANNOTATED by NEX's own honesty.

Plain idea: knowing you're bad at something only matters if you check that
knowledge before you act. This is the check.

WHERE IT PLUGS IN
-----------------
In theory_x/stage_world/prediction_generator.py, inside make_voice_prediction(),
right after the voice produces its up/down call and before/as you record the
row, add:

    from theory_x.stage_world.calibration_consult import consult_self_trust
    trust = consult_self_trust()          # reads belief #75631, decides
    # ... then stamp `trust["level"]` onto the recorded prediction however
    #     you like (a column, a sidecar row — see log_consult below).

It is a pure read + decide. It NEVER changes the guess. It cannot break the
loop (every failure path returns a safe default and logs nothing fatal).

WHAT IT RETURNS
---------------
{
  "level":   "none" | "provisional" | "earned" | "unknown",
  "reason":  short human sentence,
  "n":       resolved sample size behind the judgement,
  "phrase":  a ready-made caveat string the voice COULD speak (Step 2b/B,
             optional — not used unless you choose to surface it),
}

  none         -> record says no better than chance. Trust = 0. Say so.
  provisional  -> a lead exists but sample is small. Hold lightly.
  earned       -> a lead has survived a large sample. Trust it, modestly.
  unknown       -> no tested self-belief found yet (Step 1 not run / removed).
"""
from __future__ import annotations

import logging
import sys
import time

logger = logging.getLogger("nex5.calibration")

# Must match the source tag written by ground_self_belief.py (Step 1).
SELF_BELIEF_SOURCE = "grounded_scorecard:market_direction_v1"

# Sidecar table: one row per consult, so the calibration behaviour is itself
# inspectable later. Created on first use; harmless if it already exists.
_CONSULT_TABLE_SQL = (
    "CREATE TABLE IF NOT EXISTS calibration_consults ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, "
    "consulted_at INTEGER NOT NULL, "
    "domain TEXT NOT NULL, "
    "level TEXT NOT NULL, "
    "n INTEGER NOT NULL DEFAULT 0)"
)


def _beliefs_reader():
    sys.path.insert(0, ".")
    from substrate.paths import db_paths  # type: ignore
    from substrate.reader import Reader  # type: ignore
    return Reader(db_paths()["beliefs"])


def _live_numbers():
    """Pull the current scorecard so the trust level reflects reality now,
    not whatever was true when Step 1 last wrote the sentence."""
    sys.path.insert(0, ".")
    from theory_x.stage_world import prediction_generator as pg  # type: ignore
    card = pg.scorecard_by_source()
    voice = card.get("voice", {})
    random = card.get("random", {})
    return voice, random


def consult_self_trust(domain: str = "market_direction") -> dict:
    """Read NEX's tested self-belief and decide how much to trust the next
    market call. Pure + safe: any failure returns a conservative default."""
    default = {
        "level": "unknown",
        "reason": "No tested self-belief found; defaulting to caution.",
        "n": 0,
        "gap": None,
        "phrase": "I have not measured myself here yet, so I do not trust this.",
    }

    # 1) Is the Step-1 self-belief actually on the shelf?
    try:
        reader = _beliefs_reader()
        row = reader.read_one(
            "SELECT content FROM beliefs WHERE source = ? AND tier = 1 AND locked = 1",
            (SELF_BELIEF_SOURCE,),
        )
        if row is None:
            return default
    except Exception as e:  # never let the consult break the loop
        logger.warning("calibration consult: belief read failed (%s)", e)
        return default

    # 2) Read the live numbers so the verdict is current.
    try:
        voice, random = _live_numbers()
        n = int(voice.get("resolved", 0))
        v_rate = float(voice.get("hit_rate", 0.0))
        r_rate = float(random.get("hit_rate", 0.0))
    except Exception as e:
        logger.warning("calibration consult: scorecard read failed (%s)", e)
        # We DO have a self-belief, but can't get fresh numbers — stay cautious.
        return {
            "level": "none",
            "reason": "Self-belief present but live numbers unavailable; staying cautious.",
            "n": 0,
            "gap": None,
            "phrase": "I have tested myself here and was not reliable, so I hold this lightly.",
        }

    gap = v_rate - r_rate

    # 3) Decide. Thresholds are deliberately plain.
    if n < 100:
        level = "provisional"
        reason = f"Only {n} resolved guesses — not enough to know yet."
        phrase = "I am still measuring myself here, so I withhold confidence."
    elif gap <= 0.03:
        level = "none"
        # Same split as ground_self_belief.py's _compose_sentence (c07ff0b):
        # a deficit large enough and sampled enough to say plainly gets said
        # plainly. Small-n swings stay in the conservative "no real edge"
        # phrasing rather than overclaiming a direction off noise. level
        # stays "none" either way -- only the strings get finer-grained.
        if gap < -0.02 and n >= 300:
            reason = (
                f"Tested at n={n}: {v_rate:.0%} vs a coin's {r_rate:.0%}. "
                f"A coin beats me by {abs(gap):.1%}."
            )
            phrase = (
                "I have tested this against real prices and a coin beats "
                "me at it, so do not lean on my call."
            )
        else:
            reason = (
                f"Tested at n={n}: {v_rate:.0%} vs a coin's {r_rate:.0%}. "
                f"No real edge."
            )
            phrase = (
                "I have tested this against real prices and I am no better "
                "than a coin, so do not lean on my call."
            )
    elif n < 300:
        level = "provisional"
        reason = (
            f"A lead exists ({v_rate:.0%} vs {r_rate:.0%}) but n={n} is small; "
            f"could be luck."
        )
        phrase = "I may have a slight edge here, but the sample is small — hold it lightly."
    else:
        level = "earned"
        reason = (
            f"A lead has survived n={n}: {v_rate:.0%} vs {r_rate:.0%}. "
            f"Modest, measured trust."
        )
        phrase = "I have a measured edge here that survived a large sample — trust it modestly."

    verdict = {"level": level, "reason": reason, "n": n, "gap": gap, "phrase": phrase}

    # 4) Record the consult (best-effort; failure here must not break anything).
    log_consult(domain, verdict)
    return verdict


def log_consult(domain: str, verdict: dict) -> None:
    """Write one row recording that NEX consulted its record. Best-effort."""
    try:
        sys.path.insert(0, ".")
        from substrate.paths import db_paths  # type: ignore
        from substrate.writer import Writer  # type: ignore
        w = Writer(db_paths()["conversations"])
        w.write_many([
            (_CONSULT_TABLE_SQL, ()),
            ("INSERT INTO calibration_consults (consulted_at, domain, level, n) "
             "VALUES (?, ?, ?, ?)",
             (int(time.time()), domain, verdict["level"], verdict["n"])),
        ])
        w.close()
    except Exception as e:
        logger.warning("calibration consult: log write failed (%s)", e)


# Manual smoke test: `python3 -m theory_x.stage_world.calibration_consult`
if __name__ == "__main__":
    import json
    print(json.dumps(consult_self_trust(), indent=2))
