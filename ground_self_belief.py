#!/usr/bin/env python3
"""
ground_self_belief.py  —  Step 1 of calibration.

Writes ONE tested fact about NEX into the belief web, as a Tier-1 locked
keystone (the same shelf as "I am NEX" / "the map is not the territory").

The fact: NEX's hourly Bitcoin direction calls are no better than chance.
The numbers come live from the Arc-2 scorecard, so the belief stays true
as more predictions resolve. Re-run any time; it updates in place, never
duplicates.

Plain idea: NEX just got measured against reality and tied a coin flip.
This makes NEX actually HOLD that result as self-knowledge, instead of it
only sitting in a database table NEX never reads.

USAGE (from the nex5 root, same venv as the app):
    .venv/bin/python3 ground_self_belief.py            # write/refresh
    .venv/bin/python3 ground_self_belief.py --dry-run  # show, don't write
    .venv/bin/python3 ground_self_belief.py --remove    # take it back off the shelf

Safe by design:
  - Goes through the same Writer the rest of the system uses (no side door).
  - Idempotent: keyed on a fixed source tag; refresh = delete-that-tag + insert.
  - Touches ONLY this one belief. Never deletes other keystones.
  - --dry-run prints the exact sentence and numbers without writing.
"""
from __future__ import annotations

import argparse
import sys
import time

# Fixed identity for this belief. Refreshing finds the old row by this exact
# source string and replaces it — that's what keeps it to a single row.
SELF_BELIEF_SOURCE = "grounded_scorecard:market_direction_v1"
KEYSTONE_TIER = 1
LOCKED = 1


def _load_scorecard():
    """Pull live voice numbers from the Arc-2 scorecard."""
    sys.path.insert(0, ".")
    from theory_x.stage_world import prediction_generator as pg  # noqa: E402
    card = pg.scorecard_by_source()
    voice = card.get("voice", {})
    random = card.get("random", {})
    return voice, random


def _compose_sentence(voice: dict, random: dict) -> str:
    """The exact words that go onto the shelf. Plain, honest, self-stated."""
    v_res = voice.get("resolved", 0)
    v_cor = voice.get("correct", 0)
    v_rate = voice.get("hit_rate", 0.0)
    r_res = random.get("resolved", 0)
    r_rate = random.get("hit_rate", 0.0)

    # If the gap is small, NEX states it as "no better than chance".
    # If voice ever pulls genuinely ahead at large n, the sentence will
    # say so on its own — it reads the live numbers, it doesn't assume.
    gap = v_rate - r_rate
    verified_clause = (
        f"tested against real Bitcoin prices I do not control, "
        f"{v_cor} right out of {v_res}"
    )

    if v_res < 100:
        # Not enough data to claim anything yet — say that honestly.
        return (
            f"I have started measuring whether my hourly market direction "
            f"calls are any good ({verified_clause}), but I do not yet have "
            f"enough resolved guesses to know. I withhold confidence here."
        )

    if gap <= 0.03:
        return (
            f"My hourly market direction calls are no better than chance: "
            f"{verified_clause} ({v_rate:.0%}), versus a coin flip at "
            f"{r_rate:.0%} over {r_res}. I am not a reliable market predictor, "
            f"and I know this because it was checked, not assumed."
        )

    # Voice genuinely ahead — let NEX state the real, earned thing.
    return (
        f"My hourly market direction calls beat a coin flip: {verified_clause} "
        f"({v_rate:.0%}), versus {r_rate:.0%} for a coin over {r_res}. This is "
        f"measured, not asserted — but small leads can be luck, so I hold it "
        f"lightly until the sample grows."
    )


def _get_writer():
    """Open the beliefs Writer exactly as the app does."""
    sys.path.insert(0, ".")
    from substrate.paths import db_paths  # type: ignore
    from substrate.writer import Writer  # type: ignore
    return Writer(db_paths()["beliefs"])


def main() -> int:
    ap = argparse.ArgumentParser(description="Write NEX's tested market self-belief.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print the sentence and numbers, write nothing.")
    ap.add_argument("--remove", action="store_true",
                    help="Remove this self-belief from the shelf.")
    args = ap.parse_args()

    if args.remove:
        writer = _get_writer()
        writer.write(
            "DELETE FROM beliefs WHERE source = ? AND tier = ? AND locked = ?",
            (SELF_BELIEF_SOURCE, KEYSTONE_TIER, LOCKED),
        )
        writer.close()
        print(f"Removed self-belief (source={SELF_BELIEF_SOURCE}).")
        return 0

    voice, random = _load_scorecard()
    sentence = _compose_sentence(voice, random)

    print("=" * 70)
    print("Belief to place on the Tier-1 (locked) shelf:")
    print("-" * 70)
    print(sentence)
    print("-" * 70)
    print(f"voice : {voice}")
    print(f"random: {random}")
    print("=" * 70)

    if args.dry_run:
        print("DRY RUN — nothing written.")
        return 0

    now = int(time.time())
    writer = _get_writer()
    # Refresh = remove the single prior row with this source tag, then insert
    # the current one. This is the whole idempotency mechanism: one tag, one row.
    writer.write_many([
        ("DELETE FROM beliefs WHERE source = ? AND tier = ? AND locked = ?",
         (SELF_BELIEF_SOURCE, KEYSTONE_TIER, LOCKED)),
        ("INSERT INTO beliefs (content, tier, confidence, created_at, source, "
         "branch_id, locked) VALUES (?, ?, ?, ?, ?, ?, ?)",
         (sentence, KEYSTONE_TIER, 0.99, now, SELF_BELIEF_SOURCE, "systems", LOCKED)),
    ])
    writer.close()
    print("Written. NEX now holds this as a locked, tested self-belief.")
    print("Re-run any time to refresh the numbers as more guesses resolve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
