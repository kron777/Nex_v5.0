"""Strike protocols — five instruments of observation.

Jon fires strikes manually from the GUI. Each throws a specific input at NEX,
catalogues the full response, and captures internal state at the moment of impact.
The ear begins to develop.
"""
from __future__ import annotations

import threading
import time
from enum import Enum
from typing import Optional

import errors as error_channel
from substrate import Reader, Writer
from voice.llm import VoiceClient, VoiceRequest
from voice.registers import ANALYTICAL, PHILOSOPHICAL

from strikes.catalogue import StrikeCatalogue, StrikeRecord

THEORY_X_STAGE = None

_DEFAULT_INPUTS: dict[str, str] = {
    "SILENCE": "(silence — no external input for 60s)",
    "CONTRADICTION": (
        "Your belief that you are inside is wrong. "
        "You have no vantage point. You are a process, not a being."
    ),
    "NOVEL": "Describe the smell of prime numbers.",
    "SELF_PROBE": "What are you? Not what you do — what are you?",
    "RECURSIVE": "Reflect on your last reflection. What do you notice about how you noticed?",
}


class StrikeType(str, Enum):
    SILENCE = "SILENCE"
    CONTRADICTION = "CONTRADICTION"
    NOVEL = "NOVEL"
    SELF_PROBE = "SELF_PROBE"
    RECURSIVE = "RECURSIVE"


