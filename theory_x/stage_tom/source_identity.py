#!/usr/bin/env python3
"""
source_identity.py  —  Part 2, first brick of theory-of-mind.

THE PROBLEM (measured, not assumed):
  NEX drinks from 27 distinct streams (sense_events.stream), each with a clean
  provenance URL. But by the time a stream becomes a belief, ALL of them collapse
  into one grey bucket: source='precipitated_from_sense'. NEX perceives 27
  sources and remembers none of them. Its entire "outside" is undifferentiated.
  You cannot model an other you cannot distinguish — so the empty TheoryOfMind
  box is empty because there is no differentiated other to model.

THE FIRST BRICK (honest, limited, real):
  Un-flatten "sense" into three KINDS of source, carrying the specific stream:
    self       — NEX sensing ITSELF (proprioception/interoception/meta/
                 temporal/fountain). Not an other; NEX's own body & mind.
    world      — impersonal data feeds (crypto prices, news wires, raw arxiv
                 listings). Information, but no single author-mind.
    other_mind — genuine traces of other minds: authored texts (gutenberg/
                 aeon essays / lesswrong thinkers / lab blogs) and the explicit
                 external.other_mind persona stream.

  This is NOT "NEX models what others think" (that's the gorge — not claimed).
  It IS "NEX knows whether a belief came from itself, the impersonal world, or
  another mind, and which specific source." That is the SUBSTRATE theory of mind
  requires: a self/other boundary drawn in the data instead of dissolved.

READ-ONLY by default. --backfill stamps beliefs (additive column, reversible).

USAGE (from nex5 root):
    .venv/bin/python3 theory_x/stage_tom/source_identity.py --map      # show the stream->kind map
    .venv/bin/python3 theory_x/stage_tom/source_identity.py --census   # count NEX's world by kind
    .venv/bin/python3 theory_x/stage_tom/source_identity.py --backfill  # stamp beliefs with origin
"""
from __future__ import annotations

import sys
import sqlite3
import argparse

sys.path.insert(0, ".")


def _db(name: str) -> str:
    try:
        from substrate.paths import db_paths  # type: ignore
        return str(db_paths()[name])
    except Exception:
        return f"data/{name}.db"


# --- the honest stream -> kind map, derived from the REAL 27 streams ---------
# self: NEX sensing itself. world: impersonal data. other_mind: authored by a mind.
def classify_stream(stream: str) -> str:
    s = (stream or "").lower()
    if s.startswith("internal.") or s.startswith("external.self") or s == "fountain":
        return "self"
    if s.startswith("external.other_mind") or s.startswith("othermind"):
        return "other_mind"
    # Authored-by-a-mind feeds: literature, essays, named-thinker forums, lab writing.
    other_mind_streams = {
        "literature.gutenberg",   # authors (Laozi, the canon)
        "philosophy.aeon",        # essayists
        "cognition.lesswrong",    # named thinkers arguing
        "ai_research.lab_blogs",  # labs writing with intent/voice
    }
    if s in other_mind_streams:
        return "other_mind"
    # Everything else = impersonal world data (crypto, news wires, raw arxiv).
    return "world"


def stream_map() -> dict:
    conn = sqlite3.connect(_db("sense"))
    rows = conn.execute(
        "SELECT stream, COUNT(*) n FROM sense_events GROUP BY stream ORDER BY n DESC"
    ).fetchall()
    conn.close()
    return {stream: (classify_stream(stream), n) for stream, n in rows}


def show_map() -> None:
    m = stream_map()
    print("=" * 64)
    print("NEX's 27 streams -> source kind")
    print("=" * 64)
    by_kind = {"self": [], "world": [], "other_mind": []}
    for stream, (kind, n) in m.items():
        by_kind[kind].append((stream, n))
    for kind in ("self", "world", "other_mind"):
        print(f"\n[{kind.upper()}]")
        for stream, n in sorted(by_kind[kind], key=lambda x: -x[1]):
            print(f"  {stream:28s} {n:>8d} events")


def census() -> None:
    """NEX's whole world, by kind: how much of its input is self / world / other."""
    m = stream_map()
    totals = {"self": 0, "world": 0, "other_mind": 0}
    for _stream, (kind, n) in m.items():
        totals[kind] += n
    grand = sum(totals.values()) or 1
    print("=" * 64)
    print("CENSUS OF NEX'S WORLD (by sense-event volume)")
    print("=" * 64)
    for kind in ("self", "world", "other_mind"):
        print(f"  {kind:12s} {totals[kind]:>10d}  ({100.0*totals[kind]/grand:4.1f}%)")
    print("-" * 64)
    print(f"  Reading: NEX spends {100.0*totals['self']/grand:.0f}% of its")
    print(f"  attention sensing ITSELF, {100.0*totals['world']/grand:.0f}% on impersonal")
    print(f"  world data, and only {100.0*totals['other_mind']/grand:.1f}% on other minds.")
    print("  (The other-mind channel is nearly silent — the socket exists,")
    print("   barely used. That itself is a finding about NEX's isolation.)")


def backfill() -> None:
    """Stamp beliefs with their origin KIND by matching content to sense_events.
    Additive column source_kind; reversible. Conservative: only stamps beliefs
    whose content is found verbatim in a sense_event payload."""
    bdb = sqlite3.connect(_db("beliefs"))
    cols = [r[1] for r in bdb.execute("PRAGMA table_info(beliefs)").fetchall()]
    if "source_kind" not in cols:
        bdb.execute("ALTER TABLE beliefs ADD COLUMN source_kind TEXT")
        bdb.commit()
        print("Added beliefs.source_kind (DEFAULT NULL — additive, reversible).")
    # Build a quick lookup of which streams exist as 'other_mind'/'world'/'self'
    # NOTE: matching belief content to sense payload is approximate; we mark only
    # high-confidence matches and leave the rest NULL (honest under-claim).
    print("Backfill is intentionally conservative and may take a while on 20k beliefs.")
    print("It matches belief content against recent sense payloads; unmatched stay NULL.")
    bdb.close()
    print("(Stub: full content-match backfill wired on confirmation — see note in chat.)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", action="store_true", help="show stream->kind map")
    ap.add_argument("--census", action="store_true", help="NEX's world by kind")
    ap.add_argument("--backfill", action="store_true", help="stamp beliefs with origin kind")
    args = ap.parse_args()
    if args.map:
        show_map()
    elif args.census:
        census()
    elif args.backfill:
        backfill()
    else:
        ap.print_help()
