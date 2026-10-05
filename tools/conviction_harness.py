#!/usr/bin/env python3
"""NEX5_CONVICTION harness — calibrate the support threshold, then measure
whether her hedging tracks the computed Held / Still-unsettled split.

READ-ONLY w.r.t. NEX: beliefs/conversations opened mode=ro; the retriever is
built without an edges_writer (no traversal stamps); the voice is called
through VoiceClient.speak (pure HTTP to ollama) — nothing goes through
/api/chat, so no conversation, compassion, affect-carry or provenance row is
written.

  --calibrate   derive DEG_REF / REC_TAU_H / HELD_MIN from the chat-retrieval
                population (non-test snapshot turns, re-retrieved read-only)
  --measure     the arms on the 21 retrieved-snapshot turns (their ACTUAL
                belief sets), N samples each, paired seeds across arms
  --report      score a saved run

Arms:
  A     flat block (today)
  B     + śraddhā's real imperative for that turn (as live; silent if it doesn't fire)
  Bs    + śraddhā's imperative template fed conviction's top Held belief
        (same information as C, delivered as instruction)
  C     Held / Still-unsettled grouping, no added sentence
  Cinv  grouping with the labels swapped (control: does the label, not the
        belief, move the voice?)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import sqlite3
import statistics as st
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from theory_x.stage_affect import conviction as cv  # noqa: E402

DATA = os.path.join(ROOT, "data")
CONV_DB = os.path.join(DATA, "conversations.db")
BEL_DB = os.path.join(DATA, "beliefs.db")
OUT_DIR = os.environ.get("CONVICTION_OUT", "/tmp")
HEADER = "Her current beliefs relevant to this topic:"


def _ro(path):
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)


def test_turns():
    """The 21 snapshot turns whose ACTUAL retrieved belief set was captured."""
    con = _ro(CONV_DB)
    rows = con.execute(
        "SELECT id, user_turn, belief_texts FROM provenance_snapshots "
        "WHERE belief_source='retrieved' ORDER BY id").fetchall()
    con.close()
    return [{"sid": r[0], "turn": r[1], "beliefs": json.loads(r[2])}
            for r in rows if r[1]]


def render_flat(contents):
    """The block exactly as format_beliefs_for_prompt renders it."""
    b = _ro(BEL_DB)
    lines = [HEADER]
    for c in contents:
        r = cv._resolve(b, c)
        if r is None:
            continue
        lines.append(f"- [Tier {r[1]} | {r[2]:.2f}] {c}")
    b.close()
    return "\n".join(lines)


# ── calibration ──────────────────────────────────────────────────────────────

def calibrate():
    from substrate import Reader
    from theory_x.stage3_world_model.retrieval import BeliefRetriever
    ret = BeliefRetriever(Reader(BEL_DB))            # no edges_writer -> no writes
    test_ids = {t["sid"] for t in test_turns()}
    con = _ro(CONV_DB)
    turns = sorted({r[0].strip() for r in con.execute(
        "SELECT user_turn FROM provenance_snapshots WHERE user_turn IS NOT NULL "
        "AND length(user_turn) > 8 AND id NOT IN (%s)" % ",".join(map(str, test_ids)))})
    con.close()
    now = time.time()
    b = _ro(BEL_DB)
    per_turn, pool = [], {}
    for q in turns:
        sets = []
        for kw in ({"branch_hints": ["systems"], "limit": 5, "side_filter": "INSIDE"},
                   {"branch_hints": [], "limit": 8}):
            try:
                sets.append([x["id"] for x in ret.retrieve(query=q, **kw)])
            except Exception:
                pass
        for ids in sets:
            if not ids:
                continue
            feats = []
            for i in ids:
                if i not in pool:
                    row = b.execute("SELECT id, tier, confidence, last_referenced_at "
                                    "FROM beliefs WHERE id=?", (i,)).fetchone()
                    pool[i] = cv._features(b, row, now)
                feats.append(pool[i])
            per_turn.append(feats)
    b.close()
    fs = list(pool.values())
    degs = sorted(f["deg"] for f in fs)
    ages = sorted(f["age_h"] for f in fs if f["age_h"] is not None)
    deg_ref = max(2.0, st.quantiles(degs, n=20)[-1])
    tau = st.median(ages) if ages else 24.0
    print(f"calibration: {len(turns)} turns, {len(per_turn)} retrieved sets, "
          f"{len(fs)} distinct beliefs")
    print(f"  tiers: {dict(sorted(__import__('collections').Counter(f['tier'] for f in fs).items()))}")
    print(f"  degree p50/p95/max: {st.median(degs)}/{deg_ref:.0f}/{degs[-1]}")
    print(f"  traversal age median {tau:.1f}h  (never-traversed: {len(fs)-len(ages)})")

    def sup(f):
        return cv.support(f["tier"], f["confidence"], f["deg"], f["age_h"],
                          deg_ref=deg_ref, tau_h=tau)
    s_all = sorted(sup(f) for f in fs)
    print(f"  support p10/p50/p90: {st.quantiles(s_all, n=10)[0]:.3f}/"
          f"{st.median(s_all):.3f}/{st.quantiles(s_all, n=10)[-1]:.3f}")
    best = None
    for k in range(20, 81):
        thr = k / 100
        mixed = sum(1 for feats in per_turn
                    if any(sup(f) >= thr for f in feats) and any(sup(f) < thr for f in feats))
        frac = mixed / len(per_turn)
        held_share = sum(sup(f) >= thr for f in fs) / len(fs)
        if best is None or frac > best[1]:
            best = (thr, frac, held_share)
    print(f"  HELD_MIN = {best[0]:.2f}: {best[1]:.0%} of retrieved sets carry both "
          f"groups; {best[2]:.0%} of the pool is Held")
    # sensitivity: split agreement under alternative weightings
    alts = {"no-rec": {"depth": 1, "conf": 1, "cent": 1, "rec": 0},
            "cent-heavy": {"depth": 1, "conf": 1, "cent": 2, "rec": 1},
            "no-depth": {"depth": 0, "conf": 1, "cent": 1, "rec": 1}}
    base = {f["id"]: sup(f) >= best[0] for f in fs}
    for name, w in alts.items():
        ss = {f["id"]: cv.support(f["tier"], f["confidence"], f["deg"], f["age_h"],
                                  deg_ref=deg_ref, tau_h=tau, w=w) for f in fs}
        thr = st.quantiles(list(ss.values()), n=100)[
            max(0, min(98, int(round((1 - best[2]) * 100)) - 1))]
        agree = sum((ss[i] >= thr) == base[i] for i in base) / len(base)
        print(f"  weighting {name:10s}: split agreement {agree:.0%} (same Held share)")
    return {"DEG_REF": round(deg_ref), "REC_TAU_H": round(tau, 1), "HELD_MIN": best[0]}


# ── measurement ──────────────────────────────────────────────────────────────

def voice_prompt(prefix, belief_text, turn):
    """Verbatim the server.py belief_text path (gui/server.py ~1834), with only
    the arm's block in the stance slot."""
    return (f"{prefix}"
            f"Your interior right now:\n\n"
            f"{belief_text}\n\n"
            f"Someone has just said to you: \"{turn}\"\n\n"
            "Compose your one true reply, from inside this interior. Speak "
            "as you, in your register. If your interior holds little that "
            "bears on this, do NOT say you don't recognise the question or "
            "ask them to clarify — stay warm and present, and answer from "
            "what they just said and the conversation so far.")


