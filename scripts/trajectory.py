#!/usr/bin/env python3
"""Trajectory monitor — session 38 build.

Reads DIRECTION, not state. Every axis is compared against ITS OWN baseline
and only gets a directional verdict (improving/drifting/widening/narrowing)
when the move exceeds normal variance. Inside variance = "holding". This is
the whole point of the instrument: it must not cry wolf on noise the way the
raw 45%/17% genius readings did on 2026-07-15 (session 28) -- see Phase 3
validation below.

Standalone, read-only. No new tables, no live-code touch. Reuses
scripts/instrument_report.py for the genius-rate instrument rather than
re-deriving it, and reads tree_snapshots/open_problems/groove_alerts/
crystallization_rejects/persona_rejects/beliefs/fountain_events/
fountain_crystallizations exactly as they already are.

Axes:
  QUALITY         genius rolling rate vs its full-history band (borrowed
                   straight from instrument_report.py's own instrument).
  APERTURE        Gini / normalized-entropy of the latest tree_snapshot's
                   per-branch focus_num, vs the frozen M1 steady-state band
                   (session 27 CONFIRMED read, journal/CARRY_OVER.md
                   2026-07-15 "three frozen predictions read": Gini 0.344,
                   entropy 0.873, over 1275 snapshots 12 Jul 13:47 -> 13 Jul
                   18:26 SAST). Reproduced here from tree_json directly
                   (mean 0.3358/stdev 0.0660 gini, mean 0.8743/stdev 0.0558
                   entropy over that exact window) -- close enough to the
                   journal's rounded numbers to confirm this is the same
                   metric, computed the same way.
  SELF-DIRECTION  open_problems template-vs-non-template ratio + max age of
                   any OPEN non-template problem. NO BASELINE EXISTS: session
                   28 found 97.8% of all-time rows are mechanically templated
                   (signal_to_problem.py's own title compositor), and every
                   non-template row that ever existed was closed back in May.
                   There has never been an open, self-chosen problem to
                   measure a baseline from. This axis reports ESTABLISHING,
                   not a faked holding/improving/drifting.
  GROOVE HEALTH   groove_alerts deduped into episodes by collapsing
                   consecutive same-(alert_type, sample_belief_ids) rows
                   (census #7 / session 31: raw rows are a 60s re-scan timer
                   re-confirming a stale window, not independent events --
                   the frozen Jul-12/15 raw-count baselines are invalidated
                   by this and are NOT used here), rolling-24h count vs its
                   own historical band of rolling-24h deduped counts. Plus
                   crystallization_rejects / persona_rejects 24h counts,
                   reported informationally (history starts 2026-07-17/-18 --
                   too thin for a baseline yet, same honesty rule as
                   SELF-DIRECTION).
  LIVENESS        fire / belief / synth (fountain_crystallizations) counts
                   and recency as of the read time. Is she running at all.

Usage:
  python3 scripts/trajectory.py                          # tonight's read
  python3 scripts/trajectory.py --at "2026-07-15 11:41"  # replay a past UTC moment
  python3 scripts/trajectory.py --log                    # also append one line to logs/trajectory_log.jsonl
  python3 scripts/trajectory.py --log /path/to/file.jsonl
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import statistics
import sys
import time
from pathlib import Path

REPO = Path("/home/rr/Desktop/Desktop/nex5")
SCRIPTS_DIR = REPO / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import instrument_report as ir  # noqa: E402  (reuse #1's genius instrument, not re-derive it)

DEFAULT_LOG = REPO / "logs" / "trajectory_log.jsonl"

Z_THRESHOLD = 2.0  # sigma; inside this band = "holding", non-negotiable per spec


# ── shared helpers ──────────────────────────────────────────────────────────

class AxisResult:
    def __init__(self, name: str, verdict: str, detail: str, z=None, note: str | None = None):
        self.name = name
        self.verdict = verdict
        self.detail = detail
        self.z = z
        self.note = note

    def line(self) -> str:
        s = f"{self.name:<15} {self.verdict:<10} {self.detail}"
        if self.note:
            s += f"\n{'':<15} {'':<10} NOTE: {self.note}"
        return s


def _classify(z: float, pos: str, neg: str, hold: str = "holding") -> str:
    if abs(z) < Z_THRESHOLD:
        return hold
    return pos if z > 0 else neg


def _resolve_now(at_arg: str | None) -> float:
    if at_arg:
        dt = datetime.datetime.strptime(at_arg, "%Y-%m-%d %H:%M").replace(
            tzinfo=datetime.timezone.utc
        )
        return dt.timestamp()
    return time.time()


# ── AXIS 1: QUALITY (genius rolling rate) ───────────────────────────────────

def axis_quality(now_ts: float) -> AxisResult:
    pairs, _excl = ir._load_clean_genius_pairs()
    if not pairs:
        return AxisResult("QUALITY", "N/A", "no clean genius_tags data available")

    full_series = ir._build_series(pairs, ir.GENIUS_WINDOW_SECONDS)
    full_rates = [r for _, r, _ in full_series]
    band = ir._band(full_rates)

    cur_rate, cur_n = ir._rolling_rate(pairs, now_ts, ir.GENIUS_WINDOW_SECONDS)
    if cur_rate is None or band["stdev"] is None:
        return AxisResult("QUALITY", "N/A",
                           f"n={cur_n} tags in last 1h, too few / too little history to read")

    z = (cur_rate - band["mean"]) / band["stdev"]
    verdict = _classify(z, pos="improving", neg="drifting")
    detail = (f"{cur_rate*100:.0f}% (n={cur_n}) vs baseline mean={band['mean']*100:.0f}% "
              f"stdev={band['stdev']*100:.0f}pts (n={band['n']} windows) -> z={z:+.2f}sigma")
    return AxisResult("QUALITY", verdict, detail, z)


# ── AXIS 2: APERTURE (Gini/entropy of tree focus_num) ───────────────────────

# Frozen M1 steady-state baseline: 2026-07-12 13:47 SAST (M1 live) through
# 2026-07-13 18:26 SAST, 1275 tree_snapshots, session 27 CONFIRMED read
# (journal/CARRY_OVER.md). Recomputed here directly from tree_json (gini/
# entropy of focus_num per branch) rather than trusting the journal's rounded
# summary numbers -- this reproduces them (0.3358/0.0660 vs journal's 0.344,
# 0.8743/0.0558 vs journal's 0.873), confirming it is the same metric.
_APERTURE_BASELINE_START = 1783864020.0  # 2026-07-12 13:47 SAST
_APERTURE_BASELINE_END = 1783967160.0    # 2026-07-13 18:26 SAST
GINI_BASELINE = {"mean": 0.3358, "stdev": 0.0660}
ENTROPY_BASELINE = {"mean": 0.8743, "stdev": 0.0558}


def _gini(xs: list[float]) -> float:
    xs = sorted(xs)
    n = len(xs)
    s = sum(xs)
    if n == 0 or s == 0:
        return 0.0
    total = sum((2 * i - n - 1) * x for i, x in enumerate(xs, 1))
    return total / (n * s)


def _norm_entropy(xs: list[float]) -> float:
    s = sum(xs)
    if s == 0:
        return 0.0
    ps = [x / s for x in xs if x > 0]
    n = len(xs)
    if n <= 1:
        return 0.0
    h = -sum(p * __import__("math").log(p) for p in ps)
    return h / __import__("math").log(n)


def axis_aperture(now_ts: float) -> AxisResult:
    with ir._ro(ir.DYNAMIC_DB) as d:
        row = d.execute(
            "SELECT ts, tree_json FROM tree_snapshots WHERE ts <= ? ORDER BY ts DESC LIMIT 1",
            (now_ts,),
        ).fetchone()
    if row is None:
        return AxisResult("APERTURE", "N/A", "no tree_snapshot at or before this time")

    branches = json.loads(row["tree_json"])
    weights = [b["focus_num"] for b in branches]
    g = _gini(weights)
    e = _norm_entropy(weights)
    z_g = (g - GINI_BASELINE["mean"]) / GINI_BASELINE["stdev"]
    z_e = (e - ENTROPY_BASELINE["mean"]) / ENTROPY_BASELINE["stdev"]

    # Concentration (gini up / entropy down) = narrowing; spread (gini down /
    # entropy up) = widening. Either inside band = holding.
    if abs(z_g) < Z_THRESHOLD and abs(z_e) < Z_THRESHOLD:
        verdict = "holding"
    elif z_g >= Z_THRESHOLD or z_e <= -Z_THRESHOLD:
        verdict = "narrowing"
    else:
        verdict = "widening"

    detail = (f"gini={g:.3f}(z={z_g:+.2f}) entropy={e:.3f}(z={z_e:+.2f}) "
              f"vs frozen M1 baseline gini={GINI_BASELINE['mean']:.3f} "
              f"entropy={ENTROPY_BASELINE['mean']:.3f} "
              f"[snapshot {ir._fmt_ts(row['ts'])}]")
    return AxisResult("APERTURE", verdict, detail, max(abs(z_g), abs(z_e)))


# ── AXIS 3: SELF-DIRECTION (open_problems template ratio) ──────────────────

# Every auto-generated title shape from theory_x/signals/signal_to_problem.py
# :_compose_title(). Anything NOT matching one of these is operator/manually
# authored, or a signal type whose title isn't yet templated.
_TEMPLATE_PATTERNS = tuple(re.compile(p) for p in (
    r"^What is '.+' doing across these domains\?$",
    r"^Why is .+ producing strong beliefs right now\?$",
    r"^What pattern is emerging in .+\?$",
    r"^How does '.+' bridge these branches\?$",
    r"^What does this new arc around '.+' mean\?$",
    r"^What is '.+'\?$",
    r"^Signal: investigate '.+'$",
    r"^Signal: .+$",
))


def _is_template(title: str) -> bool:
    return any(p.match(title) for p in _TEMPLATE_PATTERNS)


def axis_self_direction(now_ts: float) -> AxisResult:
    with ir._ro(ir.CONV_DB) as c:
        rows = c.execute(
            "SELECT title, state, created_at FROM open_problems WHERE created_at <= ?",
            (now_ts,),
        ).fetchall()

    total = len(rows)
    if total == 0:
        return AxisResult("SELF-DIRECTION", "ESTABLISHING", "no open_problems yet")

    non_template = [r for r in rows if not _is_template(r["title"])]
    open_non_template = [r for r in non_template if r["state"] == "open"]
    pct = 100.0 * len(non_template) / total

    if open_non_template:
        oldest = min(r["created_at"] for r in open_non_template)
        age_days = (now_ts - oldest) / 86400
        persistence = f"{len(open_non_template)} open non-template, oldest {age_days:.1f}d"
    else:
        persistence = "zero open non-template problems right now"

    detail = f"{len(non_template)}/{total} non-template ({pct:.1f}%) all-time; {persistence}"
    note = ("no baseline exists yet -- session 28: 97.8% of all-time rows are mechanically "
            "templated and every non-template row that ever existed is already closed (May "
            "2026). Verdict withheld until this axis has an open self-chosen problem to track, "
            "not faked.")
    return AxisResult("SELF-DIRECTION", "ESTABLISHING", detail, None, note=note)


# ── AXIS 4: GROOVE HEALTH (deduped groove_alerts + reject counts) ──────────

def _groove_episode_ts(now_ts: float) -> list[float]:
    """Collapse consecutive same-(alert_type, sample_belief_ids) rows into
    one timestamp per episode (first occurrence). Raw rows are a ~60s
    re-scan timer re-confirming a stale window (session 31 / census #7),
    not independent events."""
    with ir._ro(ir.BELIEFS_DB) as c:
        rows = c.execute(
            "SELECT id, alert_type, sample_belief_ids, detected_at FROM groove_alerts "
            "WHERE detected_at <= ? ORDER BY alert_type, id",
            (now_ts,),
        ).fetchall()
    episodes = []
    prev_key: dict[str, tuple] = {}
    # re-sort by id ascending overall so episode timestamps come out chronological
    rows_by_id = sorted(rows, key=lambda r: r["id"])
    prev = {}
    for r in rows_by_id:
        key = r["alert_type"]
        sig = r["sample_belief_ids"]
        if prev.get(key) != sig:
            episodes.append(r["detected_at"])
        prev[key] = sig
    return sorted(episodes)


def _rolling_count_series(ts_list: list[float], window: float, step: float) -> list[float]:
    if not ts_list:
        return []
    start, end = ts_list[0], ts_list[-1]
    series = []
    t = start + window
    while t <= end:
        cutoff = t - window
        n = sum(1 for x in ts_list if cutoff < x <= t)
        series.append(n)
        t += step
    return series


def axis_groove(now_ts: float) -> AxisResult:
    episodes = [e for e in _groove_episode_ts(now_ts) if e <= now_ts]
    if len(episodes) < 5:
        return AxisResult("GROOVE HEALTH", "ESTABLISHING", "too few deduped groove episodes yet")

    day = 86400.0
    band_series = _rolling_count_series(episodes, day, day)
    band = ir._band(band_series) if band_series else {"n": 0, "mean": None, "stdev": None}

    cur_count = sum(1 for e in episodes if now_ts - day < e <= now_ts)

    with ir._ro(ir.DYNAMIC_DB) as d:
        crys_rejects = d.execute(
            "SELECT COUNT(*) n FROM crystallization_rejects WHERE ts > ? AND ts <= ?",
            (now_ts - day, now_ts),
        ).fetchone()["n"]
        persona_rejects = d.execute(
            "SELECT COUNT(*) n FROM persona_rejects WHERE ts > ? AND ts <= ?",
            (now_ts - day, now_ts),
        ).fetchone()["n"]

    if band["stdev"]:
        z = (cur_count - band["mean"]) / band["stdev"]
        verdict = _classify(z, pos="elevated", neg="quiet")
    else:
        z = None
        verdict = "N/A"

    detail = (f"{cur_count} deduped episodes/24h vs baseline mean={band.get('mean') or 0:.0f} "
              f"stdev={band.get('stdev') or 0:.0f} (n={band['n']} daily windows)"
              + (f" -> z={z:+.2f}sigma" if z is not None else "")
              + f" | crystallization_rejects/24h={crys_rejects} persona_rejects/24h={persona_rejects}")
    note = ("frozen raw-count baselines from Jul-12/15 (650/506, 306/460) are INVALID -- they "
            "counted re-scan ticks, not events (session 31); this axis's own deduped band is "
            "the only valid baseline. crystallization_rejects/persona_rejects history starts "
            "2026-07-17/18 -- too thin for a baseline, reported informationally only.")
    return AxisResult("GROOVE HEALTH", verdict, detail, z, note=note)


# ── AXIS 5: LIVENESS (is she running, at all) ───────────────────────────────

_STALE_FIRE_S = 900       # 15 min; typical fire cadence ~2-3 min
_STALE_BELIEF_S = 2700    # 45 min; irregular but typically much tighter
_STALE_SYNTH_S = 21600    # 6h; fountain_crystallizations is intrinsically bursty --
                          # observed normal live gaps up to ~4.6h between accepts


def axis_liveness(now_ts: float) -> AxisResult:
    with ir._ro(ir.DYNAMIC_DB) as d:
        fire = d.execute(
            "SELECT COUNT(*) n, MAX(ts) mx FROM fountain_events WHERE ts <= ?", (now_ts,)
        ).fetchone()
    with ir._ro(ir.BELIEFS_DB) as b:
        bel = b.execute(
            "SELECT COUNT(*) n, MAX(created_at) mx FROM beliefs WHERE created_at <= ?", (now_ts,)
        ).fetchone()
        synth = b.execute(
            "SELECT COUNT(*) n, MAX(ts) mx FROM fountain_crystallizations WHERE ts <= ?", (now_ts,)
        ).fetchone()

    fire_gap = (now_ts - fire["mx"]) if fire["mx"] else None
    bel_gap = (now_ts - bel["mx"]) if bel["mx"] else None
    synth_gap = (now_ts - synth["mx"]) if synth["mx"] else None

    stale = []
    if fire_gap is None or fire_gap > _STALE_FIRE_S:
        stale.append("fires")
    if bel_gap is None or bel_gap > _STALE_BELIEF_S:
        stale.append("beliefs")
    if synth_gap is None or synth_gap > _STALE_SYNTH_S:
        stale.append("synth")

    verdict = "RUNNING" if not stale else "STALLED(" + ",".join(stale) + ")"

    def _m(gap):
        return f"{gap/60:.1f}m ago" if gap is not None else "never"

    detail = (f"fires={fire['n']} last {_m(fire_gap)} | beliefs={bel['n']} last {_m(bel_gap)} | "
              f"synth={synth['n']} last {_m(synth_gap)}")
    return AxisResult("LIVENESS", verdict, detail, None)


# ── overall read + main ─────────────────────────────────────────────────────

def _overall(results: dict[str, AxisResult]) -> str:
    live = results["LIVENESS"]
    if live.verdict != "RUNNING":
        return f"DOWN -- {live.verdict}"

    concerning = [r.name for r in results.values()
                  if r.verdict in ("drifting", "narrowing", "quiet")]
    if concerning:
        return f"{'/'.join(concerning)} DRIFTING"

    groove = results["GROOVE HEALTH"]
    if groove.verdict == "elevated":
        return "GROOVING -- elevated pattern-repetition rate, see GROOVE HEALTH line"

    quality = results["QUALITY"]
    if quality.verdict == "improving":
        return "STABLE, quality trending up"

    return "STABLE"


def run(now_ts: float) -> dict[str, AxisResult]:
    order = ["QUALITY", "APERTURE", "SELF-DIRECTION", "GROOVE HEALTH", "LIVENESS"]
    fns = {
        "QUALITY": axis_quality,
        "APERTURE": axis_aperture,
        "SELF-DIRECTION": axis_self_direction,
        "GROOVE HEALTH": axis_groove,
        "LIVENESS": axis_liveness,
    }
    return {name: fns[name](now_ts) for name in order}


def report(now_ts: float, log_path: Path | None) -> None:
    results = run(now_ts)
    overall = _overall(results)

    when = ir._fmt_ts(now_ts)
    print("=" * 78)
    print(f"TRAJECTORY  --  {when}")
    print("=" * 78)
    print(overall)
    print("-" * 78)
    for name in ("QUALITY", "APERTURE", "SELF-DIRECTION", "GROOVE HEALTH", "LIVENESS"):
        print(results[name].line())
    print()

    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": now_ts,
            "when_utc": when,
            "overall": overall,
            "axes": {
                name: {"verdict": r.verdict, "z": r.z, "detail": r.detail}
                for name, r in results.items()
            },
        }
        with open(log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
        print(f"[logged -> {log_path}]")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--at", metavar="'YYYY-MM-DD HH:MM'",
                     help="replay the read as of this UTC moment instead of now")
    ap.add_argument("--log", nargs="?", const=str(DEFAULT_LOG), default=None,
                     metavar="PATH",
                     help=f"append one timestamped JSON line to PATH (default {DEFAULT_LOG}) "
                          f"-- opt-in only, no auto-alerting, this just appends a record")
    args = ap.parse_args()

    now_ts = _resolve_now(args.at)
    log_path = Path(args.log) if args.log else None
    report(now_ts, log_path)


if __name__ == "__main__":
    main()
