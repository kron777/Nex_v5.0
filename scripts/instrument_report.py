#!/usr/bin/env python3
"""Historical-context instrument report — session 29 build.

Two read-only instruments, no new logging:

  #1 genius rolling rate     — the exact 1h-window number the live HUD shows,
                                contextualized against its own history so a
                                reading is legible as normal/elevated/unusual
                                instead of a bare percentage.
  #2 branch-ordering vs      — Pearson/Kendall-tau between focus_num and
     curiosity_weight           curiosity_weight per tree_snapshot, against
                                its own historical band.

Both instruments exclude bulk-retagging artifacts from genius_tags using a
row-level lag rule (tagged_at - fire_ts > 1h => backfill), not hardcoded
dates — see _load_clean_genius_pairs().

Usage:
  python3 scripts/instrument_report.py                 # full report
  python3 scripts/instrument_report.py --backfill-check # just the
      backfill-exclusion audit (May 30 / Jun 3 / Jul 13 known cases)
"""
from __future__ import annotations

import argparse
import datetime
import sqlite3
import statistics
import sys
from pathlib import Path

REPO = Path("/home/rr/Desktop/Desktop/nex5")
CONV_DB = REPO / "data" / "conversations.db"
DYNAMIC_DB = REPO / "data" / "dynamic.db"
BELIEFS_DB = REPO / "data" / "beliefs.db"

# Row-level backfill rule: any genius_tags row whose tag postdates its own
# fire by more than this is a reprocessing artifact, not live tagging.
# Verified against known cases (session 29 Phase 1): correctly flags 96%+ of
# the 2026-05-30 and 2026-06-03 bulk-retag days while leaving live rows from
# those same days untouched, and does not flag any of 2026-07-13's genuine
# live spike (max lag observed that day: 66s). Not date-based — generalizes
# to any future backfill, which will by construction have long lag.
BACKFILL_LAG_THRESHOLD_SECONDS = 3600

GENIUS_WINDOW_SECONDS = 3600       # matches the live HUD's rolling window
GENIUS_SMOOTH_SECONDS = 6 * 3600   # secondary, steadier trend line


def _ro(path: Path) -> sqlite3.Connection:
    c = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c


def _fmt_ts(ts: float) -> str:
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ── #1: genius rolling rate ────────────────────────────────────────────────

def _load_fire_ts() -> dict[int, float]:
    with _ro(DYNAMIC_DB) as d:
        return {r["id"]: r["ts"] for r in d.execute("SELECT id, ts FROM fountain_events")}


def _load_clean_genius_pairs() -> tuple[list[tuple[float, str]], dict]:
    """Return (clean_pairs, exclusion_report). clean_pairs sorted by tagged_at."""
    fire_ts = _load_fire_ts()
    with _ro(CONV_DB) as c:
        rows = c.execute(
            "SELECT fountain_event_id, tagged_at, class FROM genius_tags ORDER BY tagged_at ASC"
        ).fetchall()

    clean: list[tuple[float, str]] = []
    excluded_by_day: dict[str, int] = {}
    total_excluded = 0
    unmatched = 0
    for r in rows:
        ft = fire_ts.get(r["fountain_event_id"])
        if ft is None:
            unmatched += 1
            continue
        lag = r["tagged_at"] - ft
        if lag > BACKFILL_LAG_THRESHOLD_SECONDS:
            day = datetime.datetime.fromtimestamp(r["tagged_at"], datetime.timezone.utc).date().isoformat()
            excluded_by_day[day] = excluded_by_day.get(day, 0) + 1
            total_excluded += 1
            continue
        clean.append((r["tagged_at"], r["class"]))

    report = {
        "total_rows": len(rows),
        "unmatched_fire": unmatched,
        "excluded_backfill": total_excluded,
        "excluded_by_day": excluded_by_day,
        "clean_rows": len(clean),
    }
    return clean, report


def _rolling_rate(pairs: list[tuple[float, str]], t_end: float, window: float) -> tuple[float | None, int]:
    cutoff = t_end - window
    in_window = [c for t, c in pairs if cutoff < t <= t_end]
    n = len(in_window)
    if n < 5:
        return None, n
    striking = sum(1 for c in in_window if c == "STRIKING")
    return striking / n, n


def _build_series(pairs: list[tuple[float, str]], window: float, step: float | None = None) -> list[tuple[float, float, int]]:
    if not pairs:
        return []
    step = step or window
    start, end = pairs[0][0], pairs[-1][0]
    series = []
    t = start + window
    while t <= end:
        rate, n = _rolling_rate(pairs, t, window)
        if rate is not None:
            series.append((t, rate, n))
        t += step
    return series


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _percentile_of(value: float, population: list[float]) -> float:
    if not population:
        return float("nan")
    return 100.0 * sum(1 for x in population if x <= value) / len(population)


