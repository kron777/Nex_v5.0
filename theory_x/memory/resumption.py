"""
Memory Layers — Layer B: Resumption seeder.

Per Design v0.2 Sections 5 + 5b.

On boot, reads state_snapshot.json from the previous session.
If recent (< 3 days old), promotes real prior beliefs by
updating their created_at to now-1 second. This places NEX's
actual prior thoughts in the recent-context slot for the first
fountain tick post-restart.

Also re-issues pending probes from the previous session.

No synthesized beliefs. No ventriloquism. Real prior thoughts,
just promoted to recent. Verified: retrieval query in
generator.py orders by (created_at * boost_value) DESC,
so created_at is the only field that needs updating.
"""

from __future__ import annotations

import json
import logging
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

ENABLED = True
STALE_THRESHOLD_SECONDS = 3 * 24 * 3600  # 3 days
MAX_PROMOTED_BELIEFS = 5
MAX_PROBE_REISSUE = 3


class ResumptionSeeder:
    """
    Reads state_snapshot.json and promotes real prior beliefs
    to give NEX continuity across restarts. Runs once at boot,
    before the first fountain tick.
    """

    def __init__(
        self,
        beliefs_db_path: str,
        probes_db_path: str,
        snapshot_path: str,
    ) -> None:
        self._beliefs_db = beliefs_db_path
        self._probes_db = probes_db_path
        self._snapshot_path = Path(snapshot_path)
        self._consumed_path = Path(str(snapshot_path) + ".consumed")

    def run(self) -> Dict[str, Any]:
        """
        Execute the full resumption sequence.
        Returns a summary dict of what was done.
        Failures do NOT raise — auxiliary subsystem.
        """
        result: Dict[str, Any] = {
            "executed": False,
            "snapshot_found": False,
            "stale": False,
            "promoted_count": 0,
            "probes_reissued": 0,
            "error": None,
        }

        if not ENABLED:
            result["error"] = "disabled"
            return result

        try:
            if not self._snapshot_path.exists():
                logger.info("Resumption: no prior snapshot, cold start")
                return result

            result["snapshot_found"] = True
            data = self._read_snapshot()
            if data is None:
                result["error"] = "snapshot read failed"
                return result

            age = time.time() - data.get("snapshot_ts", 0)
            if age > STALE_THRESHOLD_SECONDS:
                result["stale"] = True
                logger.info(
                    "Resumption: snapshot %.1fh old, exceeds 3-day threshold, cold start",
                    age / 3600,
                )
                self._consume_snapshot()
                return result

            belief_ids = data.get("recent_belief_ids", [])[:MAX_PROMOTED_BELIEFS]
            result["promoted_count"] = self._promote_beliefs(belief_ids)

            pending = data.get("pending_probes", [])[:MAX_PROBE_REISSUE]
            result["probes_reissued"] = self._reissue_probes(pending)

            self._consume_snapshot()
            result["executed"] = True

            logger.info(
                "Resumption: promoted %d beliefs, re-queued %d probes (snapshot age %.0fs)",
                result["promoted_count"],
                result["probes_reissued"],
                age,
            )

        except Exception as e:
            logger.warning("Resumption error: %s", e)
            result["error"] = str(e)

        return result

    def _read_snapshot(self) -> Optional[Dict[str, Any]]:
        try:
            with open(self._snapshot_path) as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Snapshot read failed: %s", e)
            return None

    def _promote_beliefs(self, belief_ids: List[int]) -> int:
        """
        Update created_at = now-1 for these belief IDs.
        Retrieval query orders by (created_at * boost_value) DESC,
        so this makes them win the recent-context slot first tick.
        """
        if not belief_ids:
            return 0
        try:
            now = int(time.time())
            placeholders = ",".join("?" * len(belief_ids))
            with sqlite3.connect(self._beliefs_db, timeout=5) as conn:
                cursor = conn.execute(
                    f"UPDATE beliefs SET created_at = ? WHERE id IN ({placeholders})",
                    (now - 1, *belief_ids),
                )
                return cursor.rowcount
        except Exception as e:
            logger.warning("Belief promotion failed: %s", e)
            return 0

    def _reissue_probes(self, pending: List[Dict[str, Any]]) -> int:
        """
        Mark pending probes as re-issued: bump asked_at to now
        and append a traceability note.
        """
        if not pending:
            return 0
        reissued = 0
        try:
            now = time.time()
            with sqlite3.connect(self._probes_db, timeout=5) as conn:
                for probe in pending:
                    probe_id = probe.get("id")
                    if probe_id is None:
                        continue
                    conn.execute(
                        """
                        UPDATE probes
                        SET asked_at = ?,
                            notes = COALESCE(notes, '') || ' [reissued_after_restart]'
                        WHERE id = ?
                        AND response_received_at IS NULL
                        """,
                        (now, probe_id),
                    )
                    reissued += 1
        except Exception as e:
            logger.warning("Probe re-issue failed: %s", e)
        return reissued

    def _consume_snapshot(self) -> None:
        """Rename snapshot to .consumed so it won't re-apply on next boot."""
        try:
            if self._consumed_path.exists():
                self._consumed_path.unlink()
            shutil.move(str(self._snapshot_path), str(self._consumed_path))
        except Exception as e:
            logger.warning("Snapshot consume failed: %s", e)
