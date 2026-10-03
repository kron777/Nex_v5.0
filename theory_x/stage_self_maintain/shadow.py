"""Self-maintenance SHADOW regulator — Phase A (NEX5_SELF_MAINTAIN_SHADOW, default OFF).

Spec: nex5_research_log/self_maintenance_spec.txt (e24fbb1), section 6.

Every hour this computes what an active-set regulator WOULD do and writes one row
to dynamic.db self_maintain_shadow. It is log-only: it changes no belief, pauses
nothing, and nothing in NEX reads its table.

Active set A = beliefs with tier <= 6 AND paused = 0 (exactly what retrieval.py can
draw from). Setpoint S = median of A over the previous 7 days, from this table once
it holds >= 24 hourly rows, else from the internal.interoception snapshots
(hourly last value of tiers <= 6, minus beliefs paused today). The would-be action
is n = clamp(round(GAIN * (A - S)), 0, CAP); candidates are tier-6, unlocked,
unpaused, non-protected beliefs at least 48 h old, lowest confidence first.

It also records how many candidates sit in dormant_beliefs (the reanimation queue),
because the reanimation path injects beliefs WITHOUT a paused filter — the overlap
the live-phase spec has to resolve before anything is ever paused.

Fail-safe throughout: a failed tick logs and is skipped, never raises.
"""
from __future__ import annotations

import json
import logging
import statistics
import threading
import time
from collections import Counter
from typing import Optional

from theory_x.stage3_world_model.erosion import PROTECTED_SOURCES

log = logging.getLogger("theory_x.self_maintain.shadow")

GAIN = 0.1                  # would-pause per hour per belief of deviation
CAP = 50                    # max would-pause per hour
MIN_AGE_S = 48 * 3600       # never consider beliefs younger than 48 h
TICK_S = 3600
FIRST_DELAY_S = 600         # let boot settle before the first tick
WINDOW_S = 7 * 86400
MIN_HISTORY_HOURS = 24
VERSION = "phaseA-1"

_TABLE = (
    "CREATE TABLE IF NOT EXISTS self_maintain_shadow ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, "
    "active_count INTEGER NOT NULL, setpoint REAL, setpoint_source TEXT NOT NULL, "
    "deviation REAL, n_would_pause INTEGER NOT NULL, n_would_unpause INTEGER NOT NULL, "
    "candidate_ids TEXT NOT NULL DEFAULT '[]', candidate_conf_mean REAL, "
    "candidate_branch_mix TEXT NOT NULL DEFAULT '{}', "
    "candidate_source_mix TEXT NOT NULL DEFAULT '{}', "
    "n_in_dormant INTEGER NOT NULL DEFAULT 0, n_in_dormant_pending INTEGER NOT NULL DEFAULT 0, "
    "paused_total INTEGER NOT NULL, created_last_hour INTEGER NOT NULL, "
    "gain REAL NOT NULL, cap INTEGER NOT NULL, version TEXT NOT NULL)"
)


def would_pause_count(active: int, setpoint: Optional[float]) -> int:
    if setpoint is None:
        return 0
    return max(0, min(CAP, round(GAIN * (active - setpoint))))


def would_unpause_count(active: int, setpoint: Optional[float]) -> int:
    if setpoint is None:
        return 0
    return max(0, min(CAP, round(GAIN * (setpoint - active))))


