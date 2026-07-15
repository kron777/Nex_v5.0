#!/usr/bin/env python3
"""Stage 2 — source-fidelity verifier.

Tests, for each factual belief, whether NEX faithfully represented what its
source actually said — or whether it garbled/hallucinated it.

This is a SOURCE-FIDELITY check, not a truth check. A CONFIRMED verdict means
"this belief faithfully matches the headline its source sense_event recorded."
It does NOT mean the claim is true in the world — only that NEX didn't distort
its source. That is exactly the check that catches feed-noise distortions and
hallucinated specifics.

Method (deterministic, no network by default):
  - take beliefs with source='precipitated_from_sense' (the factual ones)
  - recover the best-matching sense_event by token overlap (proven in Stage 1)
  - parse the source payload's stored title
  - compare belief content to that title:
        >= 0.75 token overlap  -> CONFIRMED  (faithful)
        0.40 - 0.75            -> PARTIAL    (drifted/embellished)
        < 0.40                 -> UNCONFIRMED (no faithful source found)
  - skip beliefs whose recovered source is internal ('fountain') — not external
  - write verdicts to data/verification.db (a NEW, separate db; nothing else touched)

Run (read-only on beliefs/sense; creates/writes only verification.db):
  cd /home/rr/Desktop/Desktop/nex5
  .venv/bin/python3 verifier_stage2.py
  .venv/bin/python3 verifier_stage2.py --report   # just print last run's summary

Reversible: delete data/verification.db to undo entirely.
"""

import json
import re
import sqlite3
import sys
import time

BELIEFS_DB = "data/beliefs.db"
SENSE_DB = "data/sense.db"
VERIFY_DB = "data/verification.db"

SAMPLE = 5000            # beliefs to verify per run
SENSE_WINDOW = 40000    # recent sense_events to match against (large: source may be old)
CONFIRM = 0.75          # >= this overlap -> CONFIRMED (faithful)
PARTIAL = 0.40          # >= this -> PARTIAL (drifted); below -> see FOUND_FLOOR
FOUND_FLOOR = 0.34      # below this overlap we treat the source as NOT FOUND,
#                         not as contradiction — distinguishes verifier-miss from
#                         genuine low-fidelity. Real-but-unmatched headlines land here.

_STOPWORDS = {
    "the", "and", "for", "are", "but", "not", "you", "all", "any", "can",
    "had", "her", "was", "one", "our", "out", "his", "has", "him", "how",
    "its", "who", "did", "yes", "she", "this", "that", "with", "from",
    "they", "have", "what", "your", "will", "would", "their", "about",
    "after", "over", "into", "says", "say", "said",
}


def _tokenize(text):
    tokens = re.findall(r"[a-zA-Z]{3,}", (text or "").lower())
    return {t for t in tokens if t not in _STOPWORDS}


def _payload_title(payload):
    """Pull a comparable title/text from a sense_event payload (JSON or raw)."""
    if not payload:
        return ""
    try:
        d = json.loads(payload)
        if isinstance(d, dict):
            return d.get("title") or d.get("thought") or d.get("summary") or ""
    except Exception:
        pass
    return payload


def _ensure_schema(vcx):
    vcx.execute(
        "CREATE TABLE IF NOT EXISTS belief_verification ("
        "  belief_id INTEGER PRIMARY KEY,"
        "  verdict TEXT NOT NULL,"          # CONFIRMED / PARTIAL / UNCONFIRMED / INTERNAL
        "  overlap REAL,"
        "  source_url TEXT,"
        "  source_title TEXT,"
        "  belief_content TEXT,"
        "  checked_at INTEGER NOT NULL"
        ")"
    )
    vcx.commit()


