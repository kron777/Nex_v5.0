#!/usr/bin/env python3
"""NEX5_WARRANT validation gate — read-only.

(a) warrant is HIGH for hand-seeded keystones and earned syntheses, LOW for raw
    feed impressions and generic connector templates;
(b) warrant is ORTHOGONAL to plain edge degree and to question-relevance —
    reported next to the old conviction support score, which failed on both.

Nothing is written: compute_all() reads through Reader (mode=ro); the retriever
is built without an edges_writer.
"""
from __future__ import annotations

import json
import math
import os
import random
import statistics as st
import sys
import time
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from theory_x.stage_warrant.warrant import compute_all, WEIGHTS  # noqa: E402
import conviction_harness as h  # noqa: E402  (spearman, toks, test_turns)

BEL_DB = os.path.join(ROOT, "data", "beliefs.db")
CONV_DB = os.path.join(ROOT, "data", "conversations.db")
COMPONENTS = ("survival", "sustain", "indep", "xsynth")


def _ro(path):
    import sqlite3
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)


def auc(pos, neg):
    """P(random positive > random negative), ties half."""
    if not pos or not neg:
        return float("nan")
    allv = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg])
    rank, i, r_pos = 1, 0, 0.0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1][0] == allv[i][0]:
            j += 1
        avg = (rank + rank + (j - i)) / 2
        r_pos += avg * sum(1 for k in range(i, j + 1) if allv[k][1])
        rank += j - i + 1
        i = j + 1
    return (r_pos - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def main():
    now = time.time()
    t0 = time.time()
    W = compute_all(now=now)
    print(f"computed warrant for {len(W)} unpaused beliefs (tier<=7) in {time.time()-t0:.1f}s")
    con = _ro(BEL_DB)
    meta = {r[0]: {"tier": r[1], "locked": r[2], "source": r[3] or "?"}
            for r in con.execute("SELECT id, tier, locked, source FROM beliefs WHERE paused=0 AND tier<=7")}
    deg = defaultdict(int)
    for s, t in con.execute("SELECT source_id, target_id FROM belief_edges"):
        deg[s] += 1; deg[t] += 1
    con.close()
    ids = [i for i in W if i in meta]

    def summary(label, sel):
        v = [W[i]["warrant"] for i in sel]
        if not v:
            return
        q = st.quantiles(v, n=10) if len(v) > 9 else [float("nan")] * 9
        comp = "  ".join(f"{c[:4]} {st.mean(W[i][c] for i in sel):.2f}" for c in COMPONENTS)
        print(f"   {label:30s} n={len(v):6d}  mean {st.mean(v):.3f}  p10 {q[0]:.3f}  "
              f"p50 {st.median(v):.3f}  p90 {q[-1]:.3f}   | {comp}")

    print(f"\nweights {WEIGHTS}")
    print("\nBY TIER")
    for t in sorted({meta[i]['tier'] for i in ids}):
        summary(f"T{t}", [i for i in ids if meta[i]["tier"] == t])
    print("\nBY SOURCE (top 12 by count)")
    by_src = defaultdict(list)
    for i in ids:
        by_src[meta[i]["source"]].append(i)
    for s, sel in sorted(by_src.items(), key=lambda x: -len(x[1]))[:12]:
        summary(s, sel)

    groups = {
        "KEYSTONE (locked, T1-2)": [i for i in ids if meta[i]["locked"] and meta[i]["tier"] <= 2],
        "SYNTHESIS held (T<=6)": [i for i in ids if meta[i]["source"] == "synergized" and meta[i]["tier"] <= 6],
        "SYNTHESIS decayed (T7)": [i for i in ids if meta[i]["source"] == "synergized" and meta[i]["tier"] == 7],
        "RAW FEED (precip_from_sense)": [i for i in ids if meta[i]["source"] == "precipitated_from_sense"],
        "GENERIC (hot_obs+counterfact)": [i for i in ids if meta[i]["source"] in ("hot_observer", "counterfactual_node")],
    }
    print("\nGATE (a) — reference groups")
    for g, sel in groups.items():
        summary(g, sel)
    hi = groups["KEYSTONE (locked, T1-2)"] + groups["SYNTHESIS held (T<=6)"]
    lo = groups["RAW FEED (precip_from_sense)"] + groups["GENERIC (hot_obs+counterfact)"]
    print(f"   AUC(keystone+held synthesis  >  raw feed+generic) = "
          f"{auc([W[i]['warrant'] for i in hi], [W[i]['warrant'] for i in lo]):.3f}")
    nk = groups["SYNTHESIS held (T<=6)"]
    print(f"   AUC(held synthesis alone     >  raw feed+generic) = "
          f"{auc([W[i]['warrant'] for i in nk], [W[i]['warrant'] for i in lo]):.3f}")
    print(f"   AUC(held synthesis > decayed synthesis)           = "
          f"{auc([W[i]['warrant'] for i in nk], [W[i]['warrant'] for i in groups['SYNTHESIS decayed (T7)']]):.3f}")

    # ── (b1) degree ─────────────────────────────────────────────────────────
    print("\nGATE (b1) — Spearman with plain edge degree (all edge types)")
    rnd = random.Random(1)
    def rho_deg(sel, key):
        sel = sel if len(sel) <= 20000 else rnd.sample(sel, 20000)
        return h.spearman([key(i) for i in sel], [deg.get(i, 0) for i in sel])
    pools = {"all unpaused T<=7": ids,
             "chat pool T<=6": [i for i in ids if meta[i]["tier"] <= 6],
             "T<=6 excl. keystones": [i for i in ids if meta[i]["tier"] <= 6 and not meta[i]["locked"]]}
    for name, sel in pools.items():
        parts = "  ".join(f"{c[:4]} {rho_deg(sel, lambda i, c=c: W[i][c]):+.2f}" for c in COMPONENTS)
        print(f"   {name:24s} warrant {rho_deg(sel, lambda i: W[i]['warrant']):+.3f}   | {parts}")
    # old conviction support, same pool, for reference
    try:
        from theory_x.stage_affect import conviction as cv
        samp = rnd.sample(pools["chat pool T<=6"], min(1500, len(pools["chat pool T<=6"])))
        con = _ro(BEL_DB)
        sup = {}
        for i in samp:
            row = con.execute("SELECT id, tier, confidence, last_referenced_at FROM beliefs WHERE id=?", (i,)).fetchone()
            f = cv._features(con, row, now)
            sup[i] = cv.support(f["tier"], f["confidence"], f["deg"], f["age_h"])
        con.close()
        print(f"   reference: old conviction SUPPORT vs degree (n={len(samp)} of chat pool) "
              f"{h.spearman([sup[i] for i in samp], [deg.get(i, 0) for i in samp]):+.3f}; "
              f"warrant on the same sample "
              f"{h.spearman([W[i]['warrant'] for i in samp], [deg.get(i, 0) for i in samp]):+.3f}; "
              f"warrant vs support {h.spearman([W[i]['warrant'] for i in samp], [sup[i] for i in samp]):+.3f}")
    except Exception as e:
        print(f"   reference support skipped: {e}")

    # ── (b2) question relevance ─────────────────────────────────────────────
    print("\nGATE (b2) — correlation with question-relevance inside real retrieved sets")
    from substrate import Reader
    from theory_x.stage3_world_model.retrieval import BeliefRetriever
    ret = BeliefRetriever(Reader(BEL_DB))
    c2 = _ro(CONV_DB)
    turns = sorted({r[0].strip() for r in c2.execute(
        "SELECT user_turn FROM provenance_snapshots WHERE user_turn IS NOT NULL AND length(user_turn) > 8")})
    c2.close()
    per_turn = []
    for q in turns:
        qt = h.toks(q)
        for kw in ({"branch_hints": ["systems"], "limit": 5, "side_filter": "INSIDE"},
                   {"branch_hints": [], "limit": 8}):
            try:
                got = [(x["id"], len(h.toks(x.get("content", "")) & qt)) for x in ret.retrieve(query=q, **kw)]
            except Exception:
                got = []
            got = [(i, r) for i, r in got if i in W]
            if len(got) >= 3:
                per_turn.append(got)
    rhos = []
    for got in per_turn:
        wv = [W[i]["warrant"] for i, _ in got]; rv = [r for _, r in got]
        if len(set(wv)) > 1 and len(set(rv)) > 1:
            rhos.append(h.spearman(wv, rv))
    boots = sorted(st.mean(random.Random(k).choices(rhos, k=len(rhos))) for k in range(2000))
    print(f"   {len(turns)} user turns -> {len(per_turn)} retrieved sets; within-set rho "
          f"(warrant, relevance) mean {st.mean(rhos):+.3f} "
          f"[{boots[50]:+.3f},{boots[1949]:+.3f}] over {len(rhos)} sets with variation")
    # pooled, within-set ranks
    xs, ys = [], []
    for got in per_turn:
        wr = h_rank([W[i]["warrant"] for i, _ in got]); rr = h_rank([r for _, r in got])
        xs += wr; ys += rr
    print(f"   pooled within-set ranks rho {h.spearman(xs, ys):+.3f} (n={len(xs)})")
    ret_ids = {i for got in per_turn for i, _ in got}
    print(f"   warrant among retrieved beliefs: mean {st.mean(W[i]['warrant'] for i in ret_ids):.3f}, "
          f"share > 0.3: {sum(W[i]['warrant'] > 0.3 for i in ret_ids)/len(ret_ids):.0%} of {len(ret_ids)}")

    # coverage honesty
    print("\nCOVERAGE — how much of the graph each component can see")
    for c in COMPONENTS:
        nz = sum(1 for i in ids if W[i][c] > 0)
        print(f"   {c:9s} non-zero for {nz:6d} / {len(ids)} ({nz/len(ids):.1%})")


def h_rank(v):
    n = len(v)
    o = sorted(range(n), key=lambda i: v[i])
    r = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and v[o[j + 1]] == v[o[i]]:
            j += 1
        for q in range(i, j + 1):
            r[o[q]] = ((i + j) / 2) / max(1, n - 1)
        i = j + 1
    return r


if __name__ == "__main__":
    main()