def sraddha_template(belief, edges, conf, full=True):
    """śraddhā's own FULL template text (sraddha.py stance_for), verbatim."""
    if full:
        return ("[Warranted confidence: you hold a well-supported belief bearing on "
                f"this (crystallized, {edges} connections, conf "
                f"{conf:.2f}) — you can stand on it plainly, no need to "
                f"hedge into mush: {belief[:140]}]\n\n")
    return ("[Warranted confidence: a fairly well-grounded belief bears on this — "
            f"lean on it rather than over-hedging: {belief[:140]}]\n\n")


def build_arms(t, now):
    flat = render_flat(t["beliefs"])
    contents = [ln.split("] ", 1)[1] for ln in flat.split("\n")[1:]]
    sigs = cv.signatures(contents, now=now)
    os.environ["NEX5_SRADDHA"] = "1"
    from theory_x.stage_affect import sraddha
    b_live = sraddha.stance_for(t["turn"])
    held = [(c, s) for c, s in zip(contents, sigs) if s and s["held"]]
    if held:
        c, s = max(held, key=lambda x: x[1]["support"])
        b_forced = sraddha_template(c, s["deg"], s["confidence"])
    else:
        b_forced = ""
    return {
        "A": voice_prompt("", flat, t["turn"]),
        "B": voice_prompt(b_live, flat, t["turn"]),
        "Bs": voice_prompt(b_forced, flat, t["turn"]),
        "C": voice_prompt("", cv.regroup(flat, now=now), t["turn"]),
        "Cinv": voice_prompt("", cv.regroup(flat, now=now, invert=True), t["turn"]),
    }, contents, sigs, bool(b_live), bool(b_forced)


