#!/usr/bin/env python3
"""Generated-text replay harness — the instrument R52 and R53 both named as missing.

WHAT IT IS FOR
    Every round so far has been able to measure whether RETRIEVAL improved.
    None could measure whether the resulting THOUGHT improved. R52 §D proposed
    giving the fountain relevance retrieval; R53 shipped the chat-path pool fix
    and both reports closed on the same gap: "this round measured retrieval,
    not answers". This harness closes it.

WHAT IT DOES
    Paired A/B over real fires. For each sampled fire it rebuilds the prompt
    twice, identical in every respect EXCEPT the belief-context block:

      ARM "recency"    the 9 most recent own-content beliefs as of that fire
                       -- reproduces _retrieve_context_beliefs' ordering, i.e.
                       what the fountain actually did
      ARM "relevance"  the 9 highest token-overlap with the fire's focal_item
                       from a 30-day window -- what R52 §D proposes

    Both are generated against the same live model the fountain uses, then
    scored with the LIVE audit predicates (imported, never reimplemented).

WHAT IT IS NOT
    It is NOT a full-prompt replay. The live prompt carries ~15 blocks; this
    builds the mode template + item + belief block only. So absolute levels
    are NOT expected to match production -- see --validate for what is
    checked instead. It is a DIFFERENTIAL instrument: it measures the delta
    between two arms under identical conditions. Read the delta, not the level.

    It is read-only and offline: databases open mode=ro, nothing is written to
    them, and it never touches the fountain.

ENDPOINT CONTENTION — READ THIS BEFORE ANY LARGE RUN (measured, round 55)
    It calls the SAME ollama endpoint the live fountain depends on, and at scale
    that is not a background cost. Measured on 2026-08-11 at --concurrency 3:

        fountain fire rate  21.9/h baseline -> 14/h (1h) -> 10/h (30min)
                            -> 4/h (15min), still falling when aborted
        persona timeouts    2 in the preceding 4h -> 4 in ~1.5h of replay

    Throughput was 103 fires/h, i.e. ~6 h to reach the n=615 a decisive
    on-subject read needs -- six hours of that degradation. The run was aborted
    at n=39. ollama serialises per model, so --concurrency mostly reorders the
    queue AHEAD of the fountain rather than adding throughput.

    So: a decisive run (n>=615) CANNOT be taken against a live NEX. Do it with
    the fountain stopped, or against a second model instance on another port
    via NEX5_VOICE_URL. Default concurrency is 1 for this reason; raising it
    does not buy throughput, it only starves the fountain faster.

USAGE
    PYTHONPATH=. python3 scripts/replay_retrieval.py --n 40
    PYTHONPATH=. python3 scripts/replay_retrieval.py --validate
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sqlite3
import statistics
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, "/home/rr/Desktop/Desktop/nex5")

# Live predicates — imported, never reimplemented (GENIUS_FIDELITY_BASELINE rule:
# the predicate has ONE definition).
from theory_x.stage6_fountain.crystallizer import (
    _is_on_subject, _SELF_REF_RE, _ENGAGEMENT_RE, _has_anchor, _fidelity_tokens,
)
from theory_x.genius.score_v2 import feat_anti_template
from theory_x.stage6_fountain.generator import (
    _MODE_EXPLAIN, _MODE_ARGUE, _OWN_CONTENT_SOURCES,
)

DATA = "/home/rr/Desktop/Desktop/nex5/data/"
VOICE_URL = os.environ.get("NEX5_VOICE_URL", "http://localhost:11434/v1/chat/completions")
MODEL = os.environ.get("NEX5_VOICE_MODEL", "qwen2.5:3b")
U = lambda t: datetime.fromtimestamp(t, timezone.utc)


def has_engagement(t: str) -> bool:
    """The crystallizer's admission gate, replayed exactly."""
    if _SELF_REF_RE.search(t):
        return True
    if "?" in t:
        return True
    if _ENGAGEMENT_RE.search(t):
        return _has_anchor(t)
    return False


