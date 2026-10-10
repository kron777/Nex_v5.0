#!/usr/bin/env python3
"""check_template_repetition.py — the template-repetition measurement harness.

Read-only. Measures how much Nex's crystallized output collapses into a single
template — the defect this project has produced twice (R31/R32 exemplar loop,
R75/R76 hot-observer groove). It is the machine-side instrument that gates the
falsifiers for any attention/retrieval change (chat arbiter, own-content render,
stakes): a change that diversifies attention must move these numbers DOWN; one
that does not has not earned its flag regardless of how the output reads.

Why a harness at all, separate from the crystallizer's in-line semantic-repeat
guard: that guard looks at a 30-minute window, but the median inter-arrival is
~213 min (R75), so the window is usually empty — R75 found 0/15 consecutive
pairs were catchable in-line. This tool measures over **N consecutive outputs**,
not a time window, which is the whole point.

Three signals:
  1. consecutive near-duplicate rate — fraction of adjacent crystallized outputs
     whose first-sentence 5-gram Jaccard >= threshold (the repo's own R32
     exemplar-dedup construction).
  2. largest single-template cluster — the biggest group of mutually-similar
     outputs in the window, as a fraction of the window.
  3. semantic_repeat reject rate — rejects/day from crystallization_rejects
     (dynamic.db), the crystallizer's own record of the in-line guard firing.

Usage:
  PYTHONPATH=. python3 tools/check_template_repetition.py --window 200
  PYTHONPATH=. python3 tools/check_template_repetition.py --window 200 --freeze base.json
  PYTHONPATH=. python3 tools/check_template_repetition.py --window 200 --baseline base.json

With --baseline, exits non-zero if a signal regressed past --tolerance (default
0.25, i.e. +25%, the repo's own tripwire convention) — so it can gate a round.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"[a-z0-9']+")


def _first_sentence_grams(text: str) -> frozenset:
    """First-sentence 5-gram set — identical construction to the crystallizer's
    R32 exemplar dedup (generator._hot_first_sentence_grams). Reimplemented here
    so the tool stays standalone (no heavy fountain import)."""
    parts = _SENTENCE_SPLIT.split((text or "").strip())
    words = _WORD.findall((parts[0] if parts else "").lower())
    return frozenset(tuple(words[i:i + 5]) for i in range(len(words) - 4))


def _jaccard(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    union = len(a | b)
    return (len(a & b) / union) if union else 0.0


def _ro(path: str) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def _db(name: str) -> str:
    """Resolve a DB path via the substrate (NEVER a literal path — tools/ and
    genius/ already carry that /home/rr landmine; do not inherit it)."""
    from substrate.paths import db_paths
    return str(db_paths()[name])


def load_outputs(window: int) -> list[dict]:
    """The last `window` crystallized fountain_insight outputs, oldest-first.
    beliefs is NOT under reaper retention, so this is a permanent corpus."""
    con = _ro(_db("beliefs"))
    try:
        rows = con.execute(
            "SELECT content, created_at FROM beliefs "
            "WHERE source='fountain_insight' AND content IS NOT NULL "
            "ORDER BY created_at DESC LIMIT ?",
            (int(window),),
        ).fetchall()
    finally:
        con.close()
    rows = list(reversed(rows))  # oldest-first
    return [{"content": c, "created_at": t, "grams": _first_sentence_grams(c)}
            for c, t in rows]


def consecutive_duplicate_rate(outputs: list[dict], threshold: float) -> float:
    pairs = list(zip(outputs, outputs[1:]))
    if not pairs:
        return 0.0
    hits = sum(1 for a, b in pairs
               if _jaccard(a["grams"], b["grams"]) >= threshold)
    return hits / len(pairs)


def largest_cluster_fraction(outputs: list[dict], threshold: float) -> tuple[int, float]:
    """Greedy single-link clustering by gram-Jaccard; returns (size, fraction).
    O(n^2) — fine for the window sizes used here."""
    n = len(outputs)
    if n == 0:
        return 0, 0.0
    assigned = [-1] * n
    clusters: list[list[int]] = []
    for i in range(n):
        if assigned[i] != -1:
            continue
        cid = len(clusters)
        members = [i]
        assigned[i] = cid
        for j in range(i + 1, n):
            if assigned[j] == -1 and \
                    _jaccard(outputs[i]["grams"], outputs[j]["grams"]) >= threshold:
                assigned[j] = cid
                members.append(j)
        clusters.append(members)
    biggest = max(len(c) for c in clusters)
    return biggest, biggest / n


def semantic_repeat_reject_rate(span_start: float, span_end: float) -> dict:
    """Rejects/day of reason='semantic_repeat' from crystallization_rejects over
    [span_start, span_end]. Returns counts and a per-day rate (None if the span
    is degenerate or the table is unavailable)."""
    out = {"semantic_repeat": None, "total_rejects": None, "per_day": None,
           "available": False}
    try:
        con = _ro(_db("dynamic"))
    except Exception:
        return out
    try:
        sr = con.execute(
            "SELECT COUNT(*) FROM crystallization_rejects "
            "WHERE reason='semantic_repeat' AND ts >= ? AND ts <= ?",
            (span_start, span_end),
        ).fetchone()[0]
        tot = con.execute(
            "SELECT COUNT(*) FROM crystallization_rejects WHERE ts >= ? AND ts <= ?",
            (span_start, span_end),
        ).fetchone()[0]
        out.update(semantic_repeat=sr, total_rejects=tot, available=True)
        days = max((span_end - span_start) / 86400.0, 1e-9)
        if span_end > span_start:
            out["per_day"] = round(sr / days, 3)
    except sqlite3.Error:
        pass  # table absent on a fresh DB — leave available-ish but counts None
    finally:
        con.close()
    return out


def measure(window: int, threshold: float) -> dict:
    outputs = load_outputs(window)
    n = len(outputs)
    dup = consecutive_duplicate_rate(outputs, threshold)
    cl_size, cl_frac = largest_cluster_fraction(outputs, threshold)
    if n >= 2:
        span = semantic_repeat_reject_rate(outputs[0]["created_at"],
                                           outputs[-1]["created_at"])
    else:
        span = {"available": False, "per_day": None}
    return {
        "n_outputs": n,
        "threshold": threshold,
        "consecutive_duplicate_rate": round(dup, 4),
        "largest_cluster_size": cl_size,
        "largest_cluster_fraction": round(cl_frac, 4),
        "semantic_repeat": span,
    }


def _verdict(cur: dict, base: dict, tol: float) -> tuple[bool, list[str]]:
    """OK unless a signal regressed by more than `tol` (fractional) vs baseline."""
    notes = []
    ok = True
    for key in ("consecutive_duplicate_rate", "largest_cluster_fraction"):
        b = base.get(key)
        c = cur.get(key)
        if b is None or c is None:
            continue
        limit = b * (1.0 + tol) if b > 0 else tol
        arrow = "↓ improved" if c < b else ("= flat" if c == b else "↑ worse")
        notes.append(f"  {key}: {b:.4f} -> {c:.4f}  ({arrow})")
        if c > limit:
            ok = False
    return ok, notes


def main() -> int:
    ap = argparse.ArgumentParser(description="Template-repetition harness (read-only).")
    ap.add_argument("--window", type=int, default=200,
                    help="N most-recent crystallized outputs to measure (N consecutive, NOT a time window).")
    ap.add_argument("--threshold", type=float, default=0.5,
                    help="first-sentence 5-gram Jaccard to count as a near-duplicate (R32 bar).")
    ap.add_argument("--freeze", metavar="PATH",
                    help="write the current measurement as a frozen baseline and exit.")
    ap.add_argument("--baseline", metavar="PATH",
                    help="compare the current measurement against this frozen baseline.")
    ap.add_argument("--tolerance", type=float, default=0.25,
                    help="fractional regression allowed before the gate fails (default 0.25).")
    args = ap.parse_args()

    cur = measure(args.window, args.threshold)

    print("=== template-repetition ===")
    print(f"window (consecutive outputs): {cur['n_outputs']}  threshold: {cur['threshold']}")
    print(f"consecutive near-duplicate rate: {cur['consecutive_duplicate_rate']}")
    print(f"largest template cluster:        {cur['largest_cluster_size']} "
          f"({cur['largest_cluster_fraction']*100:.1f}% of window)")
    sr = cur["semantic_repeat"]
    if sr.get("available") and sr.get("semantic_repeat") is not None:
        print(f"semantic_repeat rejects in span:  {sr['semantic_repeat']} "
              f"(of {sr['total_rejects']} total; ~{sr['per_day']}/day)")
    else:
        print("semantic_repeat rejects:          (crystallization_rejects unavailable / empty)")

    if args.freeze:
        Path(args.freeze).write_text(json.dumps(cur, indent=2), encoding="utf-8")
        print(f"\nfrozen baseline written to {args.freeze}")
        return 0

    if args.baseline:
        try:
            base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
        except Exception as e:
            print(f"\n[baseline] could not read {args.baseline}: {e}", file=sys.stderr)
            return 2
        ok, notes = _verdict(cur, base, args.tolerance)
        print(f"\n=== vs baseline (tolerance +{args.tolerance:.0%}) ===")
        for ln in notes:
            print(ln)
        print("VERDICT:", "OK — not regressed" if ok else "REGRESSED — template repetition up")
        return 0 if ok else 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
