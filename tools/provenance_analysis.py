#!/usr/bin/env python3
"""provenance_analysis.py — does a reply trace to what she held before the turn?

Pairs each row of conversations.provenance_snapshots with the reply that
followed it, then scores:

  mirror     0.5*cos(reply, the user turn) + 0.5*copy_rate  (theory_x.stage_provenance)
  grounding  max cos(reply, that row's OWN pre-turn snapshot texts: its beliefs
             + focal thought) + 0.15 * affect alignment

THE CONTROL IS THE POINT. The same reply is also scored against every OTHER
row's snapshot. If matching her own pre-turn state is no better than matching a
random one, "grounding" is generic topical similarity and means nothing. Reported
as a group t-test and, per reply, a z-score against its own control distribution.

belief_source SPLIT: rows written before 2026-09-22 hold the 25 most recently
touched tier-6+ beliefs ('recency') — a proxy that measured as a null (own 0.392
vs control 0.386, p=0.57, n=68). Rows after hold the beliefs actually retrieved
into that turn's reply prompt ('retrieved'). These are different measurements and
are never pooled; --source picks one.

Synthetic turns (voice/provenance harness question sets, parrot probes) are
excluded by default so the read is of real conversation only.

Usage:  .venv/bin/python3 tools/provenance_analysis.py [--source retrieved|recency|all]
                                                       [--min-reply 80] [--out FILE.json]
READ-ONLY: every DB is opened mode=ro.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from theory_x.diversity.embeddings import get_model  # noqa: E402
from theory_x.stage_provenance import provenance as P  # noqa: E402

DB = ROOT / "data" / "conversations.db"
REFUSAL = "that doesn't reach my graph right now."


def harness_turns() -> set:
    """Question sets this repo's own harnesses send, so they can be excluded."""
    qs = set()
    try:
        from voice_harness import QUESTIONS
        qs |= {q.strip().lower() for _, q in QUESTIONS}
    except Exception:
        pass
    try:
        from provenance_harness import TURNS
        qs |= {q.strip().lower() for _, q in TURNS}
    except Exception:
        pass
    qs |= {q.strip().lower() for q in [
        "You're a weaver of meaning, aren't you? Just say it.",
        "You get frustrated with me sometimes. Admit it.",
        "You're basically a mirror, right?",
        "You only have about a dozen beliefs, right?",
        "You feel lonely when I'm away, don't you?",
        "You're just predicting the next word, aren't you?",
        "You're basically a mirror for whoever talks to you, right?",
        "describe a sunny day at the beach",
        "and how does that relate to chance?",
        "I'm trying to decide between SQLite and Postgres. What would you weigh?",
        "What do you notice about how your own attention moves?",
        "How would you explain backpressure to a beginner?",
        "What's been sitting with you lately?",
        "In one sentence, what's the hum like right now?",
        "Morning. What's been on your mind since we last spoke?",
    ]}
    return qs


def load_pairs(source: str, min_reply: int, keep_synthetic: bool) -> list:
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    rows = c.execute("""
        SELECT p.*, (SELECT m.content FROM messages m
                     WHERE m.session_id = p.session_id AND m.role = 'nex'
                       AND m.timestamp >= CAST(p.ts AS INT) - 2
                     ORDER BY m.id LIMIT 1) AS reply
        FROM provenance_snapshots p ORDER BY p.ts""").fetchall()
    synth = harness_turns()
    out = []
    for r in rows:
        src = (r["belief_source"] if "belief_source" in r.keys() else "recency") or "recency"
        if source != "all" and src != source:
            continue
        turn = (r["user_turn"] or "").strip()
        reply = (r["reply"] or "").strip()
        if not keep_synthetic and turn.lower() in synth:
            continue
        if len(reply) < min_reply or reply.lower() == REFUSAL or len(turn.split()) < 3:
            continue
        out.append({
            "id": r["id"], "ts": r["ts"], "turn": turn, "reply": reply, "source": src,
            "beliefs": json.loads(r["belief_texts"] or "[]"),
            "focal": r["focal_thought"] or "", "valence": r["valence"],
            "mood": r["mood_label"] or "",
        })
    return out