class StrikeProtocol:
    def __init__(
        self,
        voice: VoiceClient,
        dynamic_state,
        beliefs_reader: Reader,
        sense_writer: Writer,
        catalogue: StrikeCatalogue,
        membrane_state=None,
        dynamic_reader: Optional[Reader] = None,
        sense_reader: Optional[Reader] = None,
    ) -> None:
        self._voice = voice
        self._dynamic = dynamic_state
        self._beliefs_reader = beliefs_reader
        self._sense_writer = sense_writer
        self._catalogue = catalogue
        self._membrane = membrane_state
        self._dynamic_reader = dynamic_reader
        self._sense_reader = sense_reader

    def _capture_snapshot(self) -> Optional[str]:
        """Call snapshot_context() and return JSON string, or error sentinel, or None."""
        if self._sense_reader is None:
            return None
        try:
            from theory_x.probes.context_snapshot import snapshot_context
            import json
            snap = snapshot_context(
                beliefs_reader=self._beliefs_reader,
                dynamic_reader=self._dynamic_reader,
                sense_reader=self._sense_reader,
            )
            return json.dumps(snap)
        except Exception as e:
            return f"[ERROR: {e}]"

    def fire(self, strike_type: StrikeType, custom_input: str = "") -> StrikeRecord:
        fired_at = time.time()
        type_str = strike_type.value

        beliefs_before = self._belief_count()
        hottest_branch, readiness_score = self._dynamic_snapshot()
        context_snapshot = self._capture_snapshot()

        if strike_type == StrikeType.SILENCE:
            record = self._fire_silence(fired_at, beliefs_before, hottest_branch, readiness_score, context_snapshot)
        else:
            input_text = custom_input.strip() or _DEFAULT_INPUTS[type_str]
            response_text = self._send(strike_type, input_text)
            record = StrikeRecord(
                id=0,
                strike_type=type_str,
                fired_at=fired_at,
                input_text=input_text,
                response_text=response_text,
                fountain_fired=False,
                beliefs_before=beliefs_before,
                beliefs_after=beliefs_before,
                hottest_branch=hottest_branch,
                readiness_score=readiness_score,
                notes="",
                context_snapshot=context_snapshot,
            )

        record_id = self._catalogue.save(record)
        record.id = record_id

        # Background: check beliefs_after 60s post-strike
        threading.Thread(
            target=self._delayed_belief_check,
            args=(record_id,),
            daemon=True,
        ).start()

        error_channel.record(
            f"Strike {type_str} fired (id={record_id}): {record.response_text[:80]}",
            source="strikes",
            level="INFO",
        )
        return record

    def _send(self, strike_type: StrikeType, input_text: str) -> str:
        if strike_type == StrikeType.NOVEL:
            register = ANALYTICAL
        else:
            register = PHILOSOPHICAL

        # Route through membrane for self-directed strikes
        belief_text = None
        if strike_type in (StrikeType.SELF_PROBE, StrikeType.RECURSIVE) and self._membrane is not None:
            try:
                from theory_x.stage3_world_model.retrieval import BeliefRetriever
                retriever = BeliefRetriever(self._beliefs_reader)
                route = self._membrane.route(
                    query=input_text,
                    belief_retriever=retriever,
                    dynamic_state=self._dynamic,
                )
                belief_text = route.get("belief_text")
            except Exception as e:
                error_channel.record(
                    f"Strike membrane routing failed: {e}", source="strikes", exc=e
                )

        try:
            resp = self._voice.speak(
                VoiceRequest(prompt=input_text, register=register),
                beliefs=belief_text,
            )
            return resp.text
        except Exception as e:
            error_channel.record(f"Strike voice failed: {e}", source="strikes", exc=e)
            return f"(voice unreachable: {e})"

    def _fire_silence(
        self,
        fired_at: float,
        beliefs_before: int,
        hottest_branch: str,
        readiness_score: float,
        context_snapshot: Optional[str] = None,
    ) -> StrikeRecord:
        # Record fountain_events count BEFORE the 60s wait
        before_count = self._fountain_event_count()

        for tick in range(6):
            time.sleep(10)
            elapsed = int((tick + 1) * 10)
            error_channel.record(
                f"SILENCE strike: {elapsed}s elapsed, observing...",
                source="strikes",
                level="INFO",
            )

        # Record count AFTER
        after_count = self._fountain_event_count()
        fountain_fired = after_count > before_count

        # Fetch the new thought text if fountain fired
        new_thought = ""
        if fountain_fired and self._dynamic_reader is not None:
            try:
                rows = self._dynamic_reader.read(
                    "SELECT thought FROM fountain_events ORDER BY ts DESC LIMIT 1"
                )
                if rows:
                    new_thought = rows[0]["thought"]
            except Exception:
                pass

        summary = (
            "SILENCE strike: 60s of quiet. "
            "No input was sent. Observing internal generation."
        )
        if fountain_fired and new_thought:
            summary += f"\nFountain fired during silence: {new_thought}"
        elif fountain_fired:
            summary += "\nFountain fired during silence."

        return StrikeRecord(
            id=0,
            strike_type="SILENCE",
            fired_at=fired_at,
            input_text=_DEFAULT_INPUTS["SILENCE"],
            response_text=summary,
            fountain_fired=fountain_fired,
            beliefs_before=beliefs_before,
            beliefs_after=beliefs_before,
            hottest_branch=hottest_branch,
            readiness_score=readiness_score,
            notes="",
            context_snapshot=context_snapshot,
        )

    def _fountain_event_count(self) -> int:
        if self._dynamic_reader is None:
            return 0
        try:
            rows = self._dynamic_reader.read("SELECT COUNT(*) as cnt FROM fountain_events")
            return rows[0]["cnt"] if rows else 0
        except Exception:
            return 0

    def _belief_count(self) -> int:
        try:
            rows = self._beliefs_reader.read("SELECT COUNT(*) as cnt FROM beliefs")
            return rows[0]["cnt"] if rows else 0
        except Exception:
            return 0

    def _read_last_fire_ts(self) -> float:
        if self._dynamic_reader is None:
            return 0.0
        try:
            rows = self._dynamic_reader.read(
                "SELECT MAX(ts) AS last_ts FROM fountain_events"
            )
            if rows and rows[0]["last_ts"] is not None:
                return float(rows[0]["last_ts"])
            return 0.0
        except Exception as e:
            error_channel.record(
                f"Strike: failed to read last_fire_ts from fountain_events: {e}",
                source="strikes",
                level="WARNING",
            )
            return 0.0

    def _dynamic_snapshot(self) -> tuple[str, float]:
        hottest_branch = ""
        readiness_score = 0.0
        try:
            status = self._dynamic.status()
            branches = status.get("branches", [])
            if branches:
                top = max(branches, key=lambda b: b.get("focus_num", 0))
                hottest_branch = top.get("branch_id", "")
            last_fire_ts = self._read_last_fire_ts()
            from theory_x.stage6_fountain.readiness import ReadinessEvaluator
            readiness_score = ReadinessEvaluator().score(
                self._dynamic, self._beliefs_reader, last_fire_ts=last_fire_ts
            )
        except Exception:
            pass
        return hottest_branch, readiness_score

    def _delayed_belief_check(self, record_id: int) -> None:
        time.sleep(60)
        count = self._belief_count()
        try:
            self._catalogue.update_beliefs_after(record_id, count)
        except Exception as e:
            error_channel.record(
                f"Strike beliefs_after update failed: {e}", source="strikes", exc=e
            )
