#!/usr/bin/env python3
"""check_arbiter_competition.py — READ-ONLY instrument for the GLOBAL WORKSPACE arbiter.

The arbiter (theory_x/stage_tom/global_workspace.arbitrate) picks one framing line to LEAD
each fire's focus_block. Whether it EARNS ITS KEEP — decides anything beyond flat priority +
liveness — was unmeasured. Arm NEX5_GW_LOG (default OFF) and the arbiter appends one JSON
line per fire, the full candidate VECTOR: {ts, candidates:[{kind, salience}], winner_kind}.

THREE channels (Beam Q-arb round 2 — do not conflate them; conflating is a FALSE POSITIVE):

  R_correct  — observed winner vs the EFFECTIVE argmax over the logged saliences. MUST be ~0:
               the code sets winner = max-salience, so any departure is a tie-path / log bug,
               NOT the arbiter "deciding". A CORRECTNESS TRIPWIRE, never a keep signal.

  R_design   — observed winner vs the NOMINAL flat-weight ladder (1.00/0.90/0.55/0.50/0.45).
               Expected LARGE and unremarkable: the variable multipliers (surprise_score,
               focus_num) re-order the intended priority BY CONSTRUCTION. A design-consistency
               READOUT. Reading R_design>0 as "earns its keep" is the exact false positive this
               instrument exists to avoid.

  EARNS-ITS-KEEP (the real primary) — the arbiter's data-driven surface is provably tiny:
               momentum is a flat 0.55 and focus_num <= 1.0, so bonsai (focus_num*0.50 <= 0.50)
               can NEVER beat momentum. focus_num has VETO power only — it can drop bonsai under
               flat drive (0.45) when focus_num < 0.9, never promote it past momentum/stakes. So
               the only data-driven region is { momentum absent } and the question reduces to
               P(bonsai wins | momentum absent) + the focus_num distribution there. Plus the
               SURPRISE ENTRY RATE: surprise enters at score>0.3 but its salience IS the score,
               so a surprise in (0.3, 0.45) enters yet loses to flat drive — a dead band that pads
               depth and never wins. If surprise rarely clears, the nominal #1 is ~phantom.

It does NOT measure content: the arbiter emits a FRAMING line over a fetch already fixed
(generator.py :3057 precedes :3115). An EXPRESSION instrument, sibling of check_voice_stability.py.

READ-ONLY. Usage:
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
    from theory_x.stage_tom.global_workspace import SALIENCE as _LADDER
except Exception:
    _LADDER = {"surprise": 1.00, "stakes": 0.90, "momentum": 0.55, "bonsai": 0.50, "drive": 0.45}

_W_BONSAI = _LADDER.get("bonsai", 0.50)
_W_DRIVE = _LADDER.get("drive", 0.45)
_W_MOMENTUM = _LADDER.get("momentum", 0.55)
_VETO_THR = _W_DRIVE / _W_BONSAI if _W_BONSAI else 0.9   # focus_num above which bonsai beats drive
_VARIABLE_RUNGS = {"surprise", "bonsai"}                 # weight×score; the rest are flat constants
_FLAT_RUNGS = {"stakes", "momentum", "drive"}            # fixed weights, no per-fire data
_NEAR_TIE_EPS = 0.01                                     # margins below this are "near ties"
_GW_LOG_PRECISION_HINT = 6                               # decimals the logger rounds salience to


def _margin_bucket(d: float) -> str:
    if d < 0.01:
        return "<0.01"
    if d < 0.05:
        return "0.01-0.05"
    if d < 0.10:
        return "0.05-0.10"
    return ">=0.10"


def _default_path() -> str:
    return os.path.join(os.path.dirname(str(db_paths()["dynamic"])),
                        "arbiter_decisions.jsonl")


def _entropy(counts) -> float:
    n = sum(counts.values())
    if not n:
        return 0.0
    h = -sum((c / n) * math.log2(c / n) for c in counts.values() if c)
    return h if h else 0.0          # avoid -0.0 for the single-category case


def _nominal_predicted(kinds) -> str | None:
    ks = [k for k in kinds if k]
    return max(ks, key=lambda k: _LADDER.get(k, 0.0)) if ks else None


def _effective_argmax(cand) -> str | None:
    if not cand:
        return None
    i = max(range(len(cand)), key=lambda j: cand[j].get("salience", 0.0))  # first-max, as logged
    return cand[i].get("kind")


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


def _fn_bucket(fn: float) -> str:
    if fn < 0.5:
        return "<0.5"
    if fn < _VETO_THR:
        return f"0.5-{_VETO_THR:g}"
    return f">{_VETO_THR:g}"


def measure(path: str, window: int = 5000, days: float | None = None) -> dict:
    rows = _load(path, window, days)
    n = len(rows)
    if n < 30:
        return {"n": n, "error": f"insufficient logged decisions (need >=30); "
                                 f"is NEX5_GW_LOG armed? log: {path}"}

    winner_c = collections.Counter()
    depth_c = collections.Counter()
    present_c = collections.Counter()
    r_correct = r_design = 0
    data_decided = 0                         # winner is a VARIABLE rung (surprise/bonsai)
    variable_live = variable_competitive = 0  # data admitted / data able to beat a live flat rung
    surprise_live = surprise_win = surprise_dead = 0
    surprise_absent = surprise_gated = 0     # absent split: gated-out (score logged) vs none-in-window
    mom_absent = bonsai_win_ma = 0
    fn_hist = collections.Counter()          # focus_num over momentum-absent, bonsai-present fires
    margin_computable = near_tie = 0
    margin_hist = collections.Counter()
    teeth_suspected = False

    for r in rows:
        cand = r.get("candidates") or []
        kinds = [c.get("kind") for c in cand]
        sal = {c.get("kind"): c.get("salience", 0.0) for c in cand}
        obs = r.get("winner_kind") or "none"
        winner_c[obs] += 1
        depth_c[len(cand)] += 1
        for k in set(kinds):
            present_c[k] += 1
        if obs != _effective_argmax(cand):
            r_correct += 1
        if obs != _nominal_predicted(kinds):
            r_design += 1
        if obs in _VARIABLE_RUNGS:
            data_decided += 1
        # three nested competitiveness reads (Beam Q-arb r4): rung-type counts when data WON;
        # the decisive variable is often the LOSER's score (surprise 0.50 < flat momentum 0.55
        # => momentum wins BECAUSE surprise scored low). Separate admitted / competitive / won.
        var_sals = [sal[k] for k in _VARIABLE_RUNGS if k in sal]
        flat_sals = [sal[k] for k in _FLAT_RUNGS if k in sal]
        if var_sals:
            variable_live += 1
            # competitive = a data candidate exceeds the LOWEST live flat weight (can beat >=1 flat
            # rung). No flat rung live => a variable rung necessarily wins, so trivially competitive.
            if (not flat_sals) or (max(var_sals) > min(flat_sals)):
                variable_competitive += 1
        if "momentum" in sal and sal["momentum"] < _W_MOMENTUM * 0.99:
            teeth_suspected = True           # demoted momentum => L4_TEETH armed => veto ceiling broken
        if "surprise" in sal:
            surprise_live += 1
            if obs == "surprise":
                surprise_win += 1
            if sal["surprise"] < _W_DRIVE:   # enters but cannot beat flat drive -> dead band
                surprise_dead += 1
        else:
            surprise_absent += 1
            if r.get("gated_surprise_score") is not None:
                surprise_gated += 1          # a surprise existed IN-WINDOW but was gated out
        if "momentum" not in kinds:
            mom_absent += 1
            if obs == "bonsai":
                bonsai_win_ma += 1
            if "bonsai" in sal and _W_BONSAI:
                fn_hist[_fn_bucket(sal["bonsai"] / _W_BONSAI)] += 1
        if len(cand) >= 2:
            margin_computable += 1
            top2 = sorted((c.get("salience", 0.0) for c in cand), reverse=True)[:2]
            d = top2[0] - top2[1]
            margin_hist[_margin_bucket(d)] += 1
            if d < _NEAR_TIE_EPS:
                near_tie += 1

    fn_total = sum(fn_hist.values())
    vcs = variable_competitive / n
    dds = data_decided / n
    return {
        "n": n,
        "data_decided_share": round(dds, 4),                  # headline: winner is a variable rung
        "variable_live_share": round(variable_live / n, 4),   # data admitted
        "variable_competitive_share": round(vcs, 4),          # admitted AND able to beat a live flat rung
        "won_of_competitive": round(dds / vcs, 4) if vcs else None,  # of data that COULD win, how much DID
        "flat_share": round(1 - dds, 4),
        "R_correct": round(r_correct / n, 4),                 # TRIPWIRE: must be ~0
        "R_design": round(r_design / n, 4),                   # READOUT: expected large, not a keep signal
        "l4_teeth_suspected": teeth_suspected,                # if true the veto-only reduction is invalid
        "decomposition": {
            "p_surprise_win": round(winner_c.get("surprise", 0) / n, 4),
            "p_bonsai_win": round(winner_c.get("bonsai", 0) / n, 4),
        },
        "surprise": {
            "entry_rate": round(surprise_live / n, 3),
            "win_given_live": round(surprise_win / surprise_live, 3) if surprise_live else None,
            "dead_band_share_of_entries": round(surprise_dead / surprise_live, 3) if surprise_live else None,
            "gated_share_of_absent": round(surprise_gated / surprise_absent, 3) if surprise_absent else None,
        },
        "bonsai": {
            "momentum_absent_share": round(mom_absent / n, 3),
            "p_bonsai_win_given_momentum_absent": round(bonsai_win_ma / mom_absent, 3) if mom_absent else None,
            "focus_num_hist_momentum_absent": {k: round(v / fn_total, 3)
                                               for k, v in fn_hist.most_common()} if fn_total else {},
            "veto_region_share": round(fn_hist.get(f">{_VETO_THR:g}", 0) / n, 4),
        },
        "near_tie_share": round(near_tie / margin_computable, 4) if margin_computable else None,
        "margin_hist": {k: round(v / margin_computable, 3)
                        for k, v in margin_hist.most_common()} if margin_computable else {},
        "logged_salience_precision": _GW_LOG_PRECISION_HINT,
        "winner_distribution": {k: round(v / n, 3) for k, v in winner_c.most_common()},
        "winner_entropy": round(_entropy(winner_c), 4),
        "mean_candidates": round(sum(d * c for d, c in depth_c.items()) / n, 3),
        "kinds_present_rate": {k: round(v / n, 3) for k, v in present_c.most_common()},
    }


def _verdict(m: dict) -> str:
    pre = ""
    if m.get("l4_teeth_suspected"):
        pre = ("L4_TEETH SUSPECTED (momentum salience < 0.55 in-log) — the veto-only ceiling is "
               "INVALID here; re-run with L4_TEETH=0 or read the demoted ceiling. | ")
    if m.get("R_correct", 0.0) > 0.001:
        return (pre + f"CORRECTNESS ALERT (R_correct={m['R_correct']:.4f} > 0 — winner != max-salience; "
                f"inspect tie path / log precision ({m.get('logged_salience_precision')}dp), "
                f"not the arbiter deciding)")
    vls = m["variable_live_share"]
    vcs = m["variable_competitive_share"]
    dds = m["data_decided_share"]
    woc = m["won_of_competitive"]
    # Three-level diagnosis (Beam r4): the SAME small dds means opposite things.
    if vls < 0.02:
        return (pre + f"NO DATA IN ROOM (variable_live_share={vls:.4f} — surprise/bonsai almost never "
                f"fire; the arbiter is a fixed ladder by cadence, not by design. STRUCTURAL; question "
                f"closes).")
    if vcs < 0.02:
        return (pre + f"DATA ADMITTED BUT NON-COMPETITIVE (variable_live={vls:.4f}, competitive={vcs:.4f} "
                f"— admitted data candidates sit in the dead band below the lowest live flat weight and "
                f"cannot beat anything; threshold mis-calibration, not determinism).")
    if woc is not None and woc < 0.10:
        return (pre + f"DATA STRUCTURALLY OUTRANKED (competitive={vcs:.4f} but won_of_competitive={woc:.4f} "
                f"— data is in the room and COULD win, yet the weight layout near-always beats it. This is "
                f"a WEIGHT/THRESHOLD CALIBRATION fact, NOT near-determinism; re-tuning is the lever, not "
                f"acceptance).")
    return (pre + f"DATA-DECIDED (data_decided_share={dds:.4f}, won_of_competitive={woc} — a variable rung "
            f"genuinely drives the outcome; decompose surprise {m['decomposition']['p_surprise_win']:.4f} "
            f"vs bonsai {m['decomposition']['p_bonsai_win']:.4f}).")


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, default=5000)
    ap.add_argument("--days", type=float, default=None)
    ap.add_argument("--path", default=None)
    ap.add_argument("--freeze", metavar="PATH")
    ap.add_argument("--baseline", metavar="PATH")
    args = ap.parse_args(argv[1:])

    path = args.path or _default_path()
    m = measure(path, window=args.window, days=args.days)
    print("=" * 74)
    print(f"ARBITER-COMPETITION  {time.strftime('%Y-%m-%d %H:%M:%S')}  (n={m.get('n')})")
    print("=" * 74)
    if "error" in m:
        print("  " + m["error"])
        return 1
    s, b = m["surprise"], m["bonsai"]
    print(f"  competitiveness ladder   : live {m['variable_live_share']:.4f} -> competitive "
          f"{m['variable_competitive_share']:.4f} -> won {m['data_decided_share']:.4f}   "
          f"(won|competitive = {m['won_of_competitive']})")
    print(f"  VERDICT                  : {_verdict(m)}")
    print(f"  R_correct (tripwire, ~0) : {m['R_correct']:.4f}    R_design (readout, big) : {m['R_design']:.4f}")
    print(f"  margin histogram         : {m['margin_hist']}   (near-tie <0.01: {m['near_tie_share']})")
    print(f"  surprise rung (nominal #1): entry {s['entry_rate']:.3f}  win|live {s['win_given_live']}  "
          f"dead-band|entries {s['dead_band_share_of_entries']}  gated|absent {s['gated_share_of_absent']}")
    print(f"  bonsai (veto) rung       : P(win|mom-absent) {b['p_bonsai_win_given_momentum_absent']}  "
          f"veto-region share {b['veto_region_share']:.4f}  focus_num {b['focus_num_hist_momentum_absent']}")
    print(f"  winner distribution      : {m['winner_distribution']}  (entropy {m['winner_entropy']:.3f} b)")
    print(f"  kinds-present rate       : {m['kinds_present_rate']}   mean cand {m['mean_candidates']:.3f}")

    if args.freeze:
        os.makedirs(os.path.dirname(args.freeze) or ".", exist_ok=True)
        with open(args.freeze, "w") as f:
            json.dump({**m, "frozen_at": time.strftime("%Y-%m-%d")}, f, indent=2)
        print(f"\n  release profile frozen -> {args.freeze}")
    if args.baseline:
        with open(args.baseline) as f:
            base = json.load(f)
        print(f"\n  DRIFT vs {base.get('frozen_at','?')}:")
        for key in ("data_decided_share", "flat_share", "R_correct", "R_design"):
            cur, was = m.get(key), base.get(key)
            if cur is not None and was is not None:
                d = cur - was
                flag = "  ** DRIFT **" if abs(d) > 0.05 else ""
                print(f"    {key:<22s}: {cur:.4f}  (was {was:.4f}, {d:+.4f}){flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
