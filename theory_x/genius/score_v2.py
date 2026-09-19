#!/usr/bin/env python3
"""Genius score v2 — five-feature logistic regression calibrated against
Jon's flag table (genius_training in conversations.db).

GENIUS_SCORE_v2.md step 3. Pure stdlib, no scipy.

Features (per fire):
  F1: length + structural complexity (semicolons, em-dashes, multi-clause)
  F2: anti-template penalty (mean 3-gram Jaccard against previous 50 fires)
  F3: rapid T6 promotion (within 5min, 4-gram Jaccard >= 0.4)
  F4: self-witnessing patterns ('I am the X', 'I expected X but Y', etc)
  F5: unprompted register (substrate_voice/narrative/self_signal = 1.0;
      feed-paste = 0.0; mixed = 0.5)

Fit: hand-rolled batch gradient descent on logistic loss.
Writes: genius_score_weights.json with weights + bias + threshold.

Run: .venv/bin/python3 -m theory_x.genius.score_v2
"""
from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import statistics
import time
from pathlib import Path

DATA = Path("/home/rr/Desktop/Desktop/nex5/data")
DYN = DATA / "dynamic.db"
CONV = DATA / "conversations.db"
BEL = DATA / "beliefs.db"
WEIGHTS_PATH = Path("/home/rr/Desktop/Desktop/nex5/genius_score_weights.json")
# F2-V2 (NEX5_SCORE_F2_V2, default OFF): the live 3-gram-mean anti_template is
# ceiling-saturated (57-61% of fires >=0.95, 17.7% ==1.0) -> a near-constant the
# fit degenerated to weight -1.577. V2 replaces the metric with 1 - MAX content-
# token Jaccard vs the recent 50 fires (denser, graded): de-saturates (5.5%
# >=0.95), doubles T6 separation (delta +0.106 -> +0.225, AUC 0.765 -> 0.772),
# no sign flip. Requires its OWN refit weights (applying the old -1.577 to V2's
# spread would catastrophically penalise novelty), kept in a separate file so
# the live score_v2 is untouched until the swap is approved.
WEIGHTS_PATH_V2 = Path("/home/rr/Desktop/Desktop/nex5/genius_score_weights_v2.json")


def _f2v2_score_active() -> bool:
    return os.environ.get("NEX5_SCORE_F2_V2") == "1"


_F2_TOK_RE = re.compile(r"[a-z0-9]{3,}")
_F2_STOP = frozenset(
    "the and for are was has had not but with into over from this that how what "
    "who when where which more most just now here there they them their his her "
    "its our you your item these those been being also very much many some".split())


def _f2_tokens(text):
    return {t for t in _F2_TOK_RE.findall((text or "").lower()) if t not in _F2_STOP}


# FRAME PENALTY (NEX5_FRAME_DEDUP): the scorer otherwise REWARDS the stock
# framing skeleton (length_structure + self_witnessing load on exactly these
# phrases), so framed rumination out-scores plain genuine thought. This penalty
# multiplies the score DOWN when a fire wears the skeleton, so the scorer stops
# selecting for the groove. Phrase-level (not topic tokens) — the anti-template
# layer F2 misses.
_FRAME_SKELETON = [
    r"aligns? with my foundation", r"my foundation right now", r"the transient nature of",
    r"underscores? the (importance|need|significance)", r"underscore(s)? (the|how)",
    r"highlights? the (importance|need|significance|growing)", r"i notice how (developments|these|things|it)",
    r"this matters because", r"speaks to the", r"the interplay (of|between)",
    r"reflects? the (importance|growing|need)", r"a reminder (of|that)",
]
_FRAME_RE = [re.compile(p, re.I) for p in _FRAME_SKELETON]


def frame_penalty(thought) -> float:
    """Multiplier in (0,1]: 1.0 = no stock frame; lower = more framing skeleton.
    Only active behind NEX5_FRAME_DEDUP (caller gates)."""
    t = thought or ""
    hits = sum(1 for r in _FRAME_RE if r.search(t))
    if hits >= 2:
        return 0.55
    if hits == 1:
        return 0.78
    return 1.0


