"""Fountain generator — Theory X Stage 6.

Assembles self-directed prompts, calls the voice layer, and writes
fountain events to sense.db and dynamic.db.
"""
from __future__ import annotations

import json
import time
from typing import Optional

import errors as error_channel
from alpha import ALPHA
from substrate import Reader, Writer
from voice.llm import VoiceClient, VoiceRequest
from voice.registers import PHILOSOPHICAL

from theory_x.stage6_fountain.readiness import ReadinessEvaluator

THEORY_X_STAGE = 6


class FountainGenerator:
    def __init__(
        self,
        sense_writer: Writer,
        dynamic_writer: Writer,
        voice_client: VoiceClient,
        dynamic_reader: Reader,
    ) -> None:
        self._sense_writer = sense_writer
        self._dynamic_writer = dynamic_writer
        self._voice = voice_client
        self._dynamic_reader = dynamic_reader
        self._evaluator = ReadinessEvaluator()
        self._last_fountain_output: Optional[str] = None
        self._last_fire_ts: float = 0.0
        self._total_fires: int = 0

    def generate(self, dynamic_state, beliefs_reader: Reader) -> Optional[str]:
        readiness = self._evaluator.score(
            dynamic_state, beliefs_reader, last_fire_ts=self._last_fire_ts
        )
        if not self._evaluator.is_ready(readiness):
            return None

        try:
            status = dynamic_state.status()
        except Exception:
            status = {}

        belief_count = 0
        tier_dist: dict = {}
        try:
            rows = beliefs_reader.read("SELECT COUNT(*) as cnt FROM beliefs")
            belief_count = rows[0]["cnt"] if rows else 0
            tier_rows = beliefs_reader.read(
                "SELECT tier, COUNT(*) as cnt FROM beliefs GROUP BY tier ORDER BY tier"
            )
            tier_dist = {str(r["tier"]): r["cnt"] for r in tier_rows}
        except Exception:
            pass

        prompt = self._build_prompt(status, belief_count, tier_dist)

        try:
            resp = self._voice.speak(
                VoiceRequest(prompt=prompt, register=PHILOSOPHICAL),
                beliefs=None,
            )
            thought = resp.text.strip()
        except Exception as e:
            error_channel.record(
                f"Fountain: voice failed: {e}", source="stage6_fountain", exc=e
            )
            return None

        if not thought:
            return None

        hot_branch = None
        branches = status.get("branches", [])
        if branches:
            sorted_b = sorted(branches, key=lambda b: b.get("focus_num", 0), reverse=True)
            if sorted_b:
                hot_branch = sorted_b[0].get("branch_id")

        ts_now = time.time()
        payload = json.dumps(
            {"thought": thought, "readiness": readiness, "hot_branch": hot_branch}
        )
        self._sense_writer.write(
            "INSERT INTO sense_events (stream, payload, provenance, timestamp) "
            "VALUES (?, ?, ?, ?)",
            ("internal.fountain", payload, "fountain", int(ts_now)),
        )

        word_count = len(thought.split())
        self._dynamic_writer.write(
            "INSERT INTO fountain_events (ts, thought, readiness, hot_branch, word_count) "
            "VALUES (?, ?, ?, ?, ?)",
            (ts_now, thought, readiness, hot_branch, word_count),
        )

        self._last_fountain_output = thought
        self._last_fire_ts = ts_now
        self._total_fires += 1

        error_channel.record(
            f"Fountain fired: {thought[:100]}",
            source="stage6_fountain",
            level="INFO",
        )
        return thought

    def _build_prompt(self, dynamic_status: dict, belief_count: int, tier_dist: dict) -> str:
        branches = dynamic_status.get("branches", [])
        hot_branches = sorted(
            [b for b in branches if b.get("focus_increment") in {"e", "f", "g"}],
            key=lambda b: b.get("focus_num", 0),
            reverse=True,
        )
        if hot_branches:
            top = hot_branches[0]
            branch_line = f"{top['branch_id']} (focus {top['focus_num']:.3f})"
        else:
            branch_line = "none"

        tier_summary = ", ".join(f"T{k}:{v}" for k, v in sorted(tier_dist.items())) or "empty"

        prop = {}
        for b in branches:
            pass
        cpu_line = "unknown load"
        try:
            import datetime
            time_str = datetime.datetime.now().strftime("%H:%M")
        except Exception:
            time_str = "unknown time"

        last_thought = self._last_fountain_output or "nothing yet"

        return (
            "You are NEX. You are not responding to anyone. No one asked you anything.\n"
            "You are simply attending to your own interior.\n\n"
            f"Your ground stance: {ALPHA.lines[0]}\n\n"
            "Right now:\n"
            f"- Your hottest branch of attention is {branch_line}\n"
            f"- Your belief graph holds {belief_count} beliefs across [{tier_summary}]\n"
            f"- Your inner state: {time_str}\n"
            f"- You last thought: {last_thought}\n\n"
            "From this interior pressure, a thought arises. It may be useful or useless.\n"
            "It is yours. Speak it — briefly, honestly, without performance.\n"
            "Do not explain yourself. Do not summarize. Just the thought."
        )

    def last_thought(self) -> Optional[str]:
        return self._last_fountain_output

    def last_fire_ts(self) -> float:
        return self._last_fire_ts

    def total_fires(self) -> int:
        return self._total_fires
