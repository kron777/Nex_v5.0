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
DEDUP_HISTORY_SIZE = 15  # ~3 injections × 5 external slots; evicts oldest on overflow

# Streams exempt from dedup tracking. temporal changes every minute (always fresh),
# meta_awareness changes only when adapter count shifts. Neither wastes a history
# slot usefully — excluding them leaves room for slow-cadence external content.
DEDUP_EXCLUDED_STREAMS = {
    "internal.temporal",
    "internal.meta_awareness",
    # HN re-inserts the same top-stories on every poll cycle. Dedup
    # correctly blocks them as repeats; net effect is HN content rarely
    # reaches prompts despite being the freshest external stream.
    # Treat like internal.temporal — pass through, never tracked.
    "emerging_tech.hn",
}

# Phase C: payload body extraction
INCLUDE_BODIES = True               # flip False to revert to title-only
BODY_MAX_CHARS = 150                # per-event body truncation limit
TOTAL_INJECTION_CHAR_BUDGET = 1500  # cap on total chars injected per fountain fire
BODY_FIELDS = ("summary", "description", "abstract", "content", "snippet", "excerpt")

# Compiled once — used in _parse_payload
_ARXIV_BOILERPLATE = re.compile(
    r"^arXiv:\S+\s+Announce Type:\s+\w+\s*\n?Abstract:\s*", re.IGNORECASE
)
_HTML_TAG = re.compile(r"<[^>]+>")

QUALITATIVE_INTERNAL_STREAMS = {
    "internal.temporal",
    "internal.meta_awareness",
    "internal.proprioception",
    "internal.interoception",
}
NOISY_INTERNAL_STREAMS = {
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
        """Returns list of {stream, formatted_text, timestamp}, within char budget."""
        formatted = []
        budget = TOTAL_INJECTION_CHAR_BUDGET
        for ev in events:
            text = self._parse_payload(ev["stream"], ev.get("payload") or "")
            if not text:
                continue
            if len(text) > budget:
                break
            formatted.append({
                "stream": ev["stream"],
                "formatted_text": text,
                "timestamp": ev["timestamp"],
            })
            budget -= len(text)
        return formatted

    def _parse_payload(self, stream: str, payload: str) -> str:
        """
        Parse a sense event payload into a formatted injection line.
        Phase C: extracts title + truncated body when INCLUDE_BODIES is on.
        Returns empty string to skip the event.
        """
        prefix = self._stream_prefix(stream)

        if stream == "internal.temporal":
            try:
                data = json.loads(payload) if payload else {}
                iso = data.get("iso_local") or data.get("iso") or ""
                return f"[{prefix}] {iso}" if iso else ""
            except (json.JSONDecodeError, TypeError):
                return ""

        if stream == "internal.meta_awareness":
            try:
                data = json.loads(payload) if payload else {}
                count = data.get("sense_adapter_count")
                running = data.get("sense_global_running")
                if count is not None:
                    state = "running" if running else "idle"
                    return f"[{prefix}] {count} adapters {state}"
            except (json.JSONDecodeError, TypeError):
                pass
            return ""

        try:
            data = json.loads(payload) if payload else {}
        except (json.JSONDecodeError, TypeError):
            data = {}

        if not isinstance(data, dict):
            snippet = str(payload)[:80].replace("\n", " ").strip()
            return f"[{prefix}] {snippet}" if snippet else ""

        title = str(data.get("title") or data.get("name") or "").strip()

        body = ""
        if INCLUDE_BODIES:
            for field in BODY_FIELDS:
                val = data.get(field)
                if val:
                    body = str(val).strip()
                    if body:
                        break
            if body:
                body = _ARXIV_BOILERPLATE.sub("", body)
                body = _HTML_TAG.sub("", body)
                body = re.sub(r"\s+", " ", body).strip()
                if len(body) > BODY_MAX_CHARS:
                    body = body[:BODY_MAX_CHARS].rstrip() + "..."
                # Drop body if it's too short to add value or just echoes the title
                if len(body) < 15 or body.lower().startswith(title.lower()[:40]):
                    body = ""

        if title and body:
            return f"[{prefix}] {title} — {body}"
        if title:
            return f"[{prefix}] {title}"
        if body:
            return f"[{prefix}] {body}"

        url = str(data.get("url") or data.get("link") or "").strip()
        if url:
            return f"[{prefix}] {url[:150]}"

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
        """
        Fingerprint is the full formatted_text (title + body under Phase C).
        Two events with same title but different summaries get distinct fingerprints.
        """
        return event.get("formatted_text", "")

    def _dedup(self, formatted: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Drop events whose fingerprint was already injected recently.
        Streams in DEDUP_EXCLUDED_STREAMS always pass through and are
        never tracked — they either change on every fire (temporal) or
        their repetition is harmless (meta_awareness).
        """
        kept = []
        for ev in formatted:
            if ev.get("stream") in DEDUP_EXCLUDED_STREAMS:
                kept.append(ev)
                continue
            fp = self._event_fingerprint(ev)
            if fp and fp not in self._recent_fingerprints:
                kept.append(ev)
                self._recent_fingerprints.append(fp)
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
