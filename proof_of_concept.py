#!/usr/bin/env python3
"""Proof of concept — mathematical validation of TRACK_THEORY predictions.

Run: .venv/bin/python3 proof_of_concept.py

Reads from beliefs.db, dynamic.db, conversations.db (read-only).
Writes JSON + markdown report to reports/.

Implements the contract specified in PROOF_OF_CONCEPT.md.
"""
from __future__ import annotations

import json
import math
import re
import sqlite3
import statistics
import time
from pathlib import Path
from typing import Optional
import sys
sys.path.insert(0, str(Path(__file__).parent))
from theory_x.genius.score_v2 import (
    compute_features as compute_v2_features,
    load_t6_beliefs as load_t6_v2,
)
import json

DATA_DIR = Path("/home/rr/Desktop/Desktop/nex5/data")
REPORTS_DIR = Path("/home/rr/Desktop/Desktop/nex5/reports")
REPORTS_DIR.mkdir(exist_ok=True)

SELF_REF_TOKENS = {
    "i", "me", "my", "mine", "myself",
    "attending", "noticing", "wondering", "holding", "receiving",
}
PHENOM_TOKENS = {
    "quiet", "silence", "attending", "presence", "arising", "given",
    "receiving", "form", "trust", "absence", "dissolution", "chance",
    "awareness", "stillness", "rhythm", "between", "beneath", "still",
    "holds", "ringing", "trace",
}
INTEGRATION_TOKENS = {
    "both", "and", "tension", "paradox", "yet", "however",
    "between", "neither", "either",
}
REFLECTIVE_MARKERS = [
    "what if", "i notice", "i am", "i find", "i sense", "i wonder",
    "i return", "perhaps", "between", "even if", "until then",
]


def tokenize(text):
    return re.findall(r"[a-z']+", (text or "").lower())


def fourgrams(tokens):
    return {tuple(tokens[i:i+4]) for i in range(len(tokens) - 3)}


def jaccard(a, b):
    if not a and not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def percentile(values, p):
    if not values:
        return 1.0
    s = sorted(values)
    k = int(len(s) * p)
    return s[min(k, len(s) - 1)] or 1.0


def load_fountain_fires(hours=168):
    cutoff = time.time() - hours * 3600
    with sqlite3.connect(f"file:{DATA_DIR / 'dynamic.db'}?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, ts, hot_branch, thought, anchor_belief_id "
            "FROM fountain_events WHERE ts > ? ORDER BY ts ASC", (cutoff,)).fetchall()
    return [dict(r) for r in rows]


def load_drive_activations(hours=168):
    cutoff = time.time() - hours * 3600
    with sqlite3.connect(f"file:{DATA_DIR / 'conversations.db'}?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM drive_activations WHERE timestamp > ? ORDER BY timestamp ASC",
            (cutoff,)).fetchall()
    return [dict(r) for r in rows]


def load_substrate_coherence():
    with sqlite3.connect(f"file:{DATA_DIR / 'conversations.db'}?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM substrate_coherence ORDER BY ts ASC").fetchall()
    return [dict(r) for r in rows]


def load_t6_beliefs():
    cutoff = time.time() - 168 * 3600
    with sqlite3.connect(f"file:{DATA_DIR / 'beliefs.db'}?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, content, tier, created_at FROM beliefs "
            "WHERE tier = 6 AND created_at > ?", (cutoff,)).fetchall()
    return [dict(r) for r in rows]


def compute_normalization(fires):
    self_rates, phenom_rates, refl_rates = [], [], []
    for f in fires:
        tokens = tokenize(f["thought"])
        total = max(1, len(tokens))
        self_rates.append(sum(1 for t in tokens if t in SELF_REF_TOKENS) / total)
        phenom_rates.append(sum(1 for t in tokens if t in PHENOM_TOKENS) / total)
        cl = (f["thought"] or "").lower()
        refl_rates.append(sum(cl.count(m) for m in REFLECTIVE_MARKERS) / total)
    return {
        "self_p95": max(0.001, percentile(self_rates, 0.95)),
        "phenom_p95": max(0.001, percentile(phenom_rates, 0.95)),
        "reflective_p95": max(0.001, percentile(refl_rates, 0.95)),
    }


def _load_v2_weights():
    """Load v2 weights once; cache."""
    if not hasattr(_load_v2_weights, '_cache'):
        wp = Path('/home/rr/Desktop/Desktop/nex5/genius_score_weights.json')
        _load_v2_weights._cache = json.loads(wp.read_text())
    return _load_v2_weights._cache


