#!/usr/bin/env python3
"""Problem-feedback loop persistence measurement — session 40 build.

Ships alongside the injection faculty (theory_x/stage7_sustained/
problem_memory.py:select_for_injection, generator.py's input-gap block),
not after it. Read-only.

Answers the question the faculty exists to answer: does she reference her
OWN posed problems across fires WITHOUT the feed independently re-raising
the topic? "Referenced" means an observation tagged source="problem_injection"
(written only by the new write-back path in generator.py:generate() -- see
that file's session-40 comments) -- not the raw observation count, which
session 39 showed is inflated by focus_loop's undebounced duplicate writes
and the RECONCILE mechanism's generic two-problem boilerplate. This script
only ever looks at the tagged subset.

Pre-registered (session 40 Phase 1, approved):
  BEFORE:  0 -- literally zero, by construction, since no mechanism wrote
           source="problem_injection" events before this build shipped.
  AFTER (provisional, first-guess thresholds, not guaranteed):
           over the first 72h post-deploy, at least 3 distinct non-template
           anchored problems reach PERSISTED (n_fires>=4, span>=6h) via
           self-sustained events, with at least one containing a >=2h gap
           unexplained by any feed mention of that problem's keywords.
  TRIPWIRE (over-correction / rumination): any single problem accounting
           for >40% of self-sustained events in a trailing 24h window.

Usage:
  python3 scripts/problem_persistence.py             # full report, now
  python3 scripts/problem_persistence.py --at "2026-07-20 09:00"
"""
from __future__ import annotations

import argparse
import datetime
import json
import sqlite3
import sys
import time
from pathlib import Path

REPO = Path("/home/rr/Desktop/Desktop/nex5")
SCRIPTS_DIR = REPO / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from theory_x.stage7_sustained.problem_classify import is_real_question  # noqa: E402
from theory_x.stage7_sustained.problem_memory import _clean_tokens  # noqa: E402

CONV_DB = REPO / "data" / "conversations.db"
BELIEFS_DB = REPO / "data" / "beliefs.db"

PERSIST_N_FIRES = 4
PERSIST_SPAN_HOURS = 6.0
ATTRIBUTION_COOLDOWN_MIN = 15.0  # feed-mention exclusion window
CONCENTRATION_WINDOW_HOURS = 24.0
CONCENTRATION_TRIPWIRE = 0.40


def _ro(path: Path) -> sqlite3.Connection:
    c = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c


def _fmt_ts(ts: float) -> str:
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _load_problems(now: float) -> list[sqlite3.Row]:
    with _ro(CONV_DB) as c:
        return c.execute(
            "SELECT id, title, description, observations, created_at "
            "FROM open_problems WHERE created_at <= ? ORDER BY created_at",
            (now,),
        ).fetchall()


def _injection_events(observations_json: str, now: float) -> list[dict]:
    """Deduped-by-text source='problem_injection' entries, ts <= now."""
    try:
        obs = json.loads(observations_json or "[]")
    except (json.JSONDecodeError, TypeError):
        return []
    events = []
    seen_text = set()
    for o in obs:
        if not isinstance(o, dict) or o.get("source") != "problem_injection":
            continue
        ts = o.get("ts")
        if ts is None or ts > now:
            continue
        text = (o.get("text") or "").strip()
        if text in seen_text:
            continue  # defensive re-check; observe() should already prevent this
        seen_text.add(text)
        events.append({"ts": ts, "text": text})
    events.sort(key=lambda e: e["ts"])
    return events


def _feed_mentioned_recently(beliefs_conn: sqlite3.Connection, keywords: set[str],
                              event_ts: float, window_min: float) -> bool:
    """True if a precipitated_from_sense belief mentioning >=1 keyword landed
    within window_min of event_ts -- attributes the reference to the feed
    re-raising the topic, not to the injection mechanism's own initiative."""
    if not keywords:
        return False
    lo = event_ts - window_min * 60
    hi = event_ts + window_min * 60
    rows = beliefs_conn.execute(
        "SELECT content FROM beliefs WHERE source='precipitated_from_sense' "
        "AND created_at BETWEEN ? AND ?",
        (lo, hi),
    ).fetchall()
    for r in rows:
        content_words = _clean_tokens(r["content"] or "")
        if content_words & keywords:
            return True
    return False


