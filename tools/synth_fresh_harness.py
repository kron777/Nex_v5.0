#!/usr/bin/env python3
"""Synergizer stale-feed harness (NEX5_SYNTH_FRESH) — READ-ONLY replay of
BeliefSynergizer._select_pair over its own recent picks. No LLM, no writes.

For each of the last N synergizer_log rows, the candidate set is rebuilt as of
that moment (anchors and fresh beliefs created at or before the pick, the 20
prior log rows as the recently-used set) and the argmax is re-run exactly as
_select_pair does it: relatedness = (1 - distance) x rec_w over anchor x fresh,
near-duplicates (distance < 0.15) skipped. `score_fn` lets the same replay run
with NEX5_SYNTH_FRESH's weighting.

  --investigate   why stale wins (Step 1)
  --measure       flag off vs on (Step 3)
Embeddings are cached to --cache (npz) so reruns are fast.
Caveat: beliefs are read in their CURRENT state (confidence, deletions), so the
replay is checked against the actual picks and fidelity is reported.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import statistics as st
import sys
from collections import Counter, defaultdict

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from theory_x.stage3_world_model.synergizer import BeliefSynergizer as _BS  # noqa: E402

BEL_DB = os.path.join(ROOT, "data", "beliefs.db")
DYN_DB = os.path.join(ROOT, "data", "dynamic.db")
MIN_D = _BS._MIN_RELATEDNESS_DISTANCE
H = 3600.0
D = 86400.0


def _ro(p):
    return sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=10)


def load(cache_path):
    con = _ro(BEL_DB)
    con.row_factory = sqlite3.Row
    srcs = tuple(_BS._ANCHOR_SOURCES | _BS._FRESH_SOURCES)
    rows = [dict(r) for r in con.execute(
        f"SELECT id, content, branch_id, confidence, created_at, source FROM beliefs "
        f"WHERE source IN ({','.join('?' * len(srcs))}) AND confidence > 0.5", srcs)]
    parents = defaultdict(set)
    for child, parent in con.execute("SELECT child_id, parent_id FROM belief_lineage"):
        parents[child].add(parent)
    log = [dict(r) for r in con.execute(
        "SELECT id, ts, belief_id_a, belief_id_b, result_belief_id FROM synergizer_log ORDER BY id")]
    con.close()
    ids = [r["id"] for r in rows]
    vecs = None
    if cache_path and os.path.exists(cache_path):
        z = np.load(cache_path)
        cached = dict(zip(z["ids"].tolist(), z["vecs"]))
        if all(i in cached for i in ids):
            vecs = np.stack([cached[i] for i in ids])
    if vecs is None:
        from theory_x.diversity.embeddings import get_model
        m = get_model()
        texts = [(r["content"] or "").strip() or " " for r in rows]
        vecs = m.encode(texts, batch_size=128, convert_to_numpy=True, show_progress_bar=False)
        if cache_path:
            np.savez(cache_path, ids=np.array(ids), vecs=vecs)
    norm = vecs / np.maximum(np.linalg.norm(vecs, axis=1, keepdims=True), 1e-9)
    return rows, norm, parents, log


def active_branches(ts, window_h=6.0):
    """Branches of fountain fires in the window before ts (queued bridging use)."""
    con = _ro(DYN_DB)
    rows = con.execute("SELECT hot_branch, COUNT(*) FROM fountain_events WHERE ts BETWEEN ? AND ? "
                       "GROUP BY hot_branch", (ts - window_h * H, ts)).fetchall()
    con.close()
    return dict(rows)


def replay(rows, norm, log, n, score_fn=None, simulate=False):
    """Per-pick dicts with the replayed choice and candidate diagnostics.
    simulate=True: the recently-used set comes from the replay's OWN previous
    choices (closed loop), not the real log — needed when the choices differ."""
    idx = {r["id"]: k for k, r in enumerate(rows)}
    is_anchor = np.array([r["source"] in _BS._ANCHOR_SOURCES for r in rows])
    is_fresh = np.array([r["source"] in _BS._FRESH_SOURCES for r in rows])
    created = np.array([float(r["created_at"] or 0) for r in rows])
    out = []
    tail = log[-n:]
    first = len(log) - len(tail)
    sim_hist = [(x["belief_id_a"], x["belief_id_b"]) for x in log[max(0, first - 20): first]]
    for j, pick in enumerate(tail):
        ts = float(pick["ts"])
        if simulate:
            recent = {a for a, _ in sim_hist[-20:]} | {b for _, b in sim_hist[-20:]}
        else:
            prior = log[max(0, first + j - 20): first + j]
            recent = {x["belief_id_a"] for x in prior} | {x["belief_id_b"] for x in prior}
        A = np.where(is_anchor & (created <= ts))[0]
        F = np.where(is_fresh & (created < ts))[0]
        if len(A) == 0 or len(F) == 0:
            continue
        cos = norm[A] @ norm[F].T
        d = (1.0 - cos) / 2.0
        rel = 1.0 - d
        rec_a = np.array([0.5 if rows[a]["id"] in recent else 1.0 for a in A])
        rec_f = np.array([0.5 if rows[f]["id"] in recent else 1.0 for f in F])
        recw = np.minimum(rec_a[:, None], rec_f[None, :])
        score = rel * recw
        if score_fn is not None:
            w = score_fn(rows, F, ts, A)
            score = score * (w[None, :] if w.ndim == 1 else w)
        score[d < MIN_D] = -1.0
        flat = int(np.argmax(score))
        ai, fi = divmod(flat, len(F))
        sim_hist.append((rows[A[ai]]["id"], rows[F[fi]]["id"]))
        best_per_fresh = score.max(axis=0)
        order = np.argsort(-best_per_fresh)
        out.append({
            "ts": ts, "actual_a": pick["belief_id_a"], "actual_b": pick["belief_id_b"],
            "a": rows[A[ai]]["id"], "b": rows[F[fi]]["id"], "score": float(score[ai, fi]),
            "fresh_ids": [rows[f]["id"] for f in F], "best_per_fresh": best_per_fresh,
            "order": order, "F": F, "A": A,
        })
    return out, idx, created


def investigate(n, cache):
    rows, norm, parents, log = load(cache)
    res, idx, created = replay(rows, norm, log, n)
    byid = {r["id"]: r for r in rows}
    fid = sum(1 for r in res if (r["a"], r["b"]) == (r["actual_a"], r["actual_b"]))
    fid_b = sum(1 for r in res if r["b"] == r["actual_b"])
    print(f"{len(res)} picks replayed; replay reproduces the actual pair {fid}/{len(res)}, "
          f"the fresh side {fid_b}/{len(res)}")
    ages = [(r["ts"] - float(byid[r["actual_b"]]["created_at"])) / D
            for r in res if r["actual_b"] in byid]
    q = st.quantiles(ages, n=10)
    print(f"\nACTUAL fresh-side age (days): p10 {q[0]:.1f}  median {st.median(ages):.1f}  "
          f"p90 {q[-1]:.1f}  mean {st.mean(ages):.1f};  <48h: {sum(a < 2 for a in ages)}/{len(ages)}")
    src = Counter(byid[r["actual_b"]]["source"] for r in res if r["actual_b"] in byid)
    print(f"ACTUAL fresh-side source: {dict(src)}")
    self_desc = sum(1 for r in res if r["actual_a"] in parents.get(r["actual_b"], ()))
    anc_desc = sum(1 for r in res
                   if any(byid.get(p, {}).get("source") in _BS._ANCHOR_SOURCES
                          for p in parents.get(r["actual_b"], ())))
    print(f"fresh side is itself a synthesis OF THE SAME ANCHOR: {self_desc}/{len(res)}; "
          f"of some anchor: {anc_desc}/{len(res)}")
    reuse = Counter(r["actual_b"] for r in res)
    print(f"distinct fresh beliefs used: {len(reuse)} over {len(res)} picks; "
          f"top-5 reuse counts {[c for _, c in reuse.most_common(5)]}")
    reuse_a = Counter(r["actual_a"] for r in res)
    print(f"distinct anchors used: {len(reuse_a)} of {sum(1 for r in rows if r['source'] in _BS._ANCHOR_SOURCES)}")

    # recent fountain insights: were they in contention?
    print("\nRECENT (<48h) FOUNTAIN INSIGHTS AT EACH PICK")
    pool_n, in_top10, in_top50, gaps, ranks = [], 0, 0, [], []
    for r in res:
        F = r["F"]
        rec = [k for k, f in enumerate(F) if rows[f]["source"] == "fountain_insight"
               and r["ts"] - created[f] < 48 * H]
        pool_n.append(len(rec))
        if not rec:
            continue
        rank_of = {int(k): pos for pos, k in enumerate(r["order"])}
        best = min(rec, key=lambda k: rank_of[k])
        ranks.append(rank_of[best] + 1)
        in_top10 += rank_of[best] < 10
        in_top50 += rank_of[best] < 50
        gaps.append(float(r["best_per_fresh"][r["order"][0]] - r["best_per_fresh"][best]))
    have = sum(1 for x in pool_n if x)
    print(f"   picks with >=1 recent fountain insight in the pool: {have}/{len(res)} "
          f"(median {st.median(pool_n):.0f} in pool)")
    if ranks:
        print(f"   best-ranked recent insight: median rank {st.median(ranks):.0f} of "
              f"{st.median(len(r['F']) for r in res):.0f} fresh; in top-10 {in_top10}, top-50 {in_top50}")
        print(f"   score gap to the winner: median {st.median(gaps):.3f}  p10 {st.quantiles(gaps, n=10)[0]:.3f}"
              f"  p90 {st.quantiles(gaps, n=10)[-1]:.3f}")
    # what the winners look like vs everything
    win_rel = [r["score"] for r in res]
    print(f"\nwinner score (relatedness x rec_w): median {st.median(win_rel):.3f}")
    # does distance-to-anchor favour syntheses structurally?
    A_all = np.where(np.array([r["source"] in _BS._ANCHOR_SOURCES for r in rows]))[0]
    best_anchor_cos = (norm[A_all] @ norm.T).max(axis=0)
    for s in ("synergized", "fountain_insight"):
        m = [best_anchor_cos[k] for k, r in enumerate(rows) if r["source"] == s]
        print(f"   {s:17s} max cosine to any anchor: median {np.median(m):.3f}  p90 {np.percentile(m, 90):.3f}")
    syn_anc = [best_anchor_cos[k] for k, r in enumerate(rows) if r["source"] == "synergized"
               and any(byid.get(p, {}).get("source") in _BS._ANCHOR_SOURCES for p in parents.get(r["id"], ()))]
    print(f"   synergized WITH an anchor parent: median {np.median(syn_anc):.3f} (n={len(syn_anc)})")


def _fresh_fn(floor, tau):
    """NEX5_SYNTH_FRESH weighting through the REAL BeliefSynergizer.fresh_weight."""
    def fn(rows, F, ts, A=None):
        _BS._FRESH_FLOOR, _BS._FRESH_TAU_DAYS = floor, tau
        return np.array([_BS.fresh_weight(rows[f]["created_at"], ts) for f in F])
    return fn


def ancestors_of(parents, depth=6):
    memo = {}
    def anc(b, d=0):
        if b in memo:
            return memo[b]
        out = set()
        if d < depth:
            for p in parents.get(b, ()):
                out.add(p); out |= anc(p, d + 1)
        memo[b] = out
        return out
    return anc


def _desc_fn(parents, pen=0.5, floor=None, tau=None):
    """Diagnostic: an anchor's own lineage descendants count as re-use of the
    anchor (x pen), optionally with the recency weight on top."""
    anc = ancestors_of(parents)
    def fn(rows, F, ts, A):
        m = np.ones((len(A), len(F)))
        aid = [rows[a]["id"] for a in A]
        for j, f in enumerate(F):
            an = anc(rows[f]["id"])
            if an:
                for i, a in enumerate(aid):
                    if a in an:
                        m[i, j] = pen
        if floor is not None:
            _BS._FRESH_FLOOR, _BS._FRESH_TAU_DAYS = floor, tau
            m = m * np.array([_BS.fresh_weight(rows[f]["created_at"], ts) for f in F])[None, :]
        return m
    return fn


def arm_metrics(res, rows, parents, norm=None):
    from theory_x.stage6_fountain.crystallizer import _fidelity_tokens
    byid = {r["id"]: r for r in rows}
    idx_of = {r["id"]: k for k, r in enumerate(rows)}
    ages = [(r["ts"] - float(byid[r["b"]]["created_at"])) / D for r in res]
    q = st.quantiles(ages, n=10)
    src = Counter(byid[r["b"]]["source"] for r in res)
    anc = ancestors_of(parents)
    same = sum(1 for r in res if r["a"] in anc(r["b"]))
    cross = same_br = nul = 0
    for r in res:
        ba, bb = byid[r["a"]]["branch_id"], byid[r["b"]]["branch_id"]
        if ba is None or bb is None:
            nul += 1
        elif ba == bb:
            same_br += 1
        else:
            cross += 1
    reuse = Counter(r["b"] for r in res)
    # token concentration of the chosen fresh side (maxDF over the chosen texts)
    df = Counter()
    for r in res:
        df.update(set(_fidelity_tokens(byid[r["b"]]["content"] or "")))
    top_tok, top_n = df.most_common(1)[0] if df else ("", 0)
    return {
        "age_med": st.median(ages), "age_p10": q[0], "age_p90": q[-1],
        "lt48h": sum(a < 2 for a in ages) / len(ages), "lt6h": sum(a < 0.25 for a in ages) / len(ages),
        "fountain_share": src.get("fountain_insight", 0) / len(res),
        "same_anchor_desc": same / len(res),
        "cross": cross / len(res), "same_branch": same_br / len(res), "null_branch": nul / len(res),
        "distinct_fresh": len(reuse), "max_reuse": max(reuse.values()),
        "distinct_anchor": len({r["a"] for r in res}),
        "maxdf": top_n / len(res), "maxdf_tok": top_tok,
        "win_rel": st.median(r["score"] for r in res),
        # PURE relatedness of the chosen pair, (cos+1)/2 — the weighted score
        # above includes the arm's own multipliers and is not comparable across arms
        "pure_rel": (st.median((float(norm[idx_of[r["a"]]] @ norm[idx_of[r["b"]]]) + 1) / 2 for r in res)
                     if norm is not None else float("nan")),
    }


def measure(n, cache, grid):
    rows, norm, parents, log = load(cache)
    arms = [("baseline (flag off)", None)] + [(f"floor {f:.2f} tau {t:g}d", _fresh_fn(f, t)) for f, t in grid]
    if os.environ.get("SYNTH_DESC_GRID"):
        arms = [("baseline (flag off)", None)] + [
            (f"desc+{f:.2f}/{t:g}d", _desc_fn(parents, 0.5, f, t))
            for f, t in (tuple(float(x) for x in g.split(":"))
                         for g in os.environ["SYNTH_DESC_GRID"].split(","))]
    if os.environ.get("SYNTH_DESC_ARMS") == "1":
        arms += [("desc x0.5", _desc_fn(parents, 0.5)),
                 ("desc x0.3", _desc_fn(parents, 0.3)),
                 ("desc x0.5 + .85/3d", _desc_fn(parents, 0.5, 0.85, 3.0)),
                 ("desc x0.5 + .90/7d", _desc_fn(parents, 0.5, 0.90, 7.0))]
    hdr = (f"{'arm':22s} {'age med':>8s} {'p10':>5s} {'p90':>6s} {'<48h':>5s} {'<6h':>5s} "
           f"{'fount%':>6s} {'selfdesc':>8s} {'cross':>6s} {'same':>5s} {'null':>5s} "
           f"{'dist.b':>6s} {'maxre':>5s} {'dist.a':>6s} {'maxDF':>6s} {'relat':>6s}")
    print(hdr)
    for name, fn in arms:
        res, _, _ = replay(rows, norm, log, n, score_fn=fn, simulate=True)
        m = arm_metrics(res, rows, parents)
        print(f"{name:22s} {m['age_med']:8.1f} {m['age_p10']:5.1f} {m['age_p90']:6.1f} "
              f"{m['lt48h']:5.0%} {m['lt6h']:5.0%} {m['fountain_share']:6.0%} {m['same_anchor_desc']:8.0%} "
              f"{m['cross']:6.0%} {m['same_branch']:5.0%} {m['null_branch']:5.0%} "
              f"{m['distinct_fresh']:6d} {m['max_reuse']:5d} {m['distinct_anchor']:6d} "
              f"{m['maxdf']:5.0%} {m['win_rel']:6.3f}  top-token '{m['maxdf_tok']}'")


# ── NEX5_BRIDGE: three arms ─────────────────────────────────────────────────

def _bridge_ctxs(rows, log, n):
    """Real BeliefSynergizer._bridge_context as of each pick's ts (read-only)."""
    from substrate import Reader
    syn = _BS(None, Reader(BEL_DB), None)
    is_anchor = [r["source"] in _BS._ANCHOR_SOURCES for r in rows]
    is_fresh = [r["source"] in _BS._FRESH_SOURCES for r in rows]
    out = {}
    for pick in log[-n:]:
        ts = float(pick["ts"])
        anchors = [r for r, a in zip(rows, is_anchor) if a and float(r["created_at"] or 0) <= ts]
        fresh = [r for r, f in zip(rows, is_fresh) if f and float(r["created_at"] or 0) < ts]
        try:
            out[ts] = syn._bridge_context(anchors, fresh, ts)
        except Exception as e:
            print("ctx error", e); out[ts] = None
    return out


