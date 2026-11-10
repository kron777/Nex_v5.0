#!/usr/bin/env python3
"""nex5_rate.py — Jon's passive, unsolicited rating command.

SHADOW ENTRYPOINT — NOT IN THE LIVE PATH. Flag: NEX5_APATRAPYA_CHANNEL,
default OFF (this script writes regardless of the flag; the flag gates
whether anything downstream reads the result -- see theory_x/stage_tom/
apatrapya_channel.py and hri_apatrapya_prototype.py for why the flag lives
there, not here).

Usage:
    python nex5_rate.py rate <output-id> approve|disapprove|abstain [--reason "..."]
    python nex5_rate.py rate <output-id> disapprove --reason "..." --supersedes <id>

<output-id> is a messages.id for a role='nex' row (conversations.db) --
see the HUD or query conversations.db directly to find one.

Deliberately boring: this script does nothing but call record_rating() and
print the resulting row id. No prompt, no menu, no "would you like to rate
something" -- it only runs when Jon runs it, on his own initiative.
"""
from __future__ import annotations

import argparse
import sys

from substrate import Reader, Writer, db_paths
from theory_x.stage_tom.apatrapya_channel import RejectedRating, record_rating


def main() -> int:
    parser = argparse.ArgumentParser(prog="nex5_rate.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    rate = sub.add_parser("rate", help="Rate one of NEX's own outputs.")
    rate.add_argument("output_id", type=int)
    rate.add_argument("verdict", choices=("approve", "disapprove", "abstain"))
    rate.add_argument("--reason", default=None)
    rate.add_argument("--supersedes", type=int, default=None)

    args = parser.parse_args()

    paths = db_paths()
    reader = Reader(paths["conversations"])
    writer = Writer(paths["conversations"])
    try:
        row_id = record_rating(
            writer, reader, args.output_id, args.verdict,
            reason=args.reason, supersedes=args.supersedes,
        )
    except RejectedRating as e:
        print(f"REJECTED: {e}", file=sys.stderr)
        return 1
    finally:
        writer.close()

    print(f"recorded rating id={row_id} output_id={args.output_id} verdict={args.verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
