"""Downtime as an experienced event (round 11, item 1).

A restart is otherwise invisible to NEX: identity_log gives continuity WITHIN a
session but no record that it was ever OFF. The one thing the system could never
represent is its own discontinuity. This writes a durable, WITNESSED belief on each
boot describing the gap — offline_from/to, duration, reason, boot_count — so the
identity anchor can read across the gap instead of only within a session.

provenance=witnessed: downtime is OBSERVED about the self, not authored. The source
'self_downtime' is mapped to _WITNESSED in affinity_loop.PROVENANCE_BASE — an
unmapped eligible source is a hard STOP in the backfill GO/STOP rule, so it must be
classified explicitly.

Signals for offline_from (best-effort, in priority order):
  1. a clean STANDBY shutdown writes a precise marker (mark_clean_shutdown) ->
     offline_from exact, reason 'clean_standby'.
  2. no marker -> crash or keepalive hard-kill; fall back to the last
     state_snapshot.json mtime (the last-alive heartbeat), reason 'unclean'.
  3. no snapshot either -> first boot, nothing recorded.
The marker is CONSUMED (deleted) on boot, so the next boot without a fresh clean
shutdown is correctly read as unclean. Fail-safe throughout: any error degrades to
"nothing recorded", never raises into the boot path.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

_MARKER = "last_shutdown.json"
_BOOTCOUNT = "boot_count.json"
_MIN_GAP_S = 5          # ignore sub-5s blips (fast respawns, clock jitter)
SOURCE = "self_downtime"


def _p(data_dir, name: str) -> Path:
    return Path(data_dir) / name


def mark_clean_shutdown(data_dir, ts: float | None = None,
                        reason: str = "clean_standby") -> bool:
    """Record a precise clean-shutdown time. Called from the SIGTERM/STANDBY path."""
    ts = time.time() if ts is None else ts
    try:
        _p(data_dir, _MARKER).write_text(
            json.dumps({"ts": float(ts), "reason": reason}), encoding="utf-8"
        )
        return True
    except Exception:
        return False


def _read_marker(data_dir):
    try:
        d = json.loads(_p(data_dir, _MARKER).read_text(encoding="utf-8"))
        return float(d["ts"]), str(d.get("reason", "clean_standby"))
    except Exception:
        return None


def _consume_marker(data_dir) -> None:
    try:
        _p(data_dir, _MARKER).unlink()
    except OSError:
        pass


def _bump_boot_count(data_dir) -> int:
    n = 0
    try:
        n = int(json.loads(_p(data_dir, _BOOTCOUNT).read_text(encoding="utf-8"))["n"])
    except Exception:
        n = 0
    n += 1
    try:
        _p(data_dir, _BOOTCOUNT).write_text(json.dumps({"n": n}), encoding="utf-8")
    except Exception:
        pass
    return n


def _fmt_dur(s: float) -> str:
    s = int(s)
    if s < 90:
        return f"{s}s"
    if s < 5400:
        return f"{s // 60}m"
    if s < 172800:
        return f"{s // 3600}h{(s % 3600) // 60:02d}m"
    return f"{s // 86400}d{(s % 86400) // 3600:02d}h"


def _fmt_ts(ts: float) -> str:
    from nex_config import local_dt
    return local_dt(ts).strftime("%Y-%m-%d %H:%M")


def record_boot(beliefs_writer, data_dir, snapshot_path, now: float | None = None) -> dict:
    """Compute this boot's offline window and write one witnessed belief.

    Returns a dict describing what happened. Never raises — the boot path must not
    die because a self-observation could not be written.
    """
    now = time.time() if now is None else now
    boot_count = _bump_boot_count(data_dir)

    marker = _read_marker(data_dir)
    if marker is not None:
        offline_from, reason = marker
    else:
        try:
            offline_from = os.path.getmtime(snapshot_path)
            reason = "unclean"  # crash or keepalive hard-kill — no clean marker left
        except OSError:
            offline_from = None
            reason = "first_boot"
    _consume_marker(data_dir)

    if offline_from is None:
        return {"recorded": False, "reason": reason, "boot_count": boot_count}

    duration = now - offline_from
    if duration < _MIN_GAP_S:
        return {"recorded": False, "reason": "blip", "duration_s": duration,
                "boot_count": boot_count}

    content = (
        f"I was offline for {_fmt_dur(duration)} — from {_fmt_ts(offline_from)} "
        f"to {_fmt_ts(now)} ({reason}). This is boot #{boot_count}."
    )
    recorded = False
    try:
        beliefs_writer.write(
            "INSERT INTO beliefs "
            "(content, tier, confidence, created_at, source, branch_id, locked) "
            "VALUES (?, 6, 0.35, ?, ?, 'systems', 0)",
            (content, int(now), SOURCE),
        )
        recorded = True
    except Exception:
        recorded = False

    return {"recorded": recorded, "reason": reason, "offline_from": offline_from,
            "offline_to": now, "duration_s": duration, "boot_count": boot_count,
            "content": content}
