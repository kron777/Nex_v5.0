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
from theory_x.stage6_fountain.crystallizer import FountainCrystallizer
from theory_x.stage6_fountain.condenser import Condenser
from theory_x.stage6_fountain.readiness import (
    FOUNTAIN_CHECK_INTERVAL_SECONDS,
    ReadinessEvaluator,
)
from theory_x.auto_probe.groove_breaker import GrooveBreaker
from theory_x.memory.snapshot_writer import StateSnapshotWriter
from theory_x.world_bridge.selector import WorldBridgeSelector

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
    problem_memory=None,
    mode_state=None,
    groove_breaker: "GrooveBreaker | None" = None,
    snapshot_writer: "StateSnapshotWriter | None" = None,
    world_bridge_selector: "WorldBridgeSelector | None" = None,
) -> FountainState:
    crystallizer = None
    if writers.get("beliefs") and readers.get("beliefs"):
        crystallizer = FountainCrystallizer(
            beliefs_writer=writers["beliefs"],
            beliefs_reader=readers["beliefs"],
            conversations_reader=readers.get("conversations"),
            problem_memory=problem_memory,
            dynamic_reader=readers.get("dynamic"),
            mode_state=mode_state,
        )

    condenser = Condenser(voice_client=voice_client)

    generator = FountainGenerator(
        sense_writer=writers["sense"],
        dynamic_writer=writers["dynamic"],
        voice_client=voice_client,
        dynamic_reader=readers["dynamic"],
        beliefs_writer=writers.get("beliefs"),
        beliefs_reader=readers.get("beliefs"),
        crystallizer=crystallizer,
        problem_memory=problem_memory,
        sense_reader=readers.get("sense"),
        condenser=condenser,
        mode_state=mode_state,
        world_bridge_selector=world_bridge_selector,
        groove_breaker=groove_breaker,
    )

    state = FountainState(
        generator=generator,
        _dynamic_state=dynamic_state,
        _beliefs_reader=readers.get("beliefs"),
    )

    def fountain_loop() -> None:
        state._loop_running = True
        while True:
            interval = FOUNTAIN_CHECK_INTERVAL_SECONDS
            if mode_state is not None:
                try:
                    interval = mode_state.current().fountain_interval_seconds
                except Exception:
                    pass
            time.sleep(interval)
            try:
                if dynamic_state is None:
                    continue
                if mode_state is not None:
                    try:
                        if not mode_state.current().fountain_enabled:
                            logger.debug("Fountain suppressed by mode=%s", mode_state.current_name())
                            continue
                    except Exception:
                        pass

                # Diagnostic: log what the loop is deciding this tick
                try:
                    _readiness = generator._evaluator.score(
                        dynamic_state, readers["beliefs"],
                        last_fire_ts=generator.last_fire_ts(),
                    )
                    _elapsed = time.time() - generator.last_fire_ts()
                    _will_fire = generator._evaluator.is_ready(_readiness)
                    _mode_name = mode_state.current_name() if mode_state else "default"
                    logger.info(
                        "Fountain tick: readiness=%.2f interval=%ds elapsed=%.1fs "
                        "will_fire=%s mode=%s",
                        _readiness, interval, _elapsed, _will_fire, _mode_name,
                    )
                except Exception:
                    pass

                thought = generator.generate(dynamic_state, readers["beliefs"])
                if thought:
                    logger.info("Fountain fired: %s", thought[:100])
                # Phase A: passive groove observation
                if groove_breaker is not None:
                    try:
                        groove_breaker.check_and_maybe_log()
                    except Exception as _gbe:
                        logger.warning("GrooveBreaker error: %s", _gbe)
                # Phase A: state snapshot (Memory Layers)
                if snapshot_writer is not None:
                    try:
                        snapshot_writer.write_snapshot()
                    except Exception as _swe:
                        logger.warning("SnapshotWriter error: %s", _swe)
            except Exception as e:
                error_channel.record(
                    f"Fountain loop error: {e}", source="stage6_fountain", exc=e
                )

    t = threading.Thread(target=fountain_loop, daemon=True, name="fountain_loop")
    t.start()

    return state
