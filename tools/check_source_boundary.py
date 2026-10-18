#!/usr/bin/env python3
"""Self/world source-discrimination check (round 11, item 2) — READ-ONLY.

The marker of a self/world boundary is that NEX can tell "I generated this" from
"this arrived". Provenance scores by beliefs.source, so a boundary failure is a
belief whose CONTENT crossed the self/world line while its SOURCE did not.

Two directions, both measured on exact content:

  A. authored -> received  (Beam's primary concern): self-authored content that also
     exists under precipitated_from_sense. Would inflate the received band with
     self-talk and corrupt every downstream provenance number. EXPECT 0.

  B. received -> authored  (the inverse): external/world content (precipitated_from_
     sense) copied verbatim into an authored-tier source. Inflates the authored band
     with world headlines. EXPECT 0.

Direction is decided by which copy was created first. Usage:
    PYTHONPATH=. python tools/check_source_boundary.py [--db data/beliefs.db]
"""
from __future__ import annotations

import argparse
import sqlite3
from collections import Counter, defaultdict

# Mirrors the authored tier of affinity_loop.PROVENANCE_BASE.
AUTHORED = {"fountain_insight", "synergized", "counterfactual_node", "remember_loop",
            "wonder_loop", "hot_observer", "surprise", "fountain", "emergent_drive"}
WITNESSED = {"witness_loop", "pattern_loop", "identity_loop", "behavioural_observation",
             "precipitated_from_dynamic", "self_rut_notice", "self_downtime"}
RECEIVED_SENSE = "precipitated_from_sense"


def _band(source: str) -> str:
    return "authored" if source in AUTHORED else ("witnessed" if source in WITNESSED
                                                  else "received")


def class_detector(db: str):
    """Q7 class-detector: flag any SOURCE whose rows' content also appears under a
    DIFFERENT provenance band. The A/B check only sees authored<->received exact
    overlap; this catches the whole class -- a source tiered once by NAME but carrying
    mixed per-row provenance (the pattern behind 'I am nex'@0.973,
    precipitated_from_sense, counterfactual_node). Returns {source: cross_band_rows}."""
    cx = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    content_bands: dict[str, set] = defaultdict(set)
    pairs = []
    for content, source in cx.execute(
            "SELECT content, source FROM beliefs WHERE content IS NOT NULL"):
        content_bands[content].add(_band(source))
        pairs.append((content, source))
    hits: Counter = Counter()
    for content, source in pairs:
        if len(content_bands[content]) > 1:
            hits[source] += 1
    return dict(hits)


def run(db: str, max_b: int = 17) -> int:
    cx = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    by: dict[str, list] = defaultdict(list)
    for content, source, created in cx.execute(
        "SELECT content, source, created_at FROM beliefs WHERE content IS NOT NULL"
    ):
        if source in AUTHORED or source == RECEIVED_SENSE:
            by[content].append((source, created or 0))
    a_to_r = []   # authored first, then received  (self-talk -> received)
    r_to_a = Counter()  # received first, then authored (world -> authored), by src
    for content, rows in by.items():
        srcs = {s for s, _ in rows}
        if RECEIVED_SENSE not in srcs or not (srcs & AUTHORED):
            continue
        rec_t = min(t for s, t in rows if s == RECEIVED_SENSE)
        auth = [(s, t) for s, t in rows if s in AUTHORED]
        auth_t = min(t for _, t in auth)
        if auth_t < rec_t:
            a_to_r.append((content, sorted({s for s, _ in auth})))
        else:
            for s in {s for s, _ in auth}:
                r_to_a[s] += 1
    print(f"source-boundary check on {db}")
    print(f"  A. authored -> received (Beam's leak): {len(a_to_r)}   (expect 0)")
    for content, ss in a_to_r[:10]:
        print(f"       {ss} {content[:80]!r}")
    print(f"  B. received -> authored (inverse):     {sum(r_to_a.values())}   (expect 0)")
    for s, n in r_to_a.most_common():
        print(f"       {n:4d}  into {s}")
    # C. class detector (Q7): sources whose content spans >1 band -- the structural
    # signature of the whole class, not just the authored<->received exact overlaps.
    cd = class_detector(db)
    print(f"  C. cross-band sources (class detector): {len(cd)} sources, "
          f"{sum(cd.values())} rows")
    for s, n in sorted(cd.items(), key=lambda kv: -kv[1])[:10]:
        print(f"       {n:5d}  {s}  (band={_band(s)})")
    fail_a = len(a_to_r)
    b_total = sum(r_to_a.values())
    print()
    print("VERDICT A (self/world boundary):",
          "CLEAN" if fail_a == 0 else f"FAILURE x{fail_a}")
    # Ratchet gate (Q4): A=0 is the claim that must never regress silently; B is a
    # countdown that ratchets down as the source_kind class fix lands. Run this
    # wherever the live DB lives (scheduled check), not unit CI, which has no DB.
    fail = (fail_a > 0) or (b_total > max_b)
    if fail:
        print(f"RATCHET FAIL: A={fail_a} (must be 0), B={b_total} (must be <= {max_b})")
    return 1 if fail else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/beliefs.db")
    ap.add_argument("--max-b", type=int, default=17,
                    help="ratchet ceiling for Direction B (lower it as it is fixed)")
    args = ap.parse_args()
    raise SystemExit(run(args.db, max_b=args.max_b))
