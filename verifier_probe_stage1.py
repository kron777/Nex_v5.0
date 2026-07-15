#!/usr/bin/env python3
"""Stage 1 verifier probe — source recovery.

Read-only. Makes NO changes to any DB or pipeline. Tests the one risky
assumption the verifier depends on: given a belief, can we recover the URL of
the sense_event it most likely came from, by content overlap?

For each sampled belief it finds the best-matching recent sense_event
(token-overlap), recovers that event's provenance (URL), and prints the match
quality so we can judge whether backward source-recovery is good enough to
build a real verifier on top of.

Run:
  cd /home/rr/Desktop/Desktop/nex5
  .venv/bin/python3 verifier_probe_stage1.py

Reads data/beliefs.db (beliefs) and data/sense.db (sense_events). Adjust paths
below if different.
"""

import json
import re
import sqlite3
import sys

BELIEFS_DB = "data/beliefs.db"
SENSE_DB = "data/sense.db"
SAMPLE = 30            # how many recent beliefs to probe
SENSE_WINDOW = 4000    # how many recent sense_events to match against
MIN_OVERLAP = 2        # tokens shared to count as a candidate match

_STOPWORDS = {
    "the", "and", "for", "are", "but", "not", "you", "all", "any", "can",
    "had", "her", "was", "one", "our", "out", "his", "has", "him", "how",
    "its", "who", "did", "yes", "she", "this", "that", "with", "from",
    "they", "have", "what", "your", "will", "would", "their", "about",
}


def _tokenize(text):
    tokens = re.findall(r"[a-zA-Z]{3,}", (text or "").lower())
    return {t for t in tokens if t not in _STOPWORDS}


def _looks_factual(content):
    """Heuristic: skip introspective/philosophical beliefs that have no external
    source to verify against. Keep beliefs that read like external claims."""
    c = (content or "").lower()
    introspective_markers = (
        "i notice", "i am the attending", "my existence", "i feel",
        "the quiet", "i hold", "i see now", "my belief", "the tension",
        "the realization", "i find", "given my", "the duality", "i expect",
    )
    if any(m in c for m in introspective_markers):
        return False
    # too short to carry a checkable claim
    return len(c) >= 20


def main():
    try:
        bcx = sqlite3.connect(BELIEFS_DB)
        bcx.row_factory = sqlite3.Row
    except Exception as e:
        print(f"cannot open {BELIEFS_DB}: {e}")
        sys.exit(1)
    try:
        scx = sqlite3.connect(SENSE_DB)
        scx.row_factory = sqlite3.Row
    except Exception as e:
        print(f"cannot open {SENSE_DB}: {e}")
        sys.exit(1)

    # Load recent sense_events once, pre-tokenized.
    sense_rows = scx.execute(
        "SELECT id, stream, payload, provenance, timestamp "
        "FROM sense_events ORDER BY id DESC LIMIT ?",
        (SENSE_WINDOW,),
    ).fetchall()
    sense = []
    for r in sense_rows:
        # payload may be JSON or raw text; pull a text blob to tokenize
        blob = r["payload"] or ""
        toks = _tokenize(blob)
        if toks:
            sense.append((r["id"], r["stream"], r["provenance"], blob, toks))
    print(f"loaded {len(sense)} recent sense_events with tokens "
          f"(of {len(sense_rows)} fetched)\n")

    # Sample recent factual-looking beliefs.
    belief_rows = bcx.execute(
        "SELECT id, content, tier, source FROM beliefs "
        "ORDER BY id DESC LIMIT ?",
        (SAMPLE * 6,),
    ).fetchall()

    probed = 0
    recovered = 0
    strong = 0
    for b in belief_rows:
        if probed >= SAMPLE:
            break
        if not _looks_factual(b["content"]):
            continue
        probed += 1
        btoks = _tokenize(b["content"])
        if not btoks:
            print(f"[belief {b['id']}] no tokens; skipped")
            continue

        best = None
        best_overlap = 0
        for sid, stream, prov, blob, stoks in sense:
            ov = len(btoks & stoks)
            if ov > best_overlap:
                best_overlap = ov
                best = (sid, stream, prov, blob)

        frac = best_overlap / max(1, len(btoks))
        print(f"[belief {b['id']}] tier={b['tier']} src='{b['source']}'")
        print(f"  claim: {b['content'][:90]}")
        if best and best_overlap >= MIN_OVERLAP:
            recovered += 1
            tag = ""
            if frac >= 0.5:
                strong += 1
                tag = "  <== STRONG"
            print(f"  best sense_event: id={best[0]} stream={best[1]} "
                  f"overlap={best_overlap} ({frac:.0%}){tag}")
            print(f"  url: {best[2]}")
            print(f"  source_text: {(best[3] or '')[:90]}")
        else:
            print(f"  NO usable source match (best overlap={best_overlap})")
        print()

    print("=" * 60)
    print(f"probed {probed} factual-looking beliefs")
    print(f"  recovered a source URL for: {recovered} "
          f"({recovered/max(1,probed):.0%})")
    print(f"  STRONG matches (>=50% token overlap): {strong} "
          f"({strong/max(1,probed):.0%})")
    print()
    print("READ THIS: if 'recovered' is high and STRONG matches look like the")
    print("actual article a belief came from, backward source-recovery works ->")
    print("a real verifier is buildable. If matches are garbage/mismatched, the")
    print("transform from headline->belief is too lossy and we need a different")
    print("approach (thread URL forward at ingestion). Either way we learn it now.")


if __name__ == "__main__":
    main()