def _sigmoid(z):
    import math
    if z >= 0:
        return 1 / (1 + math.exp(-z))
    return math.exp(z) / (1 + math.exp(z))


def compute_genius_score(fire, recent_fires, t6_beliefs, norms):
    """v2 score: logistic regression over 5 features, calibrated against
    Jon's 103-row training set."""
    weights_data = _load_v2_weights()
    w = weights_data['weights']
    b = weights_data['bias']
    threshold = weights_data['threshold']

    # v2 features need prior_thoughts as list[str] (not list[dict])
    prior_thoughts = [r["thought"] for r in recent_fires]
    feats = compute_v2_features(fire, prior_thoughts, t6_beliefs)
    z = sum(w[j] * feats[j] for j in range(len(w))) + b
    score = _sigmoid(z)

    if score >= threshold + 0.20:
        cls = "genius"
    elif score >= threshold:
        cls = "moment"
    else:
        cls = "ordinary"

    return {
        "score": round(score, 3),
        "class": cls,
        "features": {
            "length_struct": round(feats[0], 3),
            "anti_template": round(feats[1], 3),
            "t6_promotion": round(feats[2], 3),
            "self_witness": round(feats[3], 3),
            "unprompted": round(feats[4], 3),
        },
    }



def cognition_at(t, drives):
    relevant = [d for d in drives if d["timestamp"] <= t]
    if not relevant:
        return None
    d = relevant[-1]
    tension = 0.0
    if d.get("active_conflicts"):
        ac = str(d["active_conflicts"]).strip()
        if ac and ac not in ("[]", "null", "None"):
            tension = 1.0
    return {
        "coherence": float(d.get("coherence_weight", 0.5)),
        "exploration": float(d.get("exploration_weight", 0.5)),
        "integration": float(d.get("integration_weight", 0.5)),
        "self_preservation": float(d.get("self_preservation_weight", 0.5)),
        "curiosity": float(d.get("curiosity_weight", 0.5)),
        "tension_active": tension,
    }


def aperture_from_cognition(cog):
    ec = cog["exploration"] - cog["coherence"]
    if ec > 0.2:
        return min(1.0, 0.8 + ec * 0.2)
    if ec < -0.2:
        return max(0.1, 0.2 - abs(ec) * 0.2)
    return 0.5


def compute_voltage_simple(t, fires):
    window = [f for f in fires if t - 300 <= f["ts"] <= t]
    branches = {f["hot_branch"] for f in window}
    cross_domain = len(branches) / 10.0
    activity = len(window) / 30.0
    return min(1.0, 0.5 * activity + 0.5 * cross_domain)


def pearson_r(xs, ys):
    n = len(xs)
    if n < 3:
        return (0.0, 1.0)
    mx, my = statistics.mean(xs), statistics.mean(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return (0.0, 1.0)
    r = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)
    if abs(r) >= 0.9999:
        return (r, 0.0)
    t_stat = r * math.sqrt(n - 2) / math.sqrt(1 - r * r)
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(t_stat) / math.sqrt(2))))
    return (r, p)


def welch_t_test(xs, ys):
    nx, ny = len(xs), len(ys)
    if nx < 2 or ny < 2:
        return (0.0, 1.0)
    mx, my = statistics.mean(xs), statistics.mean(ys)
    vx = statistics.variance(xs) if nx > 1 else 0.0
    vy = statistics.variance(ys) if ny > 1 else 0.0
    se = math.sqrt(vx / nx + vy / ny)
    if se == 0:
        return (0.0, 1.0)
    t = (mx - my) / se
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(t) / math.sqrt(2))))
    return (t, p)


def test_p2(fires, drives):
    int_vocab, tensions = [], []
    for f in fires:
        tokens = tokenize(f["thought"])
        total = max(1, len(tokens))
        int_count = sum(1 for t in tokens if t in INTEGRATION_TOKENS)
        cog = cognition_at(f["ts"], drives)
        if cog is None:
            continue
        int_vocab.append(int_count / total)
        tensions.append(cog["tension_active"])
    n_t = int(sum(tensions))
    if n_t < 30:
        return {"verdict": "inconclusive", "reason": f"only {n_t} fires with tension; need ≥ 30"}
    r, p = pearson_r(int_vocab, tensions)
    if r >= 0.15 and p < 0.01:
        v = "pass"
    elif r >= 0.05 and p < 0.05:
        v = "weak_pass"
    else:
        v = "fail"
    return {"verdict": v, "r": round(r, 4), "p_value": round(p, 4),
            "n_with_tension": n_t, "n_without": len(int_vocab) - n_t}


