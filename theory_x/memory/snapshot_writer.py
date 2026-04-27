"""
Memory Layers — Layer A: State Snapshot Writer.

Per Design v0.2 Sections 4 + 8 Phase A.

Captures NEX state to a JSON file after each fountain fire and on graceful
shutdown. Does NOT do resumption (Layer B). Does NOT track important moments
(Layer C).

Phase A: pure observation. Snapshots accumulate; nothing reads them yet.
"""

from __future__ import annotations

import atexit
import json
import logging
import signal
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

ENABLED = True
SNAPSHOT_FILENAME = "state_snapshot.json"
TMP_SUFFIX = ".tmp"
RECENT_FIRES_LIMIT = 10
RECENT_GROOVE_ALERTS_LIMIT = 5
RECENT_BELIEF_IDS_LIMIT = 5
PENDING_PROBE_RECENCY_SECONDS = 3600


class StateSnapshotWriter:
    """
    Writes NEX state to JSON after each fountain fire and on graceful shutdown.
    Phase A only — no read-back yet.
    """

    def __init__(
        self,
        beliefs_db_path: str,
        dynamic_db_path: str,
        probes_db_path: str,
        snapshot_dir: str,
    ):
        self._beliefs_db = beliefs_db_path
        self._dynamic_db = dynamic_db_path
        self._probes_db = probes_db_path
        self._snapshot_path = Path(snapshot_dir) / SNAPSHOT_FILENAME
        self._tmp_path = Path(str(self._snapshot_path) + TMP_SUFFIX)
        self._mode_state = None
        self._register_state: Dict[str, Any] = {}

        try:
            signal.signal(signal.SIGTERM, self._on_sigterm)
            atexit.register(self._on_atexit)
        except Exception as e:
            logger.warning("SnapshotWriter: signal handler setup failed: %s", e)

    def attach_mode_state(self, mode_state) -> None:
        """Inject mode_state from run.py after construction."""
        self._mode_state = mode_state

    def update_register_state(self, state: Dict[str, Any]) -> None:
        """Called by fountain after each fire to update register-run state."""
        self._register_state = state or {}

    def write_snapshot(self) -> bool:
        """
        Capture current state and write to JSON.
        Returns True on success, False on any failure.
        Failure does NOT raise — this is an auxiliary subsystem.
        """
        if not ENABLED:
            return False
        try:
            snapshot = self._build_snapshot()
            self._atomic_write(snapshot)
            return True
        except Exception as e:
            logger.warning("SnapshotWriter: write failed: %s", e)
            return False

    # ------------------------------------------------------------------ #
    # Private build methods                                                #
    # ------------------------------------------------------------------ #

    def _build_snapshot(self) -> Dict[str, Any]:
        return {
            "snapshot_ts": time.time(),
            "mode": self._fetch_mode(),
            "voice": self._fetch_voice(),
            "active_branches": self._fetch_active_branches(),
            "recent_fountain_fires": self._fetch_recent_fires(),
            "recent_groove_alerts": self._fetch_groove_alerts(),
            "pending_probes": self._fetch_pending_probes(),
            "register_run_state": dict(self._register_state),
            "active_unresolve_arc": None,
            "recent_belief_ids": self._fetch_recent_belief_ids(),
        }

    def _fetch_mode(self) -> str:
        if self._mode_state is not None:
            try:
                return self._mode_state.current_name()
            except Exception:
                pass
        try:
            with sqlite3.connect(self._beliefs_db, timeout=5) as conn:
                row = conn.execute(
                    "SELECT value FROM config WHERE key='current_mode'"
                ).fetchone()
            return row[0] if row else "mind"
        except Exception:
            return "mind"

    def _fetch_voice(self) -> str:
        try:
            with sqlite3.connect(self._beliefs_db, timeout=5) as conn:
                row = conn.execute(
                    "SELECT value FROM config WHERE key='current_voice'"
                ).fetchone()
            return row[0] if row else "af_sarah"
        except Exception:
            return "af_sarah"

    def _fetch_active_branches(self) -> List[Dict[str, Any]]:
        try:
            with sqlite3.connect(self._dynamic_db, timeout=5) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT name, curiosity_weight, last_attended_at
                    FROM bonsai_branches
                    ORDER BY curiosity_weight DESC
                    LIMIT 10
                    """
                ).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.debug("SnapshotWriter: branches fetch failed: %s", e)
            return []

    def _fetch_recent_fires(self) -> List[Dict[str, Any]]:
        try:
            with sqlite3.connect(self._dynamic_db, timeout=5) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT id, ts, hot_branch, thought, word_count
                    FROM fountain_events
                    WHERE hot_branch NOT IN ('voice_fallback', 'quiescent')
                    AND thought IS NOT NULL
                    ORDER BY ts DESC
                    LIMIT ?
                    """,
                    (RECENT_FIRES_LIMIT,),
                ).fetchall()
            result = [dict(r) for r in rows]
            for r in result:
                if r.get("thought"):
                    r["thought"] = r["thought"][:300]
            return result
        except Exception as e:
            logger.debug("SnapshotWriter: fires fetch failed: %s", e)
            return []

    def _fetch_groove_alerts(self) -> List[Dict[str, Any]]:
        try:
            with sqlite3.connect(self._beliefs_db, timeout=5) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT id, detected_at, alert_type, severity,
                           pattern, window_size
                    FROM groove_alerts
                    ORDER BY detected_at DESC
                    LIMIT ?
                    """,
                    (RECENT_GROOVE_ALERTS_LIMIT,),
                ).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.debug("SnapshotWriter: alerts fetch failed: %s", e)
            return []

    def _fetch_pending_probes(self) -> List[Dict[str, Any]]:
        """Per Design v0.2 Section 5b — probes that need re-issue on restart."""
        try:
            cutoff = time.time() - PENDING_PROBE_RECENCY_SECONDS
            with sqlite3.connect(self._probes_db, timeout=5) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT id, asked_at, category, response_mode, probe_text, notes
                    FROM probes
                    WHERE response_received_at IS NULL
                    AND asked_at IS NOT NULL
                    AND asked_at > ?
                    ORDER BY asked_at DESC
                    LIMIT 10
                    """,
                    (cutoff,),
                ).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.debug("SnapshotWriter: probes fetch failed: %s", e)
            return []

    def _fetch_recent_belief_ids(self) -> List[int]:
        """Belief IDs that Layer B will promote on restart."""
        try:
            with sqlite3.connect(self._beliefs_db, timeout=5) as conn:
                rows = conn.execute(
                    """
                    SELECT id FROM beliefs
                    WHERE source IN ('fountain_insight', 'synergized', 'auto_probe')
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (RECENT_BELIEF_IDS_LIMIT,),
                ).fetchall()
            return [r[0] for r in rows]
        except Exception as e:
            logger.debug("SnapshotWriter: belief ids fetch failed: %s", e)
            return []

    # ------------------------------------------------------------------ #
    # Atomic write + shutdown handlers                                     #
    # ------------------------------------------------------------------ #

    def _atomic_write(self, snapshot: Dict[str, Any]) -> None:
        """Write to .tmp then rename — avoids partial-write corruption."""
        self._snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._tmp_path, "w") as f:
            json.dump(snapshot, f, indent=2, default=str)
        self._tmp_path.replace(self._snapshot_path)

    def _on_sigterm(self, signum, frame) -> None:
        """Write final snapshot on graceful shutdown."""
        logger.info("SnapshotWriter: SIGTERM received, writing final snapshot")
        self.write_snapshot()
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.raise_signal(signal.SIGTERM)

    def _on_atexit(self) -> None:
        """Best-effort snapshot on Python exit."""
        try:
            self.write_snapshot()
        except Exception:
            pass
