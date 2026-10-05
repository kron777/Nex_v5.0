#!/usr/bin/env python3
"""NEX5_CONVICTION_ORDER harness — conviction as SELECTION (ordering), measured
by UPTAKE: which retrieved beliefs her reply sentences actually draw on.

Replays a conviction_harness run (same 21 turns, same stored flat prompts, same
stored support split, seeds 1000*sid+k), so only the belief ORDER changes:
  A  current retrieval order (today)
  S  support order, highest first  (what NEX5_CONVICTION_ORDER does)
  R  random order, re-drawn per sample (position/support decorrelated)
  V  reverse support order, lowest first (position control)

Position bias is the confound: if she simply takes whatever comes first, S
shifts uptake toward high support and V toward low support by the same amount.
The belief-level regression  drawn ~ position + support, pooled over S/R/V
(where the design decorrelates the two), separates them.

READ-ONLY w.r.t. NEX: voice via VoiceClient.speak (ollama HTTP); nothing through
/api/chat; no DB writes.

  --measure --replay RUN.jsonl [--samples 6] [--out ORDER.jsonl]
  --report ORDER.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import random
import statistics as st
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import conviction_harness as h  # noqa: E402
from theory_x.stage_affect import conviction as cv  # noqa: E402

ARMS = ("A", "S", "R", "V")


def arm_prompt(flat_prompt, supports, arm, rng):
    """(prompt, order) — order[p] = index into the stored contents of the belief
    shown at position p."""
    n = len(supports)
    if arm == "A":
        return flat_prompt, list(range(n))
    if arm == "S":
        keys = supports
    elif arm == "V":
        keys = [-x for x in supports]
    else:
        keys = [rng.random() for _ in range(n)]
    order = sorted(range(n), key=lambda k: keys[k], reverse=True)   # stable
    out = cv.order_by_support(flat_prompt, supports=keys)
    if out == flat_prompt and order != list(range(n)):
        raise RuntimeError("order_by_support fell back to flat — lines/supports misaligned")
    return out, order


def measure(replay, n_samples, out_path):
    import requests
    from voice.llm import VoiceClient, VoiceRequest, _SAMPLING
    turns = h._replayed(replay)
    state = {"seed": None}

    def req_fn(url, payload):
        r = requests.post(url, json={**payload, **_SAMPLING, "seed": state["seed"]},
                          timeout=300)
        r.raise_for_status()
        return r.json()
    vc = VoiceClient(request_fn=req_fn)
    print(f"model {vc.model}; {len(turns)} turns x {len(ARMS)} arms x {n_samples}", flush=True)
    with open(out_path, "w") as fh:
        for t in turns:
            meta = {k: t[k] for k in ("sid", "turn", "contents", "support", "held")}
            meta["model"] = vc.model
            fh.write(json.dumps({"kind": "turn", **meta}) + "\n")
            for k in range(n_samples):
                seed = 1000 * t["sid"] + k
                rng = random.Random(seed)
                for arm in ARMS:
                    prompt, order = arm_prompt(t["prompts"]["A"], t["support"], arm, rng)
                    state["seed"] = seed
                    t0 = time.time()
                    try:
                        text = vc.speak(VoiceRequest(prompt=prompt)).text
                    except Exception as e:
                        text = f"__ERROR__ {e}"
                    fh.write(json.dumps({"kind": "reply", "sid": t["sid"], "arm": arm,
                                         "sample": k, "seed": seed, "order": order,
                                         "text": text,
                                         "secs": round(time.time() - t0, 1)}) + "\n")
                    fh.flush()
            print(f"  sid {t['sid']} done", flush=True)


# ── scoring ──────────────────────────────────────────────────────────────────

def _rank01(vals):
    """Within-turn rank normalised to [0,1] (0 = lowest). Ties averaged."""
    n = len(vals)
    o = sorted(range(n), key=lambda i: vals[i])
    r = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and vals[o[j + 1]] == vals[o[i]]:
            j += 1
        for q in range(i, j + 1):
            r[o[q]] = ((i + j) / 2) / (n - 1) if n > 1 else 0.5
        i = j + 1
    return r


def _anchors(text, btoks, qtoks=None, thr=3):
    """Per sentence, the best-matching belief index if it shares >= thr content
    words (question words removed first when qtoks given), else None."""
    out = []
    for s in h.sentences(text):
        st_ = h.toks(s) - (qtoks or set())
        ov = [len(st_ & b) for b in btoks]
        j = max(range(len(ov)), key=lambda i: ov[i])
        out.append(j if ov[j] >= thr else None)
    return out


def _ols2(rows):
    """drawn ~ 1 + pos + sup by least squares (2 regressors, closed form)."""
    n = len(rows)
    mx1 = st.mean(r[0] for r in rows); mx2 = st.mean(r[1] for r in rows)
    my = st.mean(r[2] for r in rows)
    s11 = sum((r[0] - mx1) ** 2 for r in rows); s22 = sum((r[1] - mx2) ** 2 for r in rows)
    s12 = sum((r[0] - mx1) * (r[1] - mx2) for r in rows)
    s1y = sum((r[0] - mx1) * (r[2] - my) for r in rows)
    s2y = sum((r[1] - mx2) * (r[2] - my) for r in rows)
    det = s11 * s22 - s12 * s12
    if n < 3 or det == 0:
        return float("nan"), float("nan")
    return (s22 * s1y - s12 * s2y) / det, (s11 * s2y - s12 * s1y) / det


def _boot(fn, groups, n=2000, seed=11):
    rnd = random.Random(seed)
    keys = list(groups)
    vals = []
    for _ in range(n):
        pick = [rnd.choice(keys) for _ in keys]
        v = fn([x for k in pick for x in groups[k]])
        if v == v:
            vals.append(v)
    vals.sort()
    return vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals))]


def report(path, strip_question=False):
    turns, replies = {}, []
    for ln in open(path):
        d = json.loads(ln)
        (turns.__setitem__(d["sid"], d) if d["kind"] == "turn" else replies.append(d))
    errs = sum(r["text"].startswith("__ERROR__") for r in replies)
    replies = [r for r in replies if not r["text"].startswith("__ERROR__")]
    model = next(iter(turns.values())).get("model", "?")
    print(f"{model}: {len(turns)} turns, {len(replies)} replies ({errs} errors)"
          + ("   [question words stripped before anchoring]" if strip_question else ""))
    srank = {sid: _rank01(t["support"]) for sid, t in turns.items()}
    btoks = {sid: [h.toks(c) for c in t["contents"]] for sid, t in turns.items()}
    qtoks = {sid: h.toks(t["turn"]) for sid, t in turns.items()}

    # per-reply records
    sent = {a: {} for a in ARMS}       # arm -> sid -> [(sup_rank, pos01)] per anchored sentence
    pairs = {a: {} for a in ARMS}      # arm -> sid -> [(pos01, sup_rank, drawn)] per belief
    tot = {a: [0, 0] for a in ARMS}
    hedge = {a: [] for a in ARMS}
    for r in replies:
        sid, a = r["sid"], r["arm"]
        n = len(turns[sid]["contents"])
        pos_of = {b: p / (n - 1) for p, b in enumerate(r["order"])}
        anc = _anchors(r["text"], btoks[sid], qtoks[sid] if strip_question else None)
        tot[a][0] += sum(j is not None for j in anc); tot[a][1] += len(anc)
        for j in anc:
            if j is not None:
                sent[a].setdefault(sid, []).append((srank[sid][j], pos_of[j]))
        drawn = {j for j in anc if j is not None}
        for b in range(n):
            pairs[a].setdefault(sid, []).append((pos_of[b], srank[sid][b], 1.0 if b in drawn else 0.0))
        hedge[a].append(100.0 * len(h.HEDGE_RE.findall(r["text"])) / h.words(r["text"]))

    print("\n1) UPTAKE + WHAT SHE DRAWS ON  (per anchored sentence; 0.50 = chance)")
    print("   arm  uptake    support-rank of drawn belief [95%CI]   position of drawn (0=first)")
    for a in ARMS:
        g = sent[a]
        allv = [x for v in g.values() for x in v]
        sr = st.mean(x[0] for x in allv)
        lo, hi = _boot(lambda xs: st.mean(x[0] for x in xs) if xs else float("nan"), g)
        ps = st.mean(x[1] for x in allv)
        print(f"   {a}    {tot[a][0] / tot[a][1]:5.1%}    {sr:.3f} [{lo:.3f},{hi:.3f}]  n={len(allv):3d}"
              f"      {ps:.3f}")

    print("\n2) CONTRASTS on support-rank of drawn beliefs (turn-bootstrap 95% CI)")
    def diff(x, y, sign=1.0):
        def f(pick_sids):
            xs = [v[0] for s in pick_sids for v in sent[x].get(s, [])]
            ys = [v[0] for s in pick_sids for v in sent[y].get(s, [])]
            return (st.mean(xs) - st.mean(ys)) if xs and ys else float("nan")
        return f
    sids = list(turns)
    def boot_sids(f, n=2000, seed=5):
        rnd = random.Random(seed); vals = []
        for _ in range(n):
            v = f([rnd.choice(sids) for _ in sids])
            if v == v:
                vals.append(v)
        vals.sort()
        return f(sids), vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals))]
    for x, y, label in (("S", "A", "S − A   (support order vs today)"),
                        ("S", "V", "S − V   (support vs reverse)"),
                        ("S", "R", "S − R"), ("R", "V", "R − V")):
        m, lo, hi = boot_sids(diff(x, y))
        print(f"   {label:34s} {m:+.3f} [{lo:+.3f},{hi:+.3f}]")
    def asym(pick):
        def mean_arm(a):
            xs = [v[0] for s in pick for v in sent[a].get(s, [])]
            return st.mean(xs) if xs else float("nan")
        return (mean_arm("S") - mean_arm("R")) - (mean_arm("R") - mean_arm("V"))
    m, lo, hi = boot_sids(asym)
    print(f"   {'(S−R) − (R−V)  asymmetry':34s} {m:+.3f} [{lo:+.3f},{hi:+.3f}]"
          "   (0 = pure position)")

    print("\n3) SEPARATE POSITION FROM SUPPORT — belief-level linear probability model")
    print("   drawn ~ position + support-rank, pooled over S/R/V (decorrelated by design)")
    pooled = {}
    for a in ("S", "R", "V"):
        for sid, v in pairs[a].items():
            pooled.setdefault(sid, []).extend(v)
    rows = [x for v in pooled.values() for x in v]
    corr_ps = h.spearman([x[0] for x in rows], [x[1] for x in rows])
    bp, bs = _ols2(rows)
    lo_p, hi_p = _boot(lambda xs: _ols2(xs)[0], pooled)
    lo_s, hi_s = _boot(lambda xs: _ols2(xs)[1], pooled)
    base = st.mean(x[2] for x in rows)
    print(f"   {len(rows)} belief×reply pairs, P(drawn) = {base:.3f}, "
          f"corr(position, support) = {corr_ps:+.2f}")
    print(f"   position (first→last): {bp:+.3f} [{lo_p:+.3f},{hi_p:+.3f}]")
    print(f"   support  (low→high):   {bs:+.3f} [{lo_s:+.3f},{hi_s:+.3f}]")
    a_rows = [x for v in pairs["A"].values() for x in v]
    print(f"   (arm A alone, today's order: corr(position,support) = "
          f"{h.spearman([x[0] for x in a_rows], [x[1] for x in a_rows]):+.2f})")

    print("\n4) SECONDARY — hedges /100 words (turn-level paired where possible)")
    for a in ARMS:
        print(f"   {a}  {st.mean(hedge[a]):.2f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--measure", action="store_true")
    ap.add_argument("--replay", metavar="RUN_JSONL")
    ap.add_argument("--samples", type=int, default=6)
    ap.add_argument("--out", default="/tmp/conviction_order.jsonl")
    ap.add_argument("--report", metavar="ORDER_JSONL")
    ap.add_argument("--strip-question", action="store_true")
    a = ap.parse_args()
    if a.measure:
        measure(a.replay, a.samples, a.out)
        report(a.out)
        report(a.out, strip_question=True)
    if a.report:
        report(a.report, strip_question=a.strip_question)
