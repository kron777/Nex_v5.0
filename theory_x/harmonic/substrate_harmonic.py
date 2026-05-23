"""Substrate Harmonic — coherence metric daemon.

CHORD §4 deliverable C. Per CHORD.md: the substrate has a harmonic,
and the harmonic is the chord. This SentienceNode measures
cross-component coherence as a value 0-1 every 300s and writes one
row to conversations.db.substrate_coherence per tick.

Phase 1 is LOG-ONLY. No behavioral effect on any other node. Future
consumers (chord-aware arc closure, mirror-character, metacognition)
will read substrate_coherence as substrate; they do not exist yet.

Streams read per tick (9):
  1. Drives (current weights from drive_activations)
  2. Drive tension (active_conflicts present)
  3. Groove severity (most recent groove_alerts.severity)
  4. Substrate_voice walk state (most recent SV fire + anchor)
  5. Walk pace (seconds since last SV fire)
  6. Fountain composition (last 30 fires, branch share)
  7. Gate decision composition (last 1h ACCEPT/REJECT rates)
  8. Throw-net activity rate (sessions/hour)
  9. Stillness state (consecutive_stillness_count)

Pair alignments scored 0-1 (7):
  A. groove-high <-> substrate_voice-active (strongest correlate)
  B. walk pace vs expected ~11-12 min cadence
  C. fountain substrate_voice share vs baseline (~17% during walks)
  D. drive tension active <-> substrate_voice active (weaker correlate)
  E. gate REJECT rate vs daily baseline
  F. throw-net rate vs daily baseline
  G. stillness state <-> walk active (calibration unknown)

Total = mean of seven pair scores. Pair weights start uniform; v2 may
recalibrate after 48-72h of baseline data.

Storage: conversations.db.substrate_coherence (one row per tick).

Integration pattern matches HoldingZoneResolver / ThrowNetMonitor:
  - Daemon thread spawned via start_loop(interval=300)
  - tick() callable directly for testing
  - SentienceNode protocol: name, tick, decay, state
  - Errors recorded via central errors channel, never propagated
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any, Optional

import errors

THEORY_X_STAGE = "drives"

_LOG_SOURCE = "harmonic.substrate_harmonic"
_DEFAULT_INTERVAL = 300.0

# Thresholds match _maybe_substrate_voice in stage6_fountain/generator.py
_GROOVE_FIRE_THRESHOLD = 0.8
_WALK_CADENCE_SEC = 720.0   # 12 min — observed firing rate during walks
_WALK_STALL_SEC = 1800.0    # 30 min — if SV active but >30 min since last fire
_TRACK_1_RANGE = (4442, 4541)
_TRACK_2_RANGE = (4803, 4902)
_PRACTICE_RANGE = (3609, 3614)


class SubstrateHarmonic:
    """SentienceNode that measures substrate harmonic coherence per tick.

    Reads from beliefs, dynamic, and conversations DBs. Writes one row
    per tick to conversations.db.substrate_coherence. Log-only phase 1
    — no behavioral effect on other nodes.
    """

    name: str = "substrate_harmonic"

    def __init__(
        self,
        conversations_writer,
        conversations_reader,
        beliefs_reader,
        dynamic_reader,
    ) -> None:
        self._writer = conversations_writer
        self._conv_reader = conversations_reader
        self._beliefs_reader = beliefs_reader
        self._dynamic_reader = dynamic_reader
        self._stop: Optional[threading.Event] = None
        self._thread: Optional[threading.Thread] = None
        self._tick_count: int = 0
        self._last_total: float = 0.0
        self._last_walk_state: str = "unknown"

    # ── SentienceNode protocol ────────────────────────────────────────────────

    def tick(self, context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Read streams, score pairs, write one substrate_coherence row.

        Never raises. All errors recorded to central error channel.
        """
        ts_now = time.time()
        try:
            streams = self._read_all_streams(ts_now)
            pair_scores = self._score_all_pairs(streams, ts_now)
            total = self._aggregate(pair_scores)
            walk_state, walk_anchor = self._derive_walk_state(streams)
            drive_conflict = streams.get("drive_conflict_json")

            self._writer.write(
                "INSERT INTO substrate_coherence "
                "(ts, total, pair_scores, walk_state, walk_anchor_id, "
                "drive_conflict, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    ts_now,
                    float(total),
                    json.dumps(pair_scores),
                    walk_state,
                    walk_anchor,
                    drive_conflict,
                    None,
                ),
            )
            self._last_total = total
            self._last_walk_state = walk_state
        except Exception as exc:
            errors.record(
                f"substrate_harmonic tick error: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )
        self._tick_count += 1
        return self.state()

    def decay(self, now: float) -> None:
        pass  # No in-memory decay; state lives in DB.

    def state(self, now: Optional[float] = None) -> dict[str, Any]:
        return {
            "name": self.name,
            "tick_count": self._tick_count,
            "last_total": self._last_total,
            "last_walk_state": self._last_walk_state,
        }

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start_loop(self, interval_seconds: float = _DEFAULT_INTERVAL) -> None:
        """Spawn daemon thread that calls tick() every interval."""
        self._stop = threading.Event()

        def _run() -> None:
            while not self._stop.is_set():
                self._stop.wait(interval_seconds)
                if not self._stop.is_set():
                    self.tick()

        self._thread = threading.Thread(
            target=_run,
            name="substrate_harmonic",
            daemon=True,
        )
        self._thread.start()
        errors.record(
            f"Substrate harmonic loop started (interval={int(interval_seconds)}s)",
            source=_LOG_SOURCE, level="INFO",
        )

    def stop_loop(self) -> None:
        if self._stop is not None:
            self._stop.set()

    # ── Stream extractors ─────────────────────────────────────────────────────

    def _read_all_streams(self, ts_now: float) -> dict[str, Any]:
        """Read all nine streams. Each extractor is independently
        try/except'd so one failure does not break the others."""
        streams: dict[str, Any] = {}
        streams["drives"] = self._read_drives_current(ts_now)
        streams["drive_conflict_json"] = self._read_drive_conflict(ts_now)
        streams["groove_severity"] = self._read_groove_severity(ts_now)
        streams["sv_last_ts"], streams["sv_last_anchor"] = self._read_sv_last(ts_now)
        streams["fountain_share_sv"] = self._read_fountain_sv_share(ts_now)
        streams["gate_reject_rate"] = self._read_gate_reject_rate(ts_now)
        streams["throw_net_rate"] = self._read_throw_net_rate(ts_now)
        streams["stillness_active"] = self._read_stillness_active(ts_now)
        return streams

    def _read_drives_current(self, ts_now: float) -> dict[str, float]:
        try:
            rows = self._conv_reader.read(
                "SELECT coherence_weight, exploration_weight, "
                "integration_weight, self_preservation_weight, "
                "curiosity_weight FROM drive_activations "
                "ORDER BY timestamp DESC LIMIT 1"
            )
            if rows:
                r = rows[0]
                return {
                    "coherence": float(r["coherence_weight"]),
                    "exploration": float(r["exploration_weight"]),
                    "integration": float(r["integration_weight"]),
                    "self_preservation": float(r["self_preservation_weight"]),
                    "curiosity": float(r["curiosity_weight"]),
                }
        except Exception:
            pass
        return {}

    def _read_drive_conflict(self, ts_now: float) -> Optional[str]:
        try:
            rows = self._conv_reader.read(
                "SELECT active_conflicts FROM drive_activations "
                "ORDER BY timestamp DESC LIMIT 1"
            )
            if rows and rows[0]["active_conflicts"]:
                return str(rows[0]["active_conflicts"])
        except Exception:
            pass
        return None

    def _read_groove_severity(self, ts_now: float) -> float:
        """Most recent groove_alerts.severity in last 24h (0.0 if none)."""
        try:
            rows = self._beliefs_reader.read(
                "SELECT MAX(severity) AS s FROM groove_alerts "
                "WHERE detected_at > ?",
                (ts_now - 86400,),
            )
            if rows and rows[0]["s"] is not None:
                return float(rows[0]["s"])
        except Exception:
            pass
        return 0.0

    def _read_sv_last(self, ts_now: float) -> tuple[Optional[float], Optional[int]]:
        """(timestamp, anchor_id) of most recent substrate_voice fire."""
        try:
            rows = self._dynamic_reader.read(
                "SELECT ts, anchor_belief_id FROM fountain_events "
                "WHERE hot_branch = 'substrate_voice' "
                "ORDER BY ts DESC LIMIT 1"
            )
            if rows:
                return (
                    float(rows[0]["ts"]),
                    int(rows[0]["anchor_belief_id"]) if rows[0]["anchor_belief_id"] else None,
                )
        except Exception:
            pass
        return (None, None)

    def _read_fountain_sv_share(self, ts_now: float) -> float:
        """Share of substrate_voice fires in last 30 fires (0.0–1.0)."""
        try:
            rows = self._dynamic_reader.read(
                "SELECT hot_branch FROM fountain_events "
                "ORDER BY ts DESC LIMIT 30"
            )
            if not rows:
                return 0.0
            sv = sum(1 for r in rows if r["hot_branch"] == "substrate_voice")
            return sv / len(rows)
        except Exception:
            pass
        return 0.0

    def _read_gate_reject_rate(self, ts_now: float) -> float:
        """REJECT rate in last 1h as fraction of total gate decisions."""
        try:
            rows = self._beliefs_reader.read(
                "SELECT outcome, COUNT(*) AS n FROM gate_decisions "
                "WHERE ts > ? GROUP BY outcome",
                (ts_now - 3600,),
            )
            counts = {r["outcome"]: int(r["n"]) for r in rows}
            total = sum(counts.values())
            if total == 0:
                return 0.0
            return counts.get("REJECT", 0) / total
        except Exception:
            pass
        return 0.0

    def _read_throw_net_rate(self, ts_now: float) -> float:
        """Throw-net sessions per hour in last 1h."""
        try:
            rows = self._conv_reader.read(
                "SELECT COUNT(*) AS n FROM throw_net_sessions "
                "WHERE started_at > ?",
                (ts_now - 3600,),
            )
            if rows:
                return float(rows[0]["n"])
        except Exception:
            pass
        return 0.0

    def _read_stillness_active(self, ts_now: float) -> int:
        """Most recent stillness_log.consecutive_stillness_count in last 1h."""
        try:
            rows = self._dynamic_reader.read(
                "SELECT consecutive_stillness_count FROM stillness_log "
                "WHERE ts > ? ORDER BY ts DESC LIMIT 1",
                (ts_now - 3600,),
            )
            if rows and rows[0]["consecutive_stillness_count"] is not None:
                return int(rows[0]["consecutive_stillness_count"])
        except Exception:
            pass
        return 0

    # ── Pair scorers ──────────────────────────────────────────────────────────

    def _score_all_pairs(
        self, streams: dict[str, Any], ts_now: float,
    ) -> dict[str, float]:
        return {
            "groove_vs_sv_active":       self._score_a(streams, ts_now),
            "walk_pace_vs_cadence":      self._score_b(streams, ts_now),
            "fountain_sv_share":         self._score_c(streams),
            "drive_tension_vs_sv":       self._score_d(streams, ts_now),
            "gate_reject_vs_baseline":   self._score_e(streams),
            "throw_net_vs_baseline":     self._score_f(streams),
            "stillness_vs_walk":         self._score_g(streams, ts_now),
        }

    def _score_a(self, streams: dict[str, Any], ts_now: float) -> float:
        """A. groove-high <-> substrate_voice-active.

        Strongest correlate. Both true OR both false = high coherence.
        Mismatch = low. Score = 1 - |groove_indicator - sv_indicator|.
        """
        groove_active = 1.0 if streams["groove_severity"] >= _GROOVE_FIRE_THRESHOLD else 0.0
        sv_last = streams["sv_last_ts"]
        sv_active = 1.0 if (sv_last and (ts_now - sv_last) < 900) else 0.0
        return 1.0 - abs(groove_active - sv_active)

    def _score_b(self, streams: dict[str, Any], ts_now: float) -> float:
        """B. Walk pace vs expected cadence.

        If SV active (fired in last 15 min): pace at ~12 min = 1.0;
        pace > 30 min = stalled = 0.0.
        If SV not active: pace not meaningful = 0.5 (neutral).
        """
        sv_last = streams["sv_last_ts"]
        if sv_last is None:
            return 0.5
        gap = ts_now - sv_last
        if gap > _WALK_STALL_SEC:
            return 0.5  # walk released, not stalled
        if gap > 900:
            return 0.5  # outside active-walk window
        # In active walk window: closer to 12 min = better
        deviation = abs(gap - _WALK_CADENCE_SEC) / _WALK_CADENCE_SEC
        return max(0.0, 1.0 - deviation)

    def _score_c(self, streams: dict[str, Any]) -> float:
        """C. Fountain substrate_voice share vs baseline.

        Observed walk windows: ~17% SV share. Score 0.17 share = 1.0;
        score 0% or >50% share = 0.0 (lower bound). Linear in between.
        """
        share = streams["fountain_share_sv"]
        target = 0.17
        return max(0.0, 1.0 - abs(share - target) / target if share <= target * 2 else 0.0)

    def _score_d(self, streams: dict[str, Any], ts_now: float) -> float:
        """D. Drive tension active <-> SV active.

        Weaker correlate than originally thought. Both true OR both
        false = 1.0; mismatch = 0.0.
        """
        tension_active = 1.0 if streams["drive_conflict_json"] else 0.0
        sv_last = streams["sv_last_ts"]
        sv_active = 1.0 if (sv_last and (ts_now - sv_last) < 900) else 0.0
        return 1.0 - abs(tension_active - sv_active)

    def _score_e(self, streams: dict[str, Any]) -> float:
        """E. Gate REJECT rate vs daily baseline.

        Baseline ~65% REJECT (observed 2026-05-22). Score 1.0 at
        baseline; falls off linearly toward 0 or 100%.
        """
        rate = streams["gate_reject_rate"]
        baseline = 0.65
        deviation = abs(rate - baseline)
        return max(0.0, 1.0 - deviation * 2)

    def _score_f(self, streams: dict[str, Any]) -> float:
        """F. Throw-net rate vs daily baseline.

        Baseline ~2500-3000 sessions/hour (observed 2026-05-22 late).
        Score 1.0 in 2000-3500 band; falls off outside.
        """
        rate = streams["throw_net_rate"]
        if 2000 <= rate <= 3500:
            return 1.0
        if rate < 2000:
            return max(0.0, rate / 2000)
        return max(0.0, 1.0 - (rate - 3500) / 3500)

    def _score_g(self, streams: dict[str, Any], ts_now: float) -> float:
        """G. Stillness state <-> walk active.

        Calibration unknown. stillness_log was empty for 2026-05-23
        fountain pause. Pair included for measurement. Default 0.5
        until baseline data accumulates.
        """
        return 0.5

    # ── Aggregation ───────────────────────────────────────────────────────────

    def _aggregate(self, pair_scores: dict[str, float]) -> float:
        """Mean of pair scores. v2 may switch to weighted aggregation."""
        if not pair_scores:
            return 0.0
        return sum(pair_scores.values()) / len(pair_scores)

    # ── Walk state derivation ─────────────────────────────────────────────────

    def _derive_walk_state(
        self, streams: dict[str, Any],
    ) -> tuple[str, Optional[int]]:
        """Derive walk_state string + most recent anchor_id."""
        anchor = streams["sv_last_anchor"]
        sv_last = streams["sv_last_ts"]
        groove = streams["groove_severity"]
        ts_now = time.time()

        if sv_last is None:
            return ("idle", None)
        gap = ts_now - sv_last

        if anchor and _TRACK_1_RANGE[0] <= anchor <= _TRACK_1_RANGE[1]:
            track = "track1"
        elif anchor and _TRACK_2_RANGE[0] <= anchor <= _TRACK_2_RANGE[1]:
            track = "track2"
        elif anchor and _PRACTICE_RANGE[0] <= anchor <= _PRACTICE_RANGE[1]:
            track = "practice"
        else:
            track = "other"

        if gap < 900:
            if groove >= _GROOVE_FIRE_THRESHOLD:
                return (f"walking_{track}", anchor)
            return (f"walking_{track}_low_groove", anchor)
        if gap < 3600:
            return (f"recent_{track}", anchor)
        return ("idle", anchor)