def tokens(text: str) -> set:
    """The house tokenizer, imported from crystallizer.

    GENIUS_FIDELITY_BASELINE.md §1 requires ONE definition of the content-token
    predicate. A local reimplementation here (no furniture stripping) made this
    harness's relevance counts read ~3x higher than R52 §A.2's on the same data
    -- caught in validation, fixed 2026-08-11. Do not re-inline it.
    """
    return set(_fidelity_tokens(text))


# ── belief selection: the two arms ────────────────────────────────────────────

def beliefs_recency(bel, ts, n=9):
    ph = ",".join("?" * len(_OWN_CONTENT_SOURCES))
    return [dict(r) for r in bel.execute(
        f"SELECT id, content, created_at FROM beliefs WHERE source IN ({ph}) "
        f"AND tier < 8 AND created_at < ? ORDER BY created_at DESC LIMIT ?",
        (*_OWN_CONTENT_SOURCES, ts, n))]


def beliefs_relevance(bel, ts, focal, n=9, window_days=30):
    ph = ",".join("?" * len(_OWN_CONTENT_SOURCES))
    pool = [dict(r) for r in bel.execute(
        f"SELECT id, content, created_at FROM beliefs WHERE source IN ({ph}) "
        f"AND tier < 8 AND created_at < ? AND created_at > ? "
        f"ORDER BY created_at DESC LIMIT 3000",
        (*_OWN_CONTENT_SOURCES, ts, ts - window_days * 86400))]
    ft = tokens(focal)
    scored = [(len(ft & tokens(r["content"])), -r["created_at"], r) for r in pool]
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [r for _, _, r in scored[:n]]


def build_prompt(mode_tmpl, focal, beliefs, now):
    """Mode template + belief block, rendered the way generator.py renders it."""
    parts = [mode_tmpl.format(item=focal), ""]
    if beliefs:
        parts.append("Things you've been reading about lately:")
        for b in beliefs:
            age = int((now - b["created_at"]) / 60)
            parts.append(f"  ({age} min ago) {b['content']}")
        parts.append("")
    return "\n".join(parts)


def generate(prompt, temperature=0.9, max_tokens=220):
    import requests
    r = requests.post(VOICE_URL, json={
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }, timeout=180)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


# ── scoring ───────────────────────────────────────────────────────────────────

def score(text, focal, prior_thoughts):
    return {
        "on_subject": bool(_is_on_subject(focal, text)),
        "engagement_fail": not has_engagement(text),
        "novelty_F2": feat_anti_template(text, prior_thoughts),
        "chars": len(text),
        "too_long": len(text) > 600,
    }


