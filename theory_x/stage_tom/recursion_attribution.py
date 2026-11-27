#!/usr/bin/env python3
"""Read-only viewer for Fountain's runtime-owned recursion attribution rows.

The Fountain runtime is the sole producer of `recursion_attrib` rows and writes
through its shared dynamic.db Writer. This sidecar must remain read-only: a
second process cannot safely create a competing Writer for the same database.
"""
from __future__ import annotations

import sys
import time

from substrate import Reader
from substrate.paths import db_paths


def _db(name: str) -> str:
    return str(db_paths()[name])


def sample():
    """Return the latest runtime-recorded sample without creating or writing."""
    try:
        row = Reader(_db("dynamic")).read_one(
            "SELECT ts, nudge_active, branch, branch_prev, moved "
            "FROM recursion_attrib ORDER BY ts DESC LIMIT 1"
        )
        return dict(row) if row else None
    except Exception:
        return None


def verdict():
    """Print the attribution verdict from rows recorded by the Fountain runtime."""
    try:
        rows = Reader(_db("dynamic")).read(
            "SELECT nudge_active, moved FROM recursion_attrib WHERE branch_prev != ''"
        )
    except Exception:
        rows = []
    act = [r["moved"] for r in rows if r["nudge_active"] == 1]
    inact = [r["moved"] for r in rows if r["nudge_active"] == 0]
    pa = sum(act) / len(act) if act else 0.0
    pi = sum(inact) / len(inact) if inact else 0.0
    print("=" * 56)
    print("L3 RECURSION TEETH — attribution verdict")
    print("=" * 56)
    print(f"  samples: {len(rows)}  (nudge-active={len(act)}, nudge-absent={len(inact)})")
    print(f"  P(move | nudge ACTIVE):  {pa:.3f}  ({sum(act)}/{len(act)})")
    print(f"  P(move | nudge ABSENT):  {pi:.3f}  ({sum(inact)}/{len(inact)})  <- baseline drift")
    print("-" * 56)
    if len(act) < 20 or len(inact) < 20:
        print("  VERDICT: INSUFFICIENT DATA — need >=20 of each. Let the soak gather.")
    elif pa > pi + 0.10:
        print(f"  VERDICT: TEETH CONFIRMED — nudge moves attention +{pa-pi:.3f} over baseline.")
        print("           L3_recursion has teeth. L4_stakes unblocked.")
    elif abs(pa - pi) <= 0.10:
        print("  VERDICT: COSMETIC — nudge ~= baseline drift. Recursion does NOT move")
        print("           attention. L4 stays gated; recursion needs real teeth first.")
    else:
        print(f"  VERDICT: NEGATIVE — nudge moves LESS than baseline ({pa-pi:+.3f}). Investigate.")
    print("=" * 56)
    return {"samples": len(rows), "active": len(act), "inactive": len(inact),
            "p_active": pa, "p_inactive": pi}


if __name__ == "__main__":
    if "--verdict" in sys.argv:
        verdict()
    elif "--watch" in sys.argv:
        print("[attrib] read-only: watching Fountain-owned samples — Ctrl-C to stop")
        last_ts = None
        while True:
            try:
                current = sample()
                if current and current["ts"] != last_ts:
                    print(
                        f"[attrib] ts={current['ts']:.3f} "
                        f"active={current['nudge_active']} "
                        f"branch={current['branch']} "
                        f"previous={current['branch_prev']} moved={current['moved']}"
                    )
                    last_ts = current["ts"]
                time.sleep(20)
            except KeyboardInterrupt:
                print("\n[attrib] stopped")
                break
            except Exception as exc:
                print(f"[attrib] err: {exc!r}")
                time.sleep(20)
    else:
        print("latest Fountain runtime sample:", sample())
        print("Use --watch to observe or --verdict to evaluate existing samples.")