def analyze(now: float) -> dict:
    problems = _load_problems(now)
    beliefs_conn = _ro(BELIEFS_DB)

    results = []
    for p in problems:
        title = p["title"] or ""
        desc = p["description"] or ""
        if not is_real_question(title, desc):
            continue
        events = _injection_events(p["observations"], now)
        if not events:
            continue
        keywords = _clean_tokens(title + " " + desc)
        self_sustained = [
            e for e in events
            if not _feed_mentioned_recently(beliefs_conn, keywords, e["ts"],
                                             ATTRIBUTION_COOLDOWN_MIN)
        ]
        if not self_sustained:
            continue
        n_fires = len(self_sustained)
        span_hrs = (self_sustained[-1]["ts"] - self_sustained[0]["ts"]) / 3600.0
        persisted = n_fires >= PERSIST_N_FIRES and span_hrs >= PERSIST_SPAN_HOURS
        results.append({
            "id": p["id"], "title": title,
            "n_injection_events": len(events),
            "n_self_sustained": n_fires,
            "span_hours": span_hrs,
            "persisted": persisted,
            "events": self_sustained,
        })

    beliefs_conn.close()

    # Concentration tripwire, trailing window ending at `now`.
    cutoff = now - CONCENTRATION_WINDOW_HOURS * 3600
    counts = {}
    total = 0
    for r in results:
        n = sum(1 for e in r["events"] if e["ts"] > cutoff)
        if n:
            counts[r["id"]] = n
            total += n
    concentration = 0.0
    dominant = None
    if total:
        dominant_id, dominant_n = max(counts.items(), key=lambda kv: kv[1])
        concentration = dominant_n / total
        dominant = dominant_id

    return {
        "problems_evaluated": len(problems),
        "qualifying_with_events": len(results),
        "self_sustained_count": sum(1 for r in results if r["n_self_sustained"] > 0),
        "persisted_count": sum(1 for r in results if r["persisted"]),
        "results": results,
        "concentration_window_hours": CONCENTRATION_WINDOW_HOURS,
        "concentration_fraction": concentration,
        "concentration_dominant_id": dominant,
        "concentration_tripwire": concentration > CONCENTRATION_TRIPWIRE,
    }


def report(now: float) -> None:
    a = analyze(now)
    print("=" * 78)
    print(f"PROBLEM PERSISTENCE  --  {_fmt_ts(now)}")
    print("=" * 78)
    print(f"open_problems evaluated (non-template, anchor-passing): "
          f"{a['problems_evaluated']} total table rows scanned")
    print(f"problems with >=1 problem_injection event ever: {a['qualifying_with_events']}")
    print(f"problems with >=1 SELF-SUSTAINED event (feed-mention excluded): "
          f"{a['self_sustained_count']}")
    print(f"problems meeting PERSISTED bar "
          f"(n_fires>={PERSIST_N_FIRES}, span>={PERSIST_SPAN_HOURS}h): "
          f"{a['persisted_count']}")
    print()
    for r in a["results"]:
        flag = "PERSISTED" if r["persisted"] else "tracked"
        print(f"  [{flag:9s}] id={r['id']:4d}  self_sustained={r['n_self_sustained']:2d} "
              f"(of {r['n_injection_events']:2d} injection events)  "
              f"span={r['span_hours']:.1f}h  {r['title'][:60]!r}")
    print()
    print(f"CONCENTRATION (trailing {a['concentration_window_hours']:.0f}h): "
          f"{a['concentration_fraction']*100:.0f}% of self-sustained events belong to "
          f"problem id={a['concentration_dominant_id']}"
          if a["concentration_dominant_id"] is not None else
          "CONCENTRATION: no self-sustained events in trailing window")
    if a["concentration_tripwire"]:
        print(f"  *** TRIPWIRE: exceeds {CONCENTRATION_TRIPWIRE*100:.0f}% -- "
              f"rumination risk, check the cooldown/pool-size guards ***")
    print()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--at", metavar="'YYYY-MM-DD HH:MM'",
                     help="evaluate as of this UTC moment instead of now")
    args = ap.parse_args()
    if args.at:
        dt = datetime.datetime.strptime(args.at, "%Y-%m-%d %H:%M").replace(
            tzinfo=datetime.timezone.utc
        )
        report(dt.timestamp())
    else:
        report(time.time())


if __name__ == "__main__":
    main()