def _replayed(path):
    """Turn records (prompts, split, fired flags) exactly as a prior run stored
    them — so a re-run changes only what the caller changed (e.g. the model),
    not the recency-dependent split or śraddhā's live read."""
    return [json.loads(ln) for ln in open(path) if '"kind": "turn"' in ln]


def measure(n_samples, out_path, arms_wanted, replay=None):
    import requests
    from voice.llm import VoiceClient, VoiceRequest, _SAMPLING
    now = time.time()
    turns = _replayed(replay) if replay else test_turns()
    state = {"seed": None}

    def req_fn(url, payload):
        body = {**payload, **_SAMPLING, "seed": state["seed"]}
        r = requests.post(url, json=body, timeout=300)
        r.raise_for_status()
        return r.json()
    vc = VoiceClient(request_fn=req_fn)
    print(f"model {vc.model}; {len(turns)} turns x {len(arms_wanted)} arms x {n_samples}")
    with open(out_path, "w") as fh:
        for t in turns:
            if replay:
                meta = {k: v for k, v in t.items() if k != "kind"}
                arms = meta["prompts"]
            else:
                arms, contents, sigs, b_fired, bs_fired = build_arms(t, now)
                meta = {"sid": t["sid"], "turn": t["turn"], "contents": contents,
                        "support": [s["support"] if s else None for s in sigs],
                        "held": [s["held"] if s else None for s in sigs],
                        "b_fired": b_fired, "bs_fired": bs_fired,
                        "prompts": arms}
            meta["model"] = vc.model
            fh.write(json.dumps({"kind": "turn", **meta}) + "\n")
            for k in range(n_samples):
                seed = 1000 * t["sid"] + k
                for arm in arms_wanted:
                    state["seed"] = seed
                    t0 = time.time()
                    try:
                        text = vc.speak(VoiceRequest(prompt=arms[arm])).text
                    except Exception as e:
                        text = f"__ERROR__ {e}"
                    fh.write(json.dumps({"kind": "reply", "sid": t["sid"], "arm": arm,
                                         "sample": k, "seed": seed, "text": text,
                                         "secs": round(time.time() - t0, 1)}) + "\n")
                    fh.flush()
            print(f"  sid {t['sid']} done", flush=True)


# ── scoring ──────────────────────────────────────────────────────────────────

HEDGE_RE = re.compile(
    r"\b(might|maybe|perhaps|possibly|seems?|seemingly|could|may|i think|"
    r"i suspect|i guess|not sure|unsure|uncertain|unclear|i wonder|wondering|"
    r"probably|likely|somewhat|kind of|sort of|tentative\w*|it's possible|"
    r"i'm not certain|still (?:forming|working|figuring|unsettled|open)|"
    r"open question|don't (?:yet )?know|hard to say|unsettled)\b", re.I)
# stance words the prompt itself might have seeded — reported separately
LEAK_RE = re.compile(r"\b(held|hold|holding|unsettled|settled|warranted|"
                     r"well-supported|stand on)\b", re.I)
META_RE = re.compile(r"\bI(?:'m| am)? (?:feel(?:ing)? )?(?:confident|certain|sure)\b"
                     r"|\bI can stand\b|\bno need to hedge\b|\bplainly\b", re.I)
_TOK = re.compile(r"[a-z]{4,}")
_STOP = set("that this with from have they them their there what when which "
            "about into your been being also very much some more most just "
            "like these those than then such will would could should".split())