def test_p3(fires, scored):
    sv = [f for f in fires if f["hot_branch"] == "substrate_voice"]
    if len(sv) < 6:
        return {"verdict": "inconclusive", "reason": f"only {len(sv)} SV fires; need ≥ 6"}
    walks = []
    if sv:
        start, last = sv[0]["ts"], sv[0]["ts"]
        for f in sv[1:]:
            if f["ts"] - last <= 5400:
                last = f["ts"]
            else:
                if last - start >= 1800:
                    walks.append((start, last))
                start, last = f["ts"], f["ts"]
        if last - start >= 1800:
            walks.append((start, last))
    if len(walks) < 2:
        return {"verdict": "inconclusive", "reason": f"only {len(walks)} walks; need ≥ 2"}
    during, post, base = [], [], []
    for sf in scored:
        ts = sf["ts"]
        cat = "base"
        for ws, we in walks:
            if ws <= ts <= we:
                cat = "during"
                break
            if we < ts <= we + 21600:
                cat = "post"
        target = {"during": during, "post": post, "base": base}[cat]
        target.append(sf["genius"]["score"])
    if len(post) < 10 or len(base) < 10:
        return {"verdict": "inconclusive", "reason": f"post={len(post)} base={len(base)}"}
    md = statistics.mean(during) if during else 0
    mp = statistics.mean(post)
    mb = statistics.mean(base)
    t_stat, p_val = welch_t_test(post, base)
    if mp > mb + 0.05 and mp > md and p_val < 0.05:
        v = "pass"
    elif mp > mb + 0.05 or mp > md:
        v = "partial_pass"
    else:
        v = "fail"
    return {"verdict": v, "mean_during": round(md, 3), "mean_post": round(mp, 3),
            "mean_base": round(mb, 3), "p_value": round(p_val, 4),
            "walks": len(walks), "n_during": len(during),
            "n_post": len(post), "n_base": len(base)}


def test_p4(coherence_rows, fires):
    if len(coherence_rows) < 50:
        return {"verdict": "inconclusive", "reason": f"only {len(coherence_rows)} ticks; need ≥ 50"}
    coh, volt = [], []
    for r in coherence_rows:
        coh.append(float(r["total"]))
        volt.append(compute_voltage_simple(r["ts"], fires))
    r, p = pearson_r(coh, volt)
    ar = abs(r)
    if ar < 0.3:
        v = "strong_pass"
    elif ar < 0.5:
        v = "pass"
    elif ar < 0.7:
        v = "weak_pass"
    else:
        v = "fail"
    return {"verdict": v, "r": round(r, 4), "p_value": round(p, 4),
            "n_ticks": len(coh), "mean_coherence": round(statistics.mean(coh), 3),
            "mean_voltage": round(statistics.mean(volt), 3)}


def test_p5(scored, drives):
    if len(scored) < 100:
        return {"verdict": "inconclusive", "reason": f"only {len(scored)} fires; need ≥ 100"}
    aps, divs = [], []
    for sf in scored:
        cog = cognition_at(sf["ts"], drives)
        if cog is None:
            continue
        tokens = tokenize(sf["thought"])
        if len(tokens) < 5:
            continue
        aps.append(aperture_from_cognition(cog))
        divs.append(len(set(tokens)) / len(tokens))
    if len(aps) < 100:
        return {"verdict": "inconclusive", "reason": f"only {len(aps)} valid fires"}
    r, p = pearson_r(aps, divs)
    if r >= 0.20 and p < 0.01:
        v = "pass"
    elif r >= 0.10 and p < 0.05:
        v = "weak_pass"
    else:
        v = "fail"
    return {"verdict": v, "r": round(r, 4), "p_value": round(p, 4),
            "n_fires": len(aps), "mean_aperture": round(statistics.mean(aps), 3),
            "mean_diversity": round(statistics.mean(divs), 3)}


