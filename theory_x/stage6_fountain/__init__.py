"""Theory X Stage 6 — Fountain Ignition."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

import errors as error_channel
from substrate import Reader, Writer
from voice.llm import VoiceClient

from theory_x.stage6_fountain.generator import FountainGenerator
from theory_x.stage6_fountain.readiness import (
    FOUNTAIN_CHECK_INTERVAL_SECONDS,
    ReadinessEvaluator,
)

THEORY_X_STAGE = 6

logger = logging.getLogger("theory_x.stage6_fountain")


@dataclass
class FountainState:
    generator: FountainGenerator
    _evaluator: ReadinessEvaluator = field(default_factory=ReadinessEvaluator)
    _dynamic_state: Optional[object] = field(default=None)
    _beliefs_reader: Optional[Reader] = field(default=None)
    _loop_running: bool = field(default=False)

    def status(self) -> dict:
        readiness = 0.0
        if self._dynamic_state is not None and self._beliefs_reader is not None:
            try:
                readiness = self._evaluator.score(
                    self._dynamic_state,
                    self._beliefs_reader,
                    last_fire_ts=self.generator.last_fire_ts(),
                )
            except Exception:
                pass
        return {
            "last_thought": self.generator.last_thought(),
            "last_fire_ts": self.generator.last_fire_ts(),
            "total_fires": self.generator.total_fires(),
            "readiness_score": readiness,
            "loop_running": self._loop_running,
        }


def build_fountain(
    writers: dict[str, Writer],
    readers: dict[str, Reader],
    voice_client: VoiceClient,
    dynamic_state=None,
) -> FountainState:
    generator = FountainGenerator(
        sense_writer=writers["sense"],
        dynamic_writer=writers["dynamic"],
        voice_client=voice_client,
        dynamic_reader=readers["dynamic"],
    )

    state = FountainState(
        generator=generator,
        _dynamic_state=dynamic_state,
        _beliefs_reader=readers.get("beliefs"),
    )

    def fountain_loop() -> None:
        state._loop_running = True
        while True:
            time.sleep(FOUNTAIN_CHECK_INTERVAL_SECONDS)
            try:
                if dynamic_state is None:
                    continue
                thought = generator.generate(dynamic_state, readers["beliefs"])
                if thought:
                    logger.info("Fountain: %s", thought[:100])
            except Exception as e:
                error_channel.record(
                    f"Fountain loop error: {e}", source="stage6_fountain", exc=e
                )

    t = threading.Thread(target=fountain_loop, daemon=True, name="fountain_loop")
    t.start()

    return state
