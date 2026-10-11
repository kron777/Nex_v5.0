#!/usr/bin/env python3
"""check_session_consistency.py — chat-side self-consistency harness.

Read-only. The template/groove defect transposed to the chat register: within a
single conversation, does Nex repeat herself, and does her register collapse to
one value? These are the chat-path falsifiers for the attention arbiter — if it
diversifies attention, self-repetition and register-collapse should not get
worse.

Reads conversations.db messages(role, content, register, session_id, timestamp)
and sessions. (`register` is nullable — reported as a populated-fraction, not
assumed present.)

Metrics:
  (a) self-repetition — per session, the max pairwise first-sentence 5-gram
      Jaccard between her own ('nex') messages; reported as the worst session and
      the mean of per-session maxes.
  (b) register-collapse — over 'nex' messages: fraction with a non-NULL register,
      and the largest single-register share (1.0 = fully collapsed to one).
  (c) carry-fidelity — PENDING: needs the self_present structured carry (W3). A
      placeholder is printed so the harness is complete when that ships.

Usage:
  PYTHONPATH=. python3 tools/check_session_consistency.py
  PYTHONPATH=. python3 tools/check_session_consistency.py --freeze base.json
  PYTHONPATH=. python3 tools/check_session_consistency.py --baseline base.json
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"[a-z0-9']+")


def _first_sentence_grams(text: str) -> frozenset:
    parts = _SENTENCE_SPLIT.split((text or "").strip())
    words = _WORD.findall((parts[0] if parts else "").lower())
    return frozenset(tuple(words[i:i + 5]) for i in range(len(words) - 4))


def _jaccard(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    u = len(a | b)
    return (len(a & b) / u) if u else 0.0


def _ro(path: str) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def _db(name: str) -> str:
    from substrate.paths import db_paths
    return str(db_paths()[name])


def load_nex_messages() -> list[dict]:
    con = _ro(_db("conversations"))
    try:
        rows = con.execute(
            "SELECT session_id, content, register, timestamp FROM messages "
            "WHERE role='nex' AND content IS NOT NULL ORDER BY session_id, timestamp"
        ).fetchall()
    finally:
        con.close()
    return [{"session_id": s, "content": c, "register": r, "timestamp": t}
            for s, c, r, t in rows]


def self_repetition(msgs: list[dict], threshold: float) -> dict:
    by_session: dict[str, list[frozenset]] = defaultdict(list)
    for m in msgs:
        by_session[m["session_id"]].append(_first_sentence_grams(m["content"]))
    session_maxes = []
    worst = 0.0
    n_multi = 0
    for grams in by_session.values():
        if len(grams) < 2:
            continue
        n_multi += 1
        mx = 0.0
        for i in range(len(grams)):
            for j in range(i + 1, len(grams)):
                mx = max(mx, _jaccard(grams[i], grams[j]))
        session_maxes.append(mx)
        worst = max(worst, mx)
    return {
        "sessions_with_multiple_nex_msgs": n_multi,
        "worst_session_self_repetition": round(worst, 4),
        "mean_session_self_repetition": round(statistics.mean(session_maxes), 4)
        if session_maxes else 0.0,
        # fraction of multi-msg sessions whose worst pair is a near-duplicate:
        "fraction_sessions_with_near_dup": round(
            sum(1 for v in session_maxes if v >= threshold) / n_multi, 4)
        if n_multi else 0.0,
    }


def register_collapse(msgs: list[dict]) -> dict:
    n = len(msgs)
    populated = [m["register"] for m in msgs if m["register"]]
    counts = Counter(populated)
    top_share = (counts.most_common(1)[0][1] / len(populated)) if populated else None
    return {
        "nex_messages": n,
        "register_populated_fraction": round(len(populated) / n, 4) if n else 0.0,
        "distinct_registers": len(counts),
        "largest_register_share": round(top_share, 4) if top_share is not None else None,
        "register_distribution": dict(counts.most_common()),
    }


def measure(threshold: float) -> dict:
    msgs = load_nex_messages()
    return {
        "threshold": threshold,
        "self_repetition": self_repetition(msgs, threshold),
        "register": register_collapse(msgs),
        "carry_fidelity": "PENDING — needs the self_present structured carry (W3)",
    }


def _verdict(cur: dict, base: dict, tol: float) -> tuple[bool, list[str]]:
    notes, ok = [], True
    pairs = [
        ("self_repetition", "worst_session_self_repetition"),
        ("self_repetition", "fraction_sessions_with_near_dup"),
        ("register", "largest_register_share"),
    ]
    for grp, key in pairs:
        b = base.get(grp, {}).get(key)
        c = cur.get(grp, {}).get(key)
        if b is None or c is None:
            continue
        limit = b * (1.0 + tol) if b > 0 else tol
        arrow = "↓" if c < b else ("=" if c == b else "↑")
        notes.append(f"  {grp}.{key}: {b} -> {c}  ({arrow})")
        if c > limit:
            ok = False
    return ok, notes


def main() -> int:
    ap = argparse.ArgumentParser(description="Session self-consistency harness (read-only).")
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--freeze", metavar="PATH")
    ap.add_argument("--baseline", metavar="PATH")
    ap.add_argument("--tolerance", type=float, default=0.25)
    args = ap.parse_args()

    cur = measure(args.threshold)
    sr, rg = cur["self_repetition"], cur["register"]
    print("=== session self-consistency ===")
    print(f"nex messages: {rg['nex_messages']}  "
          f"sessions w/ >=2 nex msgs: {sr['sessions_with_multiple_nex_msgs']}")
    print(f"self-repetition: worst={sr['worst_session_self_repetition']}  "
          f"mean={sr['mean_session_self_repetition']}  "
          f"near-dup sessions={sr['fraction_sessions_with_near_dup']}")
    print(f"register: populated={rg['register_populated_fraction']}  "
          f"distinct={rg['distinct_registers']}  "
          f"largest-share={rg['largest_register_share']}")
    print(f"register distribution: {rg['register_distribution']}")
    print(f"carry-fidelity (c): {cur['carry_fidelity']}")

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
        print("VERDICT:", "OK — no chat-side rut introduced" if ok else "REGRESSED")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