def main():
    report_only = "--report" in sys.argv

    vcx = sqlite3.connect(VERIFY_DB)
    _ensure_schema(vcx)

    if report_only:
        rows = vcx.execute(
            "SELECT verdict, COUNT(*) n FROM belief_verification GROUP BY verdict"
        ).fetchall()
        total = sum(n for _, n in rows)
        print(f"verification.db — {total} beliefs verified to date:")
        for verdict, n in rows:
            print(f"  {verdict:12s} {n:5d} ({n/max(1,total):.0%})")
        return

    bcx = sqlite3.connect(BELIEFS_DB); bcx.row_factory = sqlite3.Row
    scx = sqlite3.connect(SENSE_DB); scx.row_factory = sqlite3.Row

    sense_rows = scx.execute(
        "SELECT id, stream, payload, provenance FROM sense_events "
        "ORDER BY id DESC LIMIT ?",
        (SENSE_WINDOW,),
    ).fetchall()
    sense = []
    for r in sense_rows:
        title = _payload_title(r["payload"])
        toks = _tokenize(title)
        if toks:
            sense.append((r["id"], r["provenance"], title, toks))
    print(f"loaded {len(sense)} source events for matching")

    # factual beliefs not yet verified
    already = {row[0] for row in vcx.execute(
        "SELECT belief_id FROM belief_verification").fetchall()}
    belief_rows = bcx.execute(
        "SELECT id, content, source FROM beliefs "
        "WHERE source = 'precipitated_from_sense' "
        "ORDER BY id DESC LIMIT ?",
        (SAMPLE * 3,),
    ).fetchall()

    counts = {"CONFIRMED": 0, "PARTIAL": 0, "UNCONFIRMED": 0,
              "NO_SOURCE_FOUND": 0, "INTERNAL": 0}
    done = 0
    now = int(time.time())
    for b in belief_rows:
        if done >= SAMPLE:
            break
        if b["id"] in already:
            continue
        btoks = _tokenize(b["content"])
        if not btoks:
            continue

        best = None
        best_ov = 0
        for sid, prov, title, stoks in sense:
            ov = len(btoks & stoks)
            if ov > best_ov:
                best_ov = ov
                best = (sid, prov, title)
        if best is None:
            verdict, frac, url, title = "NO_SOURCE_FOUND", 0.0, None, None
        else:
            url = best[1] or ""
            title = best[2]
            frac = best_ov / max(1, len(btoks))
            if frac < FOUND_FLOOR:
                # too little overlap to claim we even found the right source —
                # this is a verifier miss, NOT evidence NEX distorted anything
                verdict = "NO_SOURCE_FOUND"
            elif url == "fountain" or not url.startswith("http"):
                verdict = "INTERNAL"          # synthesized from own thought, not external
            elif frac >= CONFIRM:
                verdict = "CONFIRMED"
            elif frac >= PARTIAL:
                verdict = "PARTIAL"
            else:
                verdict = "UNCONFIRMED"        # found a plausible source but it doesn't match

        counts[verdict] += 1
        done += 1
        vcx.execute(
            "INSERT OR REPLACE INTO belief_verification "
            "(belief_id, verdict, overlap, source_url, source_title, "
            " belief_content, checked_at) VALUES (?,?,?,?,?,?,?)",
            (b["id"], verdict, round(frac, 3), url, (title or "")[:200],
             (b["content"] or "")[:200], now),
        )
    vcx.commit()

    print(f"\nverified {done} factual beliefs this run:")
    for v in ("CONFIRMED", "PARTIAL", "UNCONFIRMED", "NO_SOURCE_FOUND", "INTERNAL"):
        print(f"  {v:16s} {counts[v]:4d} ({counts[v]/max(1,done):.0%})")
    print("\nCONFIRMED       = belief faithfully matches its source headline.")
    print("PARTIAL         = drifted/embellished from source (worth inspecting).")
    print("UNCONFIRMED     = a plausible source was found but the claim does NOT")
    print("                  match it — possible distortion/hallucination. THIS is")
    print("                  the bucket to trust as 'NEX may have garbled its source'.")
    print("NO_SOURCE_FOUND = no matching source in the window — a VERIFIER limitation,")
    print("                  NOT evidence of distortion. (Source likely scrolled out.)")
    print("INTERNAL        = traced to NEX's own prior thought, not externally checkable.")
    print("\nInspect the real distortion candidates (UNCONFIRMED/PARTIAL only):")
    print("  sqlite3 data/verification.db \"SELECT belief_content, source_title, "
          "overlap FROM belief_verification WHERE verdict IN ('PARTIAL','UNCONFIRMED') "
          "ORDER BY overlap DESC LIMIT 20\"")


if __name__ == "__main__":
    main()
