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
RECEIVED_SENSE = "precipitated_from_sense"


def run(db: str) -> int:
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
    fail_a = len(a_to_r)
    print()
    print("VERDICT A (self/world boundary):",
          "CLEAN" if fail_a == 0 else f"FAILURE x{fail_a}")
    return 0 if fail_a == 0 else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/beliefs.db")
    raise SystemExit(run(ap.parse_args().db))