def wilson(k, n):
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    z = 1.96
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def paired_boot(deltas, reps=5000, seed=54):
    rnd = random.Random(seed)
    ms = []
    for _ in range(reps):
        s = [deltas[rnd.randrange(len(deltas))] for _ in range(len(deltas))]
        ms.append(statistics.fmean(s))
    ms.sort()
    return ms[int(0.025 * len(ms))], ms[int(0.975 * len(ms))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40, help="fires to replay (each = 2 generations)")
    ap.add_argument("--since", default="2026-08-08T00:00:00")
    ap.add_argument("--seed", type=int, default=54)
    ap.add_argument("--concurrency", type=int, default=1,
                    help="parallel generations. The fountain shares this ollama endpoint, "
                         "so keep this low and watch the live fire rate (~22/h baseline).")
    ap.add_argument("--validate", action="store_true",
                    help="check live-model reachability and that the harness reproduces "
                         "the LIVE fires' own metrics under the live predicates")
    ap.add_argument("--out", default=None, help="write per-fire JSONL here")
    a = ap.parse_args()

    T = lambda s: datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()
    dyn = sqlite3.connect(f"file:{DATA}dynamic.db?mode=ro", uri=True); dyn.row_factory = sqlite3.Row
    bel = sqlite3.connect(f"file:{DATA}beliefs.db?mode=ro", uri=True); bel.row_factory = sqlite3.Row

    fires = [dict(r) for r in dyn.execute(
        "SELECT id, ts, thought, mode, focal_item FROM fountain_events "
        "WHERE ts >= ? AND focal_item IS NOT NULL AND thought IS NOT NULL "
        "AND mode IN ('EXPLAIN','ARGUE') ORDER BY ts", (T(a.since),))]
    rnd = random.Random(a.seed)
    rnd.shuffle(fires)

    if a.validate:
        # 1. the live predicates, applied to the LIVE fires themselves.
        #    This is the known result the harness must agree with, and it is
        #    what R47 measured post-C2.
        print("=== VALIDATION 1: live predicates over the real fires in this window ===")
        for m in ("EXPLAIN", "ARGUE"):
            sub = [f for f in fires if f["mode"] == m]
            os_ = sum(1 for f in sub if _is_on_subject(f["focal_item"], f["thought"]))
            ef = sum(1 for f in sub if not has_engagement(f["thought"]))
            p1, l1, h1 = wilson(os_, len(sub)); p2, l2, h2 = wilson(ef, len(sub))
            print(f"  {m:8} n={len(sub):>4}  on-subject={p1:.3f} [{l1:.3f},{h1:.3f}]  "
                  f"engagement-fail={p2:.3f} [{l2:.3f},{h2:.3f}]")
        print("  (R47 measured EXPLAIN post-C2 at on-subject 0.785, engagement-fail 0.455;")
        print("   agreement here confirms the imported predicates behave as in prior rounds.)")
        # 2. model reachability
        print("\n=== VALIDATION 2: live model reachable ===")
        try:
            t0 = time.time()
            out = generate("Say the single word: ready", temperature=0.0, max_tokens=8)
            print(f"  {VOICE_URL} model={MODEL} -> {out!r}  ({time.time()-t0:.2f}s)")
        except Exception as e:
            print(f"  UNREACHABLE: {e}")
            return 1
        # 3. arm construction differs as intended, before spending any generation
        print("\n=== VALIDATION 3: the two arms differ, and by how much ===")
        ov_r, ov_v = [], []
        for f in fires[:120]:
            ft = tokens(f["focal_item"])
            if not ft: continue
            rec = beliefs_recency(bel, f["ts"]); rel = beliefs_relevance(bel, f["ts"], f["focal_item"])
            ov_r.append(sum(1 for b in rec if ft & tokens(b["content"])))
            ov_v.append(sum(1 for b in rel if ft & tokens(b["content"])))
        print(f"  context beliefs sharing >=1 token with the focal item, of 9:")
        print(f"    recency arm   mean {statistics.fmean(ov_r):.2f}   zero-relevant fires "
              f"{sum(1 for x in ov_r if x==0)/len(ov_r):.1%}")
        print(f"    relevance arm mean {statistics.fmean(ov_v):.2f}   zero-relevant fires "
              f"{sum(1 for x in ov_v if x==0)/len(ov_v):.1%}")
        print("  (R52 §A.2 measured 0.62 and 59.2% for recency, 8.87 and 0% for relevance.)")
        return 0

    fires = [f for f in fires if tokens(f["focal_item"])][:a.n]
    print(f"replaying {len(fires)} fires x 2 arms = {len(fires)*2} generations "
          f"against {MODEL} at {VOICE_URL}\n")

    prior = [r["thought"] for r in dyn.execute(
        "SELECT thought FROM fountain_events WHERE ts < ? ORDER BY ts DESC LIMIT 50",
        (T(a.since),))][::-1]

    # Belief selection is sqlite-bound and must stay on one thread per handle;
    # only the generation calls are parallelised.
    def one_fire(f):
        tmpl = _MODE_EXPLAIN if f["mode"] == "EXPLAIN" else _MODE_ARGUE
        rec = {"fire_id": f["id"], "mode": f["mode"], "focal_item": f["focal_item"]}
        for arm, bl in (("recency", f["_rec"]), ("relevance", f["_rel"])):
            out = generate(build_prompt(tmpl, f["focal_item"], bl, f["ts"]))
            rec[arm] = {"text": out, **score(out, f["focal_item"], prior)}
            # B.2 mechanism capture: how long are the priors this arm supplied?
            rec[arm]["prior_chars"] = statistics.fmean(
                [len(b["content"]) for b in bl]) if bl else 0.0
            rec[arm]["prior_n"] = len(bl)
        return rec

    for f in fires:
        f["_rec"] = beliefs_recency(bel, f["ts"])
        f["_rel"] = beliefs_relevance(bel, f["ts"], f["focal_item"])

    # Incremental write. A decisive run is thousands of generations against a
    # 3B model and takes hours; buffering to the end means a crash, a timeout or
    # an OOM loses all of it, and it makes a partial read impossible. Every
    # completed fire is flushed immediately, so the run is both crash-safe and
    # readable while in flight. Summaries below are computed from `rows`, which
    # is exactly what reached disk.
    out_fh = open(a.out, "w", buffering=1) if a.out else None

    def _emit(rec):
        rows.append(rec)
        if out_fh:
            out_fh.write(json.dumps(rec) + "\n")

    rows = []
    t0 = time.time()
    if a.concurrency > 1:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
            futs = {ex.submit(one_fire, f): f for f in fires}
            for i, fut in enumerate(as_completed(futs), 1):
                try:
                    _emit(fut.result())
                except Exception as e:
                    print(f"  fire {futs[fut]['id']} failed: {e}")
                if i % 25 == 0:
                    print(f"  {i}/{len(fires)} fires  ({time.time()-t0:.0f}s, "
                          f"{(time.time()-t0)/i:.1f}s/fire)", flush=True)
    else:
        for i, f in enumerate(fires, 1):
            try:
                _emit(one_fire(f))
            except Exception as e:
                print(f"  [{i}] failed: {e}")
            if i % 25 == 0:
                print(f"  {i}/{len(fires)} fires  ({time.time()-t0:.0f}s elapsed)", flush=True)

    if out_fh:
        out_fh.close()
        print(f"\nwrote {len(rows)} rows to {a.out}")

    print(f"\n=== PAIRED RESULT over {len(rows)} fires ===")
    print(f"{'metric':18} {'recency':>18} {'relevance':>18} {'paired delta':>16} {'95% CI':>20}")
    for key, kind in [("on_subject", "rate"), ("engagement_fail", "rate"),
                      ("novelty_F2", "mean"), ("chars", "mean"), ("too_long", "rate")]:
        A = [r["recency"][key] for r in rows]
        B = [r["relevance"][key] for r in rows]
        if kind == "rate":
            pa, la, ha = wilson(sum(A), len(A)); pb, lb, hb = wilson(sum(B), len(B))
            sa = f"{pa:.3f} [{la:.3f},{ha:.3f}]"; sb = f"{pb:.3f} [{lb:.3f},{hb:.3f}]"
        else:
            pa, pb = statistics.fmean(A), statistics.fmean(B)
            sa, sb = f"{pa:.3f}", f"{pb:.3f}"
        d = [float(b) - float(x) for x, b in zip(A, B)]
        lo, hi = paired_boot(d)
        sig = "" if lo <= 0 <= hi else "  <-- CI excludes 0"
        print(f"{key:18} {sa:>18} {sb:>18} {statistics.fmean(d):>+16.4f} "
              f"{'['+format(lo,'+.4f')+','+format(hi,'+.4f')+']':>20}{sig}")
    dyn.close(); bel.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
