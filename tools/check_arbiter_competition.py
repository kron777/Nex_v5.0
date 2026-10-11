#!/usr/bin/env python3
"""check_arbiter_competition.py — READ-ONLY instrument for the GLOBAL WORKSPACE arbiter.

The arbiter (theory_x/stage_tom/global_workspace.arbitrate) picks one framing line
to LEAD each fire's focus_block. Whether it earns its keep — how often it overrides
its routine bonsai baseline rather than rubber-stamping it — was unmeasured, because
the decision is not recorded anywhere. Arm NEX5_GW_LOG (default OFF) and the arbiter
appends one JSON line per fire to arbiter_decisions.jsonl; this tool reads that log.

WHAT IT MEASURES (and, as importantly, what it does NOT):
  - winner-kind distribution + winner ENTROPY  — how varied the broadcast lead is.
  - NON-BONSAI win share                        — fires where the lead was NOT the
                                                  routine attention baseline.
  - OVERRIDE-given-bonsai-present               — among fires where bonsai WAS a
                                                  candidate, how often it LOST. This is
                                                  the honest "did the arbiter override an
                                                  available baseline" number; the raw
                                                  non-bonsai share mixes in fires where
                                                  bonsai was never an option.
  - candidate DEPTH                             — mean candidates/fire (1 == no contest).
  - kinds-present RATE                          — per kind, the fraction of fires it was
                                                  even eligible. The CADENCE term: the
                                                  weights fix momentum (0.55) > bonsai
                                                  ceiling (<=0.50), so a non-bonsai win is
                                                  largely momentum-LIVENESS, not a quality
                                                  judgement. Read override alongside this.

It does NOT measure content: the arbiter emits a FRAMING line over a fetch that is
already fixed (generator.py :3057 precedes :3115), so the winner changes the lead
instruction, never the retrieved material. This is an EXPRESSION instrument, a sibling
of check_voice_stability.py, not a selection one.

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

_DRIFT_BAND = 0.15  # |delta| beyond this on a share flags drift


def _default_path() -> str:
    return os.path.join(os.path.dirname(str(db_paths()["dynamic"])),
                        "arbiter_decisions.jsonl")


def _entropy(counts) -> float:
    n = sum(counts.values())
    if not n:
        return 0.0
    return -sum((c / n) * math.log2(c / n) for c in counts.values() if c)


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
    present_c = collections.Counter()      # per-kind eligibility count
    bonsai_present = 0
    bonsai_lost = 0
    non_bonsai_wins = 0
    for r in rows:
        wk = r.get("winner_kind") or "none"
        winner_c[wk] += 1
        depth_c[int(r.get("n_candidates") or 0)] += 1
        kp = r.get("kinds_present") or []
        for k in kp:
            present_c[k] += 1
        if "bonsai" in kp:
            bonsai_present += 1
            if wk != "bonsai":
                bonsai_lost += 1
        if wk != "bonsai":
            non_bonsai_wins += 1

    return {
        "n": n,
        "winner_distribution": {k: round(v / n, 3) for k, v in winner_c.most_common()},
        "winner_entropy": round(_entropy(winner_c), 4),
        "non_bonsai_win_share": round(non_bonsai_wins / n, 3),
        "override_given_bonsai_present": (
            round(bonsai_lost / bonsai_present, 3) if bonsai_present else None),
        "bonsai_present_share": round(bonsai_present / n, 3),
        "mean_candidates": round(sum(d * c for d, c in depth_c.items()) / n, 3),
        "depth_distribution": {str(k): round(v / n, 3) for k, v in sorted(depth_c.items())},
        "kinds_present_rate": {k: round(v / n, 3) for k, v in present_c.most_common()},
    }


def _verdict(m: dict) -> str:
    # Descriptive, deliberately coarse. The binding number is override-given-bonsai;
    # the raw non-bonsai share is reported but is confounded by eligibility cadence.
    ov = m.get("override_given_bonsai_present")
    if ov is None:
        return "INDETERMINATE (bonsai never a candidate in-window)"
    if ov < 0.05:
        return ("RUBBER-STAMP (arbiter broadcasts the bonsai baseline ~always; "
                "its decision adds ~no variation to the lead frame)")
    if ov < 0.25:
        return "MOSTLY-BASELINE (arbiter overrides bonsai only occasionally)"
    return ("ACTIVE (arbiter frequently overrides the baseline; read against "
            "kinds_present_rate — a momentum-dominated override is cadence, not judgement)")


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
    print("=" * 70)
    print(f"ARBITER-COMPETITION  {time.strftime('%Y-%m-%d %H:%M:%S')}  (n={m.get('n')})")
    print("=" * 70)
    if "error" in m:
        print("  " + m["error"])
        return 1
    print(f"  winner distribution      : {m['winner_distribution']}")
    print(f"  winner entropy           : {m['winner_entropy']:.3f} bits")
    print(f"  non-bonsai win share     : {m['non_bonsai_win_share']:.3f}   (raw; confounded by cadence)")
    ov = m['override_given_bonsai_present']
    print(f"  override | bonsai present : {ov if ov is None else f'{ov:.3f}'}   <- the honest number "
          f"(bonsai present in {m['bonsai_present_share']:.0%} of fires)")
    print(f"  mean candidates / fire   : {m['mean_candidates']:.3f}   depth {m['depth_distribution']}")
    print(f"  kinds-present rate       : {m['kinds_present_rate']}   (cadence / eligibility)")
    print(f"  VERDICT                  : {_verdict(m)}")

    if args.freeze:
        os.makedirs(os.path.dirname(args.freeze) or ".", exist_ok=True)
        with open(args.freeze, "w") as f:
            json.dump({**m, "frozen_at": time.strftime("%Y-%m-%d")}, f, indent=2)
        print(f"\n  release profile frozen -> {args.freeze}")
    if args.baseline:
        with open(args.baseline) as f:
            base = json.load(f)
        print(f"\n  DRIFT vs {base.get('frozen_at','?')} (winner-share movement):")
        bw = base.get("winner_distribution", {})
        cw = m["winner_distribution"]
        for k in sorted(set(bw) | set(cw)):
            b_, c_ = bw.get(k, 0.0), cw.get(k, 0.0)
            d = c_ - b_
            flag = "  ** SHIFT **" if abs(d) > _DRIFT_BAND else ""
            print(f"    {k:<10s} : {c_:.3f}  (was {b_:.3f}, {d:+.3f}){flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
