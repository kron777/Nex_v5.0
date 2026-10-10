#!/usr/bin/env python3
"""check_cadence.py — the fire-cadence measurement harness.

Read-only guardrail: an attention/retrieval change (chat arbiter, own-content
render, stakes) must not silently move the clock — speed her up into chatter or
slow her into silence. This measures how often she fires and reports whether a
round perturbed it.

Reads dynamic.fountain_events(ts). fountain_events is NOT under reaper retention
(verified — Beam's "30-day cap" warning does not apply here), so full history is
available. Downtime is the real confound (she was shut down 2026-08-24), so the
PRIMARY metric is the MEDIAN inter-arrival and an active-rate derived from it
(86400/median) — both robust to the few huge gaps that downtime produces — not
count/span, which downtime inflates. Large gaps are reported separately as
likely pauses.

Usage:
  PYTHONPATH=. python3 tools/check_cadence.py [--days N]
  PYTHONPATH=. python3 tools/check_cadence.py --freeze base.json
  PYTHONPATH=. python3 tools/check_cadence.py --baseline base.json

Falsifier (guardrail): active fires/day within +/-20% of the frozen baseline and
median inter-arrival not collapsed -> the change did not perturb cadence. With
--baseline, exits non-zero outside that band.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
import sys
from pathlib import Path

_PAUSE_GAP_S = 6 * 3600.0   # a gap longer than this is treated as a pause, not a cadence


def _ro(path: str) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def _db(name: str) -> str:
    from substrate.paths import db_paths  # resolve via substrate, never a literal path
    return str(db_paths()[name])


def load_fire_ts(days: int | None) -> list[float]:
    con = _ro(_db("dynamic"))
    try:
        if days:
            import time
            cutoff = time.time() - days * 86400
            rows = con.execute(
                "SELECT ts FROM fountain_events WHERE ts > ? ORDER BY ts ASC",
                (cutoff,),
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT ts FROM fountain_events ORDER BY ts ASC").fetchall()
    finally:
        con.close()
    return [float(r[0]) for r in rows if r[0] is not None]


def measure(days: int | None) -> dict:
    ts = load_fire_ts(days)
    n = len(ts)
    if n < 2:
        return {"n_fires": n, "median_inter_arrival_min": None,
                "p90_inter_arrival_min": None, "active_fires_per_day": None,
                "raw_fires_per_day": None, "likely_pauses": 0,
                "paused_hours": 0.0, "span_days": 0.0}
    gaps = [b - a for a, b in zip(ts, ts[1:]) if b > a]
    active_gaps = [g for g in gaps if g <= _PAUSE_GAP_S]
    pauses = [g for g in gaps if g > _PAUSE_GAP_S]
    med = statistics.median(active_gaps) if active_gaps else statistics.median(gaps)
    p90 = (statistics.quantiles(active_gaps, n=10)[8]
           if len(active_gaps) >= 10 else (max(active_gaps) if active_gaps else med))
    span_days = (ts[-1] - ts[0]) / 86400.0
    return {
        "n_fires": n,
        "median_inter_arrival_min": round(med / 60.0, 2),
        "p90_inter_arrival_min": round(p90 / 60.0, 2),
        # downtime-robust active rate from the median gap:
        "active_fires_per_day": round(86400.0 / med, 2) if med > 0 else None,
        # naive rate (downtime-inflated) — for contrast only:
        "raw_fires_per_day": round(n / span_days, 2) if span_days > 0 else None,
        "likely_pauses": len(pauses),
        "paused_hours": round(sum(pauses) / 3600.0, 1),
        "span_days": round(span_days, 1),
    }


def _verdict(cur: dict, base: dict, band: float) -> tuple[bool, list[str]]:
    notes, ok = [], True
    b = base.get("active_fires_per_day")
    c = cur.get("active_fires_per_day")
    if b and c:
        ratio = c / b
        notes.append(f"  active fires/day: {b} -> {c}  ({(ratio-1)*100:+.1f}%)")
        if abs(ratio - 1.0) > band:
            ok = False
    bm, cm = base.get("median_inter_arrival_min"), cur.get("median_inter_arrival_min")
    if bm and cm:
        notes.append(f"  median inter-arrival (min): {bm} -> {cm}")
    return ok, notes


def main() -> int:
    ap = argparse.ArgumentParser(description="Fire-cadence harness (read-only).")
    ap.add_argument("--days", type=int, default=None, help="limit to the last N days (default: all history).")
    ap.add_argument("--freeze", metavar="PATH", help="write current measurement as a frozen baseline.")
    ap.add_argument("--baseline", metavar="PATH", help="compare against a frozen baseline.")
    ap.add_argument("--band", type=float, default=0.20, help="allowed +/- fraction on active fires/day (default 0.20).")
    args = ap.parse_args()

    cur = measure(args.days)
    print("=== fire cadence ===")
    print(f"fires: {cur['n_fires']}  span: {cur['span_days']}d  "
          f"(likely pauses: {cur['likely_pauses']}, {cur['paused_hours']}h paused)")
    print(f"median inter-arrival: {cur['median_inter_arrival_min']} min   "
          f"p90: {cur['p90_inter_arrival_min']} min")
    print(f"active fires/day (median-derived): {cur['active_fires_per_day']}   "
          f"raw fires/day (downtime-inflated): {cur['raw_fires_per_day']}")

    if args.freeze:
        Path(args.freeze).write_text(json.dumps(cur, indent=2), encoding="utf-8")
        print(f"\nfrozen baseline written to {args.freeze}")
        return 0
    if args.baseline:
        try:
            base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
        except Exception as e:
            print(f"\n[baseline] could not read {args.baseline}: {e}", file=sys.stderr)
            return 2
        ok, notes = _verdict(cur, base, args.band)
        print(f"\n=== vs baseline (band +/-{args.band:.0%}) ===")
        for ln in notes:
            print(ln)
        print("VERDICT:", "OK — cadence not perturbed" if ok else "PERTURBED — fire rate moved")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
