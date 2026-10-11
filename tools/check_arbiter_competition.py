#!/usr/bin/env python3
"""check_arbiter_competition.py — READ-ONLY instrument for the GLOBAL WORKSPACE arbiter.

The arbiter (theory_x/stage_tom/global_workspace.arbitrate) picks one framing line to
LEAD each fire's focus_block. Whether it EARNS ITS KEEP — decides anything beyond a fixed
priority order — was unmeasured, because the decision was recorded nowhere. Arm NEX5_GW_LOG
(default OFF) and the arbiter appends one JSON line per fire, the full candidate VECTOR:
    {ts, candidates:[{kind, salience}], winner_kind}

PRIMARY — LADDER RESIDUAL (Beam Q-arb). The salience weights form a static ladder
(surprise 1.00 > stakes 0.90 > momentum 0.55 > bonsai 0.50 > drive 0.45). A naive "override
rate" just reads out WHICH candidates were live (cadence), not whether the arbiter decided
anything. The decision content is the RESIDUAL: the fraction of fires where the observed
winner differs from the one the STATIC weight-ladder predicts from that fire's live kinds.
  - residual ~= 0  -> STRICT LADDER: the arbiter selects the top-priority AVAILABLE line and
                     decides nothing beyond priority. "Earns its keep" = no; question closes.
  - residual  > 0  -> something re-ranks candidates. It can only be the two VARIABLE
                     multipliers: surprise = surprise_score x 1.00 (a weak surprise, score in
                     (0.3, 0.55), falls BELOW flat momentum 0.55); bonsai = focus_num x 0.50
                     (a low-focus bonsai falls BELOW flat drive 0.45). momentum/stakes/drive are
                     CONSTANT, so they never move. The residual therefore localizes to
                     surprise_score and focus_num — and focus_num comes from sense_events -> bonsai,
                     closing the loop back to the sense_events selector.

It does NOT measure content: the arbiter emits a FRAMING line over a fetch already fixed
(generator.py :3057 precedes :3115), so the winner changes the lead instruction, never the
retrieved material. An EXPRESSION instrument, a sibling of check_voice_stability.py.

READ-ONLY: reads the JSONL append log; writes nothing (except --freeze -> a profile).
Usage:
  python3 tools/check_arbiter_competition.py [--window N | --days D] [--path FILE]
  python3 tools/check_arbiter_competition.py --freeze observation_reports/arbiter/v1.json
  python3 tools/check_arbiter_competition.py --baseline observation_reports/arbiter/v1.json
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import os
import sys
import time

sys.path.insert(0, __file__.rsplit("/tools/", 1)[0])

from substrate.paths import db_paths  # noqa: E402

try:
    from theory_x.stage_tom.global_workspace import SALIENCE as _LADDER  # the static weights
except Exception:
    _LADDER = {"surprise": 1.00, "stakes": 0.90, "momentum": 0.55, "bonsai": 0.50, "drive": 0.45}

_RESID_BAND = 0.02   # residual below this == strict ladder


def _default_path() -> str:
    return os.path.join(os.path.dirname(str(db_paths()["dynamic"])),
                        "arbiter_decisions.jsonl")


def _entropy(counts) -> float:
    n = sum(counts.values())
    if not n:
        return 0.0
    h = -sum((c / n) * math.log2(c / n) for c in counts.values() if c)
    return h if h else 0.0          # avoid -0.0 for the single-category case


def _ladder_predicted(kinds_present) -> str | None:
    """The winner the STATIC weight-ladder predicts: the live kind with the highest fixed
    weight. Deterministic — the five weights are distinct."""
    kinds = [k for k in kinds_present if k]
    if not kinds:
        return None
    return max(kinds, key=lambda k: _LADDER.get(k, 0.0))


def _load(path: str, window: int, days: float | None) -> list:
    rows = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
    except FileNotFoundError:
        return []
    if days is not None:
        cut = time.time() - days * 86400
        rows = [r for r in rows if (r.get("ts") or 0) > cut]
    else:
        rows = rows[-window:]
    return rows


def measure(path: str, window: int = 5000, days: float | None = None) -> dict:
    rows = _load(path, window, days)
    n = len(rows)
    if n < 30:
        return {"n": n, "error": f"insufficient logged decisions (need >=30); "
                                 f"is NEX5_GW_LOG armed? log: {path}"}

    winner_c = collections.Counter()
    depth_c = collections.Counter()
    present_c = collections.Counter()
    residual_hits = 0
    sig_total = collections.Counter()
    sig_residual = collections.Counter()
    sig_predicted: dict = {}
    sig_observed = collections.defaultdict(collections.Counter)

    for r in rows:
        cand = r.get("candidates") or []
        kinds_present = [c.get("kind") for c in cand]
        obs = r.get("winner_kind") or "none"
        winner_c[obs] += 1
        depth_c[len(cand)] += 1
        for k in set(kinds_present):
            present_c[k] += 1
        pred = _ladder_predicted(kinds_present)
        sig = ",".join(sorted(set(k for k in kinds_present if k))) or "none"
        sig_total[sig] += 1
        sig_predicted[sig] = pred
        sig_observed[sig][obs] += 1
        if obs != pred:
            residual_hits += 1
            sig_residual[sig] += 1

    by_signature = []
    for sig, tot in sig_total.most_common():
        by_signature.append({
            "signature": sig,
            "n": tot,
            "share": round(tot / n, 3),
            "ladder_predicted": sig_predicted[sig],
            "observed": {k: round(v / tot, 3) for k, v in sig_observed[sig].most_common()},
            "residual_rate": round(sig_residual[sig] / tot, 3),
        })

    return {
        "n": n,
        "residual_rate": round(residual_hits / n, 4),          # PRIMARY
        "winner_distribution": {k: round(v / n, 3) for k, v in winner_c.most_common()},
        "winner_entropy": round(_entropy(winner_c), 4),
        "mean_candidates": round(sum(d * c for d, c in depth_c.items()) / n, 3),
        "depth_distribution": {str(k): round(v / n, 3) for k, v in sorted(depth_c.items())},
        "kinds_present_rate": {k: round(v / n, 3) for k, v in present_c.most_common()},
        "by_signature": by_signature,
    }


def _verdict(m: dict) -> str:
    rr = m.get("residual_rate")
    if rr is None:
        return "INDETERMINATE"
    if rr < _RESID_BAND:
        return ("STRICT LADDER (observed winner == static-weight prediction ~always; the "
                "arbiter picks the top-priority AVAILABLE line and decides nothing beyond "
                "the priority order — 'earns its keep' = no, and the question closes)")
    if rr < 0.10:
        return "NEAR-LADDER (a small residual beyond priority; localize it in by_signature)"
    return ("RESIDUAL PRESENT (the arbiter departs the static ladder materially — the variable "
            "multipliers surprise_score / focus_num are re-ranking; read by_signature for where)")


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, default=5000)
    ap.add_argument("--days", type=float, default=None)
    ap.add_argument("--path", default=None, help="override the decisions JSONL path")
    ap.add_argument("--freeze", metavar="PATH")
    ap.add_argument("--baseline", metavar="PATH")
    args = ap.parse_args(argv[1:])

    path = args.path or _default_path()
    m = measure(path, window=args.window, days=args.days)
    print("=" * 72)
    print(f"ARBITER-COMPETITION  {time.strftime('%Y-%m-%d %H:%M:%S')}  (n={m.get('n')})")
    print("=" * 72)
    if "error" in m:
        print("  " + m["error"])
        return 1
    print(f"  LADDER RESIDUAL (primary) : {m['residual_rate']:.4f}   "
          f"(observed winner != static-weight prediction)")
    print(f"  VERDICT                   : {_verdict(m)}")
    print(f"  winner distribution       : {m['winner_distribution']}  (entropy {m['winner_entropy']:.3f} b)")
    print(f"  mean candidates / fire    : {m['mean_candidates']:.3f}   depth {m['depth_distribution']}")
    print(f"  kinds-present rate        : {m['kinds_present_rate']}   (cadence / eligibility)")
    print("  by liveness signature (predicted vs observed -- the residual lives in cols 3 vs 4):")
    print(f"    {'signature':<34s} {'n':>5s} {'predicted':>10s}  observed / residual")
    for s in m["by_signature"]:
        print(f"    {s['signature']:<34s} {s['n']:>5d} {str(s['ladder_predicted']):>10s}  "
              f"{s['observed']}  r={s['residual_rate']:.3f}")

    if args.freeze:
        os.makedirs(os.path.dirname(args.freeze) or ".", exist_ok=True)
        with open(args.freeze, "w") as f:
            json.dump({**m, "frozen_at": time.strftime("%Y-%m-%d")}, f, indent=2)
        print(f"\n  release profile frozen -> {args.freeze}")
    if args.baseline:
        with open(args.baseline) as f:
            base = json.load(f)
        rb, rc = base.get("residual_rate"), m.get("residual_rate")
        if rb is not None:
            d = rc - rb
            flag = "  ** RESIDUAL DRIFT **" if abs(d) > 0.05 else ""
            print(f"\n  DRIFT vs {base.get('frozen_at','?')}:")
            print(f"    residual_rate : {rc:.4f}  (was {rb:.4f}, {d:+.4f}){flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
