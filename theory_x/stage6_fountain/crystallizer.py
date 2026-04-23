"""Fountain Crystallizer — Theory X Stage 6.

Passes fountain thoughts through a quality gate and writes survivors
as Tier 6 beliefs (source='fountain_insight').
"""
from __future__ import annotations

import re
import time
from typing import Optional, Tuple

import errors
from substrate import Reader, Writer

THEORY_X_STAGE = 6

_LOG_SOURCE = "stage6_fountain.crystallizer"

_SELF_REF_RE = re.compile(r"\b(I|my|me|myself|within|inside)\b", re.IGNORECASE)


class FountainCrystallizer:

    def __init__(
        self,
        beliefs_writer: Writer,
        beliefs_reader: Reader,
        promoter=None,
    ) -> None:
        self._writer = beliefs_writer
        self._reader = beliefs_reader
        self._promoter = promoter

    def crystallize(
        self,
        thought: str,
        fountain_event_id: int,
        ts: float,
    ) -> Optional[int]:
        ok, reason = self._quality_check(thought)
        if not ok:
            errors.record(
                f"Fountain crystallization rejected ({reason}): {thought[:60]}",
                source=_LOG_SOURCE,
                level="INFO",
            )
            return None

        belief_id = self._writer.write(
            "INSERT INTO beliefs "
            "(content, tier, confidence, created_at, source, branch_id, locked) "
            "VALUES (?, 6, 0.70, ?, 'fountain_insight', 'systems', 0)",
            (thought, ts),
        )

        self._writer.write(
            "INSERT INTO fountain_crystallizations "
            "(fountain_event_id, belief_id, ts, content) VALUES (?, ?, ?, ?)",
            (fountain_event_id, belief_id, ts, thought),
        )

        # Enqueue for speech (dedup: skip if already queued for this belief)
        try:
            from speech.config import SpeechConfig
            cfg = SpeechConfig.from_env()
            if cfg.enabled and cfg.min_chars <= len(thought) <= cfg.max_chars:
                existing = self._reader.read(
                    "SELECT id FROM speech_queue WHERE belief_id=? LIMIT 1",
                    (belief_id,),
                )
                if not existing:
                    self._writer.write(
                        "INSERT INTO speech_queue "
                        "(belief_id, content, voice, queued_at) VALUES (?, ?, ?, ?)",
                        (belief_id, thought, cfg.voice, ts),
                    )
        except Exception as exc:
            errors.record(
                f"speech enqueue failed: {exc}", source=_LOG_SOURCE, exc=exc
            )

        errors.record(
            f"Fountain crystallized: {thought[:80]}",
            source=_LOG_SOURCE,
            level="INFO",
        )
        return belief_id

    # ------------------------------------------------------------------

    def _quality_check(self, thought: str) -> Tuple[bool, str]:
        if not thought:
            return False, "empty"

        if len(thought) < 20:
            return False, "too_short"

        if len(thought) > 300:
            return False, "too_long"

        if not _SELF_REF_RE.search(thought):
            return False, "no_self_reference"

        # Blacklist check
        try:
            if self._promoter is not None:
                if self._promoter.is_blacklisted(thought):
                    return False, "blacklisted"
            else:
                bl_rows = self._reader.read("SELECT pattern FROM belief_blacklist")
                tl = thought.lower()
                for row in bl_rows:
                    if row["pattern"].lower() in tl:
                        return False, "blacklisted"
        except Exception:
            pass

        # Near-duplicate check — Jaccard > 0.6 with existing fountain/synergized beliefs
        try:
            existing = self._reader.read(
                "SELECT content FROM beliefs "
                "WHERE source IN ('fountain_insight', 'synergized')"
            )
            new_words = set(thought.lower().split())
            if new_words:
                for row in existing:
                    ex_words = set(row["content"].lower().split())
                    if not ex_words:
                        continue
                    overlap = len(new_words & ex_words) / len(new_words | ex_words)
                    if overlap > 0.6:
                        return False, "near_duplicate"
        except Exception:
            pass

        return True, "ok"