def _band(values: list[float]) -> dict:
    if len(values) < 2:
        return {"n": len(values), "mean": None, "median": None, "stdev": None}
    return {
        "n": len(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "stdev": statistics.stdev(values),
    }


def report_genius(now: float | None = None) -> None:
    now = now or _load_fire_ts_max_or_now()
    pairs, excl = _load_clean_genius_pairs()

    print("=" * 78)
    print("#1  GENIUS ROLLING RATE  (fraction of fires tagged STRIKING)")
    print("=" * 78)
    print(f"genius_tags: {excl['total_rows']} total rows, "
          f"{excl['excluded_backfill']} excluded as backfill (lag > "
          f"{BACKFILL_LAG_THRESHOLD_SECONDS}s), {excl['clean_rows']} clean.")
    if excl["excluded_by_day"]:
        by_day = ", ".join(f"{d}: {n}" for d, n in sorted(excl["excluded_by_day"].items()))
        print(f"  excluded rows fall on: {by_day}")
    print()

    if not pairs:
        print("No clean data available.")
        return

    full_series = _build_series(pairs, GENIUS_WINDOW_SECONDS)
    full_rates = [r for _, r, _ in full_series]
    full_band = _band(full_rates)

    cutoff_14d = now - 14 * 86400
    recent_series = [(t, r, n) for t, r, n in full_series if t > cutoff_14d]
    recent_rates = [r for _, r, _ in recent_series]
    recent_band = _band(recent_rates)

    # current reading: latest available 1h window ending at `now`
    cur_rate, cur_n = _rolling_rate(pairs, now, GENIUS_WINDOW_SECONDS)
    smooth_rate, smooth_n = _rolling_rate(pairs, now, GENIUS_SMOOTH_SECONDS)

    print(f"CURRENT READING (1h window, matches live HUD): ", end="")
    if cur_rate is None:
        print(f"n={cur_n}, too few tags in the last hour to read.")
    else:
        pct_full = _percentile_of(cur_rate, full_rates)
        pct_recent = _percentile_of(cur_rate, recent_rates) if recent_rates else float("nan")
        print(f"{cur_rate*100:.0f}% (n={cur_n})")
        print(f"  -> {_ordinal(round(pct_full))} percentile of full history "
              f"(n={full_band['n']} windows, mean={full_band['mean']*100:.0f}%, "
              f"median={full_band['median']*100:.0f}%, stdev={full_band['stdev']*100:.0f}pts)")
        if recent_rates:
            print(f"  -> {_ordinal(round(pct_recent))} percentile of trailing 14 days "
                  f"[LOWER CONFIDENCE, n={recent_band['n']} windows, "
                  f"mean={recent_band['mean']*100:.0f}%, median={recent_band['median']*100:.0f}%]")
        else:
            print("  -> trailing-14d band: insufficient data")

    print()
    print(f"6H-SMOOTHED READING (steadier trend, DIFFERENT signal from the HUD number): ", end="")
    if smooth_rate is None:
        print(f"n={smooth_n}, too few tags in the last 6h to read.")
    else:
        print(f"{smooth_rate*100:.0f}% (n={smooth_n})")

    print()
    print("LAST 7 DAYS, daily (backfill-excluded, live rows only):")
    day_buckets: dict[str, list[str]] = {}
    for t, cls in pairs:
        if t > now - 7 * 86400:
            day = datetime.datetime.fromtimestamp(t, datetime.timezone.utc).date().isoformat()
            day_buckets.setdefault(day, []).append(cls)
    for day in sorted(day_buckets):
        classes = day_buckets[day]
        n = len(classes)
        striking = sum(1 for c in classes if c == "STRIKING")
        print(f"  {day}: n={n:4d}  striking_rate={100*striking/n:5.1f}%")

    print()
    print("KNOWN BACKFILL DAYS, sanity check (must show near-zero live rows retained is WRONG expectation —")
    print("these days DO have some genuine live rows; only the batch-retagged rows are excluded):")
    for day in ("2026-05-30", "2026-06-03", "2026-07-13"):
        day_start = datetime.datetime.fromisoformat(day).replace(tzinfo=datetime.timezone.utc).timestamp()
        day_end = day_start + 86400
        live_n = sum(1 for t, _ in pairs if day_start <= t < day_end)
        excl_n = excl["excluded_by_day"].get(day, 0)
        print(f"  {day}: live/clean rows retained = {live_n:5d}   excluded as backfill = {excl_n:5d}")
    print()


def _load_fire_ts_max_or_now() -> float:
    import time as _t
    fire_ts = _load_fire_ts()
    if not fire_ts:
        return _t.time()
    latest = max(fire_ts.values())
    now = _t.time()
    # Use "now" if fires are recent (live system); otherwise use the latest
    # known fire so the report is meaningful against a stale snapshot too.
    return now if (now - latest) < 3600 else latest


# ── #2: branch ordering vs curiosity_weight ────────────────────────────────

M1_LIVE_TS = 1783856814  # 2026-07-12 13:47:13 SAST restart, cadence-aware decay live


def _kendall_tau(focus: dict[str, float], weight: dict[str, float]) -> float | None:
    import itertools
    branches = list(focus.keys())
    concordant = discordant = 0
    for a, b in itertools.combinations(branches, 2):
        wf = weight[a] - weight[b]
        ff = focus[a] - focus[b]
        if wf == 0 or ff == 0:
            continue
        if (wf > 0) == (ff > 0):
            concordant += 1
        else:
            discordant += 1
    total = concordant + discordant
    return None if total == 0 else (concordant - discordant) / total


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    mx, my = statistics.mean(xs), statistics.mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sx = sum((x - mx) ** 2 for x in xs) ** 0.5
    sy = sum((y - my) ** 2 for y in ys) ** 0.5
    if sx == 0 or sy == 0:
        return None
    return cov / (sx * sy)


def report_ordering() -> None:
    print("=" * 78)
    print("#2  BRANCH ORDERING vs CURIOSITY_WEIGHT")
    print("=" * 78)
    import json as _json
    with _ro(DYNAMIC_DB) as d:
        rows = d.execute(
            "SELECT ts, tree_json FROM tree_snapshots WHERE ts > ? ORDER BY ts ASC",
            (M1_LIVE_TS,),
        ).fetchall()

    if not rows:
        print("No post-M1 snapshots available.")
        return

    pearsons: list[float] = []
    taus: list[float] = []
    for r in rows:
        branches = _json.loads(r["tree_json"])
        focus = {b["branch_id"]: b["focus_num"] for b in branches}
        weight = {b["branch_id"]: b["curiosity_weight"] for b in branches}
        xs = [weight[k] for k in focus]
        ys = [focus[k] for k in focus]
        if len(set(xs)) < 2:
            continue
        p = _pearson(xs, ys)
        if p is not None:
            pearsons.append(p)
        tau = _kendall_tau(focus, weight)
        if tau is not None:
            taus.append(tau)

    band_p = _band(pearsons)
    band_t = _band(taus)
    cur_p, cur_t = pearsons[-1], taus[-1]

    print(f"Historical band since M1 ({_fmt_ts(M1_LIVE_TS)} -> now), n={band_p['n']} snapshots:")
    print(f"  Pearson(weight, focus_num):    mean={band_p['mean']:.3f}  stdev={band_p['stdev']:.3f}")
    print(f"  Kendall-tau(weight, focus_num): mean={band_t['mean']:.3f}  stdev={band_t['stdev']:.3f}")
    print()
    print(f"CURRENT reading (most recent snapshot, {_fmt_ts(rows[-1]['ts'])}):")
    z_p = (cur_p - band_p["mean"]) / band_p["stdev"] if band_p["stdev"] else float("nan")
    z_t = (cur_t - band_t["mean"]) / band_t["stdev"] if band_t["stdev"] else float("nan")
    print(f"  Pearson = {cur_p:.3f}  ({z_p:+.1f} sigma from the {band_p['mean']:.2f} mean since M1)")
    print(f"  Kendall-tau = {cur_t:.3f}  ({z_t:+.1f} sigma from the {band_t['mean']:.2f} mean since M1)")
    flag = "NORMAL" if abs(z_p) < 2 else "UNUSUAL — outside 2 sigma"
    print(f"  -> {flag}")
    print("  Framing: this correlation has held ~0.25-0.30 since M1 shipped, never near 1.0.")
    print("  No prediction of strict rank-tracking exists to compare against — only that")
    print("  alpha=1.0 (rejected) would have erased differentiation entirely.")
    print()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backfill-check", action="store_true",
                     help="only show the backfill-exclusion audit")
    ap.add_argument("--at", metavar="'YYYY-MM-DD HH:MM'",
                     help="evaluate the genius reading as of this UTC moment "
                          "instead of now (for replaying past HUD readings "
                          "against their historical context)")
    args = ap.parse_args()

    if args.backfill_check:
        _, excl = _load_clean_genius_pairs()
        print(excl)
        return

    if args.at:
        dt = datetime.datetime.strptime(args.at, "%Y-%m-%d %H:%M").replace(
            tzinfo=datetime.timezone.utc
        )
        report_genius(now=dt.timestamp())
        return

    report_genius()
    report_ordering()


if __name__ == "__main__":
    main()
