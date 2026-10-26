#!/usr/bin/env python3
"""Backfill affinity under the provenance scorer (D-A, PR B part 2).

Recomputes beliefs.affinity for already-scored rows using the SAME scoring
functions the live loop calls (imported from theory_x.life.affinity_loop, never
reimplemented — so the dry-run validates the live scorer, not a copy), preserving
the old value in affinity_legacy and stamping affinity_model='prov_v1'.

SAFE BY DEFAULT. A bare invocation is a DRY RUN: it computes the new score for
every scored row, prints a per-source summary + a GO/STOP verdict, writes the full
(belief_id, source, usage, old, new) baseline to CSV, and exits 0 — touching
nothing. Writing requires BOTH `--apply` AND NEX5_AFFINITY_PROVENANCE=on, and the
--apply path REFUSES unless the same GO/STOP checks pass (override with --force).

The dry-run replaces the live shadow soak: shadow writes the OLD values and only
samples ~30 rows/tick, so it can neither judge the scoring over the whole
population nor show the downstream draw effect. The full-population dry-run judges
the scoring in one read-only pass; the downstream effect is validated post-apply by
comparing fountain draws before/after (owner-run, ~50 ticks each).

Rollback: `--rollback` (dry-run) shows what would be restored; `--rollback --apply`
executes `affinity := affinity_legacy` and clears the stamps for prov_v1 rows. Test
it against a COPY of the DB once before --apply so the undo is a known-good command.
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import sys
import time

from substrate import connect
from substrate.paths import DbPath
from theory_x.life.affinity_loop import (
    _provenance_affinity, _usage_score, PROVENANCE_BASE,
    _AUTHORED, _WITNESSED, _RECEIVED,
)

_MODEL_TAG = "prov_v1"
_BATCH = 500
FLOOR = 0.225
CEILING = 0.60
_EPS = 1e-6
_FC_DELTA_GATE = 0.10   # max allowed rise in floor/ceiling fraction (red flag 3)
_MEAN_SHIFT_WARN = 0.15  # per-source mean shift beyond this -> INVESTIGATE


def tier_of(source):
    """(tier_name, is_unmapped) for a source, matching the provenance bases."""
    base = PROVENANCE_BASE.get(source)
    unmapped = base is None
    if unmapped:
        base = _RECEIVED
    if base >= _AUTHORED - _EPS:
        return "authored", unmapped
    if base >= _WITNESSED - _EPS:
        return "witnessed", unmapped
    return "received", unmapped


def plan(cx):
    """Rows to migrate: affinity set but not yet stamped. Returns dicts with the
    usage_score and the new provenance score, computed by the live functions."""
    now = time.time()
    rows = cx.execute(
        """
        SELECT b.id, b.source,
               COALESCE(b.use_count, 0) AS use_count,
               b.last_referenced_at, b.affinity,
               (SELECT COUNT(*) FROM belief_edges WHERE source_id = b.id) AS edges_out
        FROM beliefs b
        WHERE b.affinity IS NOT NULL AND b.affinity_model IS NULL
        """
    ).fetchall()
    out = []
    for bid, source, use_count, last_ref, old_aff, edges_out in rows:
        hours_since = ((now - last_ref) / 3600) if last_ref else None
        usage = _usage_score(use_count, edges_out, hours_since)
        out.append({
            "id": bid, "source": source, "usage": usage,
            "old": old_aff, "new": _provenance_affinity(source, usage),
        })
    return out


def eligible_sources(cx):
    """Distinct sources across the affinity-eligible population (tier>=4, minus the
    sources _pick_candidates excludes). Used to catch sources that fall through to
    the 'received' default — the red flag the 30-row soak could never see."""
    rows = cx.execute(
        "SELECT DISTINCT source FROM beliefs "
        "WHERE tier >= 4 AND source NOT IN ('spectrum', 'demoted_confabulation')"
    ).fetchall()
    return [r[0] for r in rows]


def summarize(rows):
    """Per-source stats + overall floor/ceiling fractions."""
    by_src = {}
    for r in rows:
        s = by_src.setdefault(r["source"], {"olds": [], "news": [], "unmapped": False})
        s["olds"].append(r["old"])
        s["news"].append(r["new"])
        s["unmapped"] = tier_of(r["source"])[1]
    stats = {}
    for src, s in by_src.items():
        olds, news = s["olds"], s["news"]
        n = len(news)
        stats[src] = {
            "n": n,
            "mean_old": sum(olds) / n, "mean_new": sum(news) / n,
            "min_new": min(news), "max_new": max(news),
            "tier": tier_of(src)[0], "unmapped": s["unmapped"],
            "n_floor": sum(1 for v in news if abs(v - FLOOR) <= _EPS),
            "n_ceiling": sum(1 for v in news if abs(v - CEILING) <= _EPS),
        }
    n = len(rows) or 1
    frac = lambda vals, tgt: sum(1 for v in vals if abs(v - tgt) <= _EPS) / n
    overall = {
        "n": len(rows),
        "frac_old_floor": frac([r["old"] for r in rows], FLOOR),
        "frac_new_floor": frac([r["new"] for r in rows], FLOOR),
        "frac_old_ceiling": frac([r["old"] for r in rows], CEILING),
        "frac_new_ceiling": frac([r["new"] for r in rows], CEILING),
    }
    return stats, overall


def evaluate(rows, stats, overall, cx=None):
    """Beam's GO/STOP rule. Returns (verdict, reasons). verdict in
    GO / INVESTIGATE / STOP. The --apply path refuses on STOP unless --force."""
    stops, warns = [], []

    # Red flag 1 — unmapped sources (check the whole eligible population, not just
    # the rows being migrated): any source that silently defaults to 'received'.
    if cx is not None:
        unmapped = [s for s in eligible_sources(cx) if s not in PROVENANCE_BASE]
        if unmapped:
            stops.append(f"unmapped eligible sources -> silently 'received': {unmapped}")

    # Red flag 4 — NULL/NaN/out-of-envelope new values (a bug, not a judgement).
    bad = [r["id"] for r in rows
           if r["new"] is None or (isinstance(r["new"], float) and math.isnan(r["new"]))
           or r["new"] < FLOOR - _EPS or r["new"] > CEILING + _EPS]
    if bad:
        stops.append(f"{len(bad)} new values NULL/NaN/out of [{FLOOR},{CEILING}]: "
                     f"{bad[:10]}")

    # Red flag 2 — ordering must hold on real data (ranges are disjoint by design).
    tier_new = {"authored": [], "witnessed": [], "received": []}
    for r in rows:
        tier_new[tier_of(r["source"])[0]].append(r["new"])
    a, w, rc = tier_new["authored"], tier_new["witnessed"], tier_new["received"]
    if a and w and min(a) < max(w) - _EPS:
        stops.append(f"ordering: min(authored)={min(a):.4f} < max(witnessed)={max(w):.4f}")
    if w and rc and min(w) <= max(rc) + _EPS:
        stops.append(f"ordering: min(witnessed)={min(w):.4f} <= max(received)={max(rc):.4f}")

    # Red flag 3 — floor/ceiling fraction may not jump more than the gate.
    if overall["frac_new_floor"] > overall["frac_old_floor"] + _FC_DELTA_GATE:
        stops.append(f"floor fraction jumped {overall['frac_old_floor']:.3f} -> "
                     f"{overall['frac_new_floor']:.3f} (> +{_FC_DELTA_GATE})")
    if overall["frac_new_ceiling"] > overall["frac_old_ceiling"] + _FC_DELTA_GATE:
        stops.append(f"ceiling fraction jumped {overall['frac_old_ceiling']:.3f} -> "
                     f"{overall['frac_new_ceiling']:.3f} (> +{_FC_DELTA_GATE})")

    # Red flag 5 — large per-source mean shift is informational, not a stop.
    for src, st in stats.items():
        shift = st["mean_new"] - st["mean_old"]
        if abs(shift) > _MEAN_SHIFT_WARN:
            warns.append(f"source {src!r} mean shift {shift:+.3f}")

    verdict = "STOP" if stops else ("INVESTIGATE" if warns else "GO")
    return verdict, {"stop": stops, "warn": warns}


def write_baseline(rows, path):
    """Full per-row baseline CSV — the evidence artifact for post-apply verification
    and rollback (the 10-row console sample is only for eyeballing)."""
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["belief_id", "source", "usage_score", "affinity_old", "affinity_new"])
        for r in rows:
            w.writerow([r["id"], r["source"], f"{r['usage']:.6f}",
                        "" if r["old"] is None else f"{r['old']:.6f}",
                        f"{r['new']:.6f}"])
    return path


def _print_report(rows, stats, overall, verdict, reasons, baseline_path):
    print("[affinity backfill] DRY RUN — no changes written.")
    print(f"  rows to migrate (affinity set, affinity_model NULL): {overall['n']}")
    print(f"  batches of {_BATCH}: {(overall['n'] + _BATCH - 1) // _BATCH}")
    print(f"  baseline written: {baseline_path}")
    if stats:
        print("  per source  (tier | n | mean_old -> mean_new | new[min,max] | "
              "floor/ceil | unmapped):")
        for src in sorted(stats, key=lambda s: (stats[s]["tier"], -stats[s]["n"])):
            st = stats[src]
            print(f"    {src or '<null>':22s} {st['tier']:9s} n={st['n']:<6d} "
                  f"{st['mean_old']:.3f}->{st['mean_new']:.3f}  "
                  f"[{st['min_new']:.3f},{st['max_new']:.3f}]  "
                  f"fl={st['n_floor']} ce={st['n_ceiling']}"
                  f"{'  UNMAPPED' if st['unmapped'] else ''}")
    print(f"  floor frac  {overall['frac_old_floor']:.3f} -> {overall['frac_new_floor']:.3f}"
          f"   ceiling frac {overall['frac_old_ceiling']:.3f} -> {overall['frac_new_ceiling']:.3f}")
    print(f"  VERDICT: {verdict}")
    for s in reasons["stop"]:
        print(f"    STOP: {s}")
    for s in reasons["warn"]:
        print(f"    note: {s}")
    print("  to execute: --apply AND NEX5_AFFINITY_PROVENANCE=on (refused unless GO; "
          "override with --force)")


def apply(cx, rows, batch=_BATCH):
    """Write in batches (one BEGIN IMMEDIATE per batch). affinity_legacy is set with
    COALESCE so a re-run can never overwrite the rollback origin; the affinity_model
    IS NULL predicate makes a re-run a no-op. Returns rows actually updated."""
    now = time.time()
    written = 0
    for i in range(0, len(rows), batch):
        chunk = rows[i:i + batch]
        cx.execute("BEGIN IMMEDIATE")
        try:
            for r in chunk:
                cur = cx.execute(
                    "UPDATE beliefs SET "
                    "affinity_legacy = COALESCE(affinity_legacy, affinity), "
                    "affinity = ?, affinity_model = ?, affinity_updated_at = ? "
                    "WHERE id = ? AND affinity_model IS NULL",
                    (r["new"], _MODEL_TAG, now, r["id"]),
                )
                written += cur.rowcount
            cx.execute("COMMIT")
        except Exception:
            cx.execute("ROLLBACK")
            raise
    return written


def rollback(cx, apply_it):
    """Restore affinity from affinity_legacy and clear the stamps for prov_v1 rows.
    Dry-run unless apply_it. Returns the count (would-be, or actual)."""
    n = cx.execute(
        "SELECT COUNT(*) FROM beliefs "
        "WHERE affinity_model = ? AND affinity_legacy IS NOT NULL", (_MODEL_TAG,)
    ).fetchone()[0]
    if not apply_it:
        print(f"[affinity rollback] DRY RUN — would restore {n} rows "
              f"(affinity := affinity_legacy, clear stamps). Add --apply to execute.")
        return n
    cx.execute("BEGIN IMMEDIATE")
    try:
        cx.execute(
            "UPDATE beliefs SET affinity = affinity_legacy, "
            "affinity_model = NULL, affinity_legacy = NULL "
            "WHERE affinity_model = ? AND affinity_legacy IS NOT NULL", (_MODEL_TAG,)
        )
        cx.execute("COMMIT")
    except Exception:
        cx.execute("ROLLBACK")
        raise
    print(f"[affinity rollback] restored {n} rows.")
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description="Backfill affinity under provenance scorer")
    ap.add_argument("--db", default=None, help="beliefs DB path (default: resolved)")
    ap.add_argument("--apply", action="store_true",
                    help="actually write (also requires NEX5_AFFINITY_PROVENANCE=on)")
    ap.add_argument("--rollback", action="store_true",
                    help="restore affinity from affinity_legacy for prov_v1 rows")
    ap.add_argument("--force", action="store_true",
                    help="apply even if the GO/STOP rule says STOP (use with care)")
    ap.add_argument("--baseline", default="affinity_baseline.csv",
                    help="dry-run baseline CSV path")
    ap.add_argument("--batch", type=int, default=_BATCH)
    args = ap.parse_args(argv)

    db = args.db or str(DbPath("beliefs"))
    cx = connect(db, timeout=60)
    try:
        if args.rollback:
            return 0 if rollback(cx, args.apply) is not None else 1

        rows = plan(cx)
        stats, overall = summarize(rows)
        verdict, reasons = evaluate(rows, stats, overall, cx=cx)

        if not args.apply:
            path = write_baseline(rows, args.baseline)
            _print_report(rows, stats, overall, verdict, reasons, path)
            return 0

        if os.environ.get("NEX5_AFFINITY_PROVENANCE", "off").strip().lower() != "on":
            print("REFUSING --apply: NEX5_AFFINITY_PROVENANCE is not 'on'.",
                  file=sys.stderr)
            return 2
        if verdict == "STOP" and not args.force:
            print("REFUSING --apply: GO/STOP rule says STOP. Reasons:", file=sys.stderr)
            for s in reasons["stop"]:
                print(f"  - {s}", file=sys.stderr)
            print("  (re-run dry-run to inspect, or --force to override.)", file=sys.stderr)
            return 3
        predicted = len(rows)
        written = apply(cx, rows, batch=args.batch)
        print(f"[affinity backfill] migrated {written} rows (affinity_model={_MODEL_TAG}).")
        if written != predicted:
            print(f"WARNING: updated {written} != predicted {predicted} — the "
                  f"population moved between plan and apply; verify before trusting.",
                  file=sys.stderr)
            return 4
        return 0
    finally:
        cx.close()


if __name__ == "__main__":
    raise SystemExit(main())