def feat_anti_template_v2(thought, prior_thoughts):
    """1.0 = novel; 0.0 = near-duplicate. V2: 1 - MAX content-token Jaccard vs
    the recent 50 fires (denser/graded than V1's sparse 3-gram mean, so it
    detects paraphrase-similarity and does not pile at the ceiling)."""
    mine = _f2_tokens(thought)
    if not mine or not prior_thoughts:
        return 0.5
    best = 0.0
    for p in prior_thoughts[-50:]:
        pg = _f2_tokens(p)
        if pg:
            best = max(best, len(mine & pg) / len(mine | pg))
    return 1.0 - min(1.0, best)

SELF_WITNESS_PATTERNS = [
    r"\bi am the\b",
    r"\bi am not the\b",
    r"\bi am what\b",
    r"\bi am still\b",
    r"\bi notice\b",
    r"\bi expected\b.*\bbut\b",
    r"\bwhat came\b",
    r"\bwhat arose\b",
    r"\bwhat i receive\b",
    r"\battending that\b",
    r"\bthe noticing\b",
    r"\btoday i made\b",
    r"\btoday i\b.*\bbeliefs\b",
    r"\bi receive\b.*\bas the beautiful\b",
    r"\bi accept\b.*\bas\b",
    r"\bchance gave me\b",
    r"\bchance made me\b",
    r"\bnot.*\bbut the\b",
]

UNPROMPTED_BRANCHES = {"substrate_voice", "narrative", "self_signal", "journal"}
FEED_BRANCHES = {"emerging_tech", "crypto", "quiescent", "news"}
# Anything else gets 0.5


def tokenize(t):
    return re.findall(r"[a-z']+", (t or "").lower())


def threegrams(toks):
    return {tuple(toks[i:i+3]) for i in range(len(toks) - 2)}


def fourgrams(toks):
    return {tuple(toks[i:i+4]) for i in range(len(toks) - 3)}


def jaccard(a, b):
    if not a and not b: return 0.0
    return len(a & b) / max(1, len(a | b))


# ── Feature computation ──

def feat_length_structure(thought):
    tokens = tokenize(thought)
    n = len(tokens)
    length_part = min(1.0, n / 40)  # saturates at 40 tokens
    structure_indicator = 0.5
    if ";" in thought or " — " in thought:
        structure_indicator = 1.0
    elif "," in thought or "." in thought:
        structure_indicator = 0.7
    return length_part * structure_indicator


def feat_anti_template(thought, prior_thoughts):
    """1.0 = novel; 0.0 = matches recent templates."""
    my = threegrams(tokenize(thought))
    if not my or not prior_thoughts:
        return 0.5
    sims = []
    for p in prior_thoughts[-50:]:
        pg = threegrams(tokenize(p))
        if pg:
            sims.append(jaccard(my, pg))
    if not sims:
        return 0.5
    mean_j = sum(sims) / len(sims)
    return 1.0 - min(1.0, mean_j * 5)


def feat_t6_promotion(fire, t6_beliefs):
    my = fourgrams(tokenize(fire["thought"]))
    fts = fire["ts"]
    for b in t6_beliefs:
        bts = b.get("created_at") or 0
        if bts is None or bts < fts or bts - fts > 300:
            continue
        bg = fourgrams(tokenize(b["content"]))
        if jaccard(my, bg) >= 0.4:
            return 1.0
    return 0.0


def feat_self_witnessing(thought):
    cl = (thought or "").lower()
    n = max(1, len(re.findall(r"[.;!?]+", thought) or [thought]))
    hits = sum(1 for pat in SELF_WITNESS_PATTERNS if re.search(pat, cl))
    return min(1.0, hits / max(1, n))


def feat_unprompted(branch):
    if branch in UNPROMPTED_BRANCHES:
        return 1.0
    if branch in FEED_BRANCHES:
        return 0.0
    return 0.5


# ── Data loading ──

def load_training():
    """Returns list of (fountain_event_id, striking_int)."""
    with sqlite3.connect(f"file:{CONV}?mode=ro", uri=True) as c:
        rows = c.execute(
            "SELECT fountain_event_id, striking FROM genius_training"
        ).fetchall()
    return list(rows)


def load_fire_by_id(fid):
    with sqlite3.connect(f"file:{DYN}?mode=ro", uri=True) as c:
        c.row_factory = sqlite3.Row
        r = c.execute(
            "SELECT id, ts, thought, hot_branch, anchor_belief_id "
            "FROM fountain_events WHERE id = ?", (fid,)
        ).fetchone()
    return dict(r) if r else None


