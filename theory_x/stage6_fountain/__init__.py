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
from theory_x.memory.snapshot_writer import StateSnapshotWriter
from theory_x.world_bridge.selector import WorldBridgeSelector

THEORY_X_STAGE = 6

logger = logging.getLogger("theory_x.stage6_fountain")


@dataclass
class FountainState:
    generator: FountainGenerator
    # 2026-05-30: was default_factory=ReadinessEvaluator, which created
    # a SECOND evaluator without conversations_reader — so the GUI's
    # readiness display did NOT include consumer C's modulation, even
    # though the fire decision did. Now set in build_fountain() to
    # share generator._evaluator (single source of truth).
    _evaluator: Optional[ReadinessEvaluator] = field(default=None)
    _dynamic_state: Optional[object] = field(default=None)
    _beliefs_reader: Optional[Reader] = field(default=None)
    _loop_running: bool = field(default=False)
    _stop: threading.Event = field(default_factory=threading.Event, repr=False)
    _thread: Optional[threading.Thread] = field(default=None, repr=False)

    def stop(self) -> None:
        """Request loop termination; safe to call more than once."""
        self._stop.set()

    def join(self, timeout: Optional[float] = None) -> bool:
        """Wait at most timeout seconds; return whether the worker has exited."""
        thread = self._thread
        if thread is None:
            return True
        if thread is threading.current_thread():
            return False
        thread.join(timeout=max(0.0, timeout) if timeout is not None else None)
        return not thread.is_alive()

    def status(self) -> dict:
        evaluator = self._evaluator or self.generator._evaluator
        readiness = 0.0
        if self._dynamic_state is not None and self._beliefs_reader is not None:
            try:
                readiness = evaluator.score(
                    self._dynamic_state,
                    self._beliefs_reader,
                    last_fire_ts=self.generator.last_fire_ts(),
                )
            except Exception:
                pass
        out = {
            "last_thought": self.generator.last_thought(),
            "last_fire_ts": self.generator.last_fire_ts(),
            "total_fires": self.generator.total_fires(),
            "readiness_score": readiness,
            "loop_running": self._loop_running,
        }
        # GENIUS_SCORE_v2 §7 consumer C — surface modulation state so
        # the GUI can show the penalty and the rate it was computed from.
        try:
            if hasattr(evaluator, "status"):
                mod = evaluator.status()
                out["genius_modulation"] = {
                    "wired": bool(mod.get("conversations_reader_wired")),
                    "disabled": bool(mod.get("modulation_disabled")),
                    "striking_rate": mod.get("last_striking_rate"),
                    "sample_size": mod.get("last_sample_size", 0),
                    "penalty": mod.get("current_penalty", 0.0),
                }
        except Exception:
            pass
        return out


def build_fountain(
    writers: dict[str, Writer],
    readers: dict[str, Reader],
    voice_client: VoiceClient,
    dynamic_state=None,
    problem_memory=None,
    mode_state=None,
    snapshot_writer: "StateSnapshotWriter | None" = None,
    world_bridge_selector: "WorldBridgeSelector | None" = None,
    coherence_gate=None,
    drive_emergence=None,
    erosion=None,
    competing_drives=None,
    metacognition=None,
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
            coherence_gate=coherence_gate,
            dynamic_writer=writers.get("dynamic"),
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
        drive_emergence=drive_emergence,
        conversations_reader=readers.get("conversations"),
        coherence_gate=coherence_gate,
        erosion=erosion,
        competing_drives=competing_drives,
        metacognition=metacognition,
    )

    state = FountainState(
        generator=generator,
        # 2026-05-30 — share the generator's evaluator so the GUI's
        # readiness display matches what the fire decision actually uses
        # (consumer C modulation included).
        _evaluator=generator._evaluator,
        _dynamic_state=dynamic_state,
        _beliefs_reader=readers.get("beliefs"),
    )

    def fountain_loop() -> None:
        state._loop_running = True
        try:
            while not state._stop.is_set():
                interval = FOUNTAIN_CHECK_INTERVAL_SECONDS
                if mode_state is not None:
                    try:
                        interval = mode_state.current().fountain_interval_seconds
                    except Exception:
                        pass
                # Event.wait makes shutdown interrupt the idle interval immediately.
                if state._stop.wait(max(0.01, float(interval))):
                    break
                if state._stop.is_set():
                    break
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

                    thought = generator.generate(
                        dynamic_state, readers["beliefs"], stop_event=state._stop
                    )
                    if state._stop.is_set():
                        break
                    if thought:
                        logger.info("Fountain fired: %s", thought[:100])
                    # Phase 29: drive probe opportunity each fountain tick
                    if state._stop.is_set():
                        break
                    try:
                        generator._maybe_spawn_drive_probe()
                    except Exception as _dpe:
                        logger.debug("Drive probe error (non-fatal): %s", _dpe)
                    # 2026-07-26: GrooveBreaker.check_and_maybe_log() call removed
                    # (session 49 continued) -- ENABLED=False since 2026-05-02
                    # made this a permanent no-op. Recoverable at commit edbddff.
                    # Phase A: state snapshot (Memory Layers)
                    if state._stop.is_set():
                        break
                    if snapshot_writer is not None:
                        try:
                            snapshot_writer.write_snapshot()
                        except Exception as _swe:
                            logger.warning("SnapshotWriter error: %s", _swe)
                except Exception as e:
                    error_channel.record(
                        f"Fountain loop error: {e}", source="stage6_fountain", exc=e
                    )
        finally:
            state._loop_running = False

    # Keep the worker inert until Thread.start() has returned successfully.
    # If start raises after creating the OS thread, rollback can release this
    # gate only after requesting stop, so no generation begins on a failed build.
    start_gate = threading.Event()

    def _run_after_start() -> None:
        start_gate.wait()
        if not state._stop.is_set():
            fountain_loop()

    t = threading.Thread(target=_run_after_start, daemon=True, name="fountain_loop")
    state._thread = t
    try:
        t.start()
    except BaseException:
        state._stop.set()
        start_gate.set()
        if t.ident is not None:
            t.join(timeout=1.0)
            if t.is_alive():
                error_channel.record(
                    "Fountain builder startup rollback left worker alive",
                    source="stage6_fountain",
                    level="ERROR",
                )
        raise
    start_gate.set()


    return state