def _bridge_fn(ctxs, gain, desc_parents):
    """SYNTH_FRESH (0.85/3d + desc x0.5) x BRIDGE matrix, mirroring bridge_factor."""
    base = _desc_fn(desc_parents, _BS._DESC_PENALTY, 0.85, 3.0)
    def fn(rows, F, ts, A):
        m = base(rows, F, ts, A)
        ctx = ctxs.get(ts)
        if not ctx:
            return m
        factor = 1.0 + gain * (ctx["factor"] - 1.0) / _BS._BRIDGE_GAIN   # rescale to this arm's gain
        fid = [rows[f]["id"] for f in F]
        elig = np.array([i in ctx["eligible"] for i in fid])
        fbr = [ctx["eligible"].get(i) for i in fid]
        for i, a in enumerate(A):
            aid = rows[a]["id"]
            reg = ctx["region"].get(aid, set())
            linked = set(reg)
            for r_ in reg:
                linked |= ctx["syn"].get(r_, set())
            abr = ctx["anchor_branch"].get(aid)
            row = np.where(elig & np.array([b != abr for b in fbr])
                           & np.array([f not in linked for f in fid]), factor, 1.0)
            m[i] = m[i] * row
        return m
    return fn


def measure_bridge(n, cache, gains):
    rows, norm, parents, log = load(cache)
    ctxs = _bridge_ctxs(rows, log, n)
    live = [c for c in ctxs.values() if c]
    print(f"bridge context available at {len(live)}/{len(ctxs)} picks; median active branches "
          f"{st.median(len(c['active']) for c in live) if live else 0}, median eligible fresh "
          f"{st.median(len(c['eligible']) for c in live) if live else 0}, median drive "
          f"{st.median(c['drive'] for c in live) if live else 0:.3f}, median factor "
          f"{st.median(c['factor'] for c in live) if live else 0:.3f}, median groove tokens "
          f"{st.median(len(c['groove']) for c in live) if live else 0}")
    # spot-check: harness matrix == real bridge_factor
    ts0 = next((t for t, c in ctxs.items() if c), None)
    if ts0 is not None:
        ctx = ctxs[ts0]
        A = [k for k, r in enumerate(rows) if r["source"] in _BS._ANCHOR_SOURCES and float(r["created_at"] or 0) <= ts0]
        F = [k for k, r in enumerate(rows) if r["source"] in _BS._FRESH_SOURCES and float(r["created_at"] or 0) < ts0]
        base = _desc_fn(parents, _BS._DESC_PENALTY, 0.85, 3.0)(rows, np.array(F), ts0, np.array(A))
        m = _bridge_fn(ctxs, _BS._BRIDGE_GAIN, parents)(rows, np.array(F), ts0, np.array(A)) / base
        import random as _r
        rnd = _r.Random(3); bad = 0
        for _ in range(3000):
            i, j = rnd.randrange(len(A)), rnd.randrange(len(F))
            bad += abs(m[i, j] - _BS.bridge_factor(ctx, rows[A[i]]["id"], rows[F[j]]["id"])) > 1e-9
        print(f"spot-check harness matrix vs real bridge_factor: {3000 - bad}/3000 agree")
        assert bad == 0

    byid = {r["id"]: r for r in rows}
    arms = [("A baseline", None), ("B SYNTH_FRESH", _desc_fn(parents, _BS._DESC_PENALTY, 0.85, 3.0))]
    arms += [(f"C +BRIDGE g={g:.2f}", _bridge_fn(ctxs, g, parents)) for g in gains]
    print(f"\n{'arm':20s} {'cross':>6s} {'active':>6s} {'bridge':>6s} {'fount%':>6s} {'selfdesc':>8s} "
          f"{'age med':>7s} {'<6h':>5s} {'dist.b':>6s} {'maxre':>5s} {'dist.a':>6s} {'maxDF':>6s} {'pure_rel':>8s}")
    for name, fn in arms:
        res, _, _ = replay(rows, norm, log, n, score_fn=fn, simulate=True)
        m = arm_metrics(res, rows, parents, norm)
        act = [ctxs.get(r["ts"]) for r in res]
        active_share = st.mean(1.0 if c and byid[r["b"]]["branch_id"] in c["active"] else 0.0
                               for r, c in zip(res, act))
        bridged = st.mean(1.0 if c and _BS.bridge_factor(c, r["a"], r["b"]) > 1.0 else 0.0
                          for r, c in zip(res, act))
        print(f"{name:20s} {m['cross']:6.0%} {active_share:6.0%} {bridged:6.0%} {m['fountain_share']:6.0%} "
              f"{m['same_anchor_desc']:8.0%} {m['age_med']:7.1f} {m['lt6h']:5.0%} {m['distinct_fresh']:6d} "
              f"{m['max_reuse']:5d} {m['distinct_anchor']:6d} {m['maxdf']:5.0%} {m['pure_rel']:6.3f}"
              f"  top-token '{m['maxdf_tok']}'")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--investigate", action="store_true")
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--cache", default="/tmp/synth_fresh_vecs.npz")
    ap.add_argument("--measure", action="store_true")
    ap.add_argument("--bridge", action="store_true", help="3-arm NEX5_BRIDGE measurement")
    ap.add_argument("--gains", default="0.05,0.10,0.20")
    ap.add_argument("--grid", default="0.9:3,0.85:3,0.8:1,0.8:3,0.8:7,0.7:3",
                    help="floor:tau_days,... for NEX5_SYNTH_FRESH arms")
    a = ap.parse_args()
    if a.investigate:
        investigate(a.n, a.cache)
    if a.bridge:
        measure_bridge(a.n, a.cache, [float(g) for g in a.gains.split(",")])
    if a.measure:
        grid = [tuple(float(x) for x in g.split(":")) for g in a.grid.split(",")]
        measure(a.n, a.cache, grid)