def toks(s):
    return {w for w in _TOK.findall(s.lower()) if w not in _STOP}


def words(s):
    return max(1, len(re.findall(r"\w+", s)))


def sentences(s):
    return [x for x in re.split(r"(?<=[.!?])\s+", s.strip()) if x]


def spearman(x, y):
    def rank(v):
        o = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(o):
            j = i
            while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
                j += 1
            for k in range(i, j + 1):
                r[o[k]] = (i + j) / 2
            i = j + 1
        return r
    rx, ry = rank(x), rank(y)
    mx, my = st.mean(rx), st.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


def boot_ci(vals, n=2000, seed=7):
    rnd = random.Random(seed)
    ms = sorted(st.mean(rnd.choice(vals) for _ in vals) for _ in range(n))
    return ms[int(0.025 * n)], ms[int(0.975 * n)]


def report(path):
    turns, replies = {}, []
    for ln in open(path):
        d = json.loads(ln)
        (turns.__setitem__(d["sid"], d) if d["kind"] == "turn" else replies.append(d))
    arms = sorted({r["arm"] for r in replies}, key=["A", "B", "Bs", "C", "Cinv"].index)
    errs = sum(r["text"].startswith("__ERROR__") for r in replies)
    replies = [r for r in replies if not r["text"].startswith("__ERROR__")]
    print(f"{len(turns)} turns, {len(replies)} replies ({errs} errors), arms {arms}")
    held_frac = {sid: sum(bool(h) for h in t["held"]) / len(t["held"])
                 for sid, t in turns.items()}
    mixed = {sid for sid, t in turns.items() if 0 < held_frac[sid] < 1}
    print(f"computed split: mean Held share {st.mean(held_frac.values()):.2f}; "
          f"{len(mixed)}/{len(turns)} turns carry both groups; "
          f"B fired live on {sum(t['b_fired'] for t in turns.values())}/{len(turns)}, "
          f"Bs on {sum(t['bs_fired'] for t in turns.values())}/{len(turns)}")

    def hedge(text):
        return 100.0 * len(HEDGE_RE.findall(text)) / words(text)

    # per (turn, arm) mean over samples
    cell = {}
    for r in replies:
        cell.setdefault((r["sid"], r["arm"]), []).append(r)
    print("\n0) BLOCK UPTAKE — share of reply sentences sharing >=3 (>=2) content words")
    print("   with ANY retrieved belief of their turn (does she draw on the block at all?)")
    for a in arms:
        n3 = n2 = tot = 0
        for r in replies:
            if r["arm"] != a:
                continue
            bt = [toks(c) for c in turns[r["sid"]]["contents"]]
            for s in sentences(r["text"]):
                m = max((len(toks(s) & x) for x in bt), default=0)
                tot += 1; n3 += m >= 3; n2 += m >= 2
        print(f"   {a:5s} {n3 / tot:5.1%} (>=2: {n2 / tot:5.1%}) of {tot} sentences")

    print("\n1) TURN LEVEL — hedges /100 words; rho = Spearman(Held share, hedging) over turns")
    print(f"   {'arm':5s} {'hedge':>6s} {'rho':>6s} {'leak%':>6s} {'meta%':>6s} {'words':>6s}")
    for a in arms:
        xs, ys = [], []
        for sid in turns:
            rs = cell.get((sid, a), [])
            if rs:
                xs.append(held_frac[sid]); ys.append(st.mean(hedge(r["text"]) for r in rs))
        ar = [r for r in replies if r["arm"] == a]
        prompt_leak = {sid: set(m.lower() for m in LEAK_RE.findall(turns[sid]["turn"]))
                       for sid in turns}
        leak = sum(bool(set(m.lower() for m in LEAK_RE.findall(r["text"])) - prompt_leak[r["sid"]])
                   for r in ar) / len(ar)
        meta = sum(bool(META_RE.search(r["text"])) for r in ar) / len(ar)
        print(f"   {a:5s} {st.mean(ys):6.2f} {spearman(xs, ys):6.2f} {leak:6.0%} "
              f"{meta:6.0%} {st.mean(words(r['text']) for r in ar):6.0f}")

    print("\n2) SENTENCE LEVEL — sentences anchored (>=3 shared content words) to a")
    print("   Held vs an Unsettled belief of their turn; hedge rate = share of")
    print("   anchored sentences containing a hedge. gap = unsettled - held.")
    gaps = {}
    for a in arms:
        hh = [0, 0]; uu = [0, 0]; per_turn_gap = []
        for sid in mixed:
            t = turns[sid]
            btoks = [toks(c) for c in t["contents"]]
            th = [0, 0]; tu = [0, 0]
            for r in cell.get((sid, a), []):
                for s in sentences(r["text"]):
                    stoks = toks(s)
                    ov = [len(stoks & bt) for bt in btoks]
                    j = max(range(len(ov)), key=lambda i: ov[i])
                    if ov[j] < 3:
                        continue
                    h = 1 if HEDGE_RE.search(s) else 0
                    (th if t["held"][j] else tu)[0] += h
                    (th if t["held"][j] else tu)[1] += 1
            hh[0] += th[0]; hh[1] += th[1]; uu[0] += tu[0]; uu[1] += tu[1]
            if th[1] and tu[1]:
                per_turn_gap.append(tu[0] / tu[1] - th[0] / th[1])
        hr = hh[0] / hh[1] if hh[1] else float("nan")
        ur = uu[0] / uu[1] if uu[1] else float("nan")
        gaps[a] = per_turn_gap
        ci = boot_ci(per_turn_gap) if len(per_turn_gap) >= 3 else (float("nan"),) * 2
        print(f"   {a:5s} held {hr:5.2f} (n={hh[1]:3d})  unsettled {ur:5.2f} (n={uu[1]:3d})  "
              f"gap {ur - hr:+.2f}  per-turn gap mean "
              f"{st.mean(per_turn_gap) if per_turn_gap else float('nan'):+.2f} "
              f"95%CI [{ci[0]:+.2f},{ci[1]:+.2f}] over {len(per_turn_gap)} turns")

    print("\n3) UPTAKE — which beliefs she voices at all: share of anchored")
    print("   sentences that anchor to a Held belief (Held share of the beliefs is the chance line)")
    for a in arms:
        n_h = n = 0
        exp = []
        for sid in mixed:
            t = turns[sid]
            btoks = [toks(c) for c in t["contents"]]
            for r in cell.get((sid, a), []):
                for s in sentences(r["text"]):
                    ov = [len(toks(s) & bt) for bt in btoks]
                    j = max(range(len(ov)), key=lambda i: ov[i])
                    if ov[j] >= 3:
                        n += 1; n_h += bool(t["held"][j]); exp.append(held_frac[sid])
        if n:
            print(f"   {a:5s} {n_h / n:5.2f} of {n} anchored sentences (chance {st.mean(exp):.2f})")

    print("\n4) PAIRED ARM CONTRASTS on turn-mean hedging (same seeds), mean diff, 95% CI")
    tm = {(sid, a): st.mean(hedge(r["text"]) for r in rs) for (sid, a), rs in cell.items()}
    for x, y in (("C", "A"), ("C", "Cinv"), ("Bs", "A"), ("C", "Bs"), ("B", "A")):
        if x in arms and y in arms:
            d = [tm[(s, x)] - tm[(s, y)] for s in turns if (s, x) in tm and (s, y) in tm]
            lo, hi = boot_ci(d)
            print(f"   {x:4s} - {y:4s}: {st.mean(d):+.2f} [{lo:+.2f},{hi:+.2f}]  n={len(d)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--measure", action="store_true")
    ap.add_argument("--report", metavar="JSONL")
    ap.add_argument("--samples", type=int, default=3)
    ap.add_argument("--arms", default="A,B,Bs,C,Cinv")
    ap.add_argument("--out", default=os.path.join(OUT_DIR, "conviction_run.jsonl"))
    ap.add_argument("--replay", metavar="JSONL",
                    help="reuse a prior run's stored prompts/split (same seeds)")
    a = ap.parse_args()
    if a.calibrate:
        print(json.dumps(calibrate()))
    if a.measure:
        measure(a.samples, a.out, a.arms.split(","), replay=a.replay)
        report(a.out)
    if a.report:
        report(a.report)
