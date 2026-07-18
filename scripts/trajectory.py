#!/usr/bin/env python3
"""Trajectory monitor — session 38 build, Phase 2 (3.5-axis).

Reads DIRECTION, not state. Every axis is compared against ITS OWN baseline
and only gets a directional verdict when the move exceeds normal variance.
Inside variance = "holding" / "flat". This is the whole point of the
instrument: it must not cry wolf on noise the way the raw 45%/17% genius
readings did live on 2026-07-15 (session 28) -- see Phase 3 validation below.

Standalone, read-only. No new tables, no live-code touch. Reuses
scripts/instrument_report.py for the genius-rate instrument rather than
re-deriving it.

THREE FULL AXES + ONE HALF AXIS (session 38 Phase 1 cut two candidate axes
down to what's actually measurable):

  QUALITY    genius rolling rate vs its own full-history band (borrowed
              straight from instrument_report.py). Verdict only outside
              2 sigma of the EMPIRICAL historical stdev of hourly windows
              (~25.7pts over 992 windows) -- NOT the flat "+-16pt/2sigma,
              n~23" rule of thumb floated earlier in this arc. That flat
              rule does not survive contact with the actual data: the
              session-28 "45%" reading sits 16.8pts from the historical
              mean, which a literal +-16pt cutoff would misclassify as a
              real move on the exact case this instrument exists to get
              right. The empirical per-window stdev is wider (real day-to-
              day dispersion is bigger than the naive n=23 binomial-SE
              estimate suggested) and is what's actually implemented here.
              See Phase 3 below -- this is the load-bearing design choice.
  APERTURE   Gini / normalized-entropy of the latest tree_snapshot's
              per-branch focus_num, vs the frozen M1 steady-state band
              (session 27 CONFIRMED read: gini 0.344, entropy 0.873, 1275
              snapshots 12 Jul 13:47 -> 13 Jul 18:26 SAST). Reproduced here
              directly from tree_json (0.3358/0.0660 gini, 0.8743/0.0558
              entropy over that window) -- matches the journal's rounded
              numbers, confirming same metric. Verdict outside 2 sigma of
              that band's own stdev; inside = holding.
  LIVENESS   fire / belief / synth (fountain_crystallizations) counts and
              recency as of the read time. Not a variance call -- a
              factual "is she producing" check. ALIVE if all three are
              within their normal cadence of the read time, else STALLED.
  GROOVE     (the ".5" axis -- thinner signal, reported honestly as such.)
  HEALTH     groove_alerts deduped by collapsing consecutive rows that
              share (alert_type, sample_belief_ids) -- census #7 / session
              31 proved raw rows are a ~60s re-scan timer re-confirming a
              stale window, not independent events, which invalidates any
              frozen raw-count baseline (the old 650/506 etc. numbers are
              NOT used here). Scored by SEVERITY of deduped episodes, not
              count -- a quiet day with one severe groove matters more
              than a noisy day of low-severity ones. Verdict: "rising" if
              the current 24h window's average episode severity is >=2
              sigma above its own historical band, else "flat". The dedup
              ratio (raw rows -> episodes) is printed every time so the
              number is honest on its face.

SELF-DIRECTION is deliberately OMITTED, not just left out silently --
see _SELF_DIRECTION_NOTE below for why, so the next reader doesn't
"notice it's missing" and re-add a phantom axis.

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
import math
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

Z_THRESHOLD = 2.0  # sigma; inside this band = "holding"/"flat", non-negotiable per spec

# ── why SELF-DIRECTION is not an axis here (session 38 Phase 1/2) ──────────
#
# open_problems is 97.9% mechanically templated (7 non-template rows out of
# 328, via signal_to_problem.py's own _compose_title() -- "Why is {branch}
# producing strong beliefs right now?", "Signal: investigate '{entity}'",
# and five sibling templates). All seven non-template rows that have EVER
# existed were created 2026-05-09/12 and are already closed -- there has
# never been an open, self-chosen problem to measure persistence from, and
# there is currently zero open_problems of any kind (327 closed, 1 stuck).
#
# It is not just the rare case that's template-generated: even a thread
# NEX genuinely sustained across days (the "Adams-comparison work" flagged
# as a coherence anchor at the M1 restart, session 26/CARRY_OVER.md
# 2026-07-12) shows up in open_problems only as three separate
# auto-templated "Signal: investigate 'Adams'" rows (ids 300/302/304,
# each closed within hours to ~3 days, never merged into one persistent
# entry) -- confirmed directly against the table, not assumed. Whatever
# self-directed persistence exists in her cognition, open_problems is not
# where it's currently visible.
#
# Recent churn (last 7d avg ~13.1h close time, last 30d avg ~9.7h, n=32/71)
# is fast regardless of template status -- there's no slow-vs-fast split
# between template and non-template rows to build a signal from, because
# there are no recent non-template rows at all.
#
# There is no measurable self-directed-persistence signal in this table.
# Reporting a verdict here would be reporting a phantom axis. If this is
# ever rebuilt, it needs a different data source than open_problems, not a
# different threshold on this one.
_SELF_DIRECTION_NOTE = (
    "SELF-DIRECTION intentionally omitted -- see module docstring / "
    "_SELF_DIRECTION_NOTE in scripts/trajectory.py for why (97.9% "
    "template-generated, zero currently open, no persistence signal "
    "exists in this table to threshold against)."
)


# ── shared helpers ──────────────────────────────────────────────────────────

class AxisResult:
    def __init__(self, name: str, verdict: str, detail: str, z=None, note: str | None = None):
        self.name = name
        self.verdict = verdict
        self.detail = detail
        self.z = z
        self.note = note

    def line(self) -> str:
        s = f"{self.name:<13} {self.verdict:<10} {self.detail}"
        if self.note:
            s += f"\n{'':<13} {'':<10} NOTE: {self.note}"
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
    diff_pts = (cur_rate - band["mean"]) * 100
    detail = (f"{cur_rate*100:.0f}% (n={cur_n}) vs baseline mean={band['mean']*100:.1f}% "
              f"stdev={band['stdev']*100:.1f}pts (n={band['n']} windows) -> "
              f"{diff_pts:+.1f}pts from mean, z={z:+.2f}sigma")
    return AxisResult("QUALITY", verdict, detail, z)


# ── AXIS 2: APERTURE (Gini/entropy of tree focus_num) ───────────────────────

# Frozen M1 steady-state baseline: 2026-07-12 13:47 SAST (M1 live) through
# 2026-07-13 18:26 SAST, 1275 tree_snapshots, session 27 CONFIRMED read
# (journal/CARRY_OVER.md). Recomputed here directly from tree_json rather
# than trusting the journal's rounded summary numbers -- this reproduces
# them (0.3358/0.0660 vs journal's 0.344, 0.8743/0.0558 vs journal's 0.873).
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
    h = -sum(p * math.log(p) for p in ps)
    return h / math.log(n)


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


# ── AXIS 3: LIVENESS (is she running, at all) ───────────────────────────────

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

    verdict = "ALIVE" if not stale else "STALLED(" + ",".join(stale) + ")"

    def _m(gap):
        return f"{gap/60:.1f}m ago" if gap is not None else "never"

    detail = (f"fires={fire['n']} last {_m(fire_gap)} | beliefs={bel['n']} last {_m(bel_gap)} | "
              f"synth={synth['n']} last {_m(synth_gap)}")
    return AxisResult("LIVENESS", verdict, detail, None)


# ── AXIS 3.5: GROOVE HEALTH (deduped, severity-scored) ──────────────────────

def _groove_episodes(now_ts: float) -> tuple[list[tuple[float, float]], int]:
    """Collapse consecutive same-(alert_type, sample_belief_ids) rows into
    one (ts, severity) per episode (first occurrence). Raw rows are a ~60s
    re-scan timer re-confirming a stale window (census #7 / session 31),
    not independent events -- any raw-count read is dishonest on its own.
    Returns (episodes, raw_row_count)."""
    with ir._ro(ir.BELIEFS_DB) as c:
        rows = c.execute(
            "SELECT id, alert_type, sample_belief_ids, detected_at, severity "
            "FROM groove_alerts WHERE detected_at <= ? ORDER BY id",
            (now_ts,),
        ).fetchall()
    episodes: list[tuple[float, float]] = []
    prev: dict[str, str] = {}
    for r in rows:
        key = r["alert_type"]
        sig = r["sample_belief_ids"]
        if prev.get(key) != sig:
            episodes.append((r["detected_at"], r["severity"]))
        prev[key] = sig
    episodes.sort()
    return episodes, len(rows)


def _rolling_severity_series(episodes: list[tuple[float, float]], window: float,
                              step: float) -> list[float]:
    if not episodes:
        return []
    start, end = episodes[0][0], episodes[-1][0]
    series = []
    t = start + window
    while t <= end:
        cutoff = t - window
        sevs = [s for ts, s in episodes if cutoff < ts <= t]
        if sevs:
            series.append(statistics.mean(sevs))
        t += step
    return series


def axis_groove(now_ts: float) -> AxisResult:
    episodes, raw_n = _groove_episodes(now_ts)
    dedup_line = f"{raw_n} raw rows -> {len(episodes)} deduped episodes (census #7 dedup)"

    if len(episodes) < 10:
        return AxisResult("GROOVE HEALTH", "N/A", f"{dedup_line}; too few episodes to band")

    day = 86400.0
    band_series = _rolling_severity_series(episodes, day, day)
    band = ir._band(band_series) if band_series else {"n": 0, "mean": None, "stdev": None}

    cur_window = [s for ts, s in episodes if now_ts - day < ts <= now_ts]
    cur_avg = statistics.mean(cur_window) if cur_window else None

    if cur_avg is None or not band["stdev"]:
        return AxisResult("GROOVE HEALTH", "N/A",
                           f"{dedup_line}; 0 episodes in trailing 24h -- nothing to score")

    z = (cur_avg - band["mean"]) / band["stdev"]
    verdict = "rising" if z >= Z_THRESHOLD else "flat"

    detail = (f"{dedup_line} | trailing 24h: n={len(cur_window)} episodes, "
              f"avg severity={cur_avg:.2f} vs baseline mean={band['mean']:.2f} "
              f"stdev={band['stdev']:.2f} (n={band['n']} daily windows) -> z={z:+.2f}sigma")
    return AxisResult("GROOVE HEALTH", verdict, detail, z)


# ── overall read + main ─────────────────────────────────────────────────────

def _overall(results: dict[str, AxisResult]) -> str:
    live = results["LIVENESS"]
    if live.verdict != "ALIVE":
        return f"DOWN -- {live.verdict}"

    concerning = [r.name for r in results.values() if r.verdict in ("drifting", "narrowing")]
    if concerning:
        return f"{'/'.join(concerning)} DRIFTING"

    if results["GROOVE HEALTH"].verdict == "rising":
        return "GROOVE HEALTH RISING -- see line for severity detail"

    if results["QUALITY"].verdict == "improving":
        return "STABLE, quality trending up"

    return "STABLE"


def run(now_ts: float) -> dict[str, AxisResult]:
    return {
        "QUALITY": axis_quality(now_ts),
        "APERTURE": axis_aperture(now_ts),
        "LIVENESS": axis_liveness(now_ts),
        "GROOVE HEALTH": axis_groove(now_ts),
    }


def report(now_ts: float, log_path: Path | None) -> None:
    results = run(now_ts)
    overall = _overall(results)

    when = ir._fmt_ts(now_ts)
    print("=" * 78)
    print(f"TRAJECTORY  --  {when}")
    print("=" * 78)
    print(overall)
    print("-" * 78)
    for name in ("QUALITY", "APERTURE", "LIVENESS", "GROOVE HEALTH"):
        print(results[name].line())
    print()
    print(_SELF_DIRECTION_NOTE)
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