class SelfMaintainShadow:
    def __init__(self, dynamic_writer, beliefs_reader, dynamic_reader, sense_reader):
        self._w = dynamic_writer
        self._br = beliefs_reader
        self._dr = dynamic_reader
        self._sr = sense_reader
        self._table_ready = False
        self._stop = threading.Event()

    # ---------------------------------------------------------------- setpoint
    def _setpoint(self, now: float) -> tuple[Optional[float], str]:
        own = self._dr.read(
            "SELECT active_count FROM self_maintain_shadow WHERE ts >= ?", (now - WINDOW_S,))
        if len(own) >= MIN_HISTORY_HOURS:
            return float(statistics.median(r["active_count"] for r in own)), "own_log"
        hourly: dict[int, int] = {}
        for r in self._sr.read(
                "SELECT timestamp, payload FROM sense_events "
                "WHERE stream = 'internal.interoception' AND timestamp >= ? ORDER BY timestamp",
                (now - WINDOW_S,)):
            try:
                tiers = json.loads(r["payload"])["tier_counts"]
                hourly[int(r["timestamp"]) // 3600] = sum(
                    v for k, v in tiers.items() if int(k) <= 6)
            except Exception:
                continue
        if len(hourly) < MIN_HISTORY_HOURS:
            return None, "insufficient"
        paused_le6 = self._br.read_one(
            "SELECT COUNT(*) AS n FROM beliefs WHERE tier <= 6 AND paused = 1")["n"]
        return float(statistics.median(hourly.values())) - paused_le6, "interoception"

    # -------------------------------------------------------------------- tick
    def tick(self, now: Optional[float] = None) -> Optional[dict]:
        now = time.time() if now is None else now
        if not self._table_ready:           # before _setpoint, which reads this table
            self._w.write(_TABLE, ())
            self._table_ready = True
        active = self._br.read_one(
            "SELECT COUNT(*) AS n FROM beliefs WHERE tier <= 6 AND paused = 0")["n"]
        setpoint, source = self._setpoint(now)
        n_pause = would_pause_count(active, setpoint)
        cands = []
        if n_pause > 0:
            marks = ",".join("?" * len(PROTECTED_SOURCES))
            cands = [dict(r) for r in self._br.read(
                "SELECT id, confidence, branch_id, source FROM beliefs "
                "WHERE tier = 6 AND paused = 0 AND locked = 0 AND created_at <= ? "
                f"AND (source IS NULL OR source NOT IN ({marks})) "
                "ORDER BY confidence ASC, created_at ASC LIMIT ?",
                (now - MIN_AGE_S, *sorted(PROTECTED_SOURCES), n_pause))]
        ids = [c["id"] for c in cands]
        in_dormant = pending = 0
        if ids:
            marks = ",".join("?" * len(ids))
            row = self._br.read_one(
                f"SELECT COUNT(*) AS n, SUM(reanimated_at IS NULL) AS p FROM dormant_beliefs "
                f"WHERE belief_id IN ({marks})", tuple(ids))
            in_dormant, pending = int(row["n"] or 0), int(row["p"] or 0)
        rec = {
            "ts": now, "active_count": active, "setpoint": setpoint, "setpoint_source": source,
            "deviation": None if setpoint is None else active - setpoint,
            "n_would_pause": len(ids), "n_would_unpause": would_unpause_count(active, setpoint),
            "candidate_ids": json.dumps(ids),
            "candidate_conf_mean": (sum(c["confidence"] or 0 for c in cands) / len(cands)) if cands else None,
            "candidate_branch_mix": json.dumps(Counter(c["branch_id"] or "?" for c in cands)),
            "candidate_source_mix": json.dumps(Counter(c["source"] or "?" for c in cands)),
            "n_in_dormant": in_dormant, "n_in_dormant_pending": pending,
            "paused_total": self._br.read_one("SELECT COUNT(*) AS n FROM beliefs WHERE paused = 1")["n"],
            "created_last_hour": self._br.read_one(
                "SELECT COUNT(*) AS n FROM beliefs WHERE created_at >= ?", (now - 3600,))["n"],
            "gain": GAIN, "cap": CAP, "version": VERSION,
        }
        cols = ", ".join(rec)
        self._w.write(
            f"INSERT INTO self_maintain_shadow ({cols}) VALUES ({', '.join('?' * len(rec))})",
            tuple(rec.values()))
        log.info("SELF-MAINTAIN SHADOW: A=%d S=%s (%s) would_pause=%d would_unpause=%d dormant_overlap=%d",
                 active, "-" if setpoint is None else f"{setpoint:.0f}", source,
                 rec["n_would_pause"], rec["n_would_unpause"], in_dormant)
        return rec

    # -------------------------------------------------------------------- loop
    def start_loop(self) -> None:
        def _run():
            if self._stop.wait(FIRST_DELAY_S):
                return
            while not self._stop.is_set():
                try:
                    self.tick()
                except Exception as e:      # never break NEX for a log row
                    log.warning("SELF-MAINTAIN SHADOW tick failed: %r", e)
                if self._stop.wait(TICK_S):
                    return
        threading.Thread(target=_run, name="SelfMaintainShadow", daemon=True).start()

    def stop(self) -> None:
        self._stop.set()
