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

READ-ONLY by default. Since build D every new belief and sense event is stamped at
insert (substrate/source_kind.py); --backfill --apply stamps rows from before that.

USAGE (from nex5 root):
    .venv/bin/python3 theory_x/stage_tom/source_identity.py --map      # show the stream->kind map
    .venv/bin/python3 theory_x/stage_tom/source_identity.py --census   # count NEX's world by kind
    .venv/bin/python3 theory_x/stage_tom/source_identity.py --backfill [--apply]
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter

from substrate import connect
# The stream -> kind rules moved to the write boundary (substrate/source_kind.py),
# where every belief and sense event is now stamped at insert; re-exported here.
from substrate.source_kind import classify_stream, kind_for  # noqa: F401


def _db(name: str) -> str:
    try:
        from substrate.paths import db_paths  # type: ignore
        return str(db_paths()[name])
    except Exception:
        return f"data/{name}.db"


def stream_map() -> dict:
    conn = connect(_db("sense"))
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


def backfill(apply: bool = False, beliefs_db=None, sense_db=None) -> dict:
    """Stamp source_stream/source_kind on rows written before the triggers.

    1. A precipitated_from_sense row's stream is recovered by re-deriving each
       sense event's title exactly as the distiller did: (title, timestamp)
       first, title alone second. What matches nothing stays stream-less.
    2. A row with no stream whose content is a verbatim copy of a row that has
       one inherits it (the trigger's rule, applied to the past).
    3. Every row still missing a kind gets kind_for(source, stream).
    Explicit kinds are never overwritten. Dry run unless apply=True. Needs the
    columns, so init_db must have run on this store first.
    """
    from theory_x.stage1_sense.title_extract import extract_sense_title
    bdb = connect(beliefs_db or _db("beliefs"), timeout=30)
    try:
        cols = {r[1] for r in bdb.execute("PRAGMA table_info(beliefs)")}
        if not {"source_kind", "source_stream"} <= cols:
            raise RuntimeError("beliefs has no source_kind/source_stream: run init_db first")
        rows = bdb.execute(
            "SELECT id, content, source, created_at, source_stream, source_kind "
            "FROM beliefs ORDER BY id").fetchall()
        stats: Counter = Counter(rows=len(rows))
        stream = {r[0]: r[4] for r in rows}

        lost = {r[0]: (r[1], int(r[3] or 0)) for r in rows
                if r[2] == "precipitated_from_sense" and not r[4]}
        stats["sense_rows_missing_stream"] = len(lost)
        if lost:
            want = {c for c, _ in lost.values()}
            by_exact, by_title = {}, {}
            sdb = connect(sense_db or _db("sense"), timeout=30)
            try:
                for st, payload, ts in sdb.execute(
                        "SELECT stream, payload, timestamp FROM sense_events "
                        "WHERE stream NOT LIKE 'internal.%' ORDER BY id"):
                    title = extract_sense_title(st, (payload or "").strip(), max_items=1)
                    if title in want:
                        by_exact.setdefault((title, int(ts or 0)), st)
                        by_title.setdefault(title, st)
            finally:
                sdb.close()
            for bid, key in lost.items():
                if key in by_exact:
                    stream[bid] = by_exact[key]
                    stats["recovered_exact"] += 1
                elif key[0] in by_title:
                    stream[bid] = by_title[key[0]]
                    stats["recovered_title"] += 1
                else:
                    stats["unrecoverable"] += 1

        first_stream: dict = {}
        for bid, content, *_ in rows:
            if stream[bid] and content not in first_stream:
                first_stream[content] = stream[bid]
        updates = []
        kinds: Counter = Counter()
        for bid, content, source, _created, old_stream, old_kind in rows:
            st = stream[bid]
            if not st and content in first_stream:
                st = first_stream[content]
                stats["inherited"] += 1
            kind = old_kind or kind_for(source, st)
            kinds[kind] += 1
            if st != old_stream or kind != old_kind:
                updates.append((st, kind, bid))
        stats["updated"] = len(updates)
        if apply and updates:
            bdb.executemany(
                "UPDATE beliefs SET source_stream = ?, source_kind = ? WHERE id = ?",
                updates)
            bdb.commit()
        out = dict(stats)
        out["by_kind"] = dict(kinds)
        out["applied"] = bool(apply)
        return out
    finally:
        bdb.close()


if __name__ == "__main__":
    sys.path.insert(0, ".")
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", action="store_true", help="show stream->kind map")
    ap.add_argument("--census", action="store_true", help="NEX's world by kind")
    ap.add_argument("--backfill", action="store_true",
                    help="stamp source_stream/source_kind on pre-trigger rows (dry run)")
    ap.add_argument("--apply", action="store_true", help="with --backfill: write")
    args = ap.parse_args()
    if args.map:
        show_map()
    elif args.census:
        census()
    elif args.backfill:
        print(backfill(apply=args.apply))
    else:
        ap.print_help()