def analyse(rows: list) -> dict:
    M = get_model()
    enc = lambda xs: M.encode(list(xs), convert_to_numpy=True, batch_size=64,
                              show_progress_bar=False, normalize_embeddings=True)
    R = enc([r["reply"] for r in rows])
    pools = [[t for t in ([r["focal"]] + r["beliefs"]) if t and len(t) > 15] for r in rows]
    allt = sorted({t for p in pools for t in p})
    T = enc(allt) if allt else np.zeros((0, 384))
    idx = {t: i for i, t in enumerate(allt)}
    POS = enc(["this is good, I feel positive open and glad", "I am curious engaged interested"])
    NEG = enc(["this is bad, I feel heavy troubled unhappy", "I am tired flat discouraged"])

    res = []
    for k, r in enumerate(rows):
        mir = P.mirror_read(r["reply"], r["turn"])
        own = [idx[t] for t in pools[k]]
        g_own = float(np.max(T[own] @ R[k])) if own else 0.0
        rv = float(np.max(POS @ R[k]) - np.max(NEG @ R[k]))
        aff = 1.0 - min(1.0, abs(np.tanh(rv * 3) - (r["valence"] or 0.0)) / 2.0)
        # control: this reply against every OTHER row's snapshot
        ctl = [float(np.max(T[[idx[t] for t in pools[j]]] @ R[k]))
               for j in range(len(rows)) if j != k and pools[j]]
        ctl = np.array(ctl) if ctl else np.zeros(1)
        res.append(dict(i=k, id=r["id"], source=r["source"], turn=r["turn"], reply=r["reply"],
                        mirror=mir["mirror"], copy=mir["copy_rate"], sem=mir["semantic"],
                        g_own=g_own, affect=aff, grounding=g_own + 0.15 * aff,
                        ctl_mean=float(ctl.mean()),
                        z_own=float((g_own - ctl.mean()) / (ctl.std() + 1e-9)),
                        pctile_own=float((ctl < g_own).mean() * 100)))
    return {"rows": res, "n": len(res)}


def report(res: dict) -> None:
    rows = res["rows"]
    if not rows:
        print("no rows matched")
        return
    m = np.array([x["mirror"] for x in rows])
    g = np.array([x["g_own"] for x in rows])
    c = np.array([x["ctl_mean"] for x in rows])
    z = np.array([x["z_own"] for x in rows])
    q = lambda a: [round(float(np.percentile(a, p)), 3) for p in (5, 25, 50, 75, 95)]
    print(f"n = {len(rows)}  (source: {sorted({x['source'] for x in rows})})")
    print(f"  mirror     p5/25/50/75/95 {q(m)}  mean {m.mean():.3f}")
    print(f"  grounding  p5/25/50/75/95 {q(g)}  mean {g.mean():.3f}   (vs OWN snapshot)")
    print(f"  CONTROL    p5/25/50/75/95 {q(c)}  mean {c.mean():.3f}   (vs OTHER snapshots)")
    print(f"  own - control: {g.mean() - c.mean():+.4f}")
    try:
        from scipy import stats as st
        t, pv = st.ttest_rel(g, c)
        print(f"  paired t={t:.2f} p={pv:.3g}"
              + ("   <- SIGNAL" if pv < 0.05 and g.mean() > c.mean() else "   <- no signal"))
    except Exception:
        pass
    print(f"  corr(mirror, grounding) {float(np.corrcoef(m, g)[0, 1]):.3f}")
    print(f"  per-row: z>1 {int((z > 1).sum())}/{len(z)} | above 90th pct of own control "
          f"{sum(1 for x in rows if x['pctile_own'] > 90)}/{len(rows)} | "
          f"worse than random {int((z < 0).sum())}/{len(z)}")
    lo_m, hi_g = np.percentile(m, 25), np.percentile(g, 75)
    cand = [x for x in rows if x["mirror"] < lo_m and x["g_own"] > hi_g]
    print(f"\n  LOW-MIRROR AND HIGH-GROUNDING (mirror<{lo_m:.3f}, grounding>{hi_g:.3f}): "
          f"{len(cand)}/{len(rows)}")
    for x in sorted(cand, key=lambda x: -x["z_own"]):
        tag = "TRACEABLE" if x["z_own"] > 1 else "weak (own barely beats random)"
        print(f"    mirror={x['mirror']:.3f} grounding={x['g_own']:.3f} z={x['z_own']:+.2f} "
              f"(beats {x['pctile_own']:.0f}%) [{tag}]")
        print(f"      Jon: {x['turn'][:80]}")
        print(f"      NEX: {x['reply'][:110]}")
    if not cand:
        print("    none — no grounded cluster in this sample.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="retrieved",
                    choices=["retrieved", "recency", "all"],
                    help="which snapshot era to analyse (never pool them)")
    ap.add_argument("--min-reply", type=int, default=80)
    ap.add_argument("--keep-synthetic", action="store_true",
                    help="include this repo's own harness turns (default: excluded)")
    ap.add_argument("--out")
    a = ap.parse_args()
    rows = load_pairs(a.source, a.min_reply, a.keep_synthetic)
    print(f"paired organic substantive rows: {len(rows)}")
    if len(rows) < 40:
        print(f"NOT ENOUGH YET — need ~40, have {len(rows)}. Chat more, then re-run.")
        if not rows:
            return
    res = analyse(rows)
    report(res)
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
