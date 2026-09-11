#!/usr/bin/env python3
"""measure_attrib.py — READ-ONLY soak metric for the attribution marker (2f5866e).

Tells whether the structural attribution marker actually bites on live syntheses
after the soak. Same discipline as measure_confab: measure, don't assert.

Over a recent window of source='synergized' beliefs it reports:
  - total synergized in the window
  - how many carry an `attribution:*` tag, and the rate  (THE did-it-take
    signal: old code never wrote this tag, so any > 0 means the fix fired)
  - old-code vs new-code split (by the first attribution stamp's timestamp)
  - REAL METRIC via synergizer_log lineage (child result_belief_id -> two
    parents): of syntheses whose PARENTS are contested/attributed, what
    fraction of children RETAINED a source (attribution tag, or "per [source]"
    / "per its source" in content) vs went bare — the erosion-retention rate
    the fix is meant to move.
  - a few example children showing the surfaced "per [source]".

Reuses attribution_marker's own detection helpers (imported, not re-hardcoded).

CAVEAT: "parent contested" is reconstructed from the parent's CURRENT state
(content may itself have been paraphrased/promoted since synthesis), so it is a
best-effort proxy for "contested at synthesis time".

READ-ONLY: mode=ro on every DB; writes nothing; safe to re-run.

Usage:  .venv/bin/python3 tools/measure_attrib.py [WINDOW_HOURS] [RESTART_EPOCH]
"""
from __future__ import annotations

import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from theory_x.stage3_world_model.attribution_marker import (
    contested_snippet, marker_in_tags, detect_attribution,
)

BELIEFS_DB = "/home/rr/Desktop/Desktop/nex5/data/beliefs.db"


def _ro(path):
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
    con.row_factory = sqlite3.Row
    return con


def _child_retained(content, tags):
    """Child kept a source if it carries the marker tag OR surfaces attribution
    text ("per Name" / the literal "per its source") in content."""
    if marker_in_tags(tags):
        return True
    c = content or ""
    if "(per " in c.lower():
        return True
    return detect_attribution(c) is not None


def _rate(n, d):
    return f"{(100.0 * n / d):.1f}%" if d else "n/a"


DYNAMIC_DB = "/home/rr/Desktop/Desktop/nex5/data/dynamic.db"


def measure_crystallization(cutoff):
    """The real volume path (fix #1A): fountain_insight beliefs from wide-mode
    fires that engaged a sourced focal_item. Reports did-it-take (attribution:*
    tag) and the retention rate among sourced crystallizations."""
    b = _ro(BELIEFS_DB)
    d = _ro(DYNAMIC_DB)
    links = b.execute(
        "SELECT fountain_event_id, belief_id FROM fountain_crystallizations "
        "WHERE ts > ? ORDER BY ts DESC",
        (cutoff,),
    ).fetchall()
    total = len(links)
    sourced = tagged = retained = 0
    examples = []
    for lk in links:
        fe = d.execute(
            "SELECT focal_item, mode FROM fountain_events WHERE id = ?",
            (lk["fountain_event_id"],),
        ).fetchone()
        if not fe or not fe["focal_item"]:
            continue  # DRIFT/substrate/contemplative — not a sourced fire
        sourced += 1
        bel = b.execute(
            "SELECT content, tags FROM beliefs WHERE id = ?", (lk["belief_id"],)
        ).fetchone()
        if not bel:
            continue
        content, tags = bel["content"], bel["tags"]
        has_marker = marker_in_tags(tags) is not None
        kept = has_marker or "(per " in (content or "").lower() \
            or detect_attribution(content) is not None
        if has_marker:
            tagged += 1
        if kept:
            retained += 1
            if len(examples) < 4 and "(per a feed item)" in (content or ""):
                examples.append(content[:96])
    b.close()
    d.close()
    return dict(total=total, sourced=sourced, tagged=tagged,
                retained=retained, bare=sourced - retained, examples=examples)


