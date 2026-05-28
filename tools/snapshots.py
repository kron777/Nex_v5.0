#!/usr/bin/env python3
"""snapshots CLI — manual control over substrate_snapshots.

Usage:
    snapshots stats
    snapshots show <fountain_event_id>
    snapshots show-recent [--n N]
    snapshots score-pending [--limit N]
    snapshots prune [--commit]
    snapshots pin <fountain_event_id>
    snapshots unpin <fountain_event_id>
    snapshots delete <fountain_event_id>

Run from nex5 repo root: .venv/bin/python3 -m tools.snapshots <cmd>
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Make project importable from anywhere
_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from substrate.paths import db_paths
from substrate.reader import Reader
from substrate.writer import Writer
from theory_x.snapshots.snapshots import (
    capture_snapshot, score_pending_snapshots, prune_snapshots,
    pin_snapshot, unpin_snapshot, delete_snapshot, snapshot_stats,
    backfill_coherence,
)


def _get_rw():
    paths = db_paths()
    dyn = paths["dynamic"]
    return Reader(dyn), Writer(dyn)


def _fmt_ts(ts):
    if ts is None:
        return "—"
    return datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M:%S")


def _human_bytes(n):
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024.0
    return f"{n:.1f}TB"


def cmd_stats(args):
    reader, _ = _get_rw()
    s = snapshot_stats(reader)
    print("=== substrate_snapshots stats ===")
    print(f"  total:      {s['total']}")
    print(f"  genius:     {s['genius']}  (retention: forever)")
    print(f"  moment:     {s['moment']}  (retention: 90 days)")
    print(f"  ordinary:   {s['ordinary']}  (retention: 7 days)")
    print(f"  unscored:   {s['unscored']}")
    print(f"  pinned:     {s['pinned']}")
    print(f"  oldest:     {_fmt_ts(s['oldest_ts'])}")
    print(f"  newest:     {_fmt_ts(s['newest_ts'])}")
    # Estimate size: ~5KB per snapshot
    est_bytes = s['total'] * 5000
    print(f"  est. size:  {_human_bytes(est_bytes)} (~5KB/snapshot)")


def cmd_show(args):
    reader, _ = _get_rw()
    rows = reader.read(
        "SELECT s.*, f.thought, f.hot_branch, f.readiness "
        "FROM substrate_snapshots s "
        "JOIN fountain_events f ON s.fountain_event_id = f.id "
        "WHERE s.fountain_event_id = ?",
        (args.fountain_event_id,),
    )
    if not rows:
        print(f"No snapshot for fountain_event_id={args.fountain_event_id}")
        return 1
    r = rows[0]
    print(f"=== snapshot for fire #{r['fountain_event_id']} ===")
    print(f"  captured:       {_fmt_ts(r['ts'])}")
    print(f"  retention_tier: {r['retention_tier']}")
    print(f"  pinned:         {bool(r['pinned'])}")
    print(f"  coherence:      {r['coherence']}")
    print(f"  voltage:        {r['voltage']}")
    print(f"  walk_state:     {r['walk_state']}")
    print(f"  walk_anchor:    {r['walk_anchor_id']}")
    print(f"  groove_sev:     {r['groove_severity']}")
    print(f"  hot_branch:     {r['hot_branch']}")
    print(f"  thought: {r['thought'][:200]}")
    print()
    for k in ("drives_json", "hot_branches_json", "harmonic_pairs_json",
              "gate_composition_json"):
        try:
            d = json.loads(r[k]) if r[k] else {}
            if d:
                print(f"  {k.replace('_json','')}: {json.dumps(d, indent=2)[:400]}")
        except Exception:
            pass
    return 0


def cmd_show_recent(args):
    reader, _ = _get_rw()
    rows = reader.read(
        "SELECT s.fountain_event_id, s.ts, s.retention_tier, s.pinned, "
        "       s.coherence, s.walk_state, f.thought, f.hot_branch "
        "FROM substrate_snapshots s "
        "JOIN fountain_events f ON s.fountain_event_id = f.id "
        "ORDER BY s.ts DESC LIMIT ?",
        (args.n,),
    )
    if not rows:
        print("No snapshots yet.")
        return 0
    print(f"=== last {len(rows)} snapshots ===")
    for r in rows:
        pin = "📌" if r["pinned"] else "  "
        tier = (r["retention_tier"] or "—").ljust(8)
        coh = f"{r['coherence']:.3f}" if r["coherence"] is not None else "  —  "
        thought = (r["thought"] or "")[:80]
        print(f"  {pin} #{r['fountain_event_id']:<6} {_fmt_ts(r['ts'])} "
              f"{tier} coh={coh}  {thought}")
    return 0


def cmd_score_pending(args):
    reader, writer = _get_rw()
    print(f"Scoring up to {args.limit} pending snapshots...")
    counts = score_pending_snapshots(reader, writer, limit=args.limit)
    print(f"  genius:   {counts['genius']}")
    print(f"  moment:   {counts['moment']}")
    print(f"  ordinary: {counts['ordinary']}")
    if counts.get("errors", 0) > 0:
        print(f"  errors:   {counts['errors']}")


def cmd_backfill_coherence(args):
    reader, writer = _get_rw()
    print('Backfilling coherence + harmonic pairs...')
    out = backfill_coherence(reader, writer)
    print(f"  filled: {out['filled']}")
    print(f"  missed: {out['missed']}")
    if out.get('errors', 0) > 0:
        print(f"  errors: {out['errors']}")

def cmd_prune(args):
    reader, writer = _get_rw()
    mode = "COMMIT" if args.commit else "DRY-RUN"
    print(f"=== prune ({mode}) ===")
    result = prune_snapshots(reader, writer, commit=args.commit)
    word = "deleted" if args.commit else "would delete"
    print(f"  genius:   forever ({word}: 0)")
    print(f"  moment:   > 90d  {word}: {result['moment']}")
    print(f"  ordinary: > 7d   {word}: {result['ordinary']}")
    print(f"  pinned skipped:   {result['pinned_skipped']}")
    print(f"  pending unscored: {result['pending_unscored']}")
    if not args.commit and (result['moment'] + result['ordinary']) > 0:
        print()
        print("  Re-run with --commit to actually delete.")


def cmd_pin(args):
    _, writer = _get_rw()
    ok = pin_snapshot(args.fountain_event_id, writer)
    print(f"pin #{args.fountain_event_id}: {'OK' if ok else 'FAILED'}")


def cmd_unpin(args):
    _, writer = _get_rw()
    ok = unpin_snapshot(args.fountain_event_id, writer)
    print(f"unpin #{args.fountain_event_id}: {'OK' if ok else 'FAILED'}")


def cmd_delete(args):
    _, writer = _get_rw()
    confirm = input(f"Delete snapshot for fire #{args.fountain_event_id}? [y/N]: ")
    if confirm.strip().lower() != "y":
        print("Aborted.")
        return 1
    ok = delete_snapshot(args.fountain_event_id, writer)
    print(f"delete #{args.fountain_event_id}: {'OK' if ok else 'FAILED'}")
    return 0 if ok else 1


def main():
    p = argparse.ArgumentParser(prog="snapshots")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("stats")

    sp = sub.add_parser("show")
    sp.add_argument("fountain_event_id", type=int)

    sp = sub.add_parser("show-recent")
    sp.add_argument("--n", type=int, default=20)

    sp = sub.add_parser("score-pending")
    sp.add_argument("--limit", type=int, default=1000)

    sub.add_parser("backfill-coherence")
    sp = sub.add_parser("prune")
    sp.add_argument("--commit", action="store_true",
                    help="actually delete (default is dry-run)")

    sp = sub.add_parser("pin")
    sp.add_argument("fountain_event_id", type=int)

    sp = sub.add_parser("unpin")
    sp.add_argument("fountain_event_id", type=int)

    sp = sub.add_parser("delete")
    sp.add_argument("fountain_event_id", type=int)

    args = p.parse_args()
    rc = 0
    if   args.cmd == "stats":          cmd_stats(args)
    elif args.cmd == "show":           rc = cmd_show(args)
    elif args.cmd == "show-recent":    rc = cmd_show_recent(args)
    elif args.cmd == "score-pending":  cmd_score_pending(args)
    elif args.cmd == "backfill-coherence": cmd_backfill_coherence(args)
    elif args.cmd == "prune":          cmd_prune(args)
    elif args.cmd == "pin":            cmd_pin(args)
    elif args.cmd == "unpin":          cmd_unpin(args)
    elif args.cmd == "delete":         rc = cmd_delete(args)
    sys.exit(rc or 0)


if __name__ == "__main__":
    main()