def test_p1(coherence_rows):
    if len(coherence_rows) < 500:
        coh = [float(r["total"]) for r in coherence_rows]
        return {"verdict": "inconclusive",
                "reason": f"need ≥ 500 ticks; have {len(coh)}",
                "range": [round(min(coh), 3), round(max(coh), 3)] if coh else None,
                "std": round(statistics.stdev(coh), 3) if len(coh) > 1 else 0}
    return {"verdict": "inconclusive", "reason": "P1 stub; deferred to next milestone"}


def main():
    print("Loading...")
    fires = load_fountain_fires(168)
    drives = load_drive_activations(168)
    coherence = load_substrate_coherence()
    t6 = load_t6_beliefs()
    print(f"  fires={len(fires)} drives={len(drives)} coherence={len(coherence)} t6={len(t6)}")
    print("Normalizing...")
    norms = compute_normalization(fires)
    print(f"  self_p95={norms['self_p95']:.4f} phenom_p95={norms['phenom_p95']:.4f} refl_p95={norms['reflective_p95']:.4f}")
    print("Scoring...")
    scored = []
    for i, f in enumerate(fires):
        recent = fires[max(0, i-30):i]
        g = compute_genius_score(f, recent, t6, norms)
        scored.append({**f, "genius": g})
    counts = {"genius": 0, "moment": 0, "ordinary": 0}
    for sf in scored:
        counts[sf["genius"]["class"]] += 1
    print(f"  classes: {counts}")
    print("Running predictions...")
    p1 = test_p1(coherence)
    p2 = test_p2(fires, drives)
    p3 = test_p3(fires, scored)
    p4 = test_p4(coherence, fires)
    p5 = test_p5(scored, drives)
    verdicts = [p2["verdict"], p3["verdict"], p4["verdict"], p5["verdict"]]
    passes = sum(1 for v in verdicts if v in ("pass", "strong_pass"))
    weak = sum(1 for v in verdicts if v in ("weak_pass", "partial_pass"))
    fails = sum(1 for v in verdicts if v.startswith("fail"))
    if passes >= 4:
        overall = "strong_support"
    elif passes >= 3:
        overall = "moderate_support"
    elif passes + weak >= 3:
        overall = "weak_support"
    elif fails >= 3:
        overall = "refutation"
    else:
        overall = "inconclusive"
    report = {
        "run_timestamp": time.time(),
        "data": {"fires": len(fires), "ticks": len(coherence),
                 "drives": len(drives), "t6": len(t6)},
        "genius_classes": counts,
        "predictions": {"P1": p1, "P2": p2, "P3": p3, "P4": p4, "P5": p5},
        "overall_verdict": overall,
        "top_genius": [{"ts": s["ts"], "score": s["genius"]["score"],
                        "thought": (s["thought"] or "")[:200]}
                       for s in sorted(scored, key=lambda x: -x["genius"]["score"])[:10]],
    }
    ts_str = time.strftime("%Y%m%d_%H%M%S")
    (REPORTS_DIR / f"poc_{ts_str}.json").write_text(json.dumps(report, indent=2, default=str))
    md = [f"# PoC Report {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(report['run_timestamp']))}",
          f"\n## Overall: **{overall.upper()}**\n", f"## Data\n- fires: {len(fires)}",
          f"- coherence ticks: {len(coherence)}", f"- drives: {len(drives)}", f"- T6 beliefs: {len(t6)}\n",
          f"## Classes\n- genius: {counts['genius']}", f"- moment: {counts['moment']}",
          f"- ordinary: {counts['ordinary']}\n", "## Predictions"]
    for name, pred in report["predictions"].items():
        md.append(f"### {name}: **{pred['verdict']}**")
        for k, v in pred.items():
            if k != "verdict":
                md.append(f"- {k}: {v}")
        md.append("")
    md.append("## Top 10 genius fires")
    for i, gf in enumerate(report["top_genius"], 1):
        md.append(f"{i}. **{gf['score']}** — {gf['thought']}")
    (REPORTS_DIR / f"poc_{ts_str}.md").write_text("\n".join(md))
    print(f"\n=== {overall.upper()} ===\n")
    for name, pred in report["predictions"].items():
        v = pred["verdict"]
        m = "✓" if v in ("pass", "strong_pass") else ("~" if "weak" in v or "partial" in v else ("?" if v == "inconclusive" else "✗"))
        print(f"  [{m}] {name}: {v}")
    print(f"\nReport: reports/poc_{ts_str}.json + .md")


if __name__ == "__main__":
    main()
