"""
World Bridge — Phase A: Selection logger.

Per Design v0.2. Selects sense events that would be injected
into the fountain composition prompt. Phase A: logs only.
Phase B (future): inject into generator.py:604.

Selection algorithm:
  1. Active external + qualitative-internal streams in freshness window
  2. One event per stream, capped at 5
  3. Stream-type variety prioritization
  4. Format with minimal generic parser

Audit corrections applied:
  - timestamp column (not ts)
  - signals/log in beliefs.db (not dynamic.db)
  - Live cadence computation (no stored table)
  - crypto.* skipped (noise-filtered upstream and here)
  - internal.meta_awareness uses specific fields, not raw truncation
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import time
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

ENABLED = True
MAX_SELECTIONS = 5
DEFAULT_FRESHNESS_WINDOW_SECONDS = 600
CADENCE_MULTIPLIER = 5
CADENCE_LOOKBACK_SECONDS = 3600
DEDUP_HISTORY_SIZE = 40  # ~8 injections × 5 slots; evicts oldest on overflow

QUALITATIVE_INTERNAL_STREAMS = {
    "internal.temporal",
    "internal.meta_awareness",
}
NOISY_INTERNAL_STREAMS = {
    "internal.proprioception",
    "internal.interoception",
    "internal.fountain",
}
NOISE_PREFIX_PATTERN = re.compile(r"^(crypto\.|market\.)", re.IGNORECASE)


class WorldBridgeSelector:
    """
    Selects sense events for World Bridge injection.
    Phase A: select + log only, no prompt modification.
    """

    def __init__(
        self,
        sense_db_path: str,
        beliefs_db_path: str,
    ) -> None:
        self._sense_db = sense_db_path
        self._beliefs_db = beliefs_db_path
        self._recent_fingerprints: deque = deque(maxlen=DEDUP_HISTORY_SIZE)

    def select_and_log(
        self,
        fountain_event_id: Optional[int] = None,
        mark_injected: bool = False,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Run full pipeline: identify streams, pick events, format, log.
        Returns the selected event list, or None on failure.
        Failures do NOT raise — auxiliary subsystem.
        mark_injected=True records that these events were actually
        inserted into the composition prompt (Phase B+).
        """
        if not ENABLED:
            return None
        try:
            active_streams = self._identify_active_streams()
            if not active_streams:
                self._log_selection(
                    fountain_event_id=fountain_event_id,
                    selections=[],
                    streams_seen=[],
                    injected=False,
                    notes="no_active_streams",
                )
                return []

            raw_events = self._pick_events(active_streams)
            formatted = self._format_selections(raw_events)
            pre_dedup = len(formatted)
            formatted = self._dedup(formatted)
            skipped = pre_dedup - len(formatted)
            notes = f"ok_deduped_{skipped}" if skipped else "ok"
            self._log_selection(
                fountain_event_id=fountain_event_id,
                selections=formatted,
                streams_seen=[s["stream"] for s in active_streams],
                injected=mark_injected,
                notes=notes,
            )
            return formatted
        except Exception as e:
            logger.warning("WorldBridge selector error: %s", e)
            return None

    # ------------------------------------------------------------------ #
    # Stream identification                                                #
    # ------------------------------------------------------------------ #

    def _identify_active_streams(self) -> List[Dict[str, Any]]:
        """
        Find streams with a recent event inside their freshness window.
        Returns list of {stream, last_ts, freshness_window, cadence}.
        """
        now = time.time()
        cadences = self._compute_stream_cadences(now)

        try:
            with sqlite3.connect(self._sense_db, timeout=5) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT stream, MAX(timestamp) AS last_ts
                    FROM sense_events
                    WHERE timestamp > ?
                    GROUP BY stream
                    """,
                    (now - CADENCE_LOOKBACK_SECONDS,),
                ).fetchall()
        except Exception as e:
            logger.debug("WorldBridge: stream identification failed: %s", e)
            return []

        active = []
        for row in rows:
            stream = row["stream"]
            last_ts = row["last_ts"]

            if NOISE_PREFIX_PATTERN.match(stream):
                continue
            if stream in NOISY_INTERNAL_STREAMS:
                continue
            if stream.startswith("internal.") and stream not in QUALITATIVE_INTERNAL_STREAMS:
                continue

            cadence = cadences.get(stream, DEFAULT_FRESHNESS_WINDOW_SECONDS / CADENCE_MULTIPLIER)
            window = max(60, cadence * CADENCE_MULTIPLIER)

            if (now - last_ts) <= window:
                active.append({
                    "stream": stream,
                    "last_ts": last_ts,
                    "freshness_window": window,
                    "cadence": cadence,
                })

        return active

    def _compute_stream_cadences(self, now: float) -> Dict[str, float]:
        """
        Live cadence — same math as SilenceDetector.
        Returns mean inter-event gap per stream over last hour.
        """
        try:
            with sqlite3.connect(self._sense_db, timeout=5) as conn:
                rows = conn.execute(
                    """
                    SELECT stream, timestamp
                    FROM sense_events
                    WHERE timestamp > ?
                    ORDER BY stream, timestamp ASC
                    """,
                    (now - CADENCE_LOOKBACK_SECONDS,),
                ).fetchall()
        except Exception as e:
            logger.debug("WorldBridge: cadence calc failed: %s", e)
            return {}

        stream_times: Dict[str, List[float]] = defaultdict(list)
        for stream, ts in rows:
            stream_times[stream].append(ts)

        cadences: Dict[str, float] = {}
        for stream, times in stream_times.items():
            if len(times) < 2:
                continue
            gaps = [times[i + 1] - times[i] for i in range(len(times) - 1)]
            if gaps:
                cadences[stream] = max(1.0, sum(gaps) / len(gaps))

        return cadences

    # ------------------------------------------------------------------ #
    # Event picking                                                        #
    # ------------------------------------------------------------------ #

    def _pick_events(
        self, active_streams: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Latest event per active stream, capped at MAX_SELECTIONS.
        Soft variety: cap internal streams at 2 of 5.
        """
        # Freshest stream first
        sorted_streams = sorted(active_streams, key=lambda s: s["last_ts"], reverse=True)

        selected: List[Dict[str, Any]] = []
        internal_count = 0
        for s in sorted_streams:
            if len(selected) >= MAX_SELECTIONS:
                break
            is_internal = s["stream"].startswith("internal.")
            if is_internal and internal_count >= 2:
                continue
            selected.append(s)
            if is_internal:
                internal_count += 1

        events: List[Dict[str, Any]] = []
        try:
            with sqlite3.connect(self._sense_db, timeout=5) as conn:
                conn.row_factory = sqlite3.Row
                for s in selected:
                    row = conn.execute(
                        """
                        SELECT id, stream, timestamp, payload
                        FROM sense_events
                        WHERE stream = ?
                        ORDER BY timestamp DESC
                        LIMIT 1
                        """,
                        (s["stream"],),
                    ).fetchone()
                    if row:
                        events.append(dict(row))
        except Exception as e:
            logger.debug("WorldBridge: event fetch failed: %s", e)

        return events

    # ------------------------------------------------------------------ #
    # Formatting                                                           #
    # ------------------------------------------------------------------ #

    def _format_selections(
        self, events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Returns list of {stream, formatted_text, timestamp}."""
        formatted = []
        for ev in events:
            text = self._parse_payload(ev["stream"], ev.get("payload") or "")
            if text:
                formatted.append({
                    "stream": ev["stream"],
                    "formatted_text": text,
                    "timestamp": ev["timestamp"],
                })
        return formatted

    def _parse_payload(self, stream: str, payload: str) -> str:
        """
        Minimal generic parser per Design v0.2 Section 4 step 5.
        Returns formatted text, or empty string to skip.
        """
        prefix = self._stream_prefix(stream)
        try:
            data = json.loads(payload) if payload else {}
        except (json.JSONDecodeError, TypeError):
            data = {}

        # Stream-specific overrides for known internal structures
        if stream == "internal.temporal":
            iso = data.get("iso_local") or data.get("iso") or ""
            return f"[{prefix}] {iso}" if iso else ""

        if stream == "internal.meta_awareness":
            count = data.get("sense_adapter_count")
            running = data.get("sense_global_running")
            if count is not None:
                state = "running" if running else "idle"
                return f"[{prefix}] {count} adapters {state}"
            return ""

        # Generic: title > url/link > truncated raw
        if isinstance(data, dict):
            title = data.get("title") or data.get("name")
            url = data.get("url") or data.get("link")
            if title:
                return f"[{prefix}] {str(title)[:150]}"
            if url:
                return f"[{prefix}] {str(url)[:150]}"

        snippet = str(payload)[:80].replace("\n", " ").strip()
        return f"[{prefix}] {snippet}" if snippet else ""

    def _stream_prefix(self, stream: str) -> str:
        """Map stream name to readable bracket tag."""
        if stream.startswith("news."):
            return "news"
        if stream.startswith("emerging_tech."):
            return "tech"
        if stream.startswith("ai_research.") or stream.startswith("agi."):
            return "research"
        if stream.startswith("crypto."):
            return "crypto"
        if stream.startswith("cognition."):
            return "cognition"
        if stream.startswith("philosophy."):
            return "philosophy"
        if stream.startswith("science."):
            return "science"
        if stream.startswith("literature."):
            return "lit"
        if stream.startswith("mathematics."):
            return "math"
        if stream.startswith("computing."):
            return "computing"
        if stream == "internal.temporal":
            return "temporal"
        if stream == "internal.meta_awareness":
            return "awareness"
        return stream.split(".")[0]

    # ------------------------------------------------------------------ #
    # Dedup                                                               #
    # ------------------------------------------------------------------ #

    def _event_fingerprint(self, event: Dict[str, Any]) -> str:
        """Fingerprint is the formatted_text — same title = same fingerprint."""
        return event.get("formatted_text", "")

    def _dedup(self, formatted: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Drop events whose fingerprint was already injected recently.
        Updates _recent_fingerprints with kept events only.
        """
        kept = []
        for ev in formatted:
            fp = self._event_fingerprint(ev)
            if fp and fp not in self._recent_fingerprints:
                kept.append(ev)
        for ev in kept:
            self._recent_fingerprints.append(self._event_fingerprint(ev))
        return kept

    # ------------------------------------------------------------------ #
    # Logging                                                              #
    # ------------------------------------------------------------------ #

    def _log_selection(
        self,
        fountain_event_id: Optional[int],
        selections: List[Dict[str, Any]],
        streams_seen: List[str],
        injected: bool,
        notes: str,
    ) -> None:
        try:
            with sqlite3.connect(self._beliefs_db, timeout=5) as conn:
                conn.execute(
                    """
                    INSERT INTO world_bridge_log
                      (ts, fountain_event_id, selected_events_json,
                       selection_count, streams_seen, injected, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        time.time(),
                        fountain_event_id,
                        json.dumps(selections, default=str),
                        len(selections),
                        ",".join(streams_seen),
                        int(injected),
                        notes,
                    ),
                )
        except Exception as e:
            logger.warning("WorldBridge log write failed: %s", e)
