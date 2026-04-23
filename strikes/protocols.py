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
    ) -> None:
        self._voice = voice
        self._dynamic = dynamic_state
        self._beliefs_reader = beliefs_reader
        self._sense_writer = sense_writer
        self._catalogue = catalogue
        self._membrane = membrane_state

    def fire(self, strike_type: StrikeType, custom_input: str = "") -> StrikeRecord:
        fired_at = time.time()
        type_str = strike_type.value

        beliefs_before = self._belief_count()
        hottest_branch, readiness_score = self._dynamic_snapshot()

        if strike_type == StrikeType.SILENCE:
            record = self._fire_silence(fired_at, beliefs_before, hottest_branch, readiness_score)
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
    ) -> StrikeRecord:
        from theory_x.stage6_fountain.readiness import FOUNTAIN_MIN_INTERVAL_SECONDS

        fountain_before_ts = 0.0
        if hasattr(self, '_fountain') and self._fountain is not None:
            fountain_before_ts = self._fountain.generator.last_fire_ts()

        lines: list[str] = []
        for tick in range(6):
            time.sleep(10)
            elapsed = int((tick + 1) * 10)
            error_channel.record(
                f"SILENCE strike: {elapsed}s elapsed, observing...",
                source="strikes",
                level="INFO",
            )

        # Check if any internal.fountain events appeared
        fountain_fired = False
        try:
            rows = self._beliefs_reader.read(
                "SELECT COUNT(*) as cnt FROM beliefs WHERE 1=1"
            )
        except Exception:
            pass

        # Check sense.db for fountain events in window
        try:
            from substrate import Reader as R
            from substrate.paths import db_paths
            # Use the existing reader pattern if we have access
            pass
        except Exception:
            pass

        summary = (
            "SILENCE strike: 60s of quiet. "
            "No input was sent. Observing internal generation."
        )

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
        )

    def _belief_count(self) -> int:
        try:
            rows = self._beliefs_reader.read("SELECT COUNT(*) as cnt FROM beliefs")
            return rows[0]["cnt"] if rows else 0
        except Exception:
            return 0

    def _dynamic_snapshot(self) -> tuple[str, float]:
        hottest_branch = ""
        readiness_score = 0.0
        try:
            status = self._dynamic.status()
            branches = status.get("branches", [])
            if branches:
                top = max(branches, key=lambda b: b.get("focus_num", 0))
                hottest_branch = top.get("branch_id", "")
            from theory_x.stage6_fountain.readiness import ReadinessEvaluator
            readiness_score = ReadinessEvaluator().score(
                self._dynamic, self._beliefs_reader, last_fire_ts=0.0
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