def main():
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 72.0
    restart_epoch = float(sys.argv[2]) if len(sys.argv) > 2 else None
    cutoff = time.time() - hours * 3600

    con = _ro(BELIEFS_DB)
    rows = con.execute(
        "SELECT id, content, tags, created_at FROM beliefs "
        "WHERE source='synergized' AND created_at > ? ORDER BY created_at DESC",
        (cutoff,),
    ).fetchall()

    total = len(rows)
    tagged = [r for r in rows if marker_in_tags(r["tags"])]
    n_tagged = len(tagged)

    # new-code boundary: explicit restart epoch, else earliest attribution stamp.
    if restart_epoch is None and tagged:
        restart_epoch = min(r["created_at"] for r in tagged)
    if restart_epoch is not None:
        new_rows = [r for r in rows if (r["created_at"] or 0) >= restart_epoch]
        old_rows = [r for r in rows if (r["created_at"] or 0) < restart_epoch]
    else:
        new_rows, old_rows = [], list(rows)

    # REAL METRIC: parents contested -> did the child retain a source?
    contested_syn = 0
    retained = 0
    parents_missing = 0
    examples = []
    for r in rows:
        lg = con.execute(
            "SELECT belief_id_a, belief_id_b FROM synergizer_log "
            "WHERE result_belief_id = ? ORDER BY ts DESC LIMIT 1",
            (r["id"],),
        ).fetchone()
        if not lg:
            continue
        parents = []
        for pid in (lg["belief_id_a"], lg["belief_id_b"]):
            p = con.execute(
                "SELECT content, tags FROM beliefs WHERE id = ?", (pid,)
            ).fetchone()
            if p:
                parents.append(dict(p))
        if not parents:
            parents_missing += 1
            continue
        if any(contested_snippet(p) for p in parents):
            contested_syn += 1
            if _child_retained(r["content"], r["tags"]):
                retained += 1
        # collect example children that surfaced attribution
        if len(examples) < 4 and "(per " in (r["content"] or "").lower():
            examples.append(r["content"][:96])
    con.close()

    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 74)
    print(f"ATTRIBUTION SOAK SNAPSHOT  {stamp}  window={hours:g}h")
    print("-" * 74)
    print(f"synergized in window        : {total}")
    print(f"carry attribution:* tag     : {n_tagged} ({_rate(n_tagged, total)})   "
          f"<- did-it-take (0 under old code)")
    if restart_epoch is not None:
        print(f"old-code / new-code split   : old={len(old_rows)}  new={len(new_rows)} "
              f"(boundary {time.strftime('%Y-%m-%d %H:%M', time.localtime(restart_epoch))})")
    else:
        print(f"old-code / new-code split   : all {total} pre-fix (no attribution stamps yet)")
    print("-" * 74)
    print("REAL METRIC (lineage via synergizer_log):")
    print(f"  syntheses w/ contested parent : {contested_syn}")
    print(f"  of those, child RETAINED src  : {retained} ({_rate(retained, contested_syn)})  "
          f"<- erosion-retention rate")
    print(f"  went BARE                     : {contested_syn - retained} "
          f"({_rate(contested_syn - retained, contested_syn)})")
    if parents_missing:
        print(f"  (parents no longer in store   : {parents_missing} — excluded)")
    if examples:
        print("  example children w/ surfaced source:")
        for e in examples:
            print(f"    - {e!r}")
    print("-" * 74)
    cr = measure_crystallization(cutoff)
    print("CRYSTALLIZATION PATH (fix #1A — the volume choke point):")
    print(f"  crystallizations in window    : {cr['total']}")
    print(f"  sourced (wide-mode focal_item): {cr['sourced']}")
    print(f"  carry attribution:* tag       : {cr['tagged']} ({_rate(cr['tagged'], cr['sourced'])})  "
          f"<- did-it-take (0 under old code / flag off)")
    print(f"  of sourced, RETAINED src      : {cr['retained']} ({_rate(cr['retained'], cr['sourced'])})")
    print(f"  went BARE                     : {cr['bare']} ({_rate(cr['bare'], cr['sourced'])})")
    if cr["examples"]:
        print("  example crystallized w/ '(per a feed item)':")
        for e in cr["examples"]:
            print(f"    - {e!r}")
    print("=" * 74)
    print("Note: synergizer 'contested parent' uses parents' CURRENT state "
          "(best-effort proxy for synthesis-time).")


if __name__ == "__main__":
    main()