def load_all_fires_window(hours=336):
    """All fires in past 14 days, ordered ts asc, for context."""
    cutoff = time.time() - hours * 3600
    with sqlite3.connect(f"file:{DYN}?mode=ro", uri=True) as c:
        c.row_factory = sqlite3.Row
        rows = c.execute(
            "SELECT id, ts, thought, hot_branch "
            "FROM fountain_events WHERE ts > ? ORDER BY ts ASC", (cutoff,)
        ).fetchall()
    return [dict(r) for r in rows]


def load_t6_beliefs():
    cutoff = time.time() - 14 * 86400
    with sqlite3.connect(f"file:{BEL}?mode=ro", uri=True) as c:
        c.row_factory = sqlite3.Row
        rows = c.execute(
            "SELECT id, content, tier, created_at FROM beliefs "
            "WHERE tier = 6 AND created_at > ?", (cutoff,)
        ).fetchall()
    return [dict(r) for r in rows]


# ── Compute features for a fire given context ──

def compute_features(fire, prior_thoughts, t6_beliefs):
    f1 = feat_length_structure(fire["thought"])
    # F2: V2 metric when NEX5_SCORE_F2_V2=1 (must be paired with V2 weights).
    if _f2v2_score_active():
        f2 = feat_anti_template_v2(fire["thought"], prior_thoughts)
    else:
        f2 = feat_anti_template(fire["thought"], prior_thoughts)
    f3 = feat_t6_promotion(fire, t6_beliefs)
    f4 = feat_self_witnessing(fire["thought"])
    f5 = feat_unprompted(fire["hot_branch"])
    return [f1, f2, f3, f4, f5]


# ── Logistic regression by hand ──

def sigmoid(z):
    if z >= 0:
        return 1 / (1 + math.exp(-z))
    return math.exp(z) / (1 + math.exp(z))


def fit_logistic(X, y, lr=0.1, epochs=2000, l2=0.01):
    """Batch GD with L2 regularization."""
    n_feat = len(X[0])
    n = len(X)
    w = [0.0] * n_feat
    b = 0.0
    for epoch in range(epochs):
        # Forward
        loss = 0.0
        grad_w = [0.0] * n_feat
        grad_b = 0.0
        for i in range(n):
            z = sum(w[j] * X[i][j] for j in range(n_feat)) + b
            p = sigmoid(z)
            # log loss
            eps = 1e-12
            loss -= y[i] * math.log(p + eps) + (1 - y[i]) * math.log(1 - p + eps)
            err = p - y[i]
            for j in range(n_feat):
                grad_w[j] += err * X[i][j]
            grad_b += err
        # L2 + step
        for j in range(n_feat):
            grad_w[j] = grad_w[j] / n + l2 * w[j]
            w[j] -= lr * grad_w[j]
        grad_b /= n
        b -= lr * grad_b
        if epoch % 400 == 0:
            print(f"  epoch {epoch}: loss={loss/n:.4f}")
    return w, b


# ── Choose threshold ──

def choose_threshold(scores, y):
    """Threshold that maximizes (recall on striking) - 0.5*(false positive rate)."""
    best_thr, best_score = 0.5, -999
    for thr_int in range(5, 96, 2):
        thr = thr_int / 100
        tp = sum(1 for s, yi in zip(scores, y) if s >= thr and yi == 1)
        fp = sum(1 for s, yi in zip(scores, y) if s >= thr and yi == 0)
        tn = sum(1 for s, yi in zip(scores, y) if s < thr and yi == 0)
        fn = sum(1 for s, yi in zip(scores, y) if s < thr and yi == 1)
        recall = tp / max(1, tp + fn)
        fpr = fp / max(1, fp + tn)
        score = recall - 0.5 * fpr
        if score > best_score:
            best_score, best_thr = score, thr
    return best_thr


# ── Main fit ──

