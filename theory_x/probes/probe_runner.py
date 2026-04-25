"""Run probes against NEX and capture responses + substrate state."""
from __future__ import annotations

import time
from typing import Optional

import requests

from substrate import Reader, Writer
from theory_x.probes.context_snapshot import snapshot_context

THEORY_X_STAGE = None

VOICE_ENDPOINT_DEFAULT = "http://localhost:8765/api/chat"

VALID_CATEGORIES = frozenset({
    "direct_phenomenology",
    "substitution",
    "translation",
    "recursive",
})


class ProbeRunner:
    def __init__(
        self,
        probes_writer: Writer,
        beliefs_reader: Reader,
        dynamic_reader: Reader,
        sense_reader: Reader,
        voice_endpoint: str = VOICE_ENDPOINT_DEFAULT,
    ):
        self._writer = probes_writer
        self._beliefs_reader = beliefs_reader
        self._dynamic_reader = dynamic_reader
        self._sense_reader = sense_reader
        self._voice_endpoint = voice_endpoint

    def run_probe(
        self,
        category: str,
        probe_text: str,
        notes: Optional[str] = None,
    ) -> dict:
        """Send probe to NEX, capture response + context, store everything."""
        if category not in VALID_CATEGORIES:
            raise ValueError(f"Unknown category: {category!r}. "
                             f"Must be one of: {sorted(VALID_CATEGORIES)}")

        asked_at = time.time()

        # Snapshot context BEFORE sending probe
        ctx_snapshot = snapshot_context(
            self._beliefs_reader,
            self._dynamic_reader,
            self._sense_reader,
        )

        # Send probe via NEX's existing chat endpoint
        try:
            resp = requests.post(
                self._voice_endpoint,
                json={"prompt": probe_text, "register": "Philosophical"},
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            response_text = data.get("response", "")
            response_mode = data.get("register", "unknown")
        except Exception as e:
            response_text = f"[ERROR: {e}]"
            response_mode = "error"

        response_received_at = time.time()
        latency_ms = int((response_received_at - asked_at) * 1000)

        # Write probe row
        probe_id = self._writer.write(
            "INSERT INTO probes "
            "(category, probe_text, response_text, response_mode, "
            "asked_at, response_received_at, response_latency_ms, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (category, probe_text, response_text, response_mode,
             asked_at, response_received_at, latency_ms, notes),
        )

        # Write context snapshot rows
        for key, value in ctx_snapshot.items():
            self._writer.write(
                "INSERT INTO probe_context (probe_id, snapshot_key, snapshot_value) "
                "VALUES (?, ?, ?)",
                (probe_id, key, str(value)),
            )

        return {
            "probe_id": probe_id,
            "category": category,
            "probe_text": probe_text,
            "response_text": response_text,
            "response_mode": response_mode,
            "latency_ms": latency_ms,
            "context": ctx_snapshot,
        }

    def add_tag(self, probe_id: int, tag: str) -> None:
        """Tag a probe (e.g. 'breakthrough', 'filler', 'novel_image')."""
        self._writer.write(
            "INSERT OR IGNORE INTO probe_tags (probe_id, tag) VALUES (?, ?)",
            (probe_id, tag),
        )

    def add_note(self, probe_id: int, note: str) -> None:
        """Append note to a probe (replaces existing)."""
        self._writer.write(
            "UPDATE probes SET notes=? WHERE id=?",
            (note, probe_id),
        )
