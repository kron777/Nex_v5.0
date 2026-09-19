#!/usr/bin/env python3
"""measure_confab.py — READ-ONLY soak metric for the extraction context-carry fix (6ef84ac).

Reports, over a recent window, how much single-word confabulation the
co-occurrence path is producing, and whether rows carry the new sentence-span
context yet (so old-code vs new-code rows are distinguishable across a restart).

Measures two layers:
  1. signals        — raw extraction output (beliefs.db `signals`, detector
                      'co_occurrence'). Where the fix lives; carries the entity
                      AND the new context field per row.
  2. open_problems  — what survived the quality gates and got DEPOSITED
                      (conversations.db, tags signal:{N}_branch). The
                      confabulation actually visible as fake research programs.

"Garbage" reuses the project's OWN definition — it imports
signal_to_problem._entity_has_substance (the closed-category gate +
_VAGUE_ENTITY_WORDS + corpus prose-cap check) and _extract_entity. Nothing is
re-hardcoded here.

READ-ONLY: opens every DB with mode=ro; writes nothing; safe to run repeatedly.

Usage:  .venv/bin/python3 tools/measure_confab.py [WINDOW_HOURS]   (default 24)
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import time

# Run from anywhere: put the repo root on the path so project imports resolve.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BELIEFS_DB = "/home/rr/Desktop/Desktop/nex5/data/beliefs.db"
CONV_DB = "/home/rr/Desktop/Desktop/nex5/data/conversations.db"

# Reuse the project's own definitions — do not re-hardcode.
from theory_x.signals.signal_to_problem import _entity_has_substance, _extract_entity

_TITLE_ENTITY = re.compile(r"investigate '([^']+)'")
_BRANCH_TAG = re.compile(r"signal:\d+_branch")


def _ro(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
    con.row_factory = sqlite3.Row
    return con


def _is_garbage(entity, b_cx) -> bool:
    """Project's own gate: garbage == would NOT pass _entity_has_substance."""
    if not entity:
        return True
    try:
        return not _entity_has_substance(entity, b_cx)
    except Exception:
        return not _entity_has_substance(entity, None)


def _payload_has_new_context(payload: dict) -> bool:
    """New-code (post-6ef84ac) rows carry a `context` string and/or
    dict-shaped `contexts` [{branch,span}]. Old rows have flat-string contexts
    or none."""
    if not isinstance(payload, dict):
        return False
    if isinstance(payload.get("context"), str) and payload["context"].strip():
        return True
    ctxs = payload.get("contexts")
    return bool(ctxs) and isinstance(ctxs[0], dict) and "span" in ctxs[0]


def measure_signals(cutoff: float, b_cx):
    con = _ro(BELIEFS_DB)
    rows = con.execute(
        "SELECT payload, entities FROM signals "
        "WHERE detector_name='co_occurrence' AND detected_at > ? "
        "ORDER BY detected_at DESC",
        (cutoff,),
    ).fetchall()
    con.close()
    total = len(rows)
    garbage, single_word, new_ctx = 0, 0, 0
    ex_garbage, ex_good = [], []
    for r in rows:
        try:
            payload = json.loads(r["payload"]) if r["payload"] else {}
        except Exception:
            payload = {}
        entity = _extract_entity(payload)
        if _payload_has_new_context(payload):
            new_ctx += 1
        if entity and " " not in entity.strip():
            single_word += 1
        if _is_garbage(entity, b_cx):
            garbage += 1
            if entity and len(ex_garbage) < 8 and entity not in ex_garbage:
                ex_garbage.append(entity)
        elif entity and len(ex_good) < 6 and entity not in ex_good:
            ex_good.append(entity)
    return dict(total=total, garbage=garbage, single_word=single_word,
                new_ctx=new_ctx, old_ctx=total - new_ctx,
                ex_garbage=ex_garbage, ex_good=ex_good)


def measure_problems(cutoff: float, b_cx):
    con = _ro(CONV_DB)
    rows = con.execute(
        "SELECT title, description, tags FROM open_problems WHERE created_at > ?",
        (cutoff,),
    ).fetchall()
    con.close()
    total, garbage, single_word, with_ctx = 0, 0, 0, 0
    ex_garbage = []
    for r in rows:
        tags = r["tags"] or ""
        if not _BRANCH_TAG.search(tags):
            continue  # only co-occurrence-derived problems
        total += 1
        m = _TITLE_ENTITY.search(r["title"] or "")
        entity = m.group(1) if m else None
        if r["description"] and "Seen in context:" in r["description"]:
            with_ctx += 1  # new-code deposit (consumer surfaced the span)
        if entity and " " not in entity.strip():
            single_word += 1
        if _is_garbage(entity, b_cx):
            garbage += 1
            if entity and len(ex_garbage) < 8 and entity not in ex_garbage:
                ex_garbage.append(entity)
    return dict(total=total, garbage=garbage, single_word=single_word,
                with_ctx=with_ctx, without_ctx=total - with_ctx,
                ex_garbage=ex_garbage)


def _rate(n, d):
    return f"{(100.0 * n / d):.1f}%" if d else "n/a"


def main():
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 24.0
    cutoff = time.time() - hours * 3600
    b_cx = _ro(BELIEFS_DB)  # for the corpus prose-cap tail of _entity_has_substance
    sig = measure_signals(cutoff, b_cx)
    prob = measure_problems(cutoff, b_cx)
    b_cx.close()

    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 72)
    print(f"CONFAB SOAK SNAPSHOT  {stamp}  window={hours:g}h")
    print("-" * 72)
    print(
        f"SIGNALS   (co_occurrence, raw extraction): n={sig['total']:<5} "
        f"garbage={sig['garbage']} ({_rate(sig['garbage'], sig['total'])})  "
        f"single-word={sig['single_word']}  "
        f"new-ctx={sig['new_ctx']}/{sig['total']} old-ctx={sig['old_ctx']}"
    )
    print(
        f"PROBLEMS  (deposited, {'{N}_branch'}):       n={prob['total']:<5} "
        f"garbage={prob['garbage']} ({_rate(prob['garbage'], prob['total'])})  "
        f"single-word={prob['single_word']}  "
        f"with-ctx={prob['with_ctx']}/{prob['total']} without={prob['without_ctx']}"
    )
    if sig["ex_garbage"]:
        print(f"  signal garbage examples : {', '.join(sig['ex_garbage'])}")
    if sig["ex_good"]:
        print(f"  signal good examples    : {', '.join(sig['ex_good'])}")
    if prob["ex_garbage"]:
        print(f"  problem garbage examples: {', '.join(prob['ex_garbage'])}")
    print("=" * 72)
    print("new-ctx = rows carrying the post-6ef84ac sentence-span context "
          "(old vs new code across the restart).")


if __name__ == "__main__":
    main()