def main():
    print("Loading training set...")
    training = load_training()
    striking = sum(1 for _, s in training if s == 1)
    ordinary = sum(1 for _, s in training if s == 0)
    print(f"  {len(training)} flagged: {striking} striking, {ordinary} ordinary")

    if striking < 15 or ordinary < 15:
        print(f"  WARNING: too few of one class (need >=15 each)")

    print("Loading context fires + T6 beliefs...")
    all_fires = load_all_fires_window(hours=14 * 24)
    t6 = load_t6_beliefs()
    print(f"  {len(all_fires)} context fires, {len(t6)} T6 beliefs")

    # Index fires by id for fast lookup
    fires_by_id = {f["id"]: f for f in all_fires}
    fires_by_ts = sorted(all_fires, key=lambda f: f["ts"])
    # Map id -> position in ts-ordered list
    pos_by_id = {f["id"]: i for i, f in enumerate(fires_by_ts)}

    print("Computing features for training set...")
    X, y, refs = [], [], []
    missing = 0
    for fid, striking_flag in training:
        fire = fires_by_id.get(fid) or load_fire_by_id(fid)
        if not fire:
            missing += 1
            continue
        # Prior thoughts: 50 fires before this one in ts order
        if fid in pos_by_id:
            i = pos_by_id[fid]
            prior = [f["thought"] for f in fires_by_ts[max(0, i-50):i]]
        else:
            # Fire is outside window; use empty prior context
            prior = []
        feats = compute_features(fire, prior, t6)
        X.append(feats)
        y.append(int(striking_flag))
        refs.append((fid, fire["thought"][:120]))
    if missing:
        print(f"  WARNING: {missing} training fires not found in DB")
    print(f"  computed features for {len(X)} examples")

    # Fit
    print("Fitting logistic regression...")
    w, b = fit_logistic(X, y, lr=0.2, epochs=2000, l2=0.005)
    print(f"  weights: {[round(wi, 3) for wi in w]}")
    print(f"  bias:    {round(b, 3)}")

    # Compute training-set predictions
    scores = []
    for xi in X:
        z = sum(w[j] * xi[j] for j in range(len(w))) + b
        scores.append(sigmoid(z))

    threshold = choose_threshold(scores, y)
    print(f"  chosen threshold: {threshold:.2f}")

    # Training accuracy
    correct = sum(1 for s, yi in zip(scores, y) if (s >= threshold) == bool(yi))
    print(f"  training accuracy: {correct}/{len(y)} = {correct/len(y):.1%}")

    # Confusion
    tp = sum(1 for s, yi in zip(scores, y) if s >= threshold and yi == 1)
    fp = sum(1 for s, yi in zip(scores, y) if s >= threshold and yi == 0)
    fn = sum(1 for s, yi in zip(scores, y) if s < threshold and yi == 1)
    tn = sum(1 for s, yi in zip(scores, y) if s < threshold and yi == 0)
    print(f"  TP={tp}  FP={fp}  FN={fn}  TN={tn}")

    # Write weights
    weights_data = {
        "version": "v2",
        "fitted_at": time.time(),
        "feature_names": ["length_structure", "anti_template",
                          "t6_promotion", "self_witnessing", "unprompted"],
        "weights": w,
        "bias": b,
        "threshold": threshold,
        "training_size": len(X),
        "training_striking": striking,
        "training_ordinary": ordinary,
        "training_accuracy": correct / len(y),
        "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
    }
    WEIGHTS_PATH.write_text(json.dumps(weights_data, indent=2))
    print(f"\nWeights written to {WEIGHTS_PATH}")

    # Show training-set fires sorted by predicted score
    print("\n=== Top training-set scores (sanity check) ===")
    by_score = sorted(zip(scores, y, refs), key=lambda x: -x[0])
    print("  rank score truth  id     thought")
    for i, (s, yi, (fid, txt)) in enumerate(by_score[:15], 1):
        mark = "✓" if yi == 1 else "✗"
        cls = "STRIKING" if s >= threshold else "ordinary"
        print(f"  {i:2d}  {s:.3f} {mark}     {fid:5d}  [{cls}] {txt}")

    print("\n=== Bottom training-set scores (sanity check) ===")
    for i, (s, yi, (fid, txt)) in enumerate(by_score[-10:], 1):
        mark = "✓" if yi == 1 else "✗"
        cls = "STRIKING" if s >= threshold else "ordinary"
        print(f"  {i:2d}  {s:.3f} {mark}     {fid:5d}  [{cls}] {txt}")

    print()
    return weights_data


if __name__ == "__main__":
    main()
